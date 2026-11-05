"""Fail closed when an update loses the established workspace or owner identity."""
import json
import os
from pathlib import Path


class WorkspaceError(RuntimeError):
    pass


def read_identity(state):
    state = Path(state).resolve()
    marker = state / 'workspace-identity.json'
    saved = state / 'desktop-owner.json'
    try:
        identity = json.loads(saved.read_text()) if saved.exists() else {}
        pinned = json.loads(marker.read_text()) if marker.exists() else None
    except (ValueError, OSError):
        raise WorkspaceError('Workspace identity is unreadable; recover the existing workspace before continuing.') from None
    if not isinstance(identity, dict) or (identity and not isinstance(identity.get('owner_id'), str)):
        raise WorkspaceError('Workspace owner settings are invalid.')
    if pinned is not None:
        if not isinstance(pinned, dict) or pinned.get('format') != 1 or pinned.get('path') != str(state):
            raise WorkspaceError('The established workspace location changed. Review recovery before continuing.')
        if not pinned.get('owner_id') or pinned['owner_id'] != identity.get('owner_id'):
            raise WorkspaceError('The established workspace owner changed or is missing. Review recovery before continuing.')
        if not (state / 'postgres/data/PG_VERSION').is_file():
            raise WorkspaceError('The established database is missing. Restore it instead of creating an empty replacement.')
    elif identity and not (state / 'postgres/data/PG_VERSION').is_file():
        raise WorkspaceError('Saved owner settings exist but the database is missing. Restore the workspace first.')
    return identity


def validate_owner(previous, owners):
    owners = set(owners)
    owner = previous.get('owner_id')
    if owner is not None and owner not in owners:
        raise WorkspaceError('The saved owner is absent from this database. Refusing to create a replacement workspace.')
    if owner is None and owners:
        raise WorkspaceError('An existing database has no selected owner. Recover its identity before continuing.')


def pin_identity(state, owner):
    state = Path(state).resolve()
    dest = state / 'workspace-identity.json'
    value = {'format': 1, 'path': str(state), 'owner_id': owner}
    if dest.exists():
        if json.loads(dest.read_text()) != value:
            raise WorkspaceError('Refusing to replace the established workspace identity.')
        return
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
