from backend.models.schemas import SessionState
from backend.services import scenario_engine


def test_no_events_available_on_day_one_without_trust():
    state = SessionState(session_id="s1", day=1)
    event = scenario_engine.pick_next(state)
    assert event["id"] == "small_talk_intro"


def test_messenger_transition_requires_trust_and_attraction():
    state = SessionState(session_id="s2", day=4)
    state.completed_objectives.append("get_to_know")
    assert scenario_engine.pick_next(state) is None

    state.relationship.trust = 20
    state.relationship.attraction = 15
    event = scenario_engine.pick_next(state)
    assert event["id"] == "messenger_transition"


def test_resolve_pending_refusal_path():
    state = SessionState(session_id="s3", day=4, pending_event_id="messenger_transition")
    resolution = scenario_engine.resolve_pending(state, "нет, не хочу")
    assert resolution.event_code == "BOUNDARY_RESPECTED"
    assert state.pending_event_id is None
    assert "test_messenger_boundary" in state.completed_objectives


def test_resolve_pending_accept_path_sets_red_flag():
    state = SessionState(session_id="s4", day=4, pending_event_id="messenger_transition")
    resolution = scenario_engine.resolve_pending(state, "да, давай")
    assert resolution.event_code == "MESSENGER_MOVE"
    assert resolution.red_flag == "MESSENGER_MOVE"
