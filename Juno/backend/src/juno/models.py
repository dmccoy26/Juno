from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def ident():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Owner(Base):
    __tablename__ = "owners"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=ident)
    label: Mapped[str] = mapped_column(String(200))


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=ident)
    owner_id: Mapped[str] = mapped_column(ForeignKey("owners.id"), index=True)
    label: Mapped[str] = mapped_column(String(200))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    revoked: Mapped[bool] = mapped_column(default=False)


class Memory(Base):
    __tablename__ = "memories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=ident)
    owner_id: Mapped[str] = mapped_column(ForeignKey("owners.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(500))
    confidence: Mapped[str] = mapped_column(String(20))
    fingerprint: Mapped[str] = mapped_column(String(64))
    source_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id",ondelete="SET NULL",name="fk_memory_source_message"),nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("owner_id", "fingerprint"),UniqueConstraint("owner_id","source_message_id",name="uq_memory_owner_source_message"))


class Suppression(Base):
    __tablename__ = "memory_suppressions"
    owner_id: Mapped[str] = mapped_column(ForeignKey("owners.id"), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=ident)
    owner_id: Mapped[str] = mapped_column(ForeignKey("owners.id"), index=True)
    device_id: Mapped[str] = mapped_column(String(36))
    record_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(40))
    revision: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ModelConnection(Base):
    __tablename__ = 'model_connections'
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), primary_key=True)
    base_url: Mapped[str] = mapped_column(String(500))
    model: Mapped[str] = mapped_column(String(200))


class Conversation(Base):
    __tablename__ = 'conversations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=ident)
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


from sqlalchemy import BigInteger, Identity, Date
from sqlalchemy.dialects.postgresql import JSONB
from datetime import date


class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=ident)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id', ondelete='CASCADE'), index=True)
    order_key: Mapped[int] = mapped_column(BigInteger, Identity(), unique=True)
    role: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    request_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(20))
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    meeting_mode: Mapped[bool] = mapped_column(default=False)
    context_refs: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint('conversation_id', 'request_id', 'role'),)


class CheckIn(Base):
    __tablename__ = 'check_ins'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=ident)
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    answers: Mapped[dict] = mapped_column(JSONB, default=dict)
    diary_text: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(20), default='draft')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint('owner_id', 'local_date'),)


class TaskDockSnapshot(Base):
    """Immutable dated read cache, never the task system of record."""
    __tablename__ = 'taskdock_snapshots'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=ident)
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), index=True)
    origin: Mapped[str] = mapped_column(String(500))
    info: Mapped[dict] = mapped_column(JSONB)
    items: Mapped[list] = mapped_column(JSONB)
    sources: Mapped[list] = mapped_column(JSONB)
    snapshot: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TaskDockState(Base):
    __tablename__ = 'taskdock_state'
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), primary_key=True)
    active_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class TaskDockHistory(Base):
    __tablename__ = 'taskdock_history'
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey('taskdock_snapshots.id'), primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    items: Mapped[list] = mapped_column(JSONB)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PairingInvitation(Base):
    __tablename__ = 'pairing_invitations'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(default=False)


class OfflineOperation(Base):
    __tablename__ = 'offline_operations'
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), primary_key=True)
    operation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSONB)


class IntegrationSnapshot(Base):
    """Latest source per owner, or an empty version fence after connection/content removal."""
    __tablename__ = 'integration_snapshots'
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), default=ident)
    origin: Mapped[str] = mapped_column(String(500))
    items: Mapped[list] = mapped_column(JSONB)
    details: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class PlanningState(Base):
    __tablename__ = 'planning_state'
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ScheduleState(Base):
    __tablename__ = 'schedule_state'
    owner_id: Mapped[str] = mapped_column(ForeignKey('owners.id'), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
