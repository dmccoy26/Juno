"""Leadership-focused Dean briefing with owner-reviewed continuing agenda topics."""
from copy import deepcopy
from datetime import date
import re
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import Field
from .models import OperationalState, PlanningState, now
from .planning import Strict

FORMAT = 'leadership-v1'
ROUTINE = re.compile(r'\b(?:printer|printing|MFP|LaserJet|C7000|P7570|Epson|toner|cartridge|ink|paper|staple|stapler|stacker|print test|pads|fuser)\b', re.I)
SYSTEMIC = re.compile(r'\b(?:campus.wide|fleet.wide|multiple classrooms|all classrooms|building.wide|department.wide|classroom unusable|class cancelled|classes cancelled)\b', re.I)
LEADERSHIP = re.compile(r'polic|training|manual|student.worker|office|classroom|wifi|wi.fi|wireless|seeds|technology.support.goals|leadership.council|labstats|jamf|remote.access|deep.freeze|network|licen[cs]|wacom|calibrat|computer.*replac|replac.*computer|cards?wipe|building.access|after.hours|instructor|teaching.station|lab\b', re.I)
PURCHASE = re.compile(r'\b(?:buy|purchase|order|quote|cost|budget|pcard|concur|replacement|replace|licen[cs]e)\b', re.I)

class Topic(Strict):
    title: str = Field(min_length=1,max_length=180)
    status: str = Field(default='In progress',min_length=1,max_length=100)
    detail: str = Field(default='',max_length=1600)
    category: Literal['progress','spending','blockers','decisions'] = 'progress'
    week: date | None = None

class AgendaSave(Strict):
    expected_revision: int = Field(ge=0)
    topics: list[Topic] = Field(max_length=24)


def agenda(session, owner):
    row=session.get(OperationalState,owner)
    data=(row.data if row else {}) or {}
    return {'revision':data.get('dean_agenda_revision',0),'topics':data.get('dean_agenda',[])}


def important(title, detail=''):
    # Individual consumables and device servicing stay in review evidence. A stated
    # multi-classroom outage remains eligible, even if its title mentions printing.
    return (not ROUTINE.search(title) or bool(SYSTEMIC.search(title+' '+detail))) and bool(LEADERSHIP.search(title+' '+detail) or SYSTEMIC.search(title+' '+detail))


