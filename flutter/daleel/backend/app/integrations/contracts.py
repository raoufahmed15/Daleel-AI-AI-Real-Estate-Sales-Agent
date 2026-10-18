"""Integration contracts for the three modules implemented separately (NOT implemented here):
Recommendation Engine, Lead Scoring, RAG.

A future module registers a plain callable `handler(request) -> response` with the registry.
Until then every request returns an explicit `not_implemented` response; nothing is ever invented.
"""
from typing import Callable, Literal

from pydantic import BaseModel, Field

ModuleStatus = Literal["not_implemented", "not_configured", "integrated"]


class ModuleNotConfigured(Exception):
    """Raise from a registered handler when it exists but lacks configuration (-> 503 not_configured)."""


# ---- Recommendation Engine ---------------------------------------------------
class RecommendationRequest(BaseModel):
    lead_id: int | None = None
    budget: int | None = Field(None, ge=0)
    preferred_location: str | None = None
    property_type: str | None = None
    min_bedrooms: int | None = Field(None, ge=0)
    limit: int = Field(5, ge=1, le=20)


class RecommendedProperty(BaseModel):
    property_id: int
    rank: int
    explanation: str


class RecommendationResponse(BaseModel):
    status: Literal["integrated"] = "integrated"
    items: list[RecommendedProperty]


# ---- Lead Scoring -----------------------------------------------------------
class LeadScoringRequest(BaseModel):
    lead_id: int


class LeadScoringResponse(BaseModel):
    status: Literal["integrated"] = "integrated"
    lead_id: int
    score: float = Field(..., ge=0, le=100)
    explanations: list[str]


# ---- RAG --------------------------------------------------------------------
class RagRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    lead_id: int | None = None
    top_k: int = Field(5, ge=1, le=20)


class RagEvidence(BaseModel):
    text: str
    source: str
    score: float | None = None


class RagResponse(BaseModel):
    status: Literal["integrated"] = "integrated"
    answer: str
    evidence: list[RagEvidence]
    sources: list[str]


MODULES = {
    "recommendation_engine": {
        "title": "Recommendation Engine",
        "description": "Receives lead requirements and returns eligible properties with ranking explanations.",
        "request": RecommendationRequest, "response": RecommendationResponse,
        "route": "/api/integrations/recommendation-engine/query",
    },
    "lead_scoring": {
        "title": "Lead Scoring",
        "description": "Receives lead information and returns a score with supporting explanations.",
        "request": LeadScoringRequest, "response": LeadScoringResponse,
        "route": "/api/integrations/lead-scoring/score",
    },
    "rag": {
        "title": "RAG (Retrieval-Augmented Generation)",
        "description": "Receives a question and returns an answer, supporting evidence and source references.",
        "request": RagRequest, "response": RagResponse,
        "route": "/api/integrations/rag/query",
    },
}


class ModuleRegistry:
    """Single registration point. Future code calls `registry.register("rag", handler)`."""

    def __init__(self):
        self._handlers: dict[str, Callable] = {}

    def register(self, name: str, handler: Callable):
        if name not in MODULES:
            raise KeyError(f"Unknown module '{name}'. Valid: {sorted(MODULES)}")
        self._handlers[name] = handler

    def get(self, name: str):
        return self._handlers.get(name)

    def status(self, name: str) -> ModuleStatus:
        return "integrated" if name in self._handlers else "not_implemented"
