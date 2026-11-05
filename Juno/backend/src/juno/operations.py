"""Evidence-linked read-only operations. Exact reviewed IDs, never inferred joins."""
from datetime import date, datetime, timedelta
from hashlib import sha256
import json
from copy import deepcopy
from urllib.parse import urlsplit
from uuid import UUID
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import select
from .models import OperationalState, IntegrationSnapshot, TaskDockState, PlanningState, now
from .planning import Strict
from .taskdock_api import active_snapshot
from .taskdock_planning import provided, fact


def relative_link(value):
    # Only producer-relative app links; no credentials, remote hosts or scripts.
    if not isinstance(value,str) or len(value)>2000 or not value.startswith('/') or value.startswith('//') or '\\' in value or any(ord(c)<33 for c in value):return None
    parsed=urlsplit(value)
    return value if not parsed.scheme and not parsed.netloc else None


def digest(value):return sha256(json.dumps(value,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()


def saved(session,owner):
    row=session.get(OperationalState,owner)
    return row,{'links':[],'procedures':[],'feedback':[],**(deepcopy(row.data) if row else {})}


def sources(session,owner):
    td=active_snapshot(session,owner)
    beacon=session.get(IntegrationSnapshot,(owner,'beacon'))
    if beacon and (beacon.details.get('tombstone') or beacon.details.get('active') is False):beacon=None
    status=session.get(TaskDockState,owner)
    td_stale=not td or bool(status and status.error) or now()-td.fetched_at>timedelta(hours=24)
    beacon_stale=not beacon or bool(beacon.error) or now()-beacon.fetched_at>timedelta(minutes=15)
    if beacon:
        try:beacon_stale |= now()-datetime.fromisoformat(beacon.details['generated_at'].replace('Z','+00:00'))>timedelta(minutes=15)
        except (KeyError,TypeError,ValueError):beacon_stale=True
    return td,beacon,td_stale,beacon_stale


def source_basis(session,owner):
    td,beacon,td_stale,beacon_stale=sources(session,owner)
    row,_=saved(session,owner);planning=session.get(PlanningState,owner)
    return {'taskdock_snapshot':td.id if td else None,'workspace_id':td.info.get('workspace_id') if td else None,
            'beacon_snapshot':beacon.id if beacon else None,'beacon_error':beacon.error if beacon else None,
            'taskdock_stale':td_stale,'beacon_stale':beacon_stale,'operations_revision':row.revision if row else 0,
            'planning_revision':planning.revision if planning else 0}


def evidence_id(kind,snapshot,record):return kind+':'+str(snapshot)+':'+str(record)


def briefing(session,owner):
    td,beacon,td_stale,beacon_stale=sources(session,owner)
    row,data=saved(session,owner);basis=source_basis(session,owner)
    tasks={str(t['id']):t for t in td.items} if td and not td.info.get('sharing_restricted') else {}
    workspace=td.info.get('workspace_id') if td else None
    policy=td.info.get('sharing') if td else None
    channels=set(policy.get('channels',[])) if policy and policy.get('controlled') else None
    evidence=[];cards=[];seen=set()
    for alert in (beacon.items if beacon else []):
        aid=alert['id'];eid=evidence_id('beacon',beacon.id,aid)
        evidence.append({'id':eid,'app':'Beacon','record_id':aid,'snapshot_id':beacon.id,'version':alert.get('record_version'),
                         'retrieved_at':beacon.fetched_at.isoformat(),'updated_at':alert.get('updated_at'),
                         'observed_at':alert.get('observed_at') or None,'source_link':relative_link(alert.get('source_link')),
                         'local_path':'/v1/integrations','stale':beacon_stale})
        observation_uncertain=not alert.get('observed_at') or str(alert.get('evidence','')).upper() in {'STALE','UNKNOWN'}
        if alert.get('observed_at'):
            try:
                from .planning import stamp
                observed=stamp(alert['observed_at'])
                observation_uncertain |= now()-observed>timedelta(hours=24) or observed>now()+timedelta(minutes=5)
            except (ValueError,TypeError,AttributeError):observation_uncertain=True
        links=[r for r in data['links'] if r['alert_id']==aid]
        matching=[r for r in links if r['workspace_id']==workspace and r['task_id'] in tasks and r.get('beacon_origin')==beacon.origin and r.get('beacon_instance')==beacon.details.get('instance_id')
                  and all(not r.get(k) or r[k]==alert.get(k) for k in ('asset_id','issue_id'))]
        conflicts=[];claims=[{'kind':'observation','text':alert.get('problem') or 'Observation details unavailable.','evidence_ids':[eid]}]
        if len(matching)>1:conflicts.append('More than one reviewed relationship exists; choose the intended work record.')
        linked=[]
        for link in matching:
            task=tasks[link['task_id']];seen.add(link['task_id']);teid=evidence_id('taskdock',td.id,link['task_id'])
            evidence.append({'id':teid,'app':'TaskDock','record_id':link['task_id'],'snapshot_id':td.id,'version':str(td.snapshot),
                             'retrieved_at':td.fetched_at.isoformat(),'updated_at':task.get('updated_at'),
                             'observed_at':None,'source_link':None,'local_path':'/v1/taskdock/snapshots/'+td.id,'stale':td_stale})
            done=task.get('source_completed') is True or bool(task.get('completed_at')) or task.get('behavior') in ('done','completed','archived')
            title=str(task.get('title') or 'Shared task (title withheld)')[:500] if channels is None or 'title' in channels else 'Task title withheld'
            assignee=task.get('owner') if channels is None or 'assignment' in channels else None
            if not isinstance(assignee,str):assignee=None
            claims.append({'kind':'recorded_work','text':title+(' — recorded complete; equipment recovery is not established.' if done else ' — unfinished recorded work.'),'evidence_ids':[teid]})
            impact=provided(task,'impact')[:2000]
            if impact:claims.append({'kind':'reported_impact','text':impact,'evidence_ids':[teid]})
            task_room=provided(task,'room');alert_room=alert.get('location')
            if task_room and alert_room:
                from .schedules import room_key
                if room_key(task_room)!=room_key(alert_room):conflicts.append('Beacon location and TaskDock room disagree; review both records.')
            if fact(task,'blockers').get('review_conflict'):conflicts.append('TaskDock reports contradictory blocker facts.')
            linked.append({'task_id':link['task_id'],'title':title,'assignment':assignee,'completed':done,'impact':impact or None,'evidence_id':teid})
        if links and not matching:conflicts.append('The reviewed task is unavailable in this workspace or current sharing scope; no title or assignment is disclosed.')
        # Current v1 feed does not provide a durable issue state or verified recovery.
        # Producer extensions are surfaced only when explicitly provided, never inferred from text.
        verification=alert.get('verification_state','unknown')
        if verification=='verified_recovered':
            proof=alert.get('verification_record') or {}
            coherent=bool(alert.get('asset_id') and proof.get('asset_id')==alert.get('asset_id') and all(proof.get(k) for k in ('record_id','actor_id','method','observed_at')))
            try:
                from .planning import stamp
                verified_at=stamp(proof.get('observed_at'))
                coherent=coherent and verified_at<=now()+timedelta(minutes=5) and (not alert.get('observed_at') or verified_at>=stamp(alert['observed_at']))
            except (ValueError,TypeError,AttributeError):coherent=False
            if not coherent:
                verification='unknown';conflicts.append('A recovery claim lacks coherent asset/verification evidence; recovery remains unknown.')

        if verification=='failed':conflicts.append('Beacon records failed verification; recovery is not established.')
        if verification=='verified_recovered' and linked and any(not t['completed'] for t in linked):conflicts.append('Beacon reports recovery while linked work remains unfinished; review task status.')
        authority=alert.get('decision_authority','unknown')
        service=alert.get('service_impact','unknown')
        if authority=='department_lead':claims.append({'kind':'authority','text':'Beacon explicitly records a department-lead decision requirement.','evidence_ids':[eid]})
        elif authority=='none':claims.append({'kind':'authority','text':'Beacon explicitly records no decision requirement.','evidence_ids':[eid]})
        if service!='unknown':claims.append({'kind':'service_impact','text':'Recorded service impact: '+service.replace('_',' '),'evidence_ids':[eid]})
        cards.append({'id':aid,'title':alert.get('item') or 'Beacon observation','asset_id':alert.get('asset_id'),
                      'issue_id':alert.get('issue_id'),'issue_state':alert.get('issue_state','unknown'),
                      'verification_state':verification,'verification_record':alert.get('verification_record') if verification=='verified_recovered' else None,'service_impact':service,'decision_authority':authority,
                      'relationship':'reviewed_ids' if len(matching)==1 else 'conflicting' if matching else 'unmatched',
                      'claims':claims,'tasks':linked,'conflicts':conflicts,
                      'next_action':alert.get('action') or 'Review the original observation.',
                      'recommendation':'Review the linked evidence before choosing work. '+('Confirm the required decision with the department lead.' if authority=='department_lead' else 'Decision authority is unknown; clarify it before an approval-dependent action.' if authority=='unknown' else 'Review task readiness and available time.'),
                      'missing':[name for name in ('asset_id','issue_id') if not alert.get(name)],'stale':beacon_stale or observation_uncertain or (bool(matching) and td_stale)})
    notices=[]
    if not beacon:notices.append('Beacon is unavailable or has no saved authorized feed; this does not establish healthy equipment.')
    elif beacon_stale:notices.append('Beacon observations are stale or their last refresh failed; verify current condition.')
    elif not beacon.items:notices.append('The complete saved Beacon alert feed is empty; this is not proof of verified recovery.')
    if not td:notices.append('TaskDock is unavailable; assignment and completion are unknown.')
    elif td_stale:notices.append('TaskDock is stale or its last refresh failed; review current assignments/status.')
    if len(tasks)>500:notices.append('Link selection shows the first 500 shared tasks; use a narrower source scope for larger workspaces.')
    if td and td.info.get('sharing_restricted'):notices.append('TaskDock sharing was withdrawn; linked task content is unavailable.')
    if any(not c['asset_id'] or not c['issue_id'] for c in cards):notices.append('Current Beacon alerts lack some stable asset/issue references. Reviewed alert/task links are not a verified durable cross-app issue contract.')
    missing_alerts=[r for r in data['links'] if not beacon or r['alert_id'] not in {a['id'] for a in beacon.items}]
    if missing_alerts:notices.append(str(len(missing_alerts))+' reviewed relationship(s) refer to alerts unavailable in the current feed. Absence does not establish recovery; review or remove the references.')
    notices.append('No staffing coverage gap is inferred from an empty calendar, missing qualifications or unassigned tasks.')
    return {'basis':basis,'basis_token':digest(basis),'revision':row.revision if row else 0,'cards':cards,'evidence':list({e['id']:e for e in evidence}.values()),
            'notices':notices,'task_choices':[{'id':k,'title':str(v.get('title') or k)[:500]} for k,v in list(tasks.items())[:500] if channels is None or 'title' in channels],
            'alert_choices':[{'id':a['id'],'title':a.get('item') or a['id']} for a in (beacon.items if beacon else [])]+[{'id':r['alert_id'],'title':'Unavailable observation reference'} for r in missing_alerts],
            'links':data['links'],'feedback':data['feedback'],
            'notice':'Read-only saved evidence. Reviewed links do not acknowledge an issue, assign work, grant authority or verify recovery. No owning-app writes are available.'}


class LinkInput(Strict):
    expected_revision:int=Field(ge=0)
    basis_token:str=Field(min_length=64,max_length=64)
    alert_id:str=Field(min_length=1,max_length=200)
    task_id:str=Field(min_length=1,max_length=500)
    rationale:str=Field(default='',max_length=1000)


class FeedbackInput(Strict):
    expected_revision:int=Field(ge=0)
    basis_token:str=Field(min_length=64,max_length=64)
    operation_id:UUID
    task_id:str=Field(min_length=1,max_length=500)
    planning_day:date
    outcome:Literal['accepted','dismissed','rescheduled']
    rationale:str=Field(default='',max_length=1000)
    reschedule_day:date|None=None


def write_state(session,actor,data,expected):
    row=session.get(OperationalState,actor.owner_id)
    if (row.revision if row else 0)!=expected:raise HTTPException(409,'Operational references changed; reload and review again.')
    if row is None:row=OperationalState(owner_id=actor.owner_id);session.add(row)
    from .companion import invalidate_context
    invalidate_context(session,actor.owner_id,'operations:'+actor.owner_id)
    row.data=data;row.revision=expected+1;row.updated_at=now();session.commit()
    return row.revision


def install(app,db,device,lock_owner):
    @app.get('/v1/operations')
    def read(actor=Depends(device),session=Depends(db)):return briefing(session,actor.owner_id)

    @app.post('/v1/operations/links')
    def link(value:LinkInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);view=briefing(session,actor.owner_id)
        if view['basis_token']!=value.basis_token:raise HTTPException(409,'Sources changed; review the relationship again.')
        td,beacon,_,_=sources(session,actor.owner_id)
        if not td or not beacon or value.alert_id not in {r['id'] for r in beacon.items} or value.task_id not in {r['id'] for r in view['task_choices']}:raise HTTPException(404,'Select records from the current authorized saved sources.')
        _,data=saved(session,actor.owner_id)
        existing=[r for r in data['links'] if r['alert_id']!=value.alert_id]
        if len(existing)>=500:raise HTTPException(422,'Review existing relationships before adding more.')
        alert=next(r for r in beacon.items if r['id']==value.alert_id)
        existing.append({'asset_id':alert.get('asset_id'),'issue_id':alert.get('issue_id'),'alert_id':value.alert_id,'workspace_id':td.info['workspace_id'],'task_id':value.task_id,'actor_id':actor.id,'reviewed_at':now().isoformat(),'rationale':value.rationale,'beacon_origin':beacon.origin,'beacon_instance':beacon.details.get('instance_id')})
        data['links']=existing
        write_state(session,actor,data,value.expected_revision)
        return briefing(session,actor.owner_id)

    @app.delete('/v1/operations/links/{alert_id}')
    def unlink(alert_id:str,expected_revision:int=Query(ge=0),actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);_,data=saved(session,actor.owner_id)
        if not any(r['alert_id']==alert_id for r in data['links']):raise HTTPException(404,'Reviewed relationship not found.')
        data['links']=[r for r in data['links'] if r['alert_id']!=alert_id]
        write_state(session,actor,data,expected_revision)
        return briefing(session,actor.owner_id)

    @app.post('/v1/operations/feedback')
    def feedback(value:FeedbackInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);_,data=saved(session,actor.owner_id)
        fingerprint=digest(value.model_dump(mode='json'))
        prior=next((r for r in data['feedback'] if r['operation_id']==str(value.operation_id)),None)
        if prior:
            if prior['fingerprint']!=fingerprint:raise HTTPException(409,'This feedback operation already has a different payload.')
            return {'receipt':prior,'replayed':True}
        view=briefing(session,actor.owner_id)
        if view['basis_token']!=value.basis_token:raise HTTPException(409,'Source or planning context changed; review before recording feedback.')
        from .planning import build_plan
        plan=build_plan(session,actor.owner_id,value.planning_day)
        candidate=next((t for t in plan['tasks'] if t['task_id']==value.task_id),None)
        if candidate is None:raise HTTPException(404,'Task is not available in the current authorized plan.')
        if value.outcome=='accepted' and (not candidate['actionable'] or plan['question']):raise HTTPException(409,'Resolve missing planning information before accepting this proposal.')
        if value.outcome=='rescheduled' and (value.reschedule_day is None or value.reschedule_day<value.planning_day):raise HTTPException(422,'Choose a reschedule date on or after the planning date.')
        if value.outcome!='rescheduled' and value.reschedule_day is not None:raise HTTPException(422,'A reschedule date applies only to rescheduled feedback.')
        if len(data['feedback'])>=2000:raise HTTPException(422,'Feedback history capacity reached. Existing history has been retained.')
        receipt={**value.model_dump(mode='json'),'fingerprint':fingerprint,'workspace_id':view['basis']['workspace_id'],'actor_id':actor.id,'recorded_at':now().isoformat(),'notice':'Planning feedback only; no assignment, reservation, deadline or TaskDock record changed.'}
        data['feedback'].append(receipt);write_state(session,actor,data,value.expected_revision)
        return {'receipt':receipt,'replayed':False}


PROCEDURE_KINDS={'taskdock_saved','gmail','google_chat','slack','smartsheet'}


def procedure_identity(source):
    account=source.details.get('account',{})
    identity=account.get('id') if isinstance(account,dict) else None
    identity=identity or source.details.get('workspace_id')
    return digest({'kind':source.kind,'route':source.details.get('route'),'identity':identity}) if identity else 'snapshot:'+source.id


def procedure_view(session,owner):
    _,data=saved(session,owner);rows=[];choices=[]
    for source in session.scalars(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==owner)).all():
        if source.kind not in PROCEDURE_KINDS or source.details.get('tombstone') or source.details.get('active') is False:continue
        for item in source.items:
            identity=item.get('id')
            text=item.get('body') or item.get('text') or item.get('description')
            if not isinstance(identity,str) or not isinstance(text,str) or not text.strip():continue
            choices.append({'kind':source.kind,'snapshot_id':source.id,'record_id':identity,'title':str(item.get('title') or item.get('subject') or identity)[:300]})
    for reference in data['procedures']:
        source=session.get(IntegrationSnapshot,(owner,reference['kind']))
        if source and (source.details.get('tombstone') or source.details.get('active') is False):source=None
        if source and reference.get('source_identity')!=procedure_identity(source):source=None
        item=next((r for r in source.items if r.get('id')==reference['record_id']),None) if source else None
        text=(item.get('body') or item.get('text') or item.get('description')) if item else None
        changed=not source or source.id!=reference['snapshot_id']
        stale=not source or bool(source.error) or now()-source.fetched_at>timedelta(hours=24)
        rows.append({**reference,'text':text[:12000] if isinstance(text,str) else None,'available':bool(text),'changed':changed,'stale':stale,
                     'current_snapshot_id':source.id if source else None,'retrieved_at':source.fetched_at.isoformat() if source else None,
                     'source_updated_at':str(item.get('updated_at') or item.get('modified_at') or '') if item else None,
                     'notice':'Reference text only. Selection does not establish an officially approved procedure or authorize execution. Review changed/stale instructions with the source owner.'})
    return {'items':rows,'choices':choices[:500],'limited':len(choices)>500,'notice':'Only already-authorized saved source items can be selected. No linked URL, attachment or document instruction is fetched or executed.'}


class ProcedureInput(Strict):
    expected_revision:int=Field(ge=0)
    kind:str=Field(min_length=1,max_length=30)
    snapshot_id:str=Field(min_length=1,max_length=36)
    record_id:str=Field(min_length=1,max_length=500)
    label:str=Field(min_length=1,max_length=200)


class RemoveProcedure(Strict):
    expected_revision:int=Field(ge=0)
    kind:str=Field(min_length=1,max_length=30)
    record_id:str=Field(min_length=1,max_length=500)


def install_references(app,db,device,lock_owner):
    @app.get('/v1/operations/procedures')
    def read(actor=Depends(device),session=Depends(db)):
        row,_=saved(session,actor.owner_id);return {'revision':row.revision if row else 0,**procedure_view(session,actor.owner_id)}

    @app.post('/v1/operations/procedures')
    def designate(value:ProcedureInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);view=procedure_view(session,actor.owner_id)
        if not any(all(r[k]==getattr(value,k) for k in ('kind','snapshot_id','record_id')) for r in view['choices']):raise HTTPException(409,'Select an available record from the current authorized saved source; reload after source changes.')
        _,data=saved(session,actor.owner_id)
        refs=[r for r in data['procedures'] if (r['kind'],r['record_id'])!=(value.kind,value.record_id)]
        if len(refs)>=200:raise HTTPException(422,'Procedure reference capacity reached; existing references are retained.')
        source=session.get(IntegrationSnapshot,(actor.owner_id,value.kind))
        refs.append({**value.model_dump(exclude={'expected_revision'}),'source_identity':procedure_identity(source),'reviewed_at':now().isoformat(),'actor_id':actor.id})
        data['procedures']=refs;write_state(session,actor,data,value.expected_revision)
        return read(actor,session)

    @app.post('/v1/operations/procedures/remove')
    def remove(value:RemoveProcedure,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);_,data=saved(session,actor.owner_id)
        refs=[r for r in data['procedures'] if (r['kind'],r['record_id'])!=(value.kind,value.record_id)]
        if len(refs)==len(data['procedures']):raise HTTPException(404,'Procedure reference not found.')
        data['procedures']=refs;write_state(session,actor,data,value.expected_revision)
        return read(actor,session)

    @app.get('/v1/operations/lifecycle')
    def lifecycle(actor=Depends(device),session=Depends(db)):
        from .repair_history import view
        repair=view(session,actor.owner_id)
        return {'candidates':[{'room':g['room'],'equipment':g['equipment'],'reports':g['reports'],'verified_repairs':g['verified_repairs'],'evidence':g['evidence'],
                              'recommendation':g['suggestion'],'missing':['stable Beacon asset identity','current condition','usage','replacement cost','repair cost','approved lifecycle policy'],
                              'replacement_supported':False} for g in repair['groups'] if g['distinct_repair_records']>=2],
                'limited':repair['limited'],'notice':'Investigation candidates from reviewed repair evidence, not purchase decisions or failure-date predictions. Replacement recommendations need current authorized lifecycle/cost evidence. Accepted work cannot be created in TaskDock until its write contract is available.'}
