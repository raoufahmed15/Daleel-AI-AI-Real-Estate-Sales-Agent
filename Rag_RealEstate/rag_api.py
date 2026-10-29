"""HTTP API for the real-estate RAG assistant."""
from __future__ import annotations

import logging
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

log = logging.getLogger(__name__)
ASR_SPACE = "mohammedaly22/QwenCleo-ASR-Egyptian-Arabic"
MAX_AUDIO_BYTES = 15 * 1024 * 1024

app = FastAPI(title="Daleel AI RAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query cannot be empty.")
        return value


def get_agent():
    from src.agent import get_agent as create_agent

    return create_agent()


@lru_cache(maxsize=1)
def get_asr_client():
    from gradio_client import Client

    return Client(ASR_SPACE, verbose=False)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict:
    return get_agent().ask(body.query, body.session_id).to_dict()


@app.post("/api/transcribe")
def transcribe(file: UploadFile = File(...)) -> dict[str, str]:
    if file.content_type not in ("audio/wav", "audio/x-wav", "application/octet-stream"):
        raise HTTPException(status_code=415, detail="Upload a WAV audio recording.")

    try:
        with tempfile.TemporaryDirectory(prefix="daleel-asr-") as temp_dir:
            audio_path = Path(temp_dir) / "recording.wav"
            total_bytes = 0
            with audio_path.open("wb") as saved_audio:
                while chunk := file.file.read(64 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > MAX_AUDIO_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail="Audio recording exceeds the 15 MB limit.",
                        )
                    saved_audio.write(chunk)

            if total_bytes < 44:
                raise HTTPException(status_code=400, detail="The WAV recording is empty or invalid.")

            with audio_path.open("rb") as saved_audio:
                header = saved_audio.read(12)
            if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
                raise HTTPException(status_code=400, detail="The uploaded file is not a valid WAV recording.")

            from gradio_client import handle_file

            transcript = get_asr_client().predict(
                audio_path=handle_file(str(audio_path)),
                language="Arabic",
                do_normalize=False,
                api_name="/transcribe",
            )
    except HTTPException:
        raise
    except Exception as error:
        log.exception("QwenCleo audio transcription failed")
        raise HTTPException(
            status_code=502,
            detail="The Arabic transcription service is unavailable. Please try again.",
        ) from error
    finally:
        file.file.close()

    if not isinstance(transcript, str) or not transcript.strip():
        raise HTTPException(status_code=502, detail="The transcription service returned no text.")
    if transcript.strip() == "Please provide audio.":
        raise HTTPException(status_code=422, detail="No speech was detected in the recording.")
    return {"transcript": transcript.strip()}
