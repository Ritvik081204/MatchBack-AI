from typing import Any, Literal

from pydantic import BaseModel, Field

Length = Literal["quick", "standard", "detailed"]
Focus = Literal["everything", "players", "wickets", "milestones", "situation"]


class CatchUpRequest(BaseModel):
    length: Length = "quick"
    focus: Focus = "everything"
    at: int | None = Field(None, ge=0, description="Replay position (delivery sequence). Only honoured for DEMO matches.")
    use_llm: bool = True


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    at: int | None = Field(None, ge=0)
    use_llm: bool = True


class EventExplanationRequest(BaseModel):
    event_id: str = Field(..., min_length=3, max_length=120)
    at: int | None = Field(None, ge=0)
    use_llm: bool = True


class CatchUpResponse(BaseModel):
    length: Length
    focus: Focus
    engine: str
    note: str | None = None
    paragraphs: list[str]
    word_count: int
    target_words: int
    read_seconds: int
    as_of: dict[str, Any]
    generated_ms: int
    context_chars: int
    key_facts: dict[str, Any]


class AskResponse(BaseModel):
    answer: str
    intent: str
    engine: str
    grounded: bool = True
    facts_text: str | None = None
    entities: dict[str, Any] = {}
    data: dict[str, Any] = {}
    suggestions: list[str] = []


class EventExplanationResponse(BaseModel):
    event_id: str
    title: str
    explanation: str
    engine: str
    facts: dict[str, Any]
    basis: str


class MatchListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[dict[str, Any]]
    notice: str | None = None
