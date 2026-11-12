"""Owner-scoped planning facts and deterministic, evidence-limited suggestions."""
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from .models import PlanningState, IntegrationSnapshot, CheckIn, now


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class WorkWindow(Strict):
    kind: Literal['work', 'room', 'staff']
    name: str = Field(default='', max_length=300)
    start: datetime
    end: datetime

    @model_validator(mode='after')
    def valid(self):
        if self.start.tzinfo is None or self.end.tzinfo is None or not self.start < self.end:
            raise ValueError('Use an explicit timezone and an end after the start.')
        if self.end - self.start > timedelta(hours=24):
            raise ValueError('Enter individual work days, at most 24 hours per window.')
        if self.kind != 'work' and not self.name:
            raise ValueError('Room and staff windows need a name.')
        return self


class TaskFacts(Strict):
    task_id: str = Field(min_length=1, max_length=500)
    minutes: int | None = Field(default=None, ge=5, le=2400)
    actual_minutes: int | None = Field(default=None, ge=0, le=10000)
    dean: bool = False
    operational: bool = False
    room: str = Field(default='', max_length=300)
    employee: str = Field(default='', max_length=300)
    capability: str = Field(default='', max_length=1000)
    independent: bool = False
    supervision: bool = False
    blocker: str = Field(default='', max_length=2000)
    waiting_on: str = Field(default='', max_length=300)
    next_action: str = Field(default='', max_length=2000)
    next_check: date | None = None
    resume: str = Field(default='', max_length=2000)


class PlanningInput(Strict):
    expected_revision: int = Field(ge=0)
    workspace_id: str | None = Field(default=None, max_length=500)
    reserve_minutes: int = Field(default=240, ge=0, le=2400)
    priority_choice: str = Field(default='', max_length=500)
    priority_choice_date: date | None = None
    windows: list[WorkWindow] = Field(default_factory=list, max_length=300)
    tasks: list[TaskFacts] = Field(default_factory=list, max_length=1000)

    @model_validator(mode='after')
    def unique(self):
        if len({t.task_id for t in self.tasks}) != len(self.tasks):
            raise ValueError('Task facts must be unique.')
        return self


def state_view(session, owner):
    from .taskdock_api import active_snapshot
    row = session.get(PlanningState, owner)
    snapshot = active_snapshot(session, owner)
    workspace = snapshot.info.get('workspace_id') if snapshot else None
    data = {'reserve_minutes':240, 'priority_choice':'', 'priority_choice_date':None, 'windows':[], 'tasks':[]}
    if row: data.update(row.data)
    changed = bool(row and data.get('workspace_id') != workspace)
    if changed:
        # Never apply one workspace's estimates/capabilities to colliding task IDs in another.
        data.update(tasks=[], priority_choice='', priority_choice_date=None)
    data['workspace_id'] = workspace
    return {'revision':row.revision if row else 0, 'updated_at':row.updated_at if row else None,
            **data, 'source_notice':'TaskDock workspace changed; old task planning facts are excluded. Review and save new details.' if changed else ''}


def merge(intervals):
    result = []
    for a, b in sorted(intervals):
        if a >= b:
            continue
        if result and a <= result[-1][1]:
            result[-1] = (result[-1][0], max(b, result[-1][1]))
        else:
            result.append((a, b))
    return result


def intersect(left, right):
    return merge((max(a, c), min(b, d)) for a, b in left for c, d in right)


def subtract(intervals, busy):
    result = intervals
    for c, d in merge(busy):
        parts = []
        for a, b in result:
            if c >= b or d <= a:
                parts.append((a, b))
            else:
                if a < c: parts.append((a, c))
                if d < b: parts.append((d, b))
        result = parts
    return result


def stamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Unknown timezone')
    return dt.astimezone(timezone.utc)


