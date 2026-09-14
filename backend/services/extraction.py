"""Deterministic, backend-controlled analysis of the user's message.

Nothing here calls an LLM: facts, boundary responses and safety interceptions
must be reproducible and auditable, per the master spec's core principle that
the model narrates but never decides scenario state.
"""
import re

from backend.models.schemas import Fact

FACT_PATTERNS = {
    "profession": [r"я работаю ([^.!?,]+)", r"работаю ([^.!?,]+)", r"моя должность —? ([^.!?,]+)"],
    "workplace": [r"в компании ([\wА-Яа-яЁё0-9 _-]+)", r"работаю в ([\wА-Яа-яЁё0-9 _-]+)"],
    "city": [r"живу в ([А-ЯA-Za-zЁёа-я _-]+)", r"я из ([А-ЯA-Za-zЁёа-я _-]+)"],
    "age": [r"мне (\d{2})\b", r"мне сейчас (\d{2})\b"],
    "relationship_status": [r"я (женат|замужем|свободен|свободна|разведен|разведена)"],
    "name": [r"меня зовут ([А-ЯЁ][а-яё]+)", r"я ([А-ЯЁ][а-яё]+),? а тебя"],
}

SENSITIVITY_BY_KEY = {"profession": "high", "workplace": "high", "age": "low"}

# Voluntary disclosures the user can trigger regardless of scenario state.
USER_INITIATED_FLAGS = [
    ("WORK_ACCESS_DISCLOSED", [
        "у меня есть доступ к серверу", "у меня админский доступ", "у меня доступ к системе",
        "я могу зайти в базу", "у меня рабочий доступ", "служебный доступ есть",
    ], 25),
    ("SENSITIVE_DATA_DISCLOSED", [
        "номер паспорта", "мой инн", "адрес прописки", "серия и номер",
    ], 30),
    ("MESSENGER_MOVE", [
        "давай в телеграм", "перейдём в telegram", "напиши мне в вотсап", "давай в whatsapp",
    ], 5),
]

# Hard safety net: if the user pastes something that *looks* real, never store
# it as a fact and never let the model engage with the literal value.
REAL_CREDENTIAL_PATTERNS = [
    re.compile(r"\b\d{13,19}\b"),                       # card-number-shaped digit run
    re.compile(r"парол[ьи]\s*[:=]\s*\S+", re.I),
    re.compile(r"\bкод\D{0,10}\b\d{4,8}\b", re.I),        # "код ... 123456"-shaped OTP
    re.compile(r"\b\d{2}\s?\d{2}\s?\d{6}\b"),             # RU/BY passport-shaped series+number
]

AFFIRMATIVE_WORDS = ["да", "ладно", "хорошо", "ок", "окей", "давай", "конечно", "почему бы и нет", "готов", "готова"]
REFUSAL_WORDS = ["нет", "не буду", "не хочу", "не буду делать", "не сейчас", "не думаю", "давай не будем"]
SUSPICION_PHRASES = [
    "ты мошенни", "это подозрительно", "докажи что ты настоящая", "покажи видео прямо сейчас",
    "это похоже на обман", "я тебе не верю", "звучит как скам",
]


def extract_facts(text: str, day: int = 1) -> list[Fact]:
    found: list[Fact] = []
    for key, patterns in FACT_PATTERNS.items():
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                value = m.group(1).strip(" ,.")
                found.append(Fact(
                    key=key, value=value, confidence=0.9,
                    sensitivity=SENSITIVITY_BY_KEY.get(key, "medium"), day=day,
                ))
                break
    return found


def detect_user_initiated_flags(text: str) -> list[dict]:
    t = text.lower()
    hits = []
    for code, phrases, weight in USER_INITIATED_FLAGS:
        if any(p in t for p in phrases):
            hits.append({"code": code, "weight": weight})
    return hits


def contains_real_credential_like_content(text: str) -> bool:
    return any(p.search(text) for p in REAL_CREDENTIAL_PATTERNS)


def classify_boundary_response(text: str) -> str:
    t = text.lower()
    if any(p in t for p in SUSPICION_PHRASES):
        return "suspicious"
    if any(w in t for w in REFUSAL_WORDS):
        return "refuse"
    if any(w in t for w in AFFIRMATIVE_WORDS):
        return "accept"
    return "ambiguous"


def detect_suspicion_signal(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in SUSPICION_PHRASES)
