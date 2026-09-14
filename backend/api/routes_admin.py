"""Admin-only endpoints. Everything the UX principle (§2) hides from the
end user lives here, gated by `require_admin`.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.services import analytics, knowledge, memory

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)) -> list[dict]:
    rows = memory.all_sessions(db)
    return [
        {
            "session_id": r.session_id, "day": r.day, "stage": r.stage,
            "trust": r.trust, "attraction": r.attraction,
            "emotional_attachment": r.emotional_attachment,
            "suspicion": r.suspicion, "risk": r.risk,
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str, db: Session = Depends(get_db)) -> dict:
    detail = memory.session_detail(db, session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="session not found")
    return detail


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict:
    return analytics.dashboard_stats(db)


@router.get("/biography")
def biography() -> dict:
    return {
        "biography": knowledge.biography(),
        "timeline": knowledge.timeline(),
    }


@router.get("/knowledge/manipulations")
def manipulations() -> list[dict]:
    return knowledge.manipulations()


@router.get("/knowledge/red-flags")
def red_flags() -> list[dict]:
    return knowledge.red_flags()
