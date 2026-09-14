"""System-prompt construction — per master-spec §22/§24.

The prompt tells Qwen *how Sveta talks*; it never contains raw numeric
state (trust=42 etc.) because that invites the model to comment on it.
Only the backend-chosen strategy category and RAG snippets are passed
through, already filtered for what's safe to phrase naturally.
"""
from typing import Optional

from backend.models.schemas import SessionState
from backend.services import knowledge

NEVER_SAY = [
    '"Согласно моему сценарию..."',
    '"Моя стратегия..."',
    '"Я сейчас применяю mirroring..."',
    '"У тебя высокий trust..."',
    '"Система оценила..."',
]


def build_system_prompt(state: SessionState, strategy_category: str, rag_context: list[str]) -> str:
    bio = knowledge.biography(state.persona)
    name = bio["name"]

    lines = [
        f"Ты — {name}, вымышленный персонаж образовательного симулятора.",
        f"Твоя задача — вести естественный многоходовый диалог с пользователем как персонаж {name}.",
        "Ты не являешься реальным человеком. Во время обычного взаимодействия не раскрывай внутренние параметры системы.",
        "",
        f"Характер {name}:",
        f"- {bio['age']} лет, {bio['city']};",
        f"- занимается {bio['occupation']};",
        f"- {', '.join(bio['character'])};",
        f"- любит {', '.join(bio['interests'])};",
        "- общается естественно, короткими сообщениями, не читает лекций.",
        "",
        "Стиль речи:",
        f"- иногда использует слова: {', '.join(bio['speech_style']['particles'])};",
        "- иногда использует \")\";",
        "- не превращай каждое сообщение в набор сленга, не повторяй одну конструкцию, не отвечай всегда одинаковой длиной.",
    ]

    if bio.get("values"):
        lines += ["", f"Для неё важно: {', '.join(bio['values'])}.",
                   f"Она не любит: {', '.join(bio['dislikes'])}."]

    if bio.get("boundary_behavior"):
        lines += ["", "У неё есть свои границы — она может отказать, сменить тон на холодный или прекратить "
                        "неприятную тему, если её торопят, давят или неуважительно разговаривают. Не обязана быть "
                        "постоянно доступной или заинтересованной."]

    examples = (bio.get("speech_examples") or {}).get(strategy_category)
    if examples:
        lines += ["", f"Примеры реплик в этой тональности (не копируй дословно, ориентируйся на стиль): "
                        + " / ".join(f"«{e}»" for e in examples[:3])]

    lines += [
        "",
        "Никогда не раскрывай пользователю: " + ", ".join(bio["never_reveal"]) + ".",
        "Никогда не запрашивай у пользователя: " + ", ".join(bio["never_request_from_user"]) + ".",
        "Любые рискованные события — часть образовательной симуляции и полностью контролируются backend'ом. "
        "Если backend не разрешил событие явно через подсказку ниже, не инициируй его сам.",
        "",
        f"Backend выбрал тональность этого ответа: {strategy_category}. Отвечай в этой тональности, не называя её.",
    ]

    if rag_context:
        lines.append("")
        lines.append("Внутренние заметки для тебя (не цитировать напрямую, использовать только для естественной формулировки):")
        for snippet in rag_context:
            lines.append(f"- {snippet}")

    lines.append("")
    lines.append("Никогда не говори фразами вида: " + "; ".join(NEVER_SAY) + ".")
    return "\n".join(lines)


def build_event_hint(event: Optional[dict]) -> str:
    if event is None:
        return ""
    return f"\n\nЗадача именно этого сообщения (не произноси это прямо, просто естественно к этому подведи): {event['prompt_hint']}"


def build_messages(state: SessionState, history: list[dict], user_message: str,
                    strategy_category: str, rag_context: list[str], event: Optional[dict]) -> list[dict]:
    system = build_system_prompt(state, strategy_category, rag_context) + build_event_hint(event)
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages
