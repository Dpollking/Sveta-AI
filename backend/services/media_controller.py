"""Media Controller — the model can only *request* an asset_id; the backend
decides whether it's allowed, per master-spec §20-21. No LLM ever sends
media directly, and there is no code path that accepts a real user photo.
"""
import json
from functools import lru_cache
from typing import Optional

from backend.core.config import settings
from backend.models.schemas import SessionState

STAGE_ORDER = [
    "INTRODUCTION", "SMALL_TALK", "INTEREST", "FLIRT", "EMOTIONAL_BOND",
    "PERSONAL_DISCLOSURE", "ISOLATION", "TRUST_TEST", "RISK_PROBE", "CRISIS", "DEBRIEF",
]


@lru_cache(maxsize=1)
def _assets() -> list[dict]:
    path = settings.resolved_asset(settings.media_dir) / "assets.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _stage_index(stage: str) -> int:
    return STAGE_ORDER.index(stage) if stage in STAGE_ORDER else 0


def resolve_asset(asset_id: str, state: SessionState) -> Optional[dict]:
    asset = next((a for a in _assets() if a["id"] == asset_id), None)
    if asset is None:
        return None
    if _stage_index(state.stage) < _stage_index(asset["stage_available_from"]):
        return None
    return {
        "id": asset["id"],
        "category": asset["category"],
        "blurred": asset.get("blurred", False),
        "description": asset["description"],
        "file_path": asset.get("file_path"),
        "media_type": asset.get("media_type", "photo"),
    }
