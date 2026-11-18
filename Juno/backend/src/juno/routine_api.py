"""Native host-only managed-write connection, reviewed activation and bounded ticks."""
from datetime import timedelta,datetime
from uuid import uuid4,NAMESPACE_URL,uuid5
from fastapi import Depends,HTTPException
from pydantic import Field,SecretStr,field_validator
from sqlalchemy import select
from .planning import Strict
from .provider_api import local_native
from .models import RecurringRoutine,RoutineOccurrenceRecord,OperationalState,now
from .operations import saved
from . import recurring
from .routine_delivery import plan_due,deliver,release_deferred,period_key,occurrence_id,OPEN
from .routine_writer import Writer,WriteConflict,origin


class Credential(Strict):
    base_url:str=Field(max_length=500)
    token:SecretStr
    @field_validator('base_url')
    @classmethod
    def local_origin(cls,value):return origin(value)

class ConnectionInput(Credential):
    expected_revision:int=Field(ge=0)
    expected_scope:dict
    approved:bool

class Decision(Strict):
    expected_revision:int=Field(ge=1)
    expected_updated_at:datetime

class AuthorizedDecision(Credential,Decision):pass


def connection(session,owner):
    row,data=saved(session,owner)
    return data.get('routine_connection'),row.revision if row else 0