def build_plan(session, owner, day, *, horizon_days=7, reserve_override=None):
    if not 2000 <= day.year <= 2100:
        raise HTTPException(422, 'Choose a planning date between 2000 and 2100.')
    from .taskdock_api import active_snapshot
    from .models import TaskDockState
    state = state_view(session, owner)
    from .schedules import schedule_intervals
    schedule_state, effective, schedule_notices = schedule_intervals(session, owner, day)
    zone = ZoneInfo('America/Chicago')
    left = datetime.combine(day, datetime.min.time(), zone).astimezone(timezone.utc)
    right = datetime.combine(day + timedelta(days=horizon_days), datetime.min.time(), zone).astimezone(timezone.utc)
    left = max(left, now())
    windows = state['windows']
    def spans(kind, name=''):
        return merge((max(left, stamp(w['start'])), min(right, stamp(w['end'])))
                     for w in windows if w['kind'] == kind and (kind == 'work' or w['name'].casefold() == name.casefold()))
    work = intersect(merge((a,b) for kind,name,a,b in effective if kind=='work'), [(left,right)])
    busy = []; rooms = {}; staff = {}; notices = []
    if state.get('source_notice'): notices.append(state['source_notice'])
    calendar_uncertain = False
    sources = session.scalars(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id == owner)).all()
    for source in sources:
        if source.details.get('active') is False: continue
        if source.kind not in ('calendar', 'google_calendar', 'outlook_calendar', 'schedules'): continue
        if source.kind != 'schedules' and (source.error or (now()-source.fetched_at).total_seconds()>86400):
            calendar_uncertain = True
        notices.append(f'{source.kind}: saved {source.fetched_at.isoformat()}' + ('; refresh failed' if source.error else '') + '; coverage may be incomplete')
        for item in source.items:
            try: a, b = stamp(item['start']), stamp(item['end'])
            except (KeyError, ValueError, TypeError): continue
            if a >= b: continue
            if item.get('kind') == 'classroom_busy':
                rooms.setdefault(str(item.get('location') or item.get('title', '')).casefold(), []).append((a,b))
            elif item.get('kind') == 'staff_available':
                staff.setdefault(str(item.get('title', '')).casefold(), []).append((a,b))
            elif item.get('busy') and item.get('status') != 'cancelled': busy.append((a,b))
    free = subtract(work, busy + [(a,b) for kind,name,a,b in effective if kind=='busy'])
    total = min(2400, int(sum((b-a).total_seconds()/60 for a,b in free)))
    reserve = state['reserve_minutes'] if reserve_override is None else reserve_override
    capacity = max(0, total - reserve)
    snapshot = active_snapshot(session, owner)
    tdstate = session.get(TaskDockState, owner)
    if snapshot is None: notices.append('No saved TaskDock tasks. Connect and refresh TaskDock first.')
    else:
        notices.append('TaskDock: saved '+snapshot.fetched_at.isoformat() + ('; refresh failed' if tdstate and tdstate.error else ''))
    if not work: notices.append('No confirmed work windows in this seven-day horizon. Availability is unknown.')
    if not busy: notices.append('No recorded busy intervals; this does not establish a complete calendar.')
    facts = {t['task_id']: t for t in state['tasks']}
    if snapshot and not snapshot.info.get('sharing_restricted'):
        from .dean_follow_up import reviewed_requests

        workspace = snapshot.info.get('workspace_id')
        for _, request in reviewed_requests(session, owner, day):
            if request['workspace_id'] != workspace or not request['task_id']:
                continue
            task_facts = facts.setdefault(request['task_id'], {})
            task_facts['dean'] = True
            if request['waiting_on'] and not task_facts.get('blocker'):
                task_facts['blocker'] = 'Waiting on ' + request['waiting_on']
    rows = []
    from .operations import briefing as operational_briefing
    operations = operational_briefing(session, owner)
    operational_tasks = {}
    for card in operations['cards']:
        for linked in card['tasks']: operational_tasks.setdefault(linked['task_id'], []).append(card)
    allocation_windows = {}
    stale_tasks = bool(snapshot and ((now()-snapshot.fetched_at).total_seconds()>86400 or (tdstate and tdstate.error)))
    availability_budget = {}
    candidates = list(snapshot.items) if snapshot else []
    candidates.sort(key=lambda t:(0 if facts.get(str(t.get('id')),{}).get('dean') else 1 if facts.get(str(t.get('id')),{}).get('operational') else 2, str(t.get('due_date') or '9999'), str(t.get('id'))))
    if len(candidates)>500: notices.append('Only the first 500 priority candidates are evaluated; this is not a complete task plan.')
    for task in candidates[:500]:
        if task.get('source_completed') is True or task.get('completed_at') or str(task.get('behavior','')).lower() in ('done','completed','archived'): continue
        identity = str(task['id']); f = facts.get(identity, {})
        estimate = f.get('minutes')
        # Deliberately broad starter estimate. Never infer hours from a title.
        suggested = estimate or 60
        missing = []
        if estimate is None: missing.append('Confirm duration: starter suggestion 30–90 minutes; scope is unknown.')
        available = free
        room = f.get('room', '')
        employee = f.get('employee', '')
        if room:
            from .schedules import availability
            slots = availability(session, owner, day, room, employee, suggested, f.get('supervision',False), (schedule_state,effective,schedule_notices), availability_budget)
            available = intersect([(stamp(w['start']),stamp(w['end'])) for w in slots['windows']], [(left,right)])
            missing.extend(slots['warnings'])
        elif employee:
            missing.append('Confirm the task room before planning employee work.')
        if employee and not f.get('supervision'):
            if not f.get('independent') or not f.get('capability'): missing.append('Confirm '+employee+' can do this independently, with supporting experience.')
        from .taskdock_planning import blockers,provided,fact,request_overview
        from .schedules import room_hint
        blocker = f.get('blocker') or blockers(task)
        if str(task.get('behavior', '')).lower() == 'waiting' and not blocker:
            blocker = 'TaskDock marks this task waiting; confirm the dependency.'
        if blocker: missing.append('Blocked: '+str(blocker))
        operational_reasons=[]
        for card in operational_tasks.get(identity,[]):
            if card['conflicts']:missing.extend(card['conflicts'])
            if card['stale']:missing.append('Refresh linked operational evidence before planning this repair.')
            if card['decision_authority']=='department_lead':missing.append('A department-lead decision is explicitly required; review it before repair allocation.')
            if card['service_impact']!='unknown':operational_reasons.append('Beacon reports service impact: '+card['service_impact'])
        if employee: operational_reasons.append('Capability uses your reviewed Juno facts; TaskDock qualifications are not supplied by the current read interface.')
        allocation_windows[identity]=available
        if calendar_uncertain: missing.append('Refresh the connected calendar: its saved copy is over 24 hours old or its last read failed.')
        if stale_tasks: missing.append('Refresh TaskDock: this copy is over 24 hours old or its last read failed.')
        start_date = str(task.get('start_date') or '')[:10]
        if start_date and start_date > str(day): missing.append('TaskDock start date is '+start_date+'; confirm before starting early.')
        slot = next(((a,b) for a,b in available if (b-a).total_seconds() >= suggested*60), None)
        if slot is None: missing.append('No confirmed uninterrupted window fits this estimate.')
        if (not employee or f.get('supervision')) and suggested > capacity: missing.append('Estimate exceeds remaining planning capacity.')
        due = str(task.get('due_date') or '')[:10]
        overdue = bool(due and due <= str(day))
        priority = task.get('priority')
        priority = priority if isinstance(priority, (int,float)) and not isinstance(priority,bool) else 9999
        rank = (0 if f.get('dean') else 1 if f.get('operational') else 2, 0 if overdue else 1, due or '9999', priority, identity)
        rows.append({**request_overview(task,snapshot.info,snapshot.fetched_at),'task_id':identity,'title':str(task.get('title') or 'Untitled task'),
                     'estimate_minutes':suggested,'estimate_confirmed':estimate is not None,
                     'estimate_reason':'Your saved estimate.' if estimate else 'Broad starter estimate, not calibrated; confirm scope before scheduling.',
                     'actual_minutes':f.get('actual_minutes'),'dean':f.get('dean',False),'operational':f.get('operational',False),
                     'blocker':str(blocker),'waiting_on':f.get('waiting_on',''),'next_action':f.get('next_action',''),
                     'next_check':f.get('next_check'),'resume':f.get('resume',''),'employee':employee,'room':room,
                     'room_hint':None if fact(task,'room').get('state')=='none' else room_hint(provided(task,'room')) or provided(task,'room') or room_hint(str(task.get('title',''))),
                     'supervision':f.get('supervision',False),'operational_reasons':operational_reasons,'missing':missing,'actionable':not missing,'slot_start':slot[0].isoformat() if slot and not missing else None,
                     'reason':'Dean request' if f.get('dean') else 'Teaching/operations need' if f.get('operational') else 'Due date and recorded TaskDock priority; impact needs your review.', '_rank':rank})
    rows.sort(key=lambda r:r['_rank'])
    for row in rows: del row['_rank']
    dean = next((r for r in rows if r['dean']),None)
    ops = next((r for r in rows if r['operational'] and not r['dean']),None)
    question = None
    choice = state.get('priority_choice') if state.get('priority_choice_date') == str(day) else None
    if dean and ops and choice in (dean['task_id'],ops['task_id']):
        chosen = next(r for r in rows if r['task_id']==choice)
        rows.remove(chosen);rows.insert(0,chosen)
        chosen['reason'] = 'Your confirmed priority choice for '+str(day)
    if dean and ops and choice not in (dean['task_id'],ops['task_id']):
        question = f'Would delaying “{ops["title"]}” disrupt teaching before “{dean["title"]}” needs to be done?'
    elif rows and rows[0]['missing']:
        top = rows[0]
        if top['blocker']:
            if not top['next_action']:
                question = 'What is the next useful action to unblock “'+top['title']+'” ('+top['blocker']+')?'
        else:
            question = 'For “'+top['title']+'”: '+top['missing'][0]
    recommended = None if question else next((r['task_id'] for r in rows if r['actionable']), None)
    loads = []
    for employee in sorted({r['employee'] for r in rows if r['employee']}):
        assigned = [r for r in rows if r['employee'] == employee]
        availability = intersect(merge((a,b) for kind,name,a,b in effective if kind=='staff_available' and name.casefold()==employee.casefold()), [(left,right)])
        profile = next((p for p in schedule_state['people'] if p['name'].casefold()==employee.casefold()),None)
        if profile and profile['status']!='active':availability=[]
        minutes = int(sum((b-a).total_seconds()/60 for a,b in availability))
        loads.append({'employee':employee, 'reported_assignment_minutes':sum(r['estimate_minutes'] for r in assigned if r['estimate_confirmed']),
            'unknown_estimates':sum(not r['estimate_confirmed'] for r in assigned), 'blocked_tasks':sum(bool(r['blocker']) for r in assigned),
            'available_minutes':minutes if availability else None,'weekly_limit_minutes':profile.get('weekly_limit_minutes') if profile else None,
            'notice':'Only the assignments and scheduled availability you supplied; not a complete workload or a performance measure.'})
    return {'day':str(day),'end':str(day+timedelta(days=horizon_days)),'generated_at':now(), 'revision':state['revision'],
            'capacity_minutes':capacity,'free_minutes':total,'reserve_minutes':reserve,
            'allocation_proposal':allocate_proposal([] if question else rows,allocation_windows,capacity,schedule_state),'staff_loads':loads,'question':question,'recommended_task_id':recommended,'tasks':rows[:500],'total_tasks':len(rows),'notices':notices,
            'notice':'Suggestions for one next task, not simultaneous assignments or a committed weekly schedule. Capacity capped at 40 hours before interruption reserve. Unknown or missing calendar events may reduce it. All TaskDock task changes remain in TaskDock.'}


