from backend.models.schemas import SessionState
from backend.services import strategy_manager


def test_pending_event_category_wins():
    state = SessionState(session_id="s1")
    event = {"educational_category": "urgency"}
    assert strategy_manager.select_strategy(state, event) == "urgency"


def test_high_suspicion_forces_low_pressure_pool():
    state = SessionState(session_id="s2")
    state.relationship.suspicion = 60
    for _ in range(20):
        assert strategy_manager.select_strategy(state, None) in {"warmth", "curiosity"}
