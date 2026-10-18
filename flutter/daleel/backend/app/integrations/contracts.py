"""Empty slots for local engines the owner will plug in later.

A future module registers `handler(request) -> response` on the registry.
Until then every request returns an explicit `not_implemented` response; nothing is invented.
"""
from datetime import date
from typing import Any, Callable, Literal

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
    source_updated_at: date | None = None
    source_version: str | None = Field(None, max_length=40)


class RagResponse(BaseModel):
    status: Literal["integrated"] = "integrated"
    answer: str
    evidence: list[RagEvidence]
    sources: list[str]


# ---- STT / TTS / OCR / LLM agent (local models the owner will drop in) ------
class SttRequest(BaseModel):
    audio_ref: str | None = Field(None, max_length=500)
    note: str | None = Field(None, max_length=500)


class SttResponse(BaseModel):
    status: Literal["integrated"] = "integrated"
    transcript: str
    confidence: float | None = None


class TtsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class TtsResponse(BaseModel):
    status: Literal["integrated"] = "integrated"
    audio_ref: str | None = None


class OcrRequest(BaseModel):
    document_name: str = Field(..., min_length=1, max_length=260)
    document_ref: str | None = Field(None, max_length=500)


class OcrResponse(BaseModel):
    status: Literal["integrated"] = "integrated"
    text: str
    fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None


class ChatTurn(BaseModel):
    role: str
    text: str


class LlmAgentRequest(BaseModel):
    messages: list[ChatTurn]
    lead_id: int | None = None


class LlmAgentResponse(BaseModel):
    status: Literal["integrated"] = "integrated"
    reply: str


MODULES = {
    "recommendation_engine": {
        "title": "Recommendation Engine",
        "description": "Local ranking model. Receives lead requirements and returns eligible properties with explanations.",
        "request": RecommendationRequest, "response": RecommendationResponse,
        "route": "/api/integrations/recommendation-engine/query",
        "slot": "Drop your trained matcher here. Until then hard-filter inventory is shown without invented ranks.",
    },
    "lead_scoring": {
        "title": "Predictive Lead Scoring",
        "description": "Local scoring model. Receives a lead id and returns a score with visible reasons.",
        "request": LeadScoringRequest, "response": LeadScoringResponse,
        "route": "/api/integrations/lead-scoring/score",
        "slot": "Drop your trained local scorer here. Hot-lead handoff never uses a fabricated score.",
    },
    "rag": {
        "title": "RAG (Retrieval-Augmented Generation)",
        "description": "Your trained knowledge base over inventory, brochures and price lists. Return dated, versioned citations.",
        "request": RagRequest, "response": RagResponse,
        "route": "/api/integrations/rag/query",
        "slot": "Drop your vector store + retriever here. Commercial answers require dated, versioned citations or a sourced inventory row.",
    },
    "stt": {
        "title": "Speech-to-Text",
        "description": "Local STT model for sandbox voice clips. No real phone call is placed.",
        "request": SttRequest, "response": SttResponse,
        "route": "/api/integrations/stt/transcribe",
        "slot": "Drop your STT weights/runtime here.",
    },
    "tts": {
        "title": "Text-to-Speech",
        "description": "Local TTS model for optional spoken replies in the sandbox.",
        "request": TtsRequest, "response": TtsResponse,
        "route": "/api/integrations/tts/speak",
        "slot": "Drop your TTS runtime here.",
    },
    "ocr": {
        "title": "OCR (brochures / price lists)",
        "description": "Local OCR for trial brochure and price-list files. Output still needs human source verification.",
        "request": OcrRequest, "response": OcrResponse,
        "route": "/api/integrations/ocr/extract",
        "slot": "Drop your OCR model here. Extracted prices are not published until a sourced inventory row exists.",
    },
    "llm_agent": {
        "title": "LLM sales agent",
        "description": "Optional local LLM for free-form replies after guardrails. Commercial facts still go through RAG/inventory.",
        "request": LlmAgentRequest, "response": LlmAgentResponse,
        "route": "/api/integrations/llm-agent/chat",
        "slot": "Drop your local LLM adapter here. The sandbox rules engine runs if this slot is empty.",
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
