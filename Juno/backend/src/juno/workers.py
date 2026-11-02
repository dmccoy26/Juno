"""Worker reports are attributed evidence. No TaskDock writes or owner-token reuse."""
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
import secrets
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import Depends, HTTPException, Request, Response, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from sqlalchemy import select, delete, update
from .auth import digest
from .models import WorkerPortal, Worker, WorkerInvitation, WorkerSession, WorkerGrant, WorkerReport, ScheduleState, PlanningState, Audit, now
from .taskdock_api import active_snapshot
from .taskdock_planning import provided
from .worker_assignments import assignment_options, sync_assignments, complete_excerpt, matches_assignment, normalized, mapping_key

COOKIE='__Host-juno-worker'
ASSETS=Path(__file__).parent/'worker_web'


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


class PortalInput(Strict):
    enabled:bool
    retention_days:Literal[0]=0


class WorkerInput(Strict):
    name:str=Field(min_length=1,max_length=300)


class AssignmentInput(Strict):
    key:str=Field(default="",max_length=2200)


class GrantInput(Strict):
    worker_id:str=Field(min_length=36,max_length=36)
    task_id:str=Field(min_length=1,max_length=500)
    expected_snapshot_id:str=Field(min_length=36,max_length=36)
    fields:list[Literal['title','room','issue_description','requested_outcome','due_date']]=Field(default=['title','room'],min_length=1,max_length=5)
    include_all:bool=False
    instructions:str=Field(default='',max_length=2000)
    days:int=Field(default=7,ge=1,le=30)


class Enrollment(Strict):
    invitation:SecretStr


