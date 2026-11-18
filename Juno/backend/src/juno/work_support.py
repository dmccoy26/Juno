"""Owner-private starting steps and interruption bookmarks, never task execution."""
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID
from fastapi import Depends,HTTPException,Request
from pydantic import Field,model_validator
from sqlalchemy import select,func
from .planning import Strict
from .models import WorkBookmark,WorkSupport,WorkSupportOperation,now

class SourceRef(Strict):
    task_id:str=Field(min_length=1,max_length=500)
    workspace_id:str=Field(min_length=1,max_length=500)
    snapshot_id:str=Field(min_length=1,max_length=36)

class Action(Strict):
    operation_id:UUID
    expected_revision:int=Field(ge=0)
    command:Literal['start','interrupt','resume','revise','park','finish']
    bookmark_id:str|None=Field(default=None,min_length=1,max_length=36)
    title:str|None=Field(default=None,min_length=1,max_length=300)
    first_action:str|None=Field(default=None,min_length=1,max_length=2000)
    finish_point:str|None=Field(default=None,min_length=1,max_length=2000)
    where_stopped:str|None=Field(default=None,max_length=2000)
    blocker:str|None=Field(default=None,max_length=2000)
    source_ref:SourceRef|None=None
    switch_current:bool=False

    @model_validator(mode='after')
    def valid(self):
        for key in ('title','first_action','finish_point','where_stopped','blocker'):
            value=getattr(self,key)
            if value is not None:
                value=value.strip()
                if key in ('title','first_action','finish_point') and not value:raise ValueError('Use a concrete action and finish point.')
                if any(ord(c)<32 and c not in '\n\t' for c in value):raise ValueError('Use plain text.')
                setattr(self,key,value)
        if self.command=='start':
            if self.bookmark_id or not all((self.title,self.first_action,self.finish_point)):raise ValueError('A new starting step needs a title, action and finish point.')
        elif not self.bookmark_id:raise ValueError('Choose the saved bookmark.')
        elif self.source_ref is not None:raise ValueError('An existing bookmark keeps its reviewed source reference.')
        if self.command not in ('start','revise') and any(getattr(self,k) is not None for k in ('title','first_action','finish_point')):
            raise ValueError('Review changes with the revise action.')
        if self.command=='revise' and not any(getattr(self,k) is not None for k in ('title','first_action','finish_point','where_stopped','blocker')):
            raise ValueError('Choose a detail to revise.')
        return self


def bookmark(row):
    return {k:getattr(row,k) for k in ('id','title','first_action','finish_point','where_stopped','blocker','status','source_ref','resume_count','created_at','updated_at')}

def state(session,owner):
    saved=session.get(WorkSupport,owner)
    rows=session.scalars(select(WorkBookmark).where(WorkBookmark.owner_id==owner).order_by(WorkBookmark.updated_at.desc(),WorkBookmark.id).limit(1001)).all()
    if len(rows)>1000:raise HTTPException(413,'Too many saved bookmarks for this copy. Existing records have been retained.')
    current=next((r for r in rows if saved and r.id==saved.current_id),None)
    if saved and saved.current_id and current is None:raise HTTPException(409,'The current work bookmark needs recovery review.')
    return {'owner_id':owner,'revision':saved.revision if saved else 0,'current':bookmark(current) if current else None,
            'parked':[bookmark(r) for r in rows if r.status=='parked'],
            'recent_finished':[bookmark(r) for r in rows if r.status=='finished'][:10],
            'updated_at':saved.updated_at if saved else None,
            'notice':'Private planning bookmarks. Starting or finishing a step does not assign work, change TaskDock, confirm a diary or send a report.'}


