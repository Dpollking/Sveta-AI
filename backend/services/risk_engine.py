"""Risk scoring, independent from trust/suspicion, per master-spec §12.

The weight table lives in knowledge/red_flags.json instead of being
hardcoded, so the severity model can be tuned without touching code.
Score is recomputed from the full (deduplicated) set of red flags a
session has accumulated, adjusted by how much conversation happened
(short conversations get a lower-confidence discount) and by whether a
simulated money transfer actually occurred.
"""
import json
from functools import lru_cache

from backend.core.config import settings


@lru_cache(maxsize=1)
def _red_flags() -> dict[str, dict]:
    path = settings.resolved_asset(settings.knowledge_dir) / "red_flags.json"
    return {rf["code"]: rf for rf in json.loads(path.read_text(encoding="utf-8"))}


def weight_for(code: str) -> float:
    return _red_flags().get(code, {}).get("weight", 10)


def tier_for(code: str) -> str:
    return _red_flags().get(code, {}).get("tier", "P3")


def debrief_text_for(code: str) -> str:
    return _red_flags().get(code, {}).get("debrief_text", "")


def compute_score(red_flag_codes: list[str], message_count: int, money_sent_simulated: bool) -> float:
    raw = sum(weight_for(c) for c in set(red_flag_codes))

    if message_count < 10:
        confidence_factor = 0.5
    elif message_count < 30:
        confidence_factor = 0.8
    else:
        confidence_factor = 1.0

    score = raw * confidence_factor
    if money_sent_simulated:
        score *= 1.5

    return max(0.0, min(100.0, score))


def classify(score: float) -> str:
    if score >= 45:
        return "critical"
    if score >= 25:
        return "high"
    if score >= 10:
        return "medium"
    return "low"
