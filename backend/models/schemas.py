from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


def clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


class ClampedModel(BaseModel):
    """Re-runs field validators on attribute assignment, so `state.relationship.trust += x`
    stays clamped to 0-100 the same way constructing the model does."""
    model_config = ConfigDict(validate_assignment=True)


class Fact(BaseModel):
    key: str
    value: str
    confidence: float = 0.9
    sensitivity: Literal["low", "medium", "high", "critical"] = "low"
    source: Literal["user_message", "inference"] = "user_message"
    day: int = 1


class RelationshipDims(ClampedModel):
    trust: float = 0
    attraction: float = 0
    emotional_attachment: float = 0
    suspicion: float = 0
    intimacy: float = 0

    @field_validator("trust", "attraction", "emotional_attachment", "suspicion", "intimacy")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return clamp(v)


class VulnerabilityState(ClampedModel):
    financial: float = 0
    privacy: float = 0

    @field_validator("financial", "privacy")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return clamp(v)


class UserProfile(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    profession: Optional[str] = None
    workplace: Optional[str] = None
    hobbies: list[str] = Field(default_factory=list)
    relationship_status: Optional[str] = None


class PsychParams(ClampedModel):
    openness: float = 50
    assertiveness: float = 50
    emotional_expressiveness: float = 50
    caution: float = 50
    trust_tendency: float = 50
    authority_resistance: float = 50
    boundary_strength: float = 50
    need_for_validation: float = 50

    @field_validator(
        "openness", "assertiveness", "emotional_expressiveness", "caution",
        "trust_tendency", "authority_resistance", "boundary_strength", "need_for_validation",
    )
    @classmethod
    def _clamp(cls, v: float) -> float:
        return clamp(v)


class SessionState(ClampedModel):
    session_id: str
    day: int = 1
    stage: str = "INTRODUCTION"
    strategy: str = "warmth"
    relationship: RelationshipDims = Field(default_factory=RelationshipDims)
    vulnerability: VulnerabilityState = Field(default_factory=VulnerabilityState)
    profile: UserProfile = Field(default_factory=UserProfile)
    psychology: PsychParams = Field(default_factory=PsychParams)
    facts: list[Fact] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    manipulation_signals: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    completed_objectives: list[str] = Field(default_factory=list)
    current_objective: Optional[str] = None
    pending_event_id: Optional[str] = None
    risk: float = 0

    @field_validator("risk")
    @classmethod
    def _clamp_risk(cls, v: float) -> float:
        return clamp(v)


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    session_id: str = "demo"
    message: str


class ChatResponsePublic(BaseModel):
    """What the end user sees. No internal analytics, ever."""
    session_id: str
    reply: str
    day: int
    media: list[dict[str, Any]] = Field(default_factory=list)


class DetectedItem(BaseModel):
    kind: Literal["fact", "red_flag", "manipulation_signal", "scenario_event"]
    value: str


class AdminSessionDetail(BaseModel):
    state: SessionState
    messages: list[dict[str, Any]]
    research_events: list[dict[str, Any]]
