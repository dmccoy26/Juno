"""Owner-scoped dated TaskDock cache. Dedicated tokens live only for one request."""
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from .models import TaskDockSnapshot, TaskDockState, TaskDockHistory, now
from .taskdock import TaskDockReader, TaskDockError


class RefreshInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    base_url: str = Field(max_length=500)
    token: SecretStr
    expected_snapshot_id: str | None = Field(default=None, max_length=36)
    reviewed_workspace_id: str | None = Field(default=None, max_length=200)
    reviewed_device_id: str | None = Field(default=None, max_length=200)


def active_snapshot(session, owner_id):
    state = session.get(TaskDockState, owner_id)
    return session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.id == state.active_id,
        TaskDockSnapshot.owner_id == owner_id)) if state and state.active_id else None


def snapshot_view(row, error=None, include_items=True):
    return {'id': row.id, 'origin': row.origin, 'info': row.info, 'sources': row.sources,
            'fetched_at': row.fetched_at, 'snapshot': row.snapshot, 'count': len(row.items),
            'stale': bool(error) or now() - row.fetched_at > timedelta(minutes=15),
            'error': error, **({'items': row.items} if include_items else {})}


def install(app, db, device, lock_owner, reader_factory=TaskDockReader):
    @app.get('/v1/taskdock')
    def state(actor=Depends(device), session=Depends(db)):
        state = session.get(TaskDockState, actor.owner_id)
        row = active_snapshot(session, actor.owner_id)
        return {'snapshot': snapshot_view(row, state.error) if row else None,
                'error': state.error if state else None}

    @app.get('/v1/taskdock/snapshots')
    def archive(offset: int = Query(default=0, ge=0), actor=Depends(device), session=Depends(db)):
        rows = session.scalars(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id == actor.owner_id)
            .order_by(TaskDockSnapshot.fetched_at.desc(), TaskDockSnapshot.id).offset(offset).limit(21)).all()
        return {'items': [snapshot_view(r, include_items=False) for r in rows[:20]], 'has_more': len(rows) > 20}

    @app.get('/v1/taskdock/snapshots/{identity}')
    def archived_snapshot(identity: str, actor=Depends(device), session=Depends(db)):
        row = session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.id == identity, TaskDockSnapshot.owner_id == actor.owner_id))
        if row is None: raise HTTPException(404, 'Snapshot not found.')
        return snapshot_view(row)

    @app.post('/v1/taskdock/refresh')
    def refresh(value: RefreshInput, actor=Depends(device), session=Depends(db)):
        # Do not hold the owner lock during network requests.
        current = active_snapshot(session, actor.owner_id)
        current_id = current.id if current else None
        if current_id != value.expected_snapshot_id:
            raise HTTPException(409, 'The selected snapshot changed. Reload before refreshing.')
        previous_identity = (current.info['workspace_id'], current.info['device_id']) if current else None
        session.commit()
        try:
            reader = reader_factory(value.base_url, value.token.get_secret_value())
            discovered = reader.discover()
            identity = (discovered['workspace_id'], discovered['device_id'])
            reviewed = (value.reviewed_workspace_id, value.reviewed_device_id)
            if (previous_identity is None or identity != previous_identity) and reviewed != identity:
                lock_owner(session, actor.owner_id)
                state = session.get(TaskDockState, actor.owner_id)
                if state is None: state = TaskDockState(owner_id=actor.owner_id); session.add(state)
                from .companion import invalidate_context
                if state.active_id: invalidate_context(session, actor.owner_id, 'taskdock:' + state.active_id)
                state.error = 'Connection identity needs your review. The previous snapshot has been kept.'
                session.commit()
                return {'review_required': True, 'info': discovered}
            result = reader.fetch()
            if (result.info['workspace_id'], result.info['device_id']) != identity:
                raise TaskDockError('TaskDock identity changed during refresh. Review the connection again.')
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        except TaskDockError as error:
            lock_owner(session, actor.owner_id)
            state = session.get(TaskDockState, actor.owner_id)
            if state is None: state = TaskDockState(owner_id=actor.owner_id); session.add(state)
            from .companion import invalidate_context
            if state.active_id: invalidate_context(session, actor.owner_id, 'taskdock:' + state.active_id)
            state.error = str(error)[:500]
            session.commit()
            raise HTTPException(502, str(error)) from None
        lock_owner(session, actor.owner_id)
        state = session.get(TaskDockState, actor.owner_id)
        if (state.active_id if state else None) != current_id:
            raise HTTPException(409, 'Another refresh finished first. Reload the current snapshot.')
        from .companion import invalidate_context
        # Invalidate any answers derived from the old dated snapshot, including histories.
        if current_id: invalidate_context(session, actor.owner_id, 'taskdock:' + current_id)
        row = TaskDockSnapshot(owner_id=actor.owner_id, origin=reader.base_url, info=result.info,
            items=list(result.items), sources=list(result.sources), snapshot=result.revision,
            fetched_at=datetime.fromisoformat(result.fetched_at))
        session.add(row); session.flush()
        if state is None: state = TaskDockState(owner_id=actor.owner_id); session.add(state)
        state.active_id = row.id; state.error = None
        session.commit()
        return {'review_required': False, 'snapshot': snapshot_view(row)}

    @app.post('/v1/taskdock/history')
    def history(value: RefreshInput, task_id: str = Query(min_length=1, max_length=500),
                kind: str = Query(pattern='^(updates|activity)$'), actor=Depends(device), session=Depends(db)):
        current = active_snapshot(session, actor.owner_id)
        if current is None or current.id != value.expected_snapshot_id:
            raise HTTPException(409, 'Reload the selected snapshot before reading task history.')
        if not any(task['id'] == task_id for task in current.items):
            raise HTTPException(404, 'Task is not in the selected snapshot.')
        expected = (current.info['workspace_id'], current.info['device_id'])
        if value.base_url.rstrip('/') != current.origin:
            raise HTTPException(409, 'Use the paired address for this snapshot.')
        session.commit()
        try:
            reader = reader_factory(value.base_url, value.token.get_secret_value())
            info = reader.discover()
            if (info['workspace_id'], info['device_id']) != expected:
                raise TaskDockError('TaskDock identity changed. Refresh and review the connection first.')
            rows = reader.history(task_id, kind)
            final = reader.discover()
            if (final['workspace_id'], final['device_id']) != expected:
                raise TaskDockError('TaskDock identity changed during the history read.')
        except ValueError as error: raise HTTPException(422, str(error)) from None
        except TaskDockError as error: raise HTTPException(502, str(error)) from None
        lock_owner(session, actor.owner_id)
        latest = active_snapshot(session, actor.owner_id)
        if latest is None or latest.id != value.expected_snapshot_id:
            raise HTTPException(409, 'The selected snapshot changed. Reload before reading history.')
        key = (actor.owner_id, latest.id, task_id, kind)
        cache = session.get(TaskDockHistory, key)
        if cache is None:
            cache = TaskDockHistory(owner_id=actor.owner_id, snapshot_id=latest.id, task_id=task_id, kind=kind)
            session.add(cache)
        cache.items, cache.read_at = rows, now()
        session.commit()
        return history_view(cache)

    def history_view(cache):
        return {'items': cache.items, 'read_at': cache.read_at,
                'notice': 'Separate dated history read; not frozen by the collection snapshot.'}

    @app.get('/v1/taskdock/history')
    def cached_history(snapshot_id: str = Query(max_length=36), task_id: str = Query(max_length=500),
                       kind: str = Query(pattern='^(updates|activity)$'), actor=Depends(device), session=Depends(db)):
        cache = session.get(TaskDockHistory, (actor.owner_id, snapshot_id, task_id, kind))
        if cache is None: raise HTTPException(404, 'No saved history for this snapshot and task.')
        return history_view(cache)