class Submission(Strict):
    request_key:str=Field(min_length=16,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    kind:Literal['task','shift','unexpected']
    grant_id:str|None=Field(default=None,min_length=36,max_length=36)
    correction_of:str|None=Field(default=None,min_length=36,max_length=36)
    work_date:date
    text:str=Field(min_length=1,max_length=5000)
    status:Literal['not_started','in_progress','blocked','reported_complete']='in_progress'
    actual_minutes:int|None=Field(default=None,ge=0,le=1440)
    remaining_minutes:int|None=Field(default=None,ge=0,le=2400)
    blocker_state:Literal['unknown','none','reported']='unknown'
    blocker:str=Field(default='',max_length=2000)
    next_action:str=Field(default='',max_length=2000)
    handoff:str=Field(default='',max_length=2000)
    location:str=Field(default='',max_length=300)

    @model_validator(mode='after')
    def valid(self):
        if self.kind=='task' and not self.grant_id:raise ValueError('Select a shared task.')
        if self.kind!='task' and self.grant_id:raise ValueError('Use a task update to link a task.')
        if self.blocker_state=='reported' and not self.blocker:raise ValueError('Describe the blocker or choose unknown.')
        if self.blocker_state!='reported' and self.blocker:raise ValueError('Select reported when describing a blocker.')
        if self.status=='blocked' and self.blocker_state=='none':raise ValueError('A blocked report cannot say explicitly no blocker.')
        today=now().astimezone(ZoneInfo('America/Chicago')).date()
        if self.work_date>today or self.work_date<today-timedelta(days=90):raise ValueError('Choose a work date within the last 90 days.')
        return self


class RepairContext(Strict):
    room:str=Field(default='',max_length=300)
    equipment:str=Field(default='',max_length=300)
    category:Literal['printer','offline computer','driver/display','other']='other'
    summary:str=Field(min_length=1,max_length=500)
    complete_effort:bool=False

    @model_validator(mode='after')
    def location(self):
        if not self.room and not self.equipment:raise ValueError('Supply a room or equipment for repair comparisons.')
        return self


class ReviewInput(Strict):
    expected_revision:int=Field(ge=1)
    outcome:Literal['reviewed','needs_follow_up','completion_verified','dismissed']
    note:str=Field(default='',max_length=2000)
    repair:RepairContext|None=None


class ApplyInput(Strict):
    expected_revision:int=Field(ge=1)
    expected_planning_revision:int=Field(ge=0)
    fields:list[Literal['actual_minutes','minutes','blocker','next_action','resume']]=Field(min_length=1,max_length=5)


def policy(snapshot):
    return digest(json.dumps([snapshot.origin,snapshot.info.get('workspace_id'),snapshot.info.get('device_id'),snapshot.info.get('sharing_version'),snapshot.info.get('sharing')],sort_keys=True))


def revoke_grants(session,owner):
    # Used when TaskDock actively withdraws saved source material. Revocation is permanent.
    session.execute(update(WorkerGrant).where(WorkerGrant.owner_id==owner,WorkerGrant.revoked.is_(False)).values(revoked=True,excerpt={}))


def current_task(session,owner,identity):
    snapshot=active_snapshot(session,owner)
    if not snapshot or snapshot.info.get('sharing_restricted'):raise HTTPException(409,'Task source is unavailable or sharing was withdrawn.')
    task=next((t for t in snapshot.items if t['id']==identity),None)
    if task is None:raise HTTPException(409,'Task is no longer in the current workspace.')
    return snapshot,task


def valid_grant(session,grant):
    if not grant or grant.revoked or (grant.expires_at is not None and grant.expires_at<=now()):return False
    try:snapshot,task=current_task(session,grant.owner_id,grant.task_id)
    except HTTPException:return False
    return snapshot.info.get('workspace_id')==grant.workspace_id and policy(snapshot)==grant.policy_hash and (grant.mode!='assigned' or matches_assignment(session,grant,snapshot,task))


def grant_excerpt(session,grant):
    if not valid_grant(session,grant):return {}
    if not grant.include_all:return grant.excerpt
    snapshot,task=current_task(session,grant.owner_id,grant.task_id)
    return complete_excerpt(session,snapshot,task,grant.excerpt.get('instructions',''))


def report_view(session,row):
    worker=session.get(Worker,row.worker_id)
    grant=session.get(WorkerGrant,row.grant_id) if row.grant_id else None
    return {'id':row.id,'worker_id':row.worker_id,'worker_name':worker.name,'grant_id':row.grant_id,'task_id':grant.task_id if grant else None,'workspace_id':grant.workspace_id if grant else None,'shared_excerpt':grant_excerpt(session,grant) if grant else {},'grant_active':valid_grant(session,grant),'correction_of':row.correction_of,'data':row.data,'review':row.review,'review_note':row.review_note,'revision':row.revision,'applied':row.applied,'repair_context':row.repair_context,'submitted_at':row.submitted_at}


def install(app,db,device,lock_owner,manager=None):
    def local(request:Request):
        if request.scope.get('juno_lan') or request.scope.get('juno_worker'):raise HTTPException(403,'Manage worker updates on the work Mac.')

    def audit(session,actor,record,action,revision=1):
        session.add(Audit(owner_id=actor.owner_id,device_id=actor.id,record_id=record,action=action,revision=revision))

    def owned(session,model,owner,identity):
        row=session.get(model,identity)
        if not row or row.owner_id!=owner:raise HTTPException(404,'Record not found.')
        return row

    def config(session,owner):
        row=session.get(WorkerPortal,owner)
        return row

    def enabled(session,owner):
        row=config(session,owner)
        if not row or not row.enabled:raise HTTPException(403,'Worker access is disabled.')
        return row

    def actor(request:Request,session=Depends(db)):
        if not request.scope.get('juno_worker'):raise HTTPException(403,'Use the dedicated worker portal.')
        token=request.cookies.get(COOKIE,'')
        if not 40<=len(token)<=256:raise HTTPException(401,'Open your invitation or sign in again.')
        record=session.get(WorkerSession,digest(token));worker=session.get(Worker,record.worker_id) if record else None
        if not record or record.expires_at<=now() or not worker or not worker.active:raise HTTPException(401,'Your session expired or was revoked.')
        enabled(session,worker.owner_id)
        if request.method!='GET' and not secrets.compare_digest(record.csrf_hash,digest(request.headers.get('x-juno-csrf',''))):raise HTTPException(403,'Reload the worker page before submitting.')
        return worker

    def prune(session,owner):
        # Reports are retained indefinitely. Only expired access secrets are pruned.
        session.execute(delete(WorkerSession).where(WorkerSession.worker_id.in_(select(Worker.id).where(Worker.owner_id==owner)),WorkerSession.expires_at<=now()))
        session.execute(delete(WorkerInvitation).where(WorkerInvitation.worker_id.in_(select(Worker.id).where(Worker.owner_id==owner)),WorkerInvitation.expires_at<=now()))

    def owner_ready(session,owner):
        enabled(session,owner)
        state=manager.status() if manager else {}
        if not state.get('running') or not state.get('ready'):raise HTTPException(409,'Worker HTTPS is not running. Configure approved certificate trust and network first.')
        return state

    @app.get('/v1/workers',dependencies=[Depends(local)])
    def overview(actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);prune(session,actor.owner_id);sync_assignments(session,actor.owner_id)
        settings=config(session,actor.owner_id)
        people=session.get(ScheduleState,actor.owner_id)
        rows=session.scalars(select(Worker).where(Worker.owner_id==actor.owner_id).order_by(Worker.name)).all()
        reports=session.scalars(select(WorkerReport).where(WorkerReport.owner_id==actor.owner_id).order_by(WorkerReport.submitted_at.desc()).limit(201)).all()
        grants=session.scalars(select(WorkerGrant).where(WorkerGrant.owner_id==actor.owner_id).order_by(WorkerGrant.created_at.desc()).limit(201)).all()
        result={'enabled':bool(settings and settings.enabled),'retention_days':0,'host':manager.status() if manager else {'ready':False,'running':False,'address':'','reason':'Worker hosting is unavailable in this service.'},'people':[p['name'] for p in people.data.get('people',[])] if people else [],'assignment_options':assignment_options(active_snapshot(session,actor.owner_id)),'workers':[{'id':r.id,'name':r.name,'active':r.active,'assignment_keys':r.assignment_keys} for r in rows],'reports':[report_view(session,r) for r in reports[:200]],'has_more':len(reports)>200,'grants':[{'id':g.id,'worker_id':g.worker_id,'task_id':g.task_id,'mode':g.mode,'excerpt':grant_excerpt(session,g),'active':valid_grant(session,g),'expires_at':g.expires_at} for g in grants[:200]],'more_grants':len(grants)>200}
        session.commit();return result

    @app.put('/v1/workers/settings',dependencies=[Depends(local)])
    def settings(value:PortalInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id)
        if value.enabled:
            if not manager or not manager.readiness()['ready']:raise HTTPException(409,'IT must configure approved browser HTTPS before enabling worker access.')
            try:manager.start()
            except Exception:raise HTTPException(503,'Worker HTTPS could not start. Existing laptop hosting is unchanged.') from None
        row=config(session,actor.owner_id)
        if not row:row=WorkerPortal(owner_id=actor.owner_id);session.add(row)
        row.enabled=value.enabled;row.retention_days=value.retention_days
        if not value.enabled:
            # Turning access back on must not revive old browser sessions/invitations.
            ids=select(Worker.id).where(Worker.owner_id==actor.owner_id)
            session.execute(delete(WorkerSession).where(WorkerSession.worker_id.in_(ids)))
            session.execute(delete(WorkerInvitation).where(WorkerInvitation.worker_id.in_(ids)))
        prune(session,actor.owner_id);audit(session,actor,actor.owner_id,'worker.settings');session.commit()
        if not value.enabled and manager and not session.scalar(select(WorkerPortal.owner_id).where(WorkerPortal.enabled.is_(True))):manager.close()
        return {'enabled':row.enabled}

    @app.post('/v1/workers',dependencies=[Depends(local)],status_code=201)
    def add_worker(value:WorkerInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id)
        people=session.get(ScheduleState,actor.owner_id)
        if not people or value.name not in [p['name'] for p in people.data.get('people',[])]:raise HTTPException(422,'Choose a saved schedule person first. This does not change their hours or staffing status.')
        if session.scalar(select(Worker).where(Worker.owner_id==actor.owner_id,Worker.name==value.name,Worker.active.is_(True))):raise HTTPException(409,'An active portal identity already exists for this person.')
        row=Worker(owner_id=actor.owner_id,name=value.name);session.add(row);session.flush();audit(session,actor,row.id,'worker.created');session.commit()
        return {'id':row.id,'name':row.name,'active':row.active}

    @app.post('/v1/workers/{identity}/revoke',dependencies=[Depends(local)])
    def revoke(identity:str,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);row=owned(session,Worker,actor.owner_id,identity);row.active=False
        session.execute(delete(WorkerSession).where(WorkerSession.worker_id==row.id));session.execute(delete(WorkerInvitation).where(WorkerInvitation.worker_id==row.id));session.execute(update(WorkerGrant).where(WorkerGrant.worker_id==row.id).values(revoked=True,excerpt={}))
        audit(session,actor,row.id,'worker.revoked');session.commit();return {'revoked':True}

    @app.put('/v1/workers/{identity}/assignment',dependencies=[Depends(local)])
    def map_assignment(identity:str,value:AssignmentInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);worker=owned(session,Worker,actor.owner_id,identity)
        if not worker.active:raise HTTPException(409,'Worker access was revoked.')
        choices=assignment_options(active_snapshot(session,actor.owner_id))
        if value.key and value.key not in [i['key'] for i in choices]:raise HTTPException(409,'Assignee changed; reload TaskDock before matching.')
        others=session.scalars(select(Worker).where(Worker.owner_id==actor.owner_id,Worker.active.is_(True),Worker.id!=worker.id)).all()
        if value.key and any(value.key in (w.assignment_keys or []) or (not w.assignment_keys and value.key==mapping_key(active_snapshot(session,actor.owner_id).info['workspace_id'],'name:'+normalized(w.name))) for w in others):
            raise HTTPException(409,'This TaskDock identity already matches another worker.')
        worker.assignment_keys=[value.key] if value.key else []
        sync_assignments(session,actor.owner_id);audit(session,actor,worker.id,'worker.assignment_matched');session.commit()
        return {'assignment_keys':worker.assignment_keys}

    @app.post('/v1/workers/{identity}/invitations',dependencies=[Depends(local)])
    def invite(identity:str,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);host=owner_ready(session,actor.owner_id);worker=owned(session,Worker,actor.owner_id,identity)
        if not worker.active:raise HTTPException(409,'This worker was revoked; create a new identity to enroll again.')
        session.execute(delete(WorkerInvitation).where(WorkerInvitation.worker_id==worker.id));token=secrets.token_urlsafe(48);expires=now()+timedelta(hours=24)
        session.add(WorkerInvitation(token_hash=digest(token),worker_id=worker.id,expires_at=expires,used=False));audit(session,actor,worker.id,'worker.invited');session.commit()
        return {'url':host['address']+'/worker#invite='+token,'expires_at':expires}

    @app.post('/v1/workers/grants/preview',dependencies=[Depends(local)])
    def preview(value:GrantInput,actor=Depends(device),session=Depends(db)):
        worker=owned(session,Worker,actor.owner_id,value.worker_id)
        if not worker.active:raise HTTPException(409,'Worker access was revoked.')
        snapshot,task=current_task(session,actor.owner_id,value.task_id)
        if snapshot.id!=value.expected_snapshot_id:raise HTTPException(409,'Task copy changed; reload before sharing.')
        planning=session.get(PlanningState,actor.owner_id)
        confirmed_room=next((t.get('room','') for t in planning.data.get('tasks',[]) if t['task_id']==value.task_id),'') if planning and planning.data.get('workspace_id')==snapshot.info['workspace_id'] else ''
        facts={'title':task.get('title',''),'room':confirmed_room or provided(task,'room'),'issue_description':provided(task,'issue_description'),'requested_outcome':provided(task,'requested_outcome'),'due_date':task.get('due_date') or ''}
        excerpt=complete_excerpt(session,snapshot,task,value.instructions) if value.include_all else {k:str(facts[k])[:5000] for k in dict.fromkeys(value.fields)}
        excerpt['instructions']=value.instructions
        return {'excerpt':excerpt,'worker_name':worker.name,'workspace_id':snapshot.info['workspace_id'],'source_saved_at':snapshot.fetched_at}

    @app.post('/v1/workers/grants',dependencies=[Depends(local)],status_code=201)
    def share(value:GrantInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);host=owner_ready(session,actor.owner_id);view=preview(value,actor,session);snapshot,_=current_task(session,actor.owner_id,value.task_id)
        session.execute(update(WorkerGrant).where(WorkerGrant.owner_id==actor.owner_id,WorkerGrant.worker_id==value.worker_id,WorkerGrant.workspace_id==snapshot.info['workspace_id'],WorkerGrant.task_id==value.task_id,WorkerGrant.revoked.is_(False),WorkerGrant.mode=='manual').values(revoked=True,excerpt={}))
        row=WorkerGrant(owner_id=actor.owner_id,worker_id=value.worker_id,workspace_id=snapshot.info['workspace_id'],task_id=value.task_id,policy_hash=policy(snapshot),include_all=value.include_all,excerpt={'instructions':value.instructions} if value.include_all else view['excerpt'],expires_at=now()+timedelta(days=value.days));session.add(row);session.flush();audit(session,actor,row.id,'worker.task_shared');session.commit()
        return {'id':row.id,'url':host['address']+'/worker#task='+row.id,'excerpt':grant_excerpt(session,row),'expires_at':row.expires_at}

    @app.post('/v1/workers/grants/{identity}/revoke',dependencies=[Depends(local)])
    def unshare(identity:str,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);row=owned(session,WorkerGrant,actor.owner_id,identity)
        if row.mode=='assigned':raise HTTPException(409,'Change the assignment in TaskDock, or revoke the worker’s portal access.')
        row.revoked=True;row.excerpt={};audit(session,actor,row.id,'worker.task_revoked');session.commit();return {'revoked':True}

    @app.get('/v1/workers/reports',dependencies=[Depends(local)])
    def reports(offset:int=Query(default=0,ge=0),actor=Depends(device),session=Depends(db)):
        rows=session.scalars(select(WorkerReport).where(WorkerReport.owner_id==actor.owner_id).order_by(WorkerReport.submitted_at.desc(),WorkerReport.id).offset(offset).limit(101)).all()
        return {'items':[report_view(session,r) for r in rows[:100]],'has_more':len(rows)>100}

    @app.get('/v1/workers/repair-history',dependencies=[Depends(local)])
    def repair_history(actor=Depends(device),session=Depends(db)):
        from .repair_history import view
        return view(session,actor.owner_id)

    @app.get('/v1/workers/reports/{identity}',dependencies=[Depends(local)])
    def detail(identity:str,actor=Depends(device),session=Depends(db)):
        return report_view(session,owned(session,WorkerReport,actor.owner_id,identity))

    @app.post('/v1/workers/reports/{identity}/review',dependencies=[Depends(local)])
    def review(identity:str,value:ReviewInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);row=owned(session,WorkerReport,actor.owner_id,identity)
        if row.revision!=value.expected_revision:raise HTTPException(409,'This update changed. Reload before reviewing.')
        if value.outcome=='completion_verified' and session.scalar(select(WorkerReport.id).where(WorkerReport.correction_of==row.id)):raise HTTPException(409,'A correction exists. Review the newer report before verifying completion.')
        if value.outcome=='completion_verified' and row.data['status']!='reported_complete':raise HTTPException(422,'Only a completion report can be marked verified.')
        if 'repair' in value.model_fields_set:
            if value.repair is not None:
                if row.data['kind']=='shift':raise HTTPException(422,'Shift totals are not individual repair effort. Review a task or unexpected-work report instead.')
                context=value.repair.model_dump(mode='json')
                grant=session.get(WorkerGrant,row.grant_id) if row.grant_id else None
                if grant:context.update(workspace_id=grant.workspace_id,task_id=grant.task_id)
                row.repair_context=context
            else:row.repair_context={}
        from .companion import invalidate_context
        invalidate_context(session,actor.owner_id,'worker_history:'+actor.owner_id)
        row.review=value.outcome;row.review_note=value.note;row.revision+=1;audit(session,actor,row.id,'worker.report_reviewed',row.revision);session.commit();return report_view(session,row)

    @app.post('/v1/workers/reports/{identity}/apply',dependencies=[Depends(local)])
    def apply(identity:str,value:ApplyInput,actor=Depends(device),session=Depends(db)):
        from .planning import state_view,PlanningInput,TaskFacts
        lock_owner(session,actor.owner_id);row=owned(session,WorkerReport,actor.owner_id,identity)
        if row.revision!=value.expected_revision:raise HTTPException(409,'Update changed; reload before applying.')
        grant=session.get(WorkerGrant,row.grant_id) if row.grant_id else None
        if not valid_grant(session,grant):raise HTTPException(409,'Task sharing is no longer active. Review this report without applying to that task.')
        current=state_view(session,actor.owner_id)
        if current['workspace_id']!=grant.workspace_id or current['revision']!=value.expected_planning_revision:raise HTTPException(409,'Planning changed; reload and compare before saving. Nothing was overwritten.')
        chosen=list(dict.fromkeys(value.fields))
        if any(key in row.applied for key in chosen):raise HTTPException(409,'A selected field was already applied. Review planning manually to avoid counting it twice.')
        newer=session.scalar(select(WorkerReport.id).where(WorkerReport.correction_of==row.id))
        if newer:raise HTTPException(409,'A correction exists. Review the newer report first.')
        facts=next((dict(t) for t in current['tasks'] if t['task_id']==grant.task_id),{'task_id':grant.task_id})
        payload=row.data;changes={}
        for key in chosen:
            if key=='actual_minutes':item=payload.get('actual_minutes')
            elif key=='minutes':
                item=payload.get('remaining_minutes')
                if item==0:raise HTTPException(422,'Zero remaining time is a completion report, not a schedulable estimate. Review completion instead.')
            elif key=='blocker':item=payload.get('blocker','') if payload.get('blocker_state')=='reported' else '' if payload.get('blocker_state')=='none' else None
            elif key=='next_action':item=payload.get('next_action') or None
            else:item=payload.get('handoff') or None
            if item is None:raise HTTPException(422,'Selected field was not supplied. Unknown does not clear a saved fact.')
            changes[key]={'before':facts.get(key),'after':item};facts[key]=item
        facts=TaskFacts.model_validate(facts).model_dump(mode='json')
        data={k:current[k] for k in ('workspace_id','reserve_minutes','priority_choice','priority_choice_date','windows')};data['tasks']=[t for t in current['tasks'] if t['task_id']!=grant.task_id]+[facts];data['expected_revision']=current['revision']
        from .companion import invalidate_context
        invalidate_context(session,actor.owner_id,'worker_history:'+actor.owner_id)
        row.applied={**row.applied,**{k:{**v,'planning_revision':current['revision']+1,'reviewed_at':now().isoformat()} for k,v in changes.items()}};row.review='reviewed';row.revision+=1
        audit(session,actor,row.id,'worker.report_applied',row.revision)
        # Existing planning save owns validation/context invalidation and commits this same transaction.
        app.state.save_planning(PlanningInput.model_validate(data),actor,session)
        return report_view(session,row)

    @app.delete('/v1/workers/reports/{identity}',dependencies=[Depends(local)],status_code=204)
    def remove(identity:str,expected_revision:int=Query(ge=1),actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);row=owned(session,WorkerReport,actor.owner_id,identity)
        if row.revision!=expected_revision:raise HTTPException(409,'Update changed; reload before deleting.')
        from .companion import invalidate_context
        invalidate_context(session,actor.owner_id,'worker_history:'+actor.owner_id)
        audit(session,actor,row.id,'worker.report_deleted',row.revision);session.delete(row);session.commit();return Response(status_code=204)

    @app.get('/worker')
    def page(request:Request):
        if not request.scope.get('juno_worker'):raise HTTPException(403,'Use the dedicated worker HTTPS address.')
        return FileResponse(ASSETS/'index.html',headers={'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",'Referrer-Policy':'no-referrer'})

    @app.get('/worker/{asset}')
    def asset(asset:str,request:Request):
        if not request.scope.get('juno_worker') or asset not in {'app.js','style.css'}:raise HTTPException(404)
        return FileResponse(ASSETS/asset,media_type='text/javascript' if asset.endswith('.js') else 'text/css')

    @app.post('/worker/api/enroll')
    def enroll(value:Enrollment,request:Request,session=Depends(db)):
        if not request.scope.get('juno_worker'):raise HTTPException(403)
        secret=value.invitation.get_secret_value()
        if not 40<=len(secret)<=256:raise HTTPException(401,'Invitation expired or invalid.')
        invitation=session.get(WorkerInvitation,digest(secret))
        worker=session.get(Worker,invitation.worker_id) if invitation else None
        if not worker:raise HTTPException(401,'Invitation expired or invalid.')
        lock_owner(session,worker.owner_id);session.expire_all();invitation=session.get(WorkerInvitation,digest(secret));worker=session.get(Worker,worker.id)
        if not invitation:raise HTTPException(401,'Invitation expired or invalid.')
        enabled(session,worker.owner_id)
        if not worker.active or invitation.used or invitation.expires_at<=now():raise HTTPException(401,'Invitation expired or invalid.')
        invitation.used=True;token=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(32)
        session.add(WorkerSession(token_hash=digest(token),worker_id=worker.id,csrf_hash=digest(csrf),expires_at=now()+timedelta(days=7)));session.commit()
        response=JSONResponse({'name':worker.name,'csrf':csrf,'retention_days':0});response.set_cookie(COOKIE,token,max_age=7*86400,secure=True,httponly=True,samesite='strict',path='/');return response

    @app.get('/worker/api/me')
    def me(request:Request,worker=Depends(actor),session=Depends(db)):
        # Rotate CSRF on reload. A stale open tab must reload, never bypass the check.
        token=request.cookies[COOKIE];row=session.get(WorkerSession,digest(token));csrf=secrets.token_urlsafe(32);row.csrf_hash=digest(csrf);session.commit()
        return {'name':worker.name,'csrf':csrf,'retention_days':0}

    @app.get('/worker/api/tasks')
    def tasks(worker=Depends(actor),session=Depends(db)):
        lock_owner(session,worker.owner_id);sync_assignments(session,worker.owner_id)
        rows=session.scalars(select(WorkerGrant).where(WorkerGrant.worker_id==worker.id,WorkerGrant.revoked.is_(False)).order_by(WorkerGrant.created_at.desc()).limit(501)).all()
        result={'items':[{'id':r.id,'excerpt':grant_excerpt(session,r),'mode':r.mode,'expires_at':r.expires_at} for r in rows[:500] if valid_grant(session,r)],'limit':500}
        session.commit();return result

    @app.get('/worker/api/receipts')
    def receipts(worker=Depends(actor),session=Depends(db)):
        lock_owner(session,worker.owner_id);prune(session,worker.owner_id);session.commit()
        rows=session.scalars(select(WorkerReport).where(WorkerReport.worker_id==worker.id).order_by(WorkerReport.submitted_at.desc()).limit(50)).all()
        return {'items':[{'id':r.id,'submitted_at':r.submitted_at,'kind':r.data['kind'],'review':r.review,'correction_of':r.correction_of} for r in rows]}

    @app.post('/worker/api/sign-out')
    def signout(request:Request,worker=Depends(actor),session=Depends(db)):
        session.execute(delete(WorkerSession).where(WorkerSession.token_hash==digest(request.cookies[COOKIE])));session.commit();response=JSONResponse({'signed_out':True});response.delete_cookie(COOKIE,path='/',secure=True,httponly=True,samesite='strict');return response

    @app.post('/worker/api/reports',status_code=201)
    def submit(value:Submission,request:Request,worker=Depends(actor),session=Depends(db)):
        lock_owner(session,worker.owner_id);session.expire_all();worker=actor(request,session);prune(session,worker.owner_id)
        content=value.model_dump(mode='json',exclude={'request_key'});fp=digest(json.dumps(content,sort_keys=True))
        previous=session.scalar(select(WorkerReport).where(WorkerReport.worker_id==worker.id,WorkerReport.request_key==value.request_key))
        if previous:
            if previous.payload_hash!=fp:raise HTTPException(409,'This retry differs from the received update. Reload receipts before submitting a new update.')
            return {'id':previous.id,'submitted_at':previous.submitted_at,'received':True,'duplicate':True}
        if value.grant_id:
            grant=session.get(WorkerGrant,value.grant_id)
            if not grant or grant.worker_id!=worker.id or not valid_grant(session,grant):raise HTTPException(403,'Task access expired or was withdrawn. Your update was not submitted.')
        if value.correction_of:
            previous=session.get(WorkerReport,value.correction_of)
            if not previous or previous.worker_id!=worker.id:raise HTTPException(404,'Previous receipt not found.')
            if previous.grant_id!=value.grant_id or previous.data['kind']!=value.kind:raise HTTPException(409,'A correction must refer to the same shared task or unlinked work.')
        if value.correction_of:
            from .companion import invalidate_context
            invalidate_context(session,worker.owner_id,'worker_history:'+worker.owner_id)
        row=WorkerReport(owner_id=worker.owner_id,worker_id=worker.id,grant_id=value.grant_id,correction_of=value.correction_of,request_key=value.request_key,payload_hash=fp,data=content);session.add(row);session.flush();session.commit()
        return {'id':row.id,'submitted_at':row.submitted_at,'received':True,'duplicate':False}
