"""Explicitly reviewed diary-to-plan changes and durable weekly Dean drafts."""
from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
from hashlib import sha256
import json
import re
from uuid import UUID
from fastapi import Depends,HTTPException,Query
from pydantic import AwareDatetime,Field
from sqlalchemy import select
from .models import CheckIn,PlanningState,PlanningCarry,DeanDraft,DeanDraftOperation,TaskDockHistory,TaskDockState,now
from .planning import Strict,PlanningInput,TaskFacts,state_view,persist_planning
from .taskdock_api import active_snapshot

LABELS={'resume':'Where to resume','blocker':'Blocker','waiting_on':'Waiting on','next_action':'Next action','next_check':'Next check','minutes':'Estimated minutes'}

class CarryChanges(Strict):
    resume:str=Field(default='',max_length=2000)
    blocker:str=Field(default='',max_length=2000)
    waiting_on:str=Field(default='',max_length=300)
    next_action:str=Field(default='',max_length=2000)
    next_check:date|None=None
    minutes:int|None=Field(default=None,ge=5,le=2400)

class CarryInput(Strict):
    diary_id:str=Field(min_length=1,max_length=36)
    diary_revision:int=Field(ge=1)
    planning_revision:int=Field(ge=0)
    workspace_id:str=Field(min_length=1,max_length=500)
    snapshot_id:str=Field(min_length=1,max_length=36)
    task_id:str=Field(min_length=1,max_length=500)
    source_quote:str=Field(min_length=1,max_length=10000)
    changes:CarryChanges

class CarrySave(CarryInput):
    operation_id:UUID

class DeanSave(Strict):
    operation_id:UUID
    expected_revision:int=Field(ge=0)
    text:str=Field(min_length=1,max_length=60000)
    basis:dict


