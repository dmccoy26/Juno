"""Owner-scoped canonical memory API; no model or external writes."""
from typing import Literal
from hashlib import sha256
import json
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from .auth import authenticate
from .database import engine_for, sessions
from .models import Audit, Memory, Suppression, now
from .companion import install, invalidate_context
from .local_model import LocalModel
from .taskdock import TaskDockReader
from . import taskdock_api, shared_host, offline_cache


class MemoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=10000)
    source: str = Field(min_length=1, max_length=500)
    confidence: Literal["confirmed", "observed", "inferred"]


class MemoryEdit(MemoryInput):
    expected_revision: int = Field(ge=1)


def fingerprint(value):
    return sha256(json.dumps([value.source, value.text], ensure_ascii=False).encode()).hexdigest()


def view(row):
    return {key: getattr(row, key) for key in
            ("id", "text", "source", "confidence", "revision", "created_at", "updated_at")}


def create_app(engine=None, model_factory=LocalModel, taskdock_factory=TaskDockReader, host_manager=None):
    engine = engine if engine is not None else engine_for()
    factory = sessions(engine)
    app = FastAPI(title="Juno companion service", version="0.1.0-preview.5")
    bearer = HTTPBearer(auto_error=False)

    @app.middleware("http")
    async def private_response(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def db():
        with factory() as session:
            yield session

    def device(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), session=Depends(db)):
        record = authenticate(session, credentials.credentials if credentials else "")
        if record is None:
            raise HTTPException(401, "Authentication required.", headers={"WWW-Authenticate": "Bearer"})
        return record

    def lock_owner(session, owner_id):
        # Serialize changes per owner, including suppression checks and creation.
        session.execute(text("SELECT id FROM owners WHERE id=:id FOR UPDATE"), {"id": owner_id})

    def owned(session, owner_id, memory_id):
        row = session.scalar(select(Memory).where(Memory.owner_id == owner_id, Memory.id == memory_id))
        if row is None:
            raise HTTPException(404, "Memory not found.")
        return row

    def audit(session, actor, row, action):
        session.add(Audit(owner_id=actor.owner_id, device_id=actor.id,
                          record_id=row.id, action=action, revision=row.revision))

    def suppress(session, owner_id, value):
        session.execute(insert(Suppression).values(owner_id=owner_id, fingerprint=value)
                        .on_conflict_do_nothing())

    def ensure_allowed(session, owner_id, value):
        if session.get(Suppression, (owner_id, value)) is not None:
            raise HTTPException(409, "This source content was previously removed or corrected.")

    def commit(session):
        try:
            if session.info.get('offline_transaction'): session.flush()
            else: session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "An equivalent memory already exists.") from None

    @app.get("/health")
    def health():
        return {"service": "juno", "version": "0.1.0-preview.5"}

    @app.get("/v1/memories")
    def memories(q: str = Query(default="", max_length=200),
                 limit: int = Query(default=50, ge=1, le=100),
                 offset: int = Query(default=0, ge=0), actor=Depends(device), session=Depends(db)):
        query = select(Memory).where(Memory.owner_id == actor.owner_id)
        if q:
            # Literal substring search, not wildcard or semantic search.
            query = query.where(Memory.text.icontains(q, autoescape=True))
        rows = session.scalars(query.order_by(Memory.updated_at.desc(), Memory.id).limit(limit+1).offset(offset)).all()
        return {"items": [view(r) for r in rows[:limit]], "has_more": len(rows)>limit,
                "offset": offset, "limit": limit}

    @app.post("/v1/memories", status_code=201)
    def create(value: MemoryInput, actor=Depends(device), session=Depends(db)):
        lock_owner(session, actor.owner_id)
        fp = fingerprint(value)
        ensure_allowed(session, actor.owner_id, fp)
        row = Memory(owner_id=actor.owner_id, fingerprint=fp, **value.model_dump())
        session.add(row)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "An equivalent memory already exists.") from None
        audit(session, actor, row, "memory.created")
        commit(session)
        return view(row)

    @app.get("/v1/memories/{memory_id}")
    def get(memory_id: str, actor=Depends(device), session=Depends(db)):
        return view(owned(session, actor.owner_id, memory_id))

    @app.put("/v1/memories/{memory_id}")
    def edit(memory_id: str, value: MemoryEdit, actor=Depends(device), session=Depends(db)):
        lock_owner(session, actor.owner_id)
        row = owned(session, actor.owner_id, memory_id)
        if row.revision != value.expected_revision:
            raise HTTPException(409, "Memory changed; reload before editing.")
        fp = fingerprint(value)
        ensure_allowed(session, actor.owner_id, fp)
        if fp != row.fingerprint:
            suppress(session, actor.owner_id, row.fingerprint)
        invalidate_context(session, actor.owner_id, 'memory:'+row.id)
        for key, content in value.model_dump(exclude={"expected_revision"}).items():
            setattr(row, key, content)
        row.fingerprint = fp
        row.revision += 1
        row.updated_at = now()
        audit(session, actor, row, "memory.corrected")
        commit(session)
        return view(row)

    @app.delete("/v1/memories/{memory_id}", status_code=204)
    def delete(memory_id: str, expected_revision: int = Query(ge=1),
               actor=Depends(device), session=Depends(db)):
        lock_owner(session, actor.owner_id)
        row = owned(session, actor.owner_id, memory_id)
        if row.revision != expected_revision:
            raise HTTPException(409, "Memory changed; reload before deleting.")
        suppress(session, actor.owner_id, row.fingerprint)
        invalidate_context(session, actor.owner_id, 'memory:'+row.id)
        audit(session, actor, row, "memory.deleted")
        session.delete(row)
        commit(session)
        return Response(status_code=204)

    app.state.offline_handlers = {'memory.create': (create, MemoryInput), 'memory.edit': (edit, MemoryEdit), 'memory.delete': (delete, None)}
    install(app, db, device, lock_owner, model_factory)
    taskdock_api.install(app, db, device, lock_owner, taskdock_factory)
    shared_host.install(app, db, device, lock_owner, host_manager)
    offline_cache.install(app, db, device, lock_owner)
    return app
