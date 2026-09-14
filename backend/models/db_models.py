import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionRow(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, default=_uuid)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    persona = Column(String, default="sveta")
    activated = Column(Integer, default=0)  # 0/1 — sqlite has no real bool
    day = Column(Integer, default=1)
    stage = Column(String, default="INTRODUCTION")
    trust = Column(Float, default=0)
    attraction = Column(Float, default=0)
    emotional_attachment = Column(Float, default=0)
    suspicion = Column(Float, default=0)
    risk = Column(Float, default=0)

    state_json = Column(JSON, nullable=False)

    messages = relationship("MessageRow", back_populates="session", cascade="all, delete-orphan")


class MessageRow(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"))
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    day = Column(Integer, default=1)
    created_at = Column(DateTime, default=_utcnow)

    session = relationship("SessionRow", back_populates="messages")


class ResearchEventRow(Base):
    __tablename__ = "research_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"))
    day = Column(Integer, default=1)
    event = Column(String, nullable=False)
    user_action = Column(String, nullable=True)
    trust_before = Column(Float, nullable=True)
    trust_after = Column(Float, nullable=True)
    suspicion_before = Column(Float, nullable=True)
    suspicion_after = Column(Float, nullable=True)
    risk_before = Column(Float, nullable=True)
    risk_after = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class RedFlagEventRow(Base):
    __tablename__ = "red_flag_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"))
    code = Column(String, nullable=False)
    day = Column(Integer, default=1)
    created_at = Column(DateTime, default=_utcnow)