def fingerprint(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def unfinished(task):return not (task.get('source_completed') is True or task.get('completed_at') or str(task.get('behavior','')).lower() in ('done','completed','archived'))
def valid_day(day):
    if not 2000<=day.year<=2100:raise HTTPException(422,'Choose a date between 2000 and 2100.')

def carry_source(session,owner,day):
    diary=session.scalar(select(CheckIn).where(CheckIn.owner_id==owner,CheckIn.local_date==day))
    if not diary or diary.status!='confirmed':raise HTTPException(409,'Confirm the saved diary before carrying a detail into planning.')
    snapshot=active_snapshot(session,owner)
    if not snapshot:raise HTTPException(409,'Connect and refresh TaskDock before choosing a task.')
    state=state_view(session,owner)
    status=session.get(TaskDockState,owner)
    from .taskdock_planning import provided
    facts={t['task_id']:t for t in state['tasks']}
    tasks=[{'task_id':str(t['id']),'title':str(t.get('title') or 'Untitled task'),'reference':str(t['id'])[-12:],
            'context':' · '.join(str(v) for v in (facts.get(str(t['id']),{}).get('room') or provided(t,'room'),provided(t,'equipment'),t.get('parent_title')) if v)[:500]}
           for t in snapshot.items if unfinished(t)]
    if len(tasks)>1000:raise HTTPException(413,'Too many tasks for this review. Narrow the shared workspace before continuing; no partial selection is returned.')
    return {'diary_id':diary.id,'diary_revision':diary.revision,'day':str(day),'text':diary.diary_text,
            'planning_revision':state['revision'],'workspace_id':state['workspace_id'],'snapshot_id':snapshot.id,'tasks':tasks,'taskdock_saved_at':snapshot.fetched_at.isoformat(),'source_stale':bool(status and status.error) or (now()-snapshot.fetched_at).total_seconds()>86400}

def carry_preview(session,owner,value):
    diary=session.get(CheckIn,value.diary_id)
    if not diary or diary.owner_id!=owner:raise HTTPException(404,'Diary unavailable.')
    source=carry_source(session,owner,diary.local_date)
    if value.diary_revision!=diary.revision:raise HTTPException(409,'The diary changed. Reload it and review the excerpt again.')
    if value.workspace_id!=source['workspace_id'] or value.snapshot_id!=source['snapshot_id']:raise HTTPException(409,'TaskDock context changed. Reload and choose the current task before reviewing again.')
    if value.planning_revision!=source['planning_revision']:raise HTTPException(409,'Planning changed. Reload and compare your selected values with the latest facts.')
    if not any(t['task_id']==value.task_id for t in source['tasks']):raise HTTPException(409,'This task is no longer available for planning.')
    if value.source_quote not in diary.diary_text:raise HTTPException(409,'The excerpt must appear in the current confirmed diary. Select it again after any correction.')
    changes=value.changes.model_dump(mode='json',exclude_unset=True)
    if not changes:raise HTTPException(422,'Choose at least one detail to carry forward.')
    current=state_view(session,owner)
    facts=next((t for t in current['tasks'] if t['task_id']==value.task_id),TaskFacts(task_id=value.task_id).model_dump(mode='json'))
    if all(facts.get(key)==val for key,val in changes.items()):raise HTTPException(422,'These selected values already match the saved planning facts.')
    rows=[{'key':key,'label':LABELS[key],'before':str(facts[key]) if facts.get(key) not in (None,'') else 'Unknown / not recorded',
           'after':str(val) if val not in (None,'') else 'Clear this value'} for key,val in changes.items()]
    return source,current,facts,changes,rows

CHICAGO=ZoneInfo('America/Chicago')

class MeetingPrepare(Strict):
    previous:AwareDatetime
    meeting:AwareDatetime
    previous_confirmed:bool=False
    taskdock_id:str=Field(min_length=1,max_length=36)
    beacon_id:str=Field(min_length=1,max_length=36)
    archive_refresh_failed:bool=False


def meeting_diaries(session,owner,start,end):
    return session.scalars(select(CheckIn).where(CheckIn.owner_id==owner,CheckIn.local_date>=start,
        CheckIn.local_date<=end,CheckIn.status=='confirmed').order_by(CheckIn.local_date)).all()


def weekly_basis(session,owner,day,window=None):
    valid_day(day)
    start=day if not window else datetime.fromisoformat(window['previous']).astimezone(CHICAGO).date()
    end=day+timedelta(days=6) if not window else datetime.fromisoformat(window['prepared']).astimezone(CHICAGO).date()
    diaries=meeting_diaries(session,owner,start,end)
    snapshot=active_snapshot(session,owner)
    planning=session.get(PlanningState,owner)
    status=session.get(TaskDockState,owner)
    from .operations import source_basis
    from .completion_archive import archive_basis
    operational_basis=source_basis(session,owner)
    archive = archive_basis(session, owner)
    return {**({'meeting_window':window} if window else {}),**({'completion_archive':archive} if archive else {}),'operations_basis':operational_basis,'diaries':[{'id':r.id,'revision':r.revision,'day':str(r.local_date)} for r in diaries],
            'snapshot_id':snapshot.id if snapshot else None,'workspace_id':snapshot.info.get('workspace_id') if snapshot else None,
            'taskdock_saved_at':snapshot.fetched_at.isoformat() if snapshot else None,'planning_revision':planning.revision if planning else 0,'taskdock_uncertain':not snapshot or bool(status and status.error) or (now()-snapshot.fetched_at).total_seconds()>86400}

def normalized_basis(value):
    # Older saved preparation metadata has unknown source quality, never assumed fresh.
    return {'taskdock_uncertain':True,'operations_basis':None,**value}

def dean_view(session,owner,day):
    row=session.scalar(select(DeanDraft).where(DeanDraft.owner_id==owner,DeanDraft.week_start==day))
    basis=weekly_basis(session,owner,day,row.basis.get('meeting_window') if row else None)
    return {'owner_id':owner,'week_start':str(day),'exists':row is not None,'id':row.id if row else None,
            'text':row.text if row else '', 'revision':row.revision if row else 0,'basis':normalized_basis(row.basis) if row else basis,
            'sources_changed':bool(row and normalized_basis(row.basis)!=basis),'updated_at':row.updated_at if row else None,
            'notice':'Saved reviewed writing, not a live report. Changes to evidence do not overwrite this text. Nothing is sent automatically.'}

def dean_check_in_lines(row, *, character_limit=None):
    from .companion import LABELS

    lines = [f'### {row.local_date:%a, %b %d}']
    category = ''
    used = 0
    omitted = 0
    for raw in row.diary_text.splitlines():
        item = raw.strip()
        if not item:
            continue
        if item in LABELS.values():
            category = item
            continue
        item = re.sub(r'^(?:[•*-]|[0-9]{1,3}[.)])\s+', '', item)
        entry = f'• {category} — {item}' if category else f'• {item}'
        if character_limit is not None and used + len(entry) + 1 > character_limit:
            omitted += 1
            continue
        lines.append(entry)
        used += len(entry) + 1
    if omitted:
        lines.append(f'{omitted} more in the saved check-in.')
    return lines


def meeting_text(session,owner,previous,cutoff,meeting,td,beacon,beacon_stale,previous_confirmed,archive_refresh_failed=False):
    from .planning import stamp
    from .taskdock_planning import provided,request_overview
    from .operations import briefing
    from .dean_follow_up import briefing_lines
    from .completion_archive import report_lines
    from .chairs_routing import recipient
    def dated(value):
        try:
            parsed=stamp(value)
            if previous<parsed<=cutoff:return parsed.astimezone(CHICAGO)
        except (AttributeError,ValueError,TypeError):pass
        return None

    def brief(value,limit=280):
        return ' '.join(str(value or '').split())[:limit]

    def show(when):return when.strftime('%b %d, %Y at %-I:%M %p')
    def section(lines,title,entries,limit,empty):
        lines.extend(['',title])
        lines.extend(entries[:limit] or [empty])
        if len(entries)>limit:lines.append(f'{len(entries)-limit} more in the source records.')

    lines=['Dean meeting update — draft',show(meeting)+' Central',
           f'From {show(previous)} through {show(cutoff)} Central.']
    lines.append('Start: last meeting as confirmed in Juno.' if previous_confirmed else
                 'Start: previous scheduled Thursday meeting. If it was skipped or moved, review the reporting window.')
    follow_ups = briefing_lines(session, owner, cutoff.date())
    if follow_ups:
        lines.extend(['', 'Open requests from the Dean', *follow_ups])
    dean_items = []
    for row in beacon.items:
        title, location = row.get('item') or '', row.get('location') or ''
        if row.get('issue_state') != 'resolved' and recipient(title, room=location) == 'dean':
            dean_items.append(f"• {brief(title,140)} — {brief(row.get('problem'))}")
    if dean_items:
        lines.extend(['', 'Items for the Dean', *dict.fromkeys(dean_items)])
    diaries=meeting_diaries(session,owner,previous.date(),cutoff.date())
    lines.extend(['','Confirmed check-ins (day-level records)'])
    for row in reversed(diaries[-18:]):
        lines.extend(dean_check_in_lines(row, character_limit=900))
    if not diaries:
        lines.append('No confirmed check-ins in this window.')
    if len(diaries)>18:
        lines.append(f'{len(diaries)-18} more check-ins in the source records.')
    if any(r.local_date==previous.date() for r in diaries):
        lines.append('The prior meeting day’s check-in may include work from earlier that day.')
    completed=[];updates=[];open_items=[]
    histories={r.task_id:r.items for r in session.scalars(select(TaskDockHistory).where(
        TaskDockHistory.owner_id==owner,TaskDockHistory.snapshot_id==td.id,TaskDockHistory.kind=='updates')).all()}
    for task in td.items:
        title=brief(task.get('title') or 'Untitled TaskDock item',160)
        at=dated(task.get('completed_at'))
        if at:completed.append((at,f'• {title} — marked complete {show(at)}.'))
        sample=task.get('source_updates')
        source_notes=sample.get('items') or [] if isinstance(sample,dict) else []
        for item in [*source_notes,*histories.get(task['id'],[])]:
            if not isinstance(item,dict):continue
            date_value=item.get('created_at') or item.get('posted_at') or item.get('timestamp') or item.get('observed_at')
            at=dated(date_value)
            modified=dated(item.get('modified_at') or item.get('updated_at'))
            if modified and (not at or modified>at):
                at=modified
                label=' (edited)'
            else:label=''
            body=brief(item.get('body') or item.get('text'))
            if at and body:updates.append((at,f'• {title} — {show(at)}{label}: {body}'))
        if unfinished(task):
            due=brief(task.get('due_date'),30)
            blocker=brief(provided(task,'blockers') or task.get('blocked_reason'))
            latest=brief(task.get('latest_update'))
            priority=brief(provided(task,'reported_priority') or request_overview(task,td.info,td.fetched_at)['priority_label'],40)
            activity=dated(task.get('source_updated_at') or task.get('updated_at'))
            open_items.append(((not bool(blocker),not bool(due),due,not bool(activity),title),
                f'• {title}'+(f' — due {due}' if due else '')+(f'; priority: {priority}' if priority else '')+
                (f'; blocker: {blocker}' if blocker else '')+(f'; latest note (date unverified): {latest}' if latest else '')))
    section(lines,'TaskDock: completions recorded since the meeting',
            [entry for _,entry in sorted(completed,reverse=True)],24,'No shared completion timestamps in this window.')
    lines.extend(report_lines(session, owner, previous, cutoff))
    if archive_refresh_failed:
        lines.append('Smartsheet archive refresh did not complete. Review archive coverage before sharing.')
    section(lines,'TaskDock: dated progress notes',
            list(dict.fromkeys(entry for _,entry in sorted(updates,reverse=True))),20,'No dated notes available from the shared records.')
    section(lines,'TaskDock: current open work and blockers',
            [entry for _,entry in sorted(open_items)],15,'No open work in the current shared copy.')
    cards=briefing(session,owner)['cards']
    by_id={c['id']:c for c in cards}
    recent=[];current=[];decisions=[]
    for row in beacon.items:
        at=dated(row.get('observed_at'))
        card=by_id.get(row['id'],{})
        line=f"• {brief(row.get('item'),140)} — {brief(row.get('problem'))}"
        if card.get('verification_state')=='verified_recovered':
            line+='; recovery verified in Beacon'
        elif row.get('issue_state')=='resolved':
            line+='; recorded as resolved, recovery not verified here'
        linked=[brief(t['title'],120) for t in card.get('tasks',[])[:2]]
        if linked:line+='; linked TaskDock work: '+', '.join(linked)
        verification=dated((card.get('verification_record') or {}).get('observed_at'))
        updated=dated(row.get('updated_at'))
        if verification:recent.append((verification,line+f' (recovery verified {show(verification)})'))
        elif at:recent.append((at,line+f' (observed {show(at)})'))
        elif updated:recent.append((updated,line+f' (record updated {show(updated)}; observation time separate)'))
        elif row.get('issue_state')!='resolved':current.append(line+' (observation outside this window or date unavailable)')
        if card.get('decision_authority')=='department_lead':
            decisions.append(line+'; '+brief(card.get('recommendation')))
    section(lines,'Beacon: observations since the meeting',
            [entry for _,entry in sorted(recent,reverse=True)],24,'No observations in this window from the connected Beacon feed.')
    section(lines,'Beacon: other findings still shown in the feed',current,12,'No additional findings in this copy.')
    section(lines,'Decisions to raise',decisions,10,'No department-level decision was explicitly tagged in the connected Beacon records. Review open blockers for decisions to raise.')
    lines.extend(['','Source coverage',
                  f'TaskDock refreshed {show(td.fetched_at.astimezone(CHICAGO))} Central. Shared fields and comment samples can be limited. Task completion alone does not verify a repair.',
                  f'Beacon refreshed {show(beacon.fetched_at.astimezone(CHICAGO))} Central. Includes the authorized alert feed and supported linked issues; it is not a complete equipment or incident history.'])
    candidates=sum(bool(t.get('latest_update')) for t in td.items)
    lines.append(f'TaskDock timelines read for {len(histories)} of {candidates} tasks with a shared latest progress note. Smartsheet comment samples are separate and may be partial.')
    if 'issue_snapshot_count' in beacon.details:
        lines.append(f"Beacon includes {beacon.details['issue_snapshot_count']} retained issue records across the authorized inventory, including resolved issues. Current alerts still reflect Beacon's monitoring coverage.")
    if beacon_stale:lines.append('Beacon’s feed timestamp is stale or unavailable. Verify current status before sharing.')
    return '\n'.join(lines)



def install(app,db,device,lock_owner):
    @app.get('/v1/planning/carry-forward')
    def source(day:date=Query(),actor=Depends(device),session=Depends(db)):
        valid_day(day);lock_owner(session,actor.owner_id);return carry_source(session,actor.owner_id,day)

    @app.post('/v1/planning/carry-forward/preview')
    def preview(value:CarryInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id)
        *_,rows=carry_preview(session,actor.owner_id,value)
        return {'rows':rows,'notice':'Only these selected Juno planning values will change. TaskDock and the diary stay intact.'}

    @app.post('/v1/planning/carry-forward/save')
    def save(value:CarrySave,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id)
        payload=value.model_dump(mode='json');payload['changes']=value.changes.model_dump(mode='json',exclude_unset=True);fp=fingerprint(payload);key=(actor.owner_id,str(value.operation_id))
        old=session.get(PlanningCarry,key)
        if old:
            if old.fingerprint!=fp:raise HTTPException(409,'This save identity already has different contents.')
            return {'operation_id':old.operation_id,'planning_revision':old.planning_revision,'saved_at':old.created_at,'replayed':True}
        source,current,facts,changes,rows=carry_preview(session,actor.owner_id,value)
        after={**facts,**changes}
        tasks=[t for t in current['tasks'] if t['task_id']!=value.task_id]+[after]
        data={key:current[key] for key in ('workspace_id','reserve_minutes','priority_choice','priority_choice_date','windows')}
        persist_planning(session,actor.owner_id,PlanningInput(expected_revision=current['revision'],tasks=tasks,**data))
        session.flush();revision=session.get(PlanningState,actor.owner_id).revision
        row=PlanningCarry(owner_id=actor.owner_id,operation_id=str(value.operation_id),fingerprint=fp,diary_id=value.diary_id,
            diary_revision=value.diary_revision,diary_day=date.fromisoformat(source['day']),workspace_id=value.workspace_id,task_id=value.task_id,
            source_quote=value.source_quote,before={k:facts.get(k) for k in changes},after=changes,planning_revision=revision)
        session.add(row);session.flush();receipt={'operation_id':row.operation_id,'planning_revision':revision,'saved_at':row.created_at,'replayed':False};session.commit();return receipt

    @app.get('/v1/planning/carry-forward/history')
    def history(task_id:str,workspace_id:str,actor=Depends(device),session=Depends(db)):
        rows=session.scalars(select(PlanningCarry).where(PlanningCarry.owner_id==actor.owner_id,PlanningCarry.task_id==task_id,PlanningCarry.workspace_id==workspace_id).order_by(PlanningCarry.created_at.desc()).limit(20)).all()
        items=[]
        for r in rows:
            diary=session.get(CheckIn,r.diary_id) if r.diary_id else None
            items.append({'operation_id':r.operation_id,'diary_day':str(r.diary_day),'diary_revision':r.diary_revision,'source_quote':r.source_quote,
                'before':r.before,'after':r.after,'planning_revision':r.planning_revision,'saved_at':r.created_at,
                'source_changed':not diary or diary.revision!=r.diary_revision or diary.status!='confirmed',
                'rows':[{'key':k,'label':LABELS[k],'before':str(r.before[k]) if r.before.get(k) not in (None,'') else 'Unknown / not recorded','after':str(v) if v not in (None,'') else 'Cleared'} for k,v in r.after.items()]})
        return {'items':items}


    @app.post('/v1/planning/dean-meeting/prepare')
    def prepare_meeting(value:MeetingPrepare,actor=Depends(device),session=Depends(db)):
        from .operations import sources
        previous=value.previous.astimezone(CHICAGO)
        meeting=value.meeting.astimezone(CHICAGO)
        cutoff=now().astimezone(CHICAGO)
        valid_day(previous.date());valid_day(meeting.date())
        if not previous<cutoff<=meeting or meeting.date()-previous.date()>timedelta(days=366):
            raise HTTPException(422,'Choose a past reporting start and an upcoming meeting within one year of it.')
        day=meeting.date()-timedelta(days=meeting.weekday())
        lock_owner(session,actor.owner_id)
        row=session.scalar(select(DeanDraft).where(DeanDraft.owner_id==actor.owner_id,DeanDraft.week_start==day))
        if row:return {'created':False,'week_start':str(day)}
        td,beacon,td_stale,beacon_stale=sources(session,actor.owner_id)
        if not td or td_stale or td.info.get('sharing_restricted') or td.id!=value.taskdock_id:
            raise HTTPException(409,'TaskDock did not supply a current shared copy. Refresh it again before preparing this draft.')
        if not beacon or beacon.error or beacon.id!=value.beacon_id or cutoff-beacon.fetched_at>timedelta(minutes=15):
            raise HTTPException(409,'Beacon did not supply a current copy. Refresh it again before preparing this draft.')
        window={'previous':previous.isoformat(),'meeting':meeting.isoformat(),'prepared':cutoff.isoformat(),'previous_confirmed':value.previous_confirmed}
        basis=weekly_basis(session,actor.owner_id,day,window)
        content=meeting_text(session,actor.owner_id,previous,cutoff,meeting,td,beacon,beacon_stale,value.previous_confirmed,value.archive_refresh_failed)
        session.add(DeanDraft(owner_id=actor.owner_id,week_start=day,text=content,basis=basis))
        session.commit()
        return {'created':True,'week_start':str(day)}

    @app.get('/v1/planning/weekly-draft/{day}')
    def read(day:date,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);return dean_view(session,actor.owner_id,day)

    @app.put('/v1/planning/weekly-draft/{day}')
    def write(day:date,value:DeanSave,actor=Depends(device),session=Depends(db)):
        valid_day(day);lock_owner(session,actor.owner_id);fp=fingerprint({'day':str(day),**value.model_dump(mode='json')});key=(actor.owner_id,str(value.operation_id))
        old=session.get(DeanDraftOperation,key)
        if old:
            if old.fingerprint!=fp:raise HTTPException(409,'This save identity already has different contents.')
            return old.receipt
        row=session.scalar(select(DeanDraft).where(DeanDraft.owner_id==actor.owner_id,DeanDraft.week_start==day))
        if (row.revision if row else 0)!=value.expected_revision:raise HTTPException(409,'This Dean draft changed on another device. Reload and compare; your writing has not been replaced.')
        if row:
            saved_basis = normalized_basis(row.basis)
            supplied_basis = value.basis
            # Older paired clients omit this field when editing an existing revision.
            if 'completion_archive' in saved_basis and 'completion_archive' not in supplied_basis:
                supplied_basis = {**supplied_basis, 'completion_archive': saved_basis['completion_archive']}
            if supplied_basis!=saved_basis:raise HTTPException(409,'The saved source basis changed. Reload and compare the draft.')
            row.text=value.text;row.basis=saved_basis;row.revision+=1;row.updated_at=now()
        else:
            current_basis=weekly_basis(session,actor.owner_id,day)
            if value.basis!=current_basis:raise HTTPException(409,'Evidence changed after preparation. Prepare a fresh draft and compare before saving.')
            row=DeanDraft(owner_id=actor.owner_id,week_start=day,text=value.text,basis=current_basis);session.add(row)
        session.flush();receipt={'id':row.id,'revision':row.revision,'saved_at':row.updated_at.isoformat()}
        session.add(DeanDraftOperation(owner_id=actor.owner_id,operation_id=str(value.operation_id),fingerprint=fp,receipt=receipt));session.commit();return receipt