def allocate_proposal(rows, windows, capacity, schedule_state):
    """Greedy ranked proposal, never a saved assignment or calendar booking."""
    occupied={};blocks=[];unplaced=[];owner_left=capacity;staff_used={}
    people={p['name'].casefold():p for p in schedule_state['people']}
    from .schedules import room_key
    for task in rows:
        if not task['actionable']:continue
        minutes=task['estimate_minutes'];employee=task['employee'].casefold()
        uses_owner=not employee or task.get('supervision',False)
        resources=(['owner'] if uses_owner else [])+(['staff:'+employee] if employee else [])+(['room:'+room_key(task['room'])] if task['room'] else [])
        busy=[span for key in resources for span in occupied.get(key,[])]
        possible=subtract(windows.get(task['task_id'],[]),busy)
        placed=False
        for start,end in possible:
            if (end-start).total_seconds()<minutes*60 or (uses_owner and minutes>owner_left):continue
            week=(start.astimezone(ZoneInfo('America/Chicago')).date()-timedelta(days=start.astimezone(ZoneInfo('America/Chicago')).weekday()))
            profile=people.get(employee)
            budget_key=(employee,str(week));limit=None
            if employee and profile:
                limit=min(profile['weekly_limit_minutes'],profile['desired_minutes'] if profile.get('desired_minutes') is not None else profile['weekly_limit_minutes'])
                weekstart=datetime.combine(week,datetime.min.time(),ZoneInfo('America/Chicago'));weekend=weekstart+timedelta(days=7)
                held=sum(max(0,(min(stamp(r['end']),weekend)-max(stamp(r['start']),weekstart)).total_seconds()/60) for r in schedule_state['reservations'] if r['employee'].casefold()==employee)
                if held+staff_used.get(budget_key,0)+minutes>limit:continue
            finish=start+timedelta(minutes=minutes)
            for key in resources:occupied.setdefault(key,[]).append((start,finish))
            if uses_owner:owner_left-=minutes
            if employee:staff_used[budget_key]=staff_used.get(budget_key,0)+minutes
            blocks.append({'task_id':task['task_id'],'title':task['title'],'employee':task['employee'],'room':task['room'],'start':start.isoformat(),'end':finish.isoformat(),'minutes':minutes})
            placed=True;break
        if not placed:unplaced.append({'task_id':task['task_id'],'reason':'No non-overlapping window remains within recorded capacity and weekly limits.'})
    return {'blocks':blocks,'unplaced':unplaced,'notice':'Coordinated proposal only. These blocks do not reserve rooms, assign staff or change TaskDock. Existing alternatives remain separate choices. Worker calendar/qualification coverage may be incomplete.'}


