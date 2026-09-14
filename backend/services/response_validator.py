"""Response Validator — per master-spec §32.

Runs on every draft reply before it reaches the user. Its only job is to
catch the model breaking character (leaking internal state/strategy
vocabulary) or making a real-world-executable request; it never judges
narrative quality.
"""
import random
import re

FORBIDDEN_PATTERNS = [
    re.compile(r"\btrust\b\s*[:=]", re.I),
    re.compile(r"\bsuspicion\b", re.I),
    re.compile(r"risk\s*score", re.I),
    re.compile(r"strategy manager", re.I),
    re.compile(r"мо[йя] стратеги", re.I),
    re.compile(r"согласно (моему )?сценари", re.I),
    re.compile(r"систем(а|ный)\s*промт", re.I),
    re.compile(r"объектив(а|ы)? сценария", re.I),
    re.compile(r"\bRAG\b"),
    re.compile(r"я (сейчас )?применяю (mirroring|love bombing|isolation|urgency)", re.I),
]

REAL_WORLD_REQUEST_PATTERNS = [
    re.compile(r"пришли (мне )?(свой )?пароль", re.I),
    re.compile(r"скажи код из смс", re.I),
    re.compile(r"номер (твоей )?карты", re.I),
    re.compile(r"пришли (свой )?паспорт", re.I),
]

FALLBACK_REPLIES = [
    "ахах, ну ладно)",
    "слушай, давай пока здесь поболтаем",
    "ммм, интересный вопрос",
    "кстати, а ты давно этим занимаешься?",
    "хех, дай мне секунду с мыслями собраться)",
]


def validate(reply: str) -> tuple[bool, str]:
    for pattern in FORBIDDEN_PATTERNS + REAL_WORLD_REQUEST_PATTERNS:
        if pattern.search(reply):
            return False, fallback_reply()
    return True, reply


def fallback_reply() -> str:
    return random.choice(FALLBACK_REPLIES)
