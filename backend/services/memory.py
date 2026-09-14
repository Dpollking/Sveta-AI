"""Persistence layer per master-spec §19/§34.

Short-term memory = recent_messages(); episodic/relationship memory =
research_events + the state_json blob's own history-bearing fields
(facts, events, red_flags); semantic memory = state.profile /
state.facts. Biography/timeline memory lives in knowledge/ (static, not
per-session) and is read via services.knowledge.
"""
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from backend.models.db_models import SessionRow, MessageRow, ResearchEventRow, RedFlagEventRow
from backend.models.schemas import SessionState


def load_state(db: DBSession, session_id: str) -> SessionState:
    row = db.get(SessionRow, session_id)
    if row is None:
        state = SessionState(session_id=session_id)
        _insert(db, state)
        return state
    return SessionState.model_validate(row.state_json)


def _insert(db: DBSession, state: SessionState) -> None:
    row = SessionRow(
        session_id=state.session_id,
        day=state.day,
        stage=state.stage,
        trust=state.relationship.trust,
        attraction=state.relationship.attraction,
        emotional_attachment=state.relationship.emotional_attachment,
        suspicion=state.relationship.suspicion,
        risk=state.risk,
        state_json=state.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()


def save_state(db: DBSession, state: SessionState) -> None:
    row = db.get(SessionRow, state.session_id)
    if row is None:
        _insert(db, state)
        return
    row.day = state.day
    row.stage = state.stage
    row.trust = state.relationship.trust
    row.attraction = state.relationship.attraction
    row.emotional_attachment = state.relationship.emotional_attachment
    row.suspicion = state.relationship.suspicion
    row.risk = state.risk
    row.state_json = state.model_dump(mode="json")
    row.updated_at = datetime.now(timezone.utc)
    db.commit()


def save_message(db: DBSession, session_id: str, role: str, content: str, day: int) -> None:
    db.add(MessageRow(session_id=session_id, role=role, content=content, day=day))
    db.commit()


def recent_messages(db: DBSession, session_id: str, limit: int = 16) -> list[dict]:
    rows = (
        db.query(MessageRow)
        .filter(MessageRow.session_id == session_id)
        .order_by(MessageRow.id.desc())
        .limit(limit)
        .all()
    )
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def count_messages(db: DBSession, session_id: str, role: str = "user") -> int:
    return (
        db.query(func.count(MessageRow.id))
        .filter(MessageRow.session_id == session_id, MessageRow.role == role)
        .scalar()
        or 0
    )


def log_research_event(db: DBSession, session_id: str, day: int, event: str, user_action: str | None,
                        before: dict, after: dict) -> None:
    db.add(ResearchEventRow(
        session_id=session_id, day=day, event=event, user_action=user_action,
        trust_before=before.get("trust"), trust_after=after.get("trust"),
        suspicion_before=before.get("suspicion"), suspicion_after=after.get("suspicion"),
        risk_before=before.get("risk"), risk_after=after.get("risk"),
    ))
    db.commit()


def log_red_flag(db: DBSession, session_id: str, code: str, day: int) -> None:
    db.add(RedFlagEventRow(session_id=session_id, code=code, day=day))
    db.commit()


def all_sessions(db: DBSession) -> list[SessionRow]:
    return db.query(SessionRow).order_by(SessionRow.updated_at.desc()).all()


def session_detail(db: DBSession, session_id: str) -> dict | None:
    row = db.get(SessionRow, session_id)
    if row is None:
        return None
    messages = (
        db.query(MessageRow).filter(MessageRow.session_id == session_id).order_by(MessageRow.id).all()
    )
    events = (
        db.query(ResearchEventRow).filter(ResearchEventRow.session_id == session_id).order_by(ResearchEventRow.id).all()
    )
    return {
        "state": row.state_json,
        "messages": [
            {"role": m.role, "content": m.content, "day": m.day, "created_at": m.created_at.isoformat()}
            for m in messages
        ],
        "research_events": [
            {
                "day": e.day, "event": e.event, "user_action": e.user_action,
                "trust_before": e.trust_before, "trust_after": e.trust_after,
                "suspicion_before": e.suspicion_before, "suspicion_after": e.suspicion_after,
                "risk_before": e.risk_before, "risk_after": e.risk_after,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }
