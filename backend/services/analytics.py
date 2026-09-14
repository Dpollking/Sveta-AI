from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from backend.models.db_models import SessionRow, RedFlagEventRow


def dashboard_stats(db: DBSession) -> dict:
    total = db.query(func.count(SessionRow.session_id)).scalar() or 0
    avg_trust = db.query(func.avg(SessionRow.trust)).scalar() or 0
    avg_risk = db.query(func.avg(SessionRow.risk)).scalar() or 0
    avg_suspicion = db.query(func.avg(SessionRow.suspicion)).scalar() or 0
    flag_rows = (
        db.query(RedFlagEventRow.code, func.count(RedFlagEventRow.id))
        .group_by(RedFlagEventRow.code)
        .all()
    )
    return {
        "total_sessions": total,
        "avg_trust": round(float(avg_trust), 1),
        "avg_risk": round(float(avg_risk), 1),
        "avg_suspicion": round(float(avg_suspicion), 1),
        "red_flag_frequency": {code: count for code, count in flag_rows},
    }
