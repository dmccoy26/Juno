"""Owner-scoped integration snapshots. Credentials never enter storage or model context."""
import json
from datetime import timedelta
from typing import Literal
from uuid import uuid4
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from .models import IntegrationSnapshot, now
from .integrations import BeaconReader, IntegrationError, beacon_feed, calendar_events, schedule_events, busy_summary

KINDS=('beacon','calendar','schedules')

class ImportInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind: Literal['beacon','calendar','schedules']
    content: str=Field(max_length=8_000_000)
    label: str=Field(min_length=1,max_length=200)
    start: str=''
    end: str=''
    timezone: str='America/Chicago'
    expected_id: str | None=Field(default=None,max_length=36)

class BeaconInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    base_url: str=Field(max_length=500)
    token: SecretStr
    expected_id: str | None=Field(default=None,max_length=36)


def snapshot_view(row):
    return {'kind':row.kind,'id':row.id,'origin':row.origin,'items':row.items,'count':len(row.items),
        'details':row.details,'fetched_at':row.fetched_at,'error':row.error,
        'stale':bool(row.error) or now()-row.fetched_at>timedelta(minutes=15)}


def state_view(session,owner):
    return {'items':[snapshot_view(r) for r in session.scalars(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==owner).order_by(IntegrationSnapshot.kind)).all()],
        'notice':'Dated read-only evidence. TaskDock remains the task system of record. Missing evidence is unknown, not proof of availability or health.'}


EVIDENCE_BYTES=40_000_000

def check_evidence_size(session,owner,kind,items,details):
    """One owner-wide bound, shared by imports, bridge reads and direct providers."""
    total=len(json.dumps({'items':items,'details':details},ensure_ascii=False).encode())
    others=session.scalars(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==owner,IntegrationSnapshot.kind!=kind)).all()
    total+=sum(len(json.dumps({'items':r.items,'details':r.details},ensure_ascii=False).encode()) for r in others)
    if total>EVIDENCE_BYTES:raise HTTPException(413,'The combined evidence copy exceeds 40 MB. Remove unused copies or narrow this source before refreshing.')


def install(app,db,device,lock_owner,beacon_factory=BeaconReader):
    def owned(session,owner,kind):return session.scalar(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==owner,IntegrationSnapshot.kind==kind).execution_options(populate_existing=True))
    def check(row,expected):
        if (row.id if row else None)!=expected:raise HTTPException(409,'This source changed. Reload it before replacing or deleting it.')
    def save(session,actor,kind,origin,items,details,expected):
        if len(json.dumps({'items':items,'details':details},ensure_ascii=False).encode())>16_000_000:raise HTTPException(413,'The expanded source exceeds 16 MB. Use a smaller window; the previous copy was retained.')
        lock_owner(session,actor.owner_id);row=owned(session,actor.owner_id,kind);check(row,expected)
        check_evidence_size(session,actor.owner_id,kind,items,details)
        from .companion import invalidate_context
        if row:invalidate_context(session,actor.owner_id,'integration:'+row.kind)
        else:row=IntegrationSnapshot(owner_id=actor.owner_id,kind=kind);session.add(row)
        row.id=str(uuid4());row.origin=origin;row.items=items;row.details=details;row.fetched_at=now();row.error=None
        session.commit();return snapshot_view(row)
    def failed(session,actor,kind,expected,message):
        lock_owner(session,actor.owner_id);row=owned(session,actor.owner_id,kind)
        if row and row.id==expected:
            from .companion import invalidate_context
            invalidate_context(session,actor.owner_id,'integration:'+kind)
            row.error=message[:500];session.commit()

    @app.get('/v1/integrations')
    def state(actor=Depends(device),session=Depends(db)):return state_view(session,actor.owner_id)

    @app.post('/v1/integrations/import')
    def import_file(value:ImportInput,actor=Depends(device),session=Depends(db)):
        check(owned(session,actor.owner_id,value.kind),value.expected_id)
        try:
            if value.kind=='beacon':items,details=beacon_feed(json.loads(value.content))
            elif value.kind=='calendar':items,details=calendar_events(value.content,value.start,value.end,value.timezone)
            else:items,details=schedule_events(value.content,value.start,value.end,value.timezone)
            if value.kind!='beacon':details['busy_days']=busy_summary(items,value.start,value.end,value.timezone)
        except (IntegrationError,json.JSONDecodeError) as error:
            message=str(error) if isinstance(error,IntegrationError) else 'The alert-feed JSON could not be read.'
            failed(session,actor,value.kind,value.expected_id,message)
            raise HTTPException(422,message) from None
        label=value.label.replace('\\','/').rsplit('/',1)[-1]
        if any(ord(c)<32 for c in label):raise HTTPException(422,'Invalid import label.')
        return save(session,actor,value.kind,'Imported file: '+label,items,details,value.expected_id)

    @app.post('/v1/integrations/beacon/refresh')
    def refresh(value:BeaconInput,actor=Depends(device),session=Depends(db)):
        check(owned(session,actor.owner_id,'beacon'),value.expected_id);session.commit()
        try:
            reader=beacon_factory(value.base_url,value.token.get_secret_value());items,details=reader.fetch()
        except IntegrationError as error:
            failed(session,actor,'beacon',value.expected_id,str(error));raise HTTPException(502,str(error)) from None
        return save(session,actor,'beacon',reader.origin,items,details,value.expected_id)

    @app.delete('/v1/integrations/{kind}')
    def remove(kind:Literal['beacon','calendar','schedules','taskdock_saved','gmail','google_calendar','google_tasks','google_chat','slack','smartsheet','outlook_calendar'],expected_id:str=Query(max_length=36),actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);row=owned(session,actor.owner_id,kind);check(row,expected_id)
        if row:
            from .companion import invalidate_context
            invalidate_context(session,actor.owner_id,'integration:'+kind);session.delete(row);session.commit()
        return {'deleted':True}
