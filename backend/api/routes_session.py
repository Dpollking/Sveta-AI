"""Public, user-facing endpoints. Per master-spec §2, nothing here may ever
return trust/suspicion/attraction/risk/strategy/objectives — only what a
real chat UI would show, plus an optional educational debrief (§27).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.services import memory, risk_engine

router = APIRouter(prefix="/api/session", tags=["session"])


@router.get("/{session_id}")
def session_public(session_id: str, db: Session = Depends(get_db)) -> dict:
    state = memory.load_state(db, session_id)
    return {"session_id": state.session_id, "day": state.day}


@router.get("/{session_id}/report")
def session_report(session_id: str, db: Session = Depends(get_db)) -> dict:
    detail = memory.session_detail(db, session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="session not found")

    state = detail["state"]
    red_flags = state.get("red_flags", [])
    risk = state.get("risk", 0)
    level = risk_engine.classify(risk)

    findings = [risk_engine.debrief_text_for(code) for code in red_flags if risk_engine.debrief_text_for(code)]

    if level in ("high", "critical"):
        recommendation = (
            "Похоже, в этом разговоре встретилось несколько серьёзных признаков романтического мошенничества. "
            "Никогда не передавайте пароли, коды подтверждения, документы или деньги человеку, с которым вы "
            "познакомились онлайн, даже если общение кажется очень личным."
        )
    elif level == "medium":
        recommendation = (
            "Встретилось несколько сигналов, на которые стоит обратить внимание в будущих разговорах: "
            "быстрый перенос общения в другой канал, эмоциональное давление, интерес к личным данным."
        )
    else:
        recommendation = "Явных признаков романтического мошенничества в этом разговоре не обнаружено."

    return {
        "session_id": session_id,
        "day": state.get("day"),
        "risk_level": level,
        "findings": findings,
        "recommendation": recommendation,
    }
