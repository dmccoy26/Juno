import hashlib
import secrets
from sqlalchemy import select
from .models import Device, Owner


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def provision(session, label, owner_id=None):
    if owner_id is None:
        owner = Owner(label=label)
        session.add(owner)
        session.flush()
        owner_id = owner.id
    elif session.get(Owner, owner_id) is None:
        raise ValueError("Unknown owner.")
    token = secrets.token_urlsafe(48)
    device = Device(owner_id=owner_id, label=label, token_hash=digest(token))
    session.add(device)
    session.flush()
    return device, token


def authenticate(session, token):
    if not token or len(token) > 256:
        return None
    return session.scalar(select(Device).where(Device.token_hash == digest(token), Device.revoked.is_(False)))
