"""Explicitly reviewed diary-to-plan changes and durable weekly Dean drafts."""
from datetime import date,timedelta
from hashlib import sha256
import json
from uuid import UUID
from fastapi import Depends,HTTPException,Query
from pydantic import Field
from sqlalchemy import select
from .models import CheckIn,PlanningState,PlanningCarry,DeanDraft,DeanDraftOperation,TaskDockState,now
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

def weekly_basis(session,owner,day):
    valid_day(day)
    diaries=session.scalars(select(CheckIn).where(CheckIn.owner_id==owner,CheckIn.local_date>=day,CheckIn.local_date<day+timedelta(days=7),CheckIn.status=='confirmed').order_by(CheckIn.local_date)).all()
    snapshot=active_snapshot(session,owner)
    planning=session.get(PlanningState,owner)
    status=session.get(TaskDockState,owner)
    return {'diaries':[{'id':r.id,'revision':r.revision,'day':str(r.local_date)} for r in diaries],
            'snapshot_id':snapshot.id if snapshot else None,'workspace_id':snapshot.info.get('workspace_id') if snapshot else None,
            'taskdock_saved_at':snapshot.fetched_at.isoformat() if snapshot else None,'planning_revision':planning.revision if planning else 0,'taskdock_uncertain':not snapshot or bool(status and status.error) or (now()-snapshot.fetched_at).total_seconds()>86400}

def normalized_basis(value):
    # Older saved preparation metadata has unknown source quality, never assumed fresh.
    return {'taskdock_uncertain':True,**value}

def dean_view(session,owner,day):
    row=session.scalar(select(DeanDraft).where(DeanDraft.owner_id==owner,DeanDraft.week_start==day))
    basis=weekly_basis(session,owner,day)
    return {'owner_id':owner,'week_start':str(day),'exists':row is not None,'id':row.id if row else None,
            'text':row.text if row else '', 'revision':row.revision if row else 0,'basis':normalized_basis(row.basis) if row else basis,
            'sources_changed':bool(row and normalized_basis(row.basis)!=basis),'updated_at':row.updated_at if row else None,
            'notice':'Saved reviewed writing, not a live report. Changes to evidence do not overwrite this text. Nothing is sent automatically.'}

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
            if value.basis!=normalized_basis(row.basis):raise HTTPException(409,'The saved source basis changed. Reload and compare the draft.')
            row.text=value.text;row.basis=normalized_basis(row.basis);row.revision+=1;row.updated_at=now()
        else:
            current_basis=weekly_basis(session,actor.owner_id,day)
            if value.basis!=current_basis:raise HTTPException(409,'Evidence changed after preparation. Prepare a fresh draft and compare before saving.')
            row=DeanDraft(owner_id=actor.owner_id,week_start=day,text=value.text,basis=current_basis);session.add(row)
        session.flush();receipt={'id':row.id,'revision':row.revision,'saved_at':row.updated_at.isoformat()}
        session.add(DeanDraftOperation(owner_id=actor.owner_id,operation_id=str(value.operation_id),fingerprint=fp,receipt=receipt));session.commit();return receipt
