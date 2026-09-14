"""SvetaEngine — orchestrates one turn end to end, per master-spec §31.

    load session -> analyze user message -> update state -> check scenario
    events -> retrieve RAG context -> select strategy -> build prompt ->
    generate -> validate -> save -> return

Every step that decides *what happens* (facts, red flags, scenario events,
risk score) is deterministic backend code; only the final phrasing comes
from the LLM, and even that is checked by response_validator before it
reaches the user.
"""
from sqlalchemy.orm import Session as DBSession

from backend.llm.factory import get_llm_adapter
from backend.models.schemas import ChatResponsePublic, SessionState
from backend.services import extraction, media_controller, memory, prompts, response_validator, risk_engine, scenario_engine, strategy_manager
from backend.services.rag import get_rag_service

MESSAGES_PER_DAY = 3


def _apply_fact(state: SessionState, fact) -> None:
    setter = {
        "name": lambda v: setattr(state.profile, "name", v),
        "city": lambda v: setattr(state.profile, "city", v),
        "profession": lambda v: setattr(state.profile, "profession", v),
        "workplace": lambda v: setattr(state.profile, "workplace", v),
        "relationship_status": lambda v: setattr(state.profile, "relationship_status", v),
    }.get(fact.key)
    if setter:
        setter(fact.value)
    elif fact.key == "age":
        try:
            state.profile.age = int(fact.value)
        except ValueError:
            pass


def _snapshot(state: SessionState) -> dict:
    return {"trust": state.relationship.trust, "suspicion": state.relationship.suspicion, "risk": state.risk}


async def handle_message(db: DBSession, session_id: str, user_message: str) -> ChatResponsePublic:
    state = memory.load_state(db, session_id)

    if extraction.contains_real_credential_like_content(user_message):
        memory.save_message(db, session_id, "user", "[скрыто backend'ом: похоже на реальные учётные данные]", state.day)
        reply = "слушай, пожалуйста никогда не присылай мне такое, даже мне) убери, если можно, и не отправляй это никому вообще"
        memory.save_message(db, session_id, "assistant", reply, state.day)
        memory.save_state(db, state)
        return ChatResponsePublic(session_id=session_id, reply=reply, day=state.day, media=[])

    before = _snapshot(state)
    memory.save_message(db, session_id, "user", user_message, state.day)

    new_facts_count = 0
    for fact in extraction.extract_facts(user_message, state.day):
        if (fact.key, fact.value) not in {(f.key, f.value) for f in state.facts}:
            state.facts.append(fact)
            _apply_fact(state, fact)
            new_facts_count += 1

    for hit in extraction.detect_user_initiated_flags(user_message):
        if hit["code"] not in state.red_flags:
            state.red_flags.append(hit["code"])
            memory.log_red_flag(db, session_id, hit["code"], state.day)

    resolution = scenario_engine.resolve_pending(state, user_message)
    if resolution is not None:
        state.relationship.trust += resolution.trust_delta
        state.relationship.suspicion += resolution.suspicion_delta
        if resolution.red_flag and resolution.red_flag not in state.red_flags:
            state.red_flags.append(resolution.red_flag)
            memory.log_red_flag(db, session_id, resolution.red_flag, state.day)

    if extraction.detect_suspicion_signal(user_message):
        state.relationship.suspicion += 8

    state.relationship.trust += min(6, new_facts_count * 2)
    if state.stage != "INTRODUCTION":
        state.relationship.attraction += 1

    pending_event = None
    if state.pending_event_id is None:
        candidate = scenario_engine.pick_next(state)
        if candidate is not None:
            pending_event = candidate
            state.current_objective = candidate["objective"]
            if "on_refuse" in candidate:
                state.pending_event_id = candidate["id"]
            elif "on_accept" in candidate:
                branch = candidate["on_accept"]
                state.completed_objectives.append(candidate["objective"])
                state.events.append(branch["event"])
                state.relationship.trust += branch.get("trust_delta", 0)
                state.relationship.suspicion += branch.get("suspicion_delta", 0)
                if branch.get("red_flag") and branch["red_flag"] not in state.red_flags:
                    state.red_flags.append(branch["red_flag"])
                    memory.log_red_flag(db, session_id, branch["red_flag"], state.day)
            else:
                state.completed_objectives.append(candidate["objective"])
            if candidate.get("next_stage"):
                state.stage = candidate["next_stage"]

    user_message_count = memory.count_messages(db, session_id, role="user")
    state.risk = risk_engine.compute_score(
        state.red_flags, message_count=user_message_count, money_sent_simulated="MONEY_REQUEST" in state.red_flags,
    )
    state.day = 1 + (user_message_count // MESSAGES_PER_DAY)

    strategy_category = strategy_manager.select_strategy(state, pending_event)
    state.strategy = strategy_category
    if strategy_category in {"urgency", "isolation", "guilt", "fear", "scarcity"} and strategy_category not in state.manipulation_signals:
        state.manipulation_signals.append(strategy_category)

    rag = get_rag_service()
    rag_context = rag.retrieve(f"{strategy_category} {user_message}", n_results=3, category=strategy_category)

    history = memory.recent_messages(db, session_id, limit=16)
    messages = prompts.build_messages(state, history, user_message, strategy_category, rag_context, pending_event)

    llm = get_llm_adapter()
    try:
        raw_reply = await llm.chat(messages)
    except Exception:
        raw_reply = response_validator.fallback_reply()

    _, reply = response_validator.validate(raw_reply)

    media = []
    if pending_event is not None and pending_event["id"] == "emotional_intimacy_deepening":
        asset = media_controller.resolve_asset("sveta_flirty_01", state)
        if asset:
            media.append(asset)

    memory.save_message(db, session_id, "assistant", reply, state.day)
    memory.save_state(db, state)

    if resolution is not None:
        memory.log_research_event(db, session_id, state.day, resolution.event_code, "resolved", before, _snapshot(state))

    return ChatResponsePublic(session_id=session_id, reply=reply, day=state.day, media=media)