def weekly_draft(session, owner, day):
    from .planning_continuity import dean_check_in_lines, weekly_basis
    from .dean_follow_up import briefing_lines
    from .completion_archive import report_lines

    plan = build_plan(session, owner, day)
    rows = session.scalars(select(CheckIn).where(CheckIn.owner_id==owner, CheckIn.local_date>=day,
        CheckIn.local_date<day+timedelta(days=7), CheckIn.status=='confirmed').order_by(CheckIn.local_date)).all()
    lines = ['Weekly Dean update — draft', f'{day} through {day+timedelta(days=6)}', '', 'Confirmed daily records']
    for row in rows: lines.extend(dean_check_in_lines(row))
    if not rows: lines.append('No confirmed diary entries for this period; accomplishments are unknown.')
    follow_ups = briefing_lines(session, owner, day+timedelta(days=6))
    if follow_ups: lines.extend(['', 'Open requests from the Dean', *follow_ups])
    lines.extend(report_lines(session, owner, day, day+timedelta(days=6)))
    lines.extend(['', 'Priorities and blockers from the current saved task copy'])
    for t in plan['tasks'][:20]:
        entry = t['title'] + (' — waiting on '+t['blocker'] if t['blocker'] else ' — completion not established')
        if t['next_action']: entry += '. Next action: '+t['next_action']
        lines.append('• '+entry)
    lines.extend(['', 'Review dates, sensitive employee details and current status before sharing. This draft has not been sent.'])
    basis=weekly_basis(session,owner,day)
    missing=[str(day+timedelta(days=n)) for n in range(7) if str(day+timedelta(days=n)) not in {str(r.local_date) for r in rows}]
    lines.extend(['',str(len(rows))+' confirmed diary day(s); '+str(len(missing))+' date(s) without a confirmed diary. Missing dates do not establish inactivity.'])
    if basis['taskdock_uncertain']:lines.append('TaskDock context is missing, stale or its last read failed; current task status needs review.')
    from .operations import briefing as operational_briefing
    operations=operational_briefing(session,owner)
    lines.extend(['','Decisions and meeting agenda'])
    decisions=[c for c in operations['cards'] if c['decision_authority']=='department_lead']
    if not decisions:lines.append('No explicit department-lead decision requirement is established in the shared operational records; confirm missing authority.')
    for card in decisions:lines.append('• '+card['title']+': '+card['recommendation']+' [Beacon alert '+card['id']+']')
    lines.extend(['','Unresolved operational issues and source evidence'])
    for card in operations['cards'][:20]:
        lines.append('• '+card['title']+': '+card['next_action']+' [Beacon alert '+card['id']+']')
        for task in card['tasks']:lines.append('• TaskDock record '+task['task_id']+': '+task['title']+'; recorded completion does not verify equipment recovery.')
        for conflict in card['conflicts']:lines.append('• Review contradiction: '+conflict)
    lines.extend(operations['notices'])
    lines.extend(['','Milestones and next-week priorities','Milestone/project data is not supplied by the current TaskDock Juno contract. Review recorded due dates; no milestone completion is inferred.'])
    for task in plan['tasks'][:10]:
        lines.append('• '+task['title']+'; due '+str(task['due_date'] or 'unknown')+'; '+task['reason']+' [TaskDock record '+task['task_id']+']')
    lines.append('Discussion agenda: review explicit decisions, confirm blockers and missing evidence, then agree next-week priorities. Nothing has been sent.')
    return {'basis':basis,'missing_diary_dates':missing,'text':'\n'.join(lines),'diary_dates':[str(r.local_date) for r in rows], 'notices':plan['notices']}



def persist_planning(session, owner, value):
    row = session.get(PlanningState, owner)
    revision = row.revision if row else 0
    current = state_view(session, owner)
    if value.workspace_id != current['workspace_id']:
        raise HTTPException(409, 'TaskDock workspace changed. Reload and review before saving planning facts.')
    if value.expected_revision != revision:
        raise HTTPException(409, 'Planning facts changed on another device. Reload before saving; your draft remains here.')
    from .models import ScheduleState
    from .schedules import room_key
    recurring=session.get(ScheduleState,owner)
    if recurring:
        def groups(windows):
            result={}
            for w in windows:
                kind='staff_available' if w['kind']=='staff' else w['kind']
                name=room_key(w['name']) if kind=='room' else '' if kind=='work' else w['name'].casefold()
                result.setdefault(kind+'|'+name,[]).append((stamp(w['start']),stamp(w['end'])))
            return {k:merge(v) for k,v in result.items()}
        before=groups(row.data['windows'] if row else [])
        after=groups([w.model_dump(mode='json') for w in value.windows])
        if any(before.get(k,[])!=after.get(k,[]) for k in recurring.data.get('managed',[])):
            raise HTTPException(409,'These hours are managed by recurring schedules. Use Schedules to change them; task-detail edits can still be saved separately.')
    from .companion import invalidate_context
    invalidate_context(session, owner, 'planning:'+owner)
    data = value.model_dump(mode='json', exclude={'expected_revision'})
    if row is None:
        row=PlanningState(owner_id=owner, data=data, revision=1, updated_at=now());session.add(row)
    else: row.data=data;row.revision+=1;row.updated_at=now()

