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
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("owner_id", "fingerprint"),)


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
