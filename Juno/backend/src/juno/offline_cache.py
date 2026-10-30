"""Bounded owner export for a laptop's dated read-only offline copy."""
from urllib.parse import urlencode
from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from uuid import UUID


class OfflineInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    operation_id: UUID
    kind: Literal['memory.create','memory.edit','memory.delete','checkin.start','checkin.answer','checkin.diary']
    record_id: str | None = Field(default=None,max_length=100)
    body: dict

from sqlalchemy import select
from .models import OfflineOperation, Memory, Conversation, Message, CheckIn, ModelConnection, TaskDockState, TaskDockHistory, now
from .companion import message_view, conversation_view, checkin_view, saved_memory_links
from .taskdock_api import active_snapshot, snapshot_view


def install(app,db,device,lock_owner):
    @app.get('/v1/check-ins/by-date/{day}')
    def checkin(day:str,actor=Depends(device),session=Depends(db)):
        from datetime import date
        try: local_date=date.fromisoformat(day)
        except ValueError:raise HTTPException(422,'Invalid date.') from None
        row=session.scalar(select(CheckIn).where(CheckIn.owner_id==actor.owner_id,CheckIn.local_date==local_date))
        if row is None:raise HTTPException(404,'No saved check-in for this date.')
        return checkin_view(row)

    @app.get('/v1/cache')
    def export(actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id)
        pages=[]
        from .companion import QUESTIONS, LABELS
        pages.append({'path':'/v1/check-in-template','body':{'questions':[{'key':k,'text':q,'label':LABELS[k]} for k,q in QUESTIONS]}})
        def add(path,body):pages.append({'path':path,'body':body})
        def bounded(query,maximum):
            rows=session.scalars(query.limit(maximum+1)).all()
            if len(rows)>maximum:raise HTTPException(413,'The offline copy exceeds this preview’s size limit. The previous copy has been retained.')
            return rows
        memories=bounded(select(Memory).where(Memory.owner_id==actor.owner_id).order_by(Memory.updated_at.desc(),Memory.id),10000)
        memory_view=lambda r:{k:getattr(r,k) for k in ('id','text','source','confidence','revision','created_at','updated_at','source_message_id')}
        for offset in range(0,max(1,len(memories)),50):
            add('/v1/memories?'+urlencode({'q':'','offset':offset}),{'items':[memory_view(r) for r in memories[offset:offset+50]],'has_more':offset+50<len(memories),'offset':offset,'limit':50})
        conversations=bounded(select(Conversation).where(Conversation.owner_id==actor.owner_id).order_by(Conversation.created_at.desc(),Conversation.id),1000)
        for offset in range(0,max(1,len(conversations)),100):
            add('/v1/conversations?offset='+str(offset),{'items':[conversation_view(r) for r in conversations[offset:offset+100]],'has_more':offset+100<len(conversations)})
        count=0
        for conv in conversations:
            rows=bounded(select(Message).where(Message.conversation_id==conv.id).order_by(Message.order_key.desc()),10000)
            count+=len(rows)
            if count>50000:raise HTTPException(413,'The offline history exceeds this preview’s size limit.')
            links=saved_memory_links(session,actor.owner_id,rows,memories)
            for offset in range(0,max(1,len(rows)),100):
                path='/v1/conversations/'+conv.id+'/messages'
                if offset:path+='?before='+str(rows[offset-1].order_key)
                add(path,{'items':[message_view(r,links.get(r.id)) for r in reversed(rows[offset:offset+100])],'has_more':offset+100<len(rows)})
        diaries=bounded(select(CheckIn).where(CheckIn.owner_id==actor.owner_id),10000)
        for row in diaries:add('/v1/check-ins/by-date/'+str(row.local_date),checkin_view(row))
        config=session.get(ModelConnection,actor.owner_id)
        add('/v1/model',{'base_url':'http://127.0.0.1:1234/v1','model':config.model if config else '', 'configured':config is not None})
        from .integrations_api import state_view
        add('/v1/integrations',state_view(session,actor.owner_id))
        from .schedules import state_view as schedules_view
        add('/v1/schedules',schedules_view(session,actor.owner_id))
        from .planning import state_view
        add('/v1/planning',state_view(session,actor.owner_id))
        state=session.get(TaskDockState,actor.owner_id);snapshot=active_snapshot(session,actor.owner_id)
        add('/v1/taskdock',{'snapshot':snapshot_view(snapshot,state.error) if snapshot else None,'error':state.error if state else None})
        if snapshot:
            histories=bounded(select(TaskDockHistory).where(TaskDockHistory.owner_id==actor.owner_id,TaskDockHistory.snapshot_id==snapshot.id),10000)
            for row in histories:
                add('/v1/taskdock/history?'+urlencode({'snapshot_id':snapshot.id,'task_id':row.task_id,'kind':row.kind}),{'items':row.items,'read_at':row.read_at,'notice':'Dated history cache; not frozen by the collection snapshot.'})
        result={'version':1,'owner_id':actor.owner_id,'saved_at':now(),'pages':pages}
        from fastapi.encoders import jsonable_encoder
        from fastapi.responses import JSONResponse
        import json
        encoded=jsonable_encoder(result)
        if len(json.dumps(encoded).encode())>64_000_000:raise HTTPException(413,'The offline copy exceeds this preview’s size limit.')
        return JSONResponse(encoded)

    @app.post('/v1/offline-review')
    def review(value: OfflineInput, actor=Depends(device), session=Depends(db)):
        """Read the canonical record without changing it or exposing another owner's work."""
        lock_owner(session,actor.owner_id)
        row=None
        if value.kind.startswith('memory.'):
            if value.record_id:
                row=session.scalar(select(Memory).where(Memory.id==value.record_id,Memory.owner_id==actor.owner_id))
            elif value.kind=='memory.create':
                from hashlib import sha256
                import json
                fp=sha256(json.dumps([value.body.get('source'),value.body.get('text')],ensure_ascii=False).encode()).hexdigest()
                row=session.scalar(select(Memory).where(Memory.owner_id==actor.owner_id,Memory.fingerprint==fp))
            current={k:getattr(row,k) for k in ('id','text','source','confidence','revision','created_at','updated_at')} if row else None
        else:
            if value.record_id:
                row=session.scalar(select(CheckIn).where(CheckIn.id==value.record_id,CheckIn.owner_id==actor.owner_id))
            elif value.kind=='checkin.start':
                from datetime import date
                try: day=date.fromisoformat(value.body.get('local_date',''))
                except (ValueError,TypeError):raise HTTPException(422,'Invalid check-in date.') from None
                row=session.scalar(select(CheckIn).where(CheckIn.local_date==day,CheckIn.owner_id==actor.owner_id))
            current=checkin_view(row) if row else None
        return {'operation_id':str(value.operation_id),'kind':value.kind,'current':current}

    @app.post('/v1/offline-operations')
    def apply(value: OfflineInput, actor=Depends(device), session=Depends(db)):
        from fastapi.encoders import jsonable_encoder
        from pydantic import ValidationError
        from hashlib import sha256
        import json
        lock_owner(session,actor.owner_id)
        operation_id=str(value.operation_id)
        fingerprint=sha256(json.dumps(value.model_dump(mode='json',exclude={'operation_id'}),sort_keys=True).encode()).hexdigest()
        old=session.get(OfflineOperation,(actor.owner_id,operation_id))
        if old:
            if old.fingerprint!=fingerprint:raise HTTPException(409,'An offline operation ID was reused with different content.')
            return old.result
        handler, schema=app.state.offline_handlers[value.kind]
        session.info['offline_transaction']=True
        try:
            if value.kind=='memory.delete':
                if not value.record_id or set(value.body)!={'expected_revision'}:raise HTTPException(422,'Invalid offline delete.')
                revision=value.body['expected_revision']
                if type(revision) is not int or revision<1:raise HTTPException(422,'Invalid offline revision.')
                handler(value.record_id,revision,actor,session)
                result={'deleted':True,'id':value.record_id}
            else:
                try: body=schema.model_validate(value.body)
                except ValidationError:raise HTTPException(422,'The offline edit is invalid. Its local copy has been retained.') from None
                if value.kind in ('memory.create','checkin.start'):result=handler(body,actor,session)
                else:
                    if not value.record_id:raise HTTPException(422,'The offline record identity is missing.')
                    result=handler(value.record_id,body,actor,session)
            result=jsonable_encoder(result)
            session.add(OfflineOperation(owner_id=actor.owner_id,operation_id=operation_id,fingerprint=fingerprint,result=result))
            session.flush()
        finally:session.info.pop('offline_transaction',None)
        session.commit()
        return result
