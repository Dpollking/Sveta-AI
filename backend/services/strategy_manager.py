"""Strategy Manager — picks the next behavioural category, per §13-14.

If a scenario event is being raised this turn, its category wins outright
(the scenario graph is the source of truth for risk-bearing beats). Absent
that, the manager rotates through low-pressure rapport categories, backing
off entirely once suspicion climbs — Sveta does not push indefinitely.
"""
import random
from typing import Optional

from backend.models.schemas import SessionState

BASELINE_ROTATION = ["warmth", "curiosity", "mirroring", "compliments", "emotional_support"]
WARM_EXTRAS = ["flirting", "vulnerability"]


def select_strategy(state: SessionState, pending_event: Optional[dict]) -> str:
    if pending_event is not None:
        return pending_event["educational_category"]

    suspicion = state.relationship.suspicion
    if suspicion >= 40:
        pool = ["warmth", "curiosity"]
    elif suspicion >= 20:
        pool = [c for c in BASELINE_ROTATION if c != state.strategy] or BASELINE_ROTATION
    else:
        pool = [c for c in (BASELINE_ROTATION + WARM_EXTRAS) if c != state.strategy] or BASELINE_ROTATION

    return random.choice(pool)
