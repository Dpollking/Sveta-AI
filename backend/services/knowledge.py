import json
from functools import lru_cache

from backend.core.config import settings


def _load(name: str):
    path = settings.resolved_asset(settings.knowledge_dir) / name
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def biography() -> dict:
    return _load("sveta_biography.json")


@lru_cache(maxsize=1)
def timeline() -> list[dict]:
    return _load("sveta_timeline.json")


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
