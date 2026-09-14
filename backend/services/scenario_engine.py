"""Scenario Engine — decides *what happens*, never how it's phrased.

Per master-spec §9/§25: the LLM does not invent scenario state. This
module is the single source of truth for which event is currently being
tested and what the backend-controlled consequence of the user's reaction
is. `SvetaEngine` calls `resolve_pending` first (to close out whatever was
presented last turn), then `pick_next` (to decide what to raise this turn).
"""
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from backend.core.config import settings
from backend.models.schemas import SessionState
from backend.services.extraction import classify_boundary_response


@lru_cache(maxsize=1)
def _events() -> list[dict]:
    path = settings.resolved_asset(settings.knowledge_dir) / "scenario.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _event_by_id(event_id: str) -> Optional[dict]:
    return next((e for e in _events() if e["id"] == event_id), None)


def _trigger_satisfied(trigger: dict, state: SessionState) -> bool:
    if "min_trust" in trigger and state.relationship.trust < trigger["min_trust"]:
        return False
    if "min_attraction" in trigger and state.relationship.attraction < trigger["min_attraction"]:
        return False
    if "max_suspicion" in trigger and state.relationship.suspicion > trigger["max_suspicion"]:
        return False
    if "min_risk" in trigger and state.risk < trigger["min_risk"]:
        return False
    if "requires_event" in trigger and trigger["requires_event"] not in state.events:
        return False
    return True


@dataclass
class Resolution:
    event_code: str
    red_flag: Optional[str]
    trust_delta: float
    suspicion_delta: float
    objective: str


def resolve_pending(state: SessionState, user_message: str) -> Optional[Resolution]:
    if not state.pending_event_id:
        return None

    event = _event_by_id(state.pending_event_id)
    state.pending_event_id = None
    if event is None:
        return None

    has_refusal_branch = "on_refuse" in event
    if has_refusal_branch:
        response = classify_boundary_response(user_message)
        branch = event["on_refuse"] if response in ("refuse", "suspicious") else event["on_accept"]
    else:
        branch = event["on_accept"]

    state.completed_objectives.append(event["objective"])
    state.events.append(branch["event"])

    return Resolution(
        event_code=branch["event"],
        red_flag=branch.get("red_flag"),
        trust_delta=branch.get("trust_delta", 0),
        suspicion_delta=branch.get("suspicion_delta", 0),
        objective=event["objective"],
    )


def pick_next(state: SessionState) -> Optional[dict]:
    """Choose the next scenario event to raise this turn, if any is due."""
    candidates = [
        e for e in _events()
        if e["objective"] not in state.completed_objectives
        and e["available_from_day"] <= state.day <= e.get("available_until_day", 999)
        and _trigger_satisfied(e.get("trigger", {}), state)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda e: e["available_from_day"])
    return candidates[0]
