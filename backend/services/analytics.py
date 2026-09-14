from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from backend.models.db_models import RedFlagEventRow, SessionRow


def _persona_stats(db: DBSession, persona: str | None) -> dict:
    q = db.query(SessionRow)
    if persona is not None:
        q = q.filter(SessionRow.persona == persona)

    total = q.count()
    activated = q.filter(SessionRow.activated == 1).count()
    avg_trust = q.with_entities(func.avg(SessionRow.trust)).scalar() or 0
    avg_risk = q.with_entities(func.avg(SessionRow.risk)).scalar() or 0
    avg_suspicion = q.with_entities(func.avg(SessionRow.suspicion)).scalar() or 0

    flag_query = (
        db.query(RedFlagEventRow.code, func.count(RedFlagEventRow.id))
        .join(SessionRow, SessionRow.session_id == RedFlagEventRow.session_id)
    )
    if persona is not None:
        flag_query = flag_query.filter(SessionRow.persona == persona)
    flag_rows = flag_query.group_by(RedFlagEventRow.code).all()

    return {
        "total_sessions": total,
        "activated_sessions": activated,
        "avg_trust": round(float(avg_trust), 1),
        "avg_risk": round(float(avg_risk), 1),
        "avg_suspicion": round(float(avg_suspicion), 1),
        "red_flag_frequency": {code: count for code, count in flag_rows},
    }


def dashboard_stats(db: DBSession) -> dict:
    personas = [p for (p,) in db.query(SessionRow.persona).distinct().all() if p]
    return {
        "overall": _persona_stats(db, None),
        "by_persona": {persona: _persona_stats(db, persona) for persona in personas},
    }