def compose(session,owner,previous,cutoff,meeting,td,beacon,reasoning=None):
    from .planning_continuity import unfinished
    from .taskdock_planning import provided
    from .completion_archive import archive_source
    from .dean_follow_up import briefing_lines
    from .planning import stamp
    from .chairs_routing import field
    selected=(reasoning or {}).get('selected',{})
    def eligible(title,detail,ref):
        return important(title,detail) or (ref in selected and (not ROUTINE.search(title) or SYSTEMIC.search(title+' '+detail)))
    def clean(value):
        return ' '.join(re.sub(r'<[^>]*>',' ',str(value or '')).split())
    def bullet(title,detail=''):
        return '• '+clean(title)+((' — '+clean(detail)) if detail else '')
    def in_window(value):
        try:return previous<stamp(value)<=cutoff
        except (ValueError,TypeError,AttributeError):return False
    def unique(items):return list(dict.fromkeys(items))
    week=meeting.date().fromordinal(meeting.date().toordinal()-meeting.weekday())
    topics=[t for t in agenda(session,owner)['topics'] if not t.get('week') or t['week']==str(week)]
    progress=[];spending=[];blockers=[];classroom=[];decisions=[];completed=[]
    management_rooms=set();management_open=0;management_done=0;management_blocks=[];software=set();building_access=False
    def rooms_in(value):
        return set(re.findall(r'\b(?:A\d{3}|TH\d{3}|LIB\s*\d{3})',value.upper()))
    def management(title):return bool(re.search(r'jamf|deep.freeze|remote.access|remote.desktop|\bARD\b|check.in',title,re.I))
    def administration(title):return bool(re.search(r'integration check|synthetic test|test card|pilot|Juno|prepare.*meeting|compliance training|jamf 100|cert renewal|inventory.*office|office.*imac|cardswipe not approved',title,re.I))
    groups={'progress':progress,'spending':spending,'blockers':blockers,'decisions':decisions,'classroom':classroom}
    for t in topics:
        groups[t['category']].append(bullet(t['title'],t['status']+(('; '+t['detail']) if t.get('detail') else '')))
    for line in briefing_lines(session,owner,cutoff.date()):
        if not ROUTINE.search(line) or SYSTEMIC.search(line):decisions.append(line)
    state=session.get(PlanningState,owner)
    facts={t['task_id']:t for t in ((state.data if state else {}) or {}).get('tasks',[])}
    seen=set()
    for task in td.items:
        title=clean(task.get('title'))
        detail=clean(task.get('description'))
        ref='task:'+str(task['id'])
        if administration(title) or not eligible(title,detail,ref):continue
        seen.add(title.casefold())
        f=facts.get(str(task['id']),{})
        is_management=management(title)
        if is_management and unfinished(task):management_rooms.update(rooms_in(title+' '+str(f.get('room',''))))
        if in_window(task.get('completed_at')):
            if is_management:management_done+=1
            else:completed.append(bullet(title,'recorded complete during this reporting period'))
        elif unfinished(task):
            blocker=clean(f.get('blocker') or provided(task,'blockers') or task.get('blocked_reason'))
            waiting=clean(f.get('waiting_on'))
            action=clean(f.get('next_action'))
            if blocker or waiting:
                entry='; '.join(x for x in [blocker,('Waiting on '+waiting) if waiting else '',('Next: '+action) if action else ''] if x)
                if is_management:management_blocks.append(entry)
                else:blockers.append(bullet(title,entry))
            if is_management:
                management_open+=1
            elif PURCHASE.search(title) or re.search(r'\$\s*\d',title) or selected.get(ref)=='spending':
                amounts=re.findall(r'\$\s*\d[\d,]*(?:\.\d{2})?',title+' '+detail)
                spending.append(bullet(title,('Recorded amount: '+', '.join(dict.fromkeys(amounts))+'; approval and payment status not recorded') if amounts else 'Planned cost not recorded; confirm the estimate before requesting approval'))
            elif re.search(r'leadership.council',title,re.I):decisions.append(bullet(title,'Open follow-up'+(('; due '+str(task['due_date'])) if task.get('due_date') else '')))
            elif re.search(r'seeds|technology.support.goals',title,re.I):progress.append(bullet(title,'Open policy and planning follow-up'))
            elif re.search(r'wifi|wi.fi|wireless',title,re.I):classroom.append(bullet('Building wireless connectivity',title+'; confirm scope, teaching impact and the support plan'))
            elif re.search(r'cards?wipe|building.access|after.hours',title,re.I):building_access=True
            elif re.search(r'router',title,re.I):classroom.append(bullet('Shared network monitoring','Investigate the router load alert; service impact is not recorded'))
            elif re.search(r'labstats',title,re.I):software.add('LabStats')
            elif re.search(r'lab usage',title,re.I):software.add('classroom-use reporting')
            elif re.search(r'calibrat',title,re.I):software.add('display calibration')
            elif ref in selected and selected[ref] in groups:
                groups[selected[ref]].append(bullet(title,'Open; '+(('Next: '+action) if action else 'confirm next step and any decision needed')))
            elif not any(clean(t['title']).casefold() in title.casefold() or title.casefold() in clean(t['title']).casefold() or ('student worker' in title.casefold() and 'office' in title.casefold() and 'student worker' in t['title'].casefold()) for t in topics):
                classroom.append(bullet(title,('Next: '+action) if action else 'Open; confirm impact and next step'))
    if management_blocks:blockers.append(bullet('Classroom administrator and remote access', '; '.join(unique(management_blocks))))
    if management_open:classroom.append(bullet('Classroom computer management and remote access',f'{management_open} open follow-ups across '+(', '.join(sorted(management_rooms)) or 'the recorded instructor stations')+'. Confirm the affected classes and the support timeline'))
    if software:classroom.append(bullet('Classroom software and readiness','Open work includes '+', '.join(sorted(software))))
    if building_access:decisions.append(bullet('Faculty and staff building access','Confirm after-hours access approval and the owner of the access-group changes'))
    if management_done:completed.append(bullet('Classroom management follow-ups',f'{management_done} tasks recorded complete this period; verification details are in the review notes'))
    archive=archive_source(session,owner)
    if archive and archive.details.get('active') is not False:
        archive_id=archive.details['completion_archive']['sheet_id']
        for item in archive.items:
            title=clean(item.get('title'))
            if (item.get('provider_ids') or {}).get('sheet_id')!=archive_id or title.casefold() in seen or administration(title) or management(title) or not eligible(title,'','archive:'+str(item['id'])):continue
            value=item.get('archive_completed_on')
            if value:
                included=(previous.date()<date.fromisoformat(value)<=cutoff.date()) if len(value)==10 else in_window(value)
                if included:
                    completed.append(bullet(title,'archive records completion during this period'));seen.add(title.casefold())
            elif field(item,'Status').casefold()=='completed' and in_window(field(item,'Modified')):
                completed.append(bullet(title,'archive marked completed; updated this period, completion date unknown'));seen.add(title.casefold())
    rooms=set();findings=0
    for item in beacon.items:
        title=clean(item.get('item'));problem=clean(item.get('problem'));room=clean(item.get('location'))
        if item.get('issue_state')=='resolved' or (ROUTINE.search(title+' '+problem) and not SYSTEMIC.search(title+' '+problem)):continue
        if re.search(r'jamf|check.in|deep.freeze|thawed|management',title+' '+problem,re.I) and re.search(r'\b(?:A\d{3}|ARTS?\s*\d{3}|TH\d{3}|TRUS\s*\d{3}|LIB\s*\d{3})\b',room,re.I):
            rooms.add(room);findings+=1
        elif 'beacon:'+str(item['id']) in selected:
            classroom.append(bullet(title,problem+'; monitoring observation, teaching impact not verified'))
    if findings:
        classroom.append(bullet('Classroom computer management',f'{findings} monitoring findings across '+', '.join(sorted(rooms))+'. Verify management and security state; these alerts alone do not confirm a teaching outage'))
    # Confirmed diary entries can contain project work absent from task systems.
    from .planning_continuity import meeting_diaries,dean_check_in_lines
    for diary in meeting_diaries(session,owner,previous.date(),cutoff.date()):
        for index,line in enumerate(dean_check_in_lines(diary)[1:]):
            category,_,body=line.removeprefix('• ').partition(' — ')
            for part,sentence in enumerate(re.split(r'[.!?]\s+|,\s+(?=installed|updated|fixed|restored)',body)):
                ref=f'diary:{diary.id}:{index}:{part}'
                if category in ('Blockers and next steps','Tomorrow') and ref not in selected:continue
                if administration(sentence) or not (eligible(sentence,'',ref) or re.search(r'started work|student.worker|staffing',sentence,re.I)):continue
                if any(clean(t['title']).casefold() in sentence.casefold() for t in topics):continue
                sentence=re.sub(r'\btoday\b',diary.local_date.strftime('on %b %-d'),sentence,flags=re.I)
                target=groups.get(selected.get(ref,''),progress)
                target.append(bullet(diary.local_date.strftime('%b %-d recorded update'),sentence[:450]))
    lines=['Dean meeting talking points',meeting.strftime('%B %-d, %Y'),f'Since {previous:%b %-d} · prepared {cutoff:%b %-d at %-I:%M %p} Central']
    sections=[('Decisions and blockers',decisions+blockers),('Classroom and systemic issues',classroom),('Policy, training and staffing',progress),('Spending and planned purchases',spending),('Significant progress',completed)]
    for heading,items in sections:
        values=unique(items)
        if values:lines.extend(['',heading,*values])
    if not spending:lines.extend(['','Spending and planned purchases','• No reviewed spending totals or planned costs were recorded for this period.'])
    if not (decisions or blockers):lines.extend(['','Decisions and blockers','• No explicit blockers or approval requests are recorded. Review outstanding dependencies before the meeting.'])
    return '\n'.join(lines)


def install(app,db,device,lock_owner):
    @app.get('/v1/planning/dean-agenda')
    def read(actor=Depends(device),session=Depends(db)):
        return agenda(session,actor.owner_id)
    @app.put('/v1/planning/dean-agenda')
    def save(value:AgendaSave,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id)
        if agenda(session,actor.owner_id)['revision']!=value.expected_revision:
            raise HTTPException(409,'Dean priorities changed. Reload and compare before saving.')
        row=session.get(OperationalState,actor.owner_id)
        if row is None:row=OperationalState(owner_id=actor.owner_id,data={},revision=0);session.add(row)
        data=deepcopy(row.data or {});data['dean_agenda']=[t.model_dump(mode='json') for t in value.topics];data['dean_agenda_revision']=value.expected_revision+1
        row.data=data;row.revision+=1;row.updated_at=now()
        from .companion import invalidate_context
        invalidate_context(session,actor.owner_id,'operations:'+actor.owner_id)
        session.commit();return agenda(session,actor.owner_id)
