"""Explicit saved-evidence bridge; no provider credentials cross from TaskDock."""
from fastapi import Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field,SecretStr
from sqlalchemy import select
from uuid import uuid4
from .models import IntegrationSnapshot,now
from .taskdock import TaskDockReader,TaskDockError
from .integrations_api import snapshot_view,check_evidence_size
from .providers.common import text
from .providers.http import ReadError

class BridgeInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    base_url:str=Field(max_length=500)
    token:SecretStr
    kinds:list[str]=Field(default_factory=list,max_length=4)
    expected_id:str | None=Field(default=None,max_length=36)
    reviewed_workspace_id:str | None=Field(default=None,max_length=200)
    reviewed_device_id:str | None=Field(default=None,max_length=200)


def normalize(rows):
    result=[]
    allowed={'event','event_session','event_recurrence','note','time','expense'}
    for row in rows:
        if row.get('kind') not in allowed:raise TaskDockError('TaskDock returned an unsupported evidence record.')
        fields={k:row.get(k) for k in ('id','kind','record_id','event_id','task_id','start_date','end_date','date','start_time','end_time','timezone','owner','status','version','updated_at','work_date','minutes','worker','amount_cents','created_at','frequency','interval','anchor_date','paused','monthly_mode','weekday','ordinals') if k in row}
        fields['title']=text(row.get('title') or row.get('task_title') or row['kind'].replace('_',' ').capitalize(),300)
        fields['notes']=text(row.get('body') or row.get('description') or row.get('notes'),html=row.get('kind')=='note')
        fields['location']=text(row.get('location'),500);fields['source']='taskdock_saved'
        fields['content_truncated']=any(isinstance(row.get(k),str) and len(row[k])>20000 for k in ('body','description','notes'))
        result.append(fields)
    return result


def install(app,db,device,lock_owner,reader_factory=TaskDockReader):
    def owned(session,owner):return session.scalar(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==owner,IntegrationSnapshot.kind=='taskdock_saved').execution_options(populate_existing=True))
    def check(row,expected):
        if (row.id if row else None)!=expected:raise HTTPException(409,'The saved TaskDock evidence changed. Reload before replacing it.')
    @app.post('/v1/taskdock/catalog')
    def catalog(value:BridgeInput,actor=Depends(device)):
        try:return reader_factory(value.base_url,value.token.get_secret_value()).catalog()
        except ValueError:raise HTTPException(422,'Use the supported local TaskDock API address and a dedicated Juno token.') from None
        except TaskDockError as error:raise HTTPException(error.status or 502,str(error)) from None
    @app.post('/v1/taskdock/evidence')
    def refresh(value:BridgeInput,actor=Depends(device),session=Depends(db)):
        row=owned(session,actor.owner_id);check(row,value.expected_id);session.commit()
        try:
            reader=reader_factory(value.base_url,value.token.get_secret_value());catalog=reader.catalog();info=catalog['info']
            if (value.reviewed_workspace_id,value.reviewed_device_id)!=(info['workspace_id'],info['device_id']):return {'review_required':True,'catalog':catalog}
            fetched=reader.evidence(value.kinds)
            if (fetched['catalog']['info']['workspace_id'],fetched['catalog']['info']['device_id'])!=(info['workspace_id'],info['device_id']):raise TaskDockError('TaskDock identity changed during the evidence read. Review the connection again.',409)
            rows=normalize(fetched['items'])
        except (TaskDockError,ReadError,ValueError) as error:
            message=str(error) if isinstance(error,(TaskDockError,ReadError)) else 'TaskDock connection settings are invalid.'
            status=(error.status or 502) if isinstance(error,(TaskDockError,ReadError)) else 422
            lock_owner(session,actor.owner_id);row=owned(session,actor.owner_id)
            if row and row.id==value.expected_id:
                from .companion import invalidate_context
                invalidate_context(session,actor.owner_id,'integration:taskdock_saved');row.error=message[:500]
                if status in (401,403):row.details={**row.details,'active':False}
                session.commit()
            raise HTTPException(status,message) from None
        lock_owner(session,actor.owner_id);row=owned(session,actor.owner_id);check(row,value.expected_id)
        check_evidence_size(session,actor.owner_id,'taskdock_saved',rows,{'source_freshness':fetched['catalog']['sources']})
        from .companion import invalidate_context
        if row:invalidate_context(session,actor.owner_id,'integration:taskdock_saved')
        else:row=IntegrationSnapshot(owner_id=actor.owner_id,kind='taskdock_saved');session.add(row)
        row.id=str(uuid4());row.origin=reader.base_url;row.items=rows;row.fetched_at=now();row.error=None
        row.details={'active':True,'route':'taskdock_bridge','workspace_id':info['workspace_id'],'device_id':info['device_id'],'kinds':sorted(value.kinds),
            'snapshot':fetched['snapshot'],'source_freshness':fetched['catalog']['sources'],
            'notice':'Explicitly shared stored TaskDock events, notes and recorded work only. Event recurrence definitions are not a complete personal calendar. Time records are reported work, not a measure of employee skill/performance; expense currency is unknown. No upstream refresh or credential import occurred.'}
        session.commit();return {'review_required':False,'snapshot':snapshot_view(row)}