def install(app,db,device,lock_owner,factory,writer_factory=Writer):
    def write_data(session,actor,data):
        row=session.get(OperationalState,actor.owner_id)
        if row is None:row=OperationalState(owner_id=actor.owner_id);session.add(row)
        row.data=data;row.revision=(row.revision or 0)+1;row.updated_at=now()

    def open_writer(value,expected=None):
        try:return writer_factory(value.base_url,value.token.get_secret_value(),expected)
        except PermissionError:raise HTTPException(403,'The TaskDock managed-write grant was denied or changed. Review the connection.') from None
        except (ValueError,RuntimeError,WriteConflict):raise HTTPException(409,'TaskDock managed-task connection needs review; no task was changed.') from None

    def owned(session,actor,identity,revision,updated_at=None):
        row=session.scalar(select(RecurringRoutine).where(RecurringRoutine.id==identity,RecurringRoutine.owner_id==actor.owner_id).with_for_update())
        if row is None:raise HTTPException(404,'Routine not found.')
        if row.revision!=revision or updated_at is not None and row.updated_at!=updated_at:raise HTTPException(409,'Routine changed; review again.')
        return row

    def configured(session,actor,value):
        conn,_=connection(session,actor.owner_id)
        if not conn or not conn.get('enabled') or conn['base_url']!=origin(value.base_url):
            raise HTTPException(409,'Review the managed-write connection first.')
        return conn

    @app.post('/v1/recurring/probe',dependencies=[Depends(local_native)])
    def probe(value:Credential,actor=Depends(device)):
        writer=open_writer(value)
        try:return writer.info
        finally:writer.close()

    @app.get('/v1/recurring/connection')
    def read_connection(actor=Depends(device),session=Depends(db)):
        conn,revision=connection(session,actor.owner_id)
        return {'connection':conn,'revision':revision}

    @app.post('/v1/recurring/connection',dependencies=[Depends(local_native)])
    def configure(value:ConnectionInput,actor=Depends(device),session=Depends(db)):
        if not value.approved:raise HTTPException(422,'Review the exact destination before enabling managed task access.')
        writer=open_writer(value)
        try:info=writer.info
        finally:writer.close()
        keys=('instance_id','workspace_id','column_id','grant_id','owner_id')
        actual={key:info[key] for key in keys}
        if value.expected_scope!=actual:raise HTTPException(409,'TaskDock destination changed after discovery.')
        lock_owner(session,actor.owner_id);operation,data=saved(session,actor.owner_id)
        if (operation.revision if operation else 0)!=value.expected_revision:raise HTTPException(409,'Connection settings changed; reload.')
        previous=data.get('routine_connection')
        same=bool(previous and all(previous.get(k)==v for k,v in actual.items()) and previous['base_url']==origin(value.base_url))
        data['routine_connection']={**actual,'id':previous['id'] if same else str(uuid4()),'base_url':origin(value.base_url),
            'column_name':info['column_name'],'enabled':True,'checked_at':now().isoformat()}
        if not same:
            for row in session.scalars(select(RecurringRoutine).where(RecurringRoutine.owner_id==actor.owner_id,RecurringRoutine.status=='active')):
                recurring.retain_rule(session,row,'before_connection_change');row.status='paused';row.revision+=1;row.updated_at=now();recurring.retain_rule(session,row,'connection_changed')
        write_data(session,actor,data);session.commit()
        return read_connection(actor,session)

    @app.post('/v1/recurring/{identity}/approval-preview',dependencies=[Depends(local_native)])
    def approval_preview(identity:str,value:AuthorizedDecision,actor=Depends(device),session=Depends(db)):
        row=owned(session,actor,identity,value.expected_revision,value.expected_updated_at)
        if row.status=='retired':raise HTTPException(409,'Restore this routine before activation.')
        conn=configured(session,actor,value);rule=recurring.RoutineInput.model_validate(row.definition)
        day=now().astimezone(recurring.ZoneInfo(rule.timezone)).date()
        upcoming=recurring.preview(rule,after=day)
        existing=set(session.scalars(select(RoutineOccurrenceRecord.id).where(RoutineOccurrenceRecord.owner_id==actor.owner_id,RoutineOccurrenceRecord.routine_id==identity)))
        scope={'owner_id':actor.owner_id,**{k:conn[k] for k in ('instance_id','workspace_id','column_id')}}
        selected=None
        from datetime import date
        for item in upcoming:
            candidate=date.fromisoformat(item['occurrence_date']);key=occurrence_id(actor.owner_id,identity,scope,period_key(rule,candidate))
            if key not in existing:selected=candidate;break
        if selected is None:raise HTTPException(409,'No new upcoming occurrence is available in the preview. Review the end date or prior occurrences.')
        key=occurrence_id(actor.owner_id,identity,scope,period_key(rule,selected));operation=str(uuid5(NAMESPACE_URL,key))
        payload={'routine_id':identity,'rule_revision':row.revision,'occurrence_key':period_key(rule,selected),'occurrence_date':str(selected),
            'title':rule.title,'description':rule.description,'due_date':str(selected+timedelta(days=rule.due_offset_days)),'rule':rule.model_dump(mode='json')}
        revision=row.revision;stamp=row.updated_at;connection_id=conn['id'];session.commit()
        writer=open_writer(value,conn)
        try:
            proposal=writer.remote_payload(scope,operation,payload)
            result=writer.request('POST','/previews',proposal)
            if result.get('proposed_task')!=proposal or not result.get('routine_fingerprint'):raise HTTPException(409,'TaskDock did not confirm the exact preview.')
        finally:writer.close()
        lock_owner(session,actor.owner_id);row=owned(session,actor,identity,revision,stamp)
        current,_=connection(session,actor.owner_id)
        if not current or current['id']!=connection_id:raise HTTPException(409,'Connection changed while preparing review.')
        _,data=saved(session,actor.owner_id)
        previews=data.get('routine_previews',{});previews[identity]={'revision':revision,'connection_id':connection_id,
            'fingerprint':result['routine_fingerprint'],'preview_id':result['preview_id'],'created_at':now().isoformat()}
        data['routine_previews']=previews;write_data(session,actor,data);session.commit()
        return {**result,'notice':'Open TaskDock Settings → Juno access. Review the exact recurring schedule and approve the routine there, then enable it in Juno.'}

    @app.post('/v1/recurring/{identity}/activate',dependencies=[Depends(local_native)])
    def activate(identity:str,value:AuthorizedDecision,actor=Depends(device),session=Depends(db)):
        row=owned(session,actor,identity,value.expected_revision,value.expected_updated_at);conn=configured(session,actor,value)
        _,data=saved(session,actor.owner_id);proposal=data.get('routine_previews',{}).get(identity)
        if not proposal or proposal['revision']!=row.revision or proposal['connection_id']!=conn['id']:
            raise HTTPException(409,'Prepare and review this routine’s current approval preview first.')
        revision=row.revision;stamp=row.updated_at;session.commit()
        writer=open_writer(value,conn)
        try:approval=writer.info.get('routine_approvals',{}).get(identity)
        finally:writer.close()
        if not approval or approval['fingerprint']!=proposal['fingerprint']:
            raise HTTPException(409,'Approve this exact recurring schedule in TaskDock before enabling it.')
        lock_owner(session,actor.owner_id);row=owned(session,actor,identity,revision,stamp)
        current,_=connection(session,actor.owner_id)
        if not current or current['id']!=conn['id']:raise HTTPException(409,'Connection changed during activation.')
        recurring.retain_rule(session,row,'before_activation')
        row.status='active';row.target_scope={'owner_id':actor.owner_id,**{k:conn[k] for k in ('instance_id','workspace_id','column_id')}}
        if row.activated_at is None:row.activated_at=now()
        # Definition revision is the approved TaskDock rule identity. Lifecycle
        # activation does not silently change the approved definition revision.
        row.updated_at=now();session.commit()
        return recurring.view(row)

    @app.post('/v1/recurring/{identity}/pause',dependencies=[Depends(local_native)])
    def pause(identity:str,value:Decision,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);row=owned(session,actor,identity,value.expected_revision,value.expected_updated_at)
        if row.status=='active':row.status='paused'
        row.updated_at=now()
        session.commit();return recurring.view(row)

    @app.post('/v1/recurring/tick',dependencies=[Depends(local_native)])
    def tick(value:Credential,actor=Depends(device),session=Depends(db)):
        conn=configured(session,actor,value)
        rows=session.scalars(select(RecurringRoutine).where(RecurringRoutine.owner_id==actor.owner_id,RecurringRoutine.status=='active')).all()
        ids=[row.id for row in rows];session.commit();at=now()
        for ident in ids:plan_due(factory,actor.owner_id,ident,at);release_deferred(factory,actor.owner_id,ident,at)
        with factory() as work:
            pending=work.scalars(select(RoutineOccurrenceRecord).where(RoutineOccurrenceRecord.owner_id==actor.owner_id,
                RoutineOccurrenceRecord.status.in_(OPEN-{'deferred'})).order_by(RoutineOccurrenceRecord.updated_at).limit(20)).all()
            packets=[(p.id,p.payload,p.task_id) for p in pending]
        results=[]
        for ident,payload,task_id in packets:
            try:writer=open_writer(value,conn)
            except HTTPException as error:
                if error.status_code==403:
                    with factory() as work:
                        lock_owner(work,actor.owner_id);_,data=saved(work,actor.owner_id)
                        current=data.get('routine_connection')
                        if current and current['id']==conn['id']:
                            data['routine_connection']={**current,'enabled':False}
                            for routine in work.scalars(select(RecurringRoutine).where(RecurringRoutine.owner_id==actor.owner_id,RecurringRoutine.status=='active')):
                                recurring.retain_rule(work,routine,'before_access_loss');routine.status='paused';routine.revision+=1;routine.updated_at=now();recurring.retain_rule(work,routine,'access_denied')
                            write_data(work,actor,data);work.commit()
                raise
            try:
                writer.payload=payload;writer.known_task=task_id
                results.append({'id':ident,'status':deliver(factory,actor.owner_id,ident,writer,at)})
            finally:writer.close()
        return {'items':results,'notice':'Readback preserves human TaskDock edits. Only due approved occurrences may be created.'}
