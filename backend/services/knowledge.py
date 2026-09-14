import json
from functools import lru_cache

from backend.core.config import settings

DEFAULT_PERSONA = "sveta"
KNOWN_PERSONAS = ("sveta", "sergey")


def _load(name: str):
    path = settings.resolved_asset(settings.knowledge_dir) / name
    return json.loads(path.read_text(encoding="utf-8"))


def _persona_or_default(persona: str) -> str:
    return persona if persona in KNOWN_PERSONAS else DEFAULT_PERSONA


@lru_cache(maxsize=len(KNOWN_PERSONAS))
def biography(persona: str = DEFAULT_PERSONA) -> dict:
    return _load(f"personas/{_persona_or_default(persona)}/biography.json")


@lru_cache(maxsize=len(KNOWN_PERSONAS))
def timeline(persona: str = DEFAULT_PERSONA) -> list[dict]:
    return _load(f"personas/{_persona_or_default(persona)}/timeline.json")


@lru_cache(maxsize=1)
def manipulations() -> list[dict]:
    return _load("manipulations.json")


@lru_cache(maxsize=1)
def red_flags() -> list[dict]:
    return _load("red_flags.json")


@lru_cache(maxsize=1)
def educational_material() -> list[dict]:
    return _load("educational_material.json")


@lru_cache(maxsize=1)
def sources() -> list[dict]:
    return _load("sources.json")