def install(app,db,device,lock_owner):
    @app.get('/v1/work-support')
    def read(actor=Depends(device),session=Depends(db)):
        return state(session,actor.owner_id)

    @app.post('/v1/work-support/actions')
    def apply(value:Action,request:Request,actor=Depends(device),session=Depends(db)):
        if request.headers.get('origin'):raise HTTPException(403,'Use native Juno to update your work bookmark.')
        lock_owner(session,actor.owner_id)
        fingerprint=sha256(json.dumps(value.model_dump(mode='json',exclude={'operation_id'}),sort_keys=True).encode()).hexdigest()
        operation=session.get(WorkSupportOperation,(actor.owner_id,str(value.operation_id)))
        if operation:
            if operation.fingerprint!=fingerprint:raise HTTPException(409,'This request ID was already used for a different work-bookmark action.')
            return {**state(session,actor.owner_id),'replayed':True,'applied_bookmark_id':operation.bookmark_id}
        saved=session.get(WorkSupport,actor.owner_id)
        if (saved.revision if saved else 0)!=value.expected_revision:
            raise HTTPException(409,'Your work bookmark changed on another screen or Mac. Your typed notes are kept; reload and compare before saving again.')
        if saved is None:
            saved=WorkSupport(owner_id=actor.owner_id,revision=0);session.add(saved)
        current=session.get(WorkBookmark,saved.current_id) if saved.current_id else None
        if current and current.owner_id!=actor.owner_id:raise HTTPException(409,'Bookmark ownership needs recovery review.')
        at=now()
        def park_current(next_id=None):
            if current and current.id!=next_id:
                if not value.switch_current:raise HTTPException(409,'Park the current step explicitly before switching work.')
                current.status='parked';current.updated_at=at
        if value.command=='start':
            if session.scalar(select(func.count()).select_from(WorkBookmark).where(WorkBookmark.owner_id==actor.owner_id))>=1000:
                raise HTTPException(413,'Your saved work bookmarks are full. No record was removed.')
            if value.source_ref:
                from .taskdock_api import active_snapshot
                copy=active_snapshot(session,actor.owner_id);ref=value.source_ref
                if not copy or copy.id!=ref.snapshot_id or copy.info.get('workspace_id')!=ref.workspace_id or not any(t['id']==ref.task_id for t in copy.items):
                    raise HTTPException(409,'The saved issue copy changed. Keep your first step, reload Today and review the issue again.')
            park_current()
            target=WorkBookmark(owner_id=actor.owner_id,title=value.title,first_action=value.first_action,finish_point=value.finish_point,
                where_stopped=value.where_stopped or '',blocker=value.blocker or '',status='working',resume_count=0,
                source_ref=value.source_ref.model_dump() if value.source_ref else None,created_at=at,updated_at=at)
            session.add(target);session.flush();saved.current_id=target.id
        else:
            target=session.get(WorkBookmark,value.bookmark_id)
            if not target or target.owner_id!=actor.owner_id:raise HTTPException(404,'Work bookmark not found.')
            if value.command=='resume':
                if target.status=='finished':raise HTTPException(409,'That step is finished. Start a new step without reopening it automatically.')
                park_current(target.id)
                if target.status!='working':target.resume_count+=1
                target.status='working';saved.current_id=target.id
            else:
                if not current or current.id!=target.id:raise HTTPException(409,'This is no longer the current step. Review it before changing anything.')
                if value.command=='interrupt':target.status='interrupted'
                elif value.command=='park':target.status='parked';saved.current_id=None
                elif value.command=='finish':target.status='finished';saved.current_id=None
                elif value.command=='revise':
                    for key in ('title','first_action','finish_point'):
                        if getattr(value,key) is not None:setattr(target,key,getattr(value,key))
            for key in ('where_stopped','blocker'):
                if getattr(value,key) is not None:setattr(target,key,getattr(value,key))
            target.updated_at=at
        saved.revision+=1;saved.updated_at=at
        session.add(WorkSupportOperation(owner_id=actor.owner_id,operation_id=str(value.operation_id),fingerprint=fingerprint,
            bookmark_id=target.id,revision=saved.revision,command=value.command,created_at=at))
        session.commit()
        return {**state(session,actor.owner_id),'replayed':False,'applied_bookmark_id':target.id}
