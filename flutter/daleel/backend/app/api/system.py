from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config
from ..integrations.contracts import (
    MODULES,
    LlmAgentRequest,
    LeadScoringRequest,
    ModuleNotConfigured,
    OcrRequest,
    RagRequest,
    RecommendationRequest,
    SttRequest,
    TtsRequest,
)
from ..services import dashboard
from .deps import get_db

router = APIRouter(prefix="/api", tags=["System & Integrations"])

HF_POINTS = [
    {"name": "LLMProvider", "status": "reserved", "note": "Future local/hosted language model adapter."},
    {"name": "QualificationProvider", "status": "reserved", "note": "Future conversational qualification extraction."},
    {"name": "SpeechToTextProvider", "status": "reserved", "note": "Future voice input."},
    {"name": "TextToSpeechProvider", "status": "reserved", "note": "Future voice output."},
    {"name": "OCRProvider", "status": "reserved", "note": "Future document OCR."},
]


def _module_info(registry):
    return [{"module": k, "title": v["title"], "description": v["description"], "status": registry.status(k),
             "label": "Integrated" if registry.status(k) == "integrated" else "Not integrated yet",
             "endpoint": v["route"], "integration_slot": v["slot"]} for k, v in MODULES.items()]


@router.get("/health")
def health(request: Request, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unavailable",
            "version": config.APP_VERSION}


@router.get("/dashboard")
def dashboard_metrics(db: Session = Depends(get_db)):
    return dashboard.metrics(db)


@router.get("/integrations")
def integrations(request: Request):
    return {"modules": _module_info(request.app.state.registry),
            "note": "These modules are built separately. Unintegrated modules never return invented results."}


@router.get("/settings")
def settings(request: Request, db: Session = Depends(get_db)):
    engine = request.app.state.engine
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "unavailable"
    return {"app_mode": config.APP_MODE, "version": config.APP_VERSION, "notice": config.DEMO_NOTICE,
            "database": {"dialect": engine.dialect.name, "status": db_status},
            "modules": _module_info(request.app.state.registry),
            "future_huggingface_integration_points": HF_POINTS,
            "external_ai_calls_enabled": False}


def _dispatch(request: Request, name: str, payload):
    handler = request.app.state.registry.get(name)
    if handler is None:
        return JSONResponse({"status": "not_implemented", "module": name,
                             "message": f"{MODULES[name]['title']} has not been implemented yet."}, status_code=501)
    try:
        result = handler(payload)
    except ModuleNotConfigured as e:
        return JSONResponse({"status": "not_configured", "module": name, "message": str(e) or "Module not configured."},
                            status_code=503)
    return MODULES[name]["response"].model_validate(result)


@router.post("/integrations/recommendation-engine/query")
def recommend(body: RecommendationRequest, request: Request):
    return _dispatch(request, "recommendation_engine", body)


@router.post("/integrations/lead-scoring/score")
def score(body: LeadScoringRequest, request: Request):
    return _dispatch(request, "lead_scoring", body)


@router.post("/integrations/rag/query")
def rag(body: RagRequest, request: Request):
    return _dispatch(request, "rag", body)


@router.post("/integrations/stt/transcribe")
def transcribe(body: SttRequest, request: Request):
    return _dispatch(request, "stt", body)


@router.post("/integrations/tts/speak")
def speak(body: TtsRequest, request: Request):
    return _dispatch(request, "tts", body)


@router.post("/integrations/ocr/extract")
def extract_document(body: OcrRequest, request: Request):
    return _dispatch(request, "ocr", body)


@router.post("/integrations/llm-agent/chat")
def chat_with_agent(body: LlmAgentRequest, request: Request):
    return _dispatch(request, "llm_agent", body)