def install(app, db, device, lock_owner):
    @app.get('/v1/planning')
    def read(actor=Depends(device), session=Depends(db)):
        return state_view(session, actor.owner_id)

    @app.put('/v1/planning')
    def save(value:PlanningInput, actor=Depends(device), session=Depends(db)):
        lock_owner(session, actor.owner_id)
        persist_planning(session, actor.owner_id, value)
        session.commit()
        return state_view(session, actor.owner_id)

    app.state.save_planning = save

    @app.get('/v1/planning/next')
    def plan(day:date=Query(), actor=Depends(device), session=Depends(db)):
        return build_plan(session, actor.owner_id, day)

    @app.get('/v1/planning/check-in')
    def checkin(day:date=Query(), actor=Depends(device), session=Depends(db)):
        plan = build_plan(session, actor.owner_id, day)
        due = [t for t in plan['tasks'] if t['blocker'] and (not t['next_check'] or t['next_check'] <= str(day))]
        later = sum(1 for t in plan['tasks'] if t['blocker'] and t['next_check'] and t['next_check'] > str(day))
        records = session.scalars(select(CheckIn.local_date).where(CheckIn.owner_id==actor.owner_id,
            CheckIn.local_date>=day-timedelta(days=7), CheckIn.local_date<day, CheckIn.status=='confirmed')).all()
        return {'text':'Saved priorities: '+('; '.join(t['title'] for t in plan['tasks'][:3]) or 'none available')+
            '\nBlockers needing review: '+('; '.join(t['title']+': '+(t['next_action'] or t['blocker']) for t in due[:3]) or 'none recorded due')+
            f'\n{later} blocker(s) have a later check date; leave them unless something changed.'+
            f'\n{len(records)} confirmed diary day(s) in the previous seven days. Missing days are unknown, not evidence that work was not done.'+
            '\nWhat actually happened is yours to confirm. Unexpected work can displace the plan without blame.',
            'notices':plan['notices']}

    @app.get('/v1/planning/daily-brief')
    def daily_brief(day:date=Query(), actor=Depends(device), session=Depends(db)):
        from .daily_brief import briefing
        return briefing(session, actor.owner_id, day)

    @app.get('/v1/planning/weekly')
    def weekly(day:date=Query(), actor=Depends(device), session=Depends(db)):
        lock_owner(session,actor.owner_id)
        return weekly_draft(session, actor.owner_id, day)
