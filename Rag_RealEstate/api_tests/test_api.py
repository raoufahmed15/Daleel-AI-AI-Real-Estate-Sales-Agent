from io import BytesIO
import struct
from fastapi.testclient import TestClient

import rag_api


class FakeAgent:
    def __init__(self):
        self.calls = []

    def ask(self, query, session_id):
        self.calls.append((query, session_id))
        return FakeResult()


class FakeResult:
    def to_dict(self):
        return {
            "status": "answered",
            "reply": "الإجابة من المصدر",
            "reason": None,
            "sources": [{"doc_id": "FAQ-01", "title": "الأسئلة الشائعة", "version": "v1", "issue_date": ""}],
        }


class FakeAsrClient:
    def __init__(self):
        self.calls = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        assert kwargs["audio_path"]
        with open(kwargs["audio_path"]["path"], "rb") as audio_file:
            header = audio_file.read(12)
            assert header[:4] == b"RIFF"
            assert header[8:12] == b"WAVE"
        return "عايز شقة في القاهرة الجديدة"


def wav_sample():
    pcm = b"\x00\x00" * 8
    return (
        b"RIFF"
        + struct.pack("<I", 36 + len(pcm))
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16)
        + b"data"
        + struct.pack("<I", len(pcm))
        + pcm
    )


def test_health():
    assert TestClient(rag_api.app).get("/api/health").json() == {"status": "ok"}


def test_chat_calls_rag_and_returns_sources(monkeypatch):
    agent = FakeAgent()
    monkeypatch.setattr(rag_api, "get_agent", lambda: agent)

    response = TestClient(rag_api.app).post(
        "/api/chat", json={"query": "  ما هي خطط السداد؟  ", "session_id": "chat_123"}
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "الإجابة من المصدر"
    assert response.json()["sources"][0]["doc_id"] == "FAQ-01"
    assert agent.calls == [("ما هي خطط السداد؟", "chat_123")]


def test_chat_rejects_invalid_session_id():
    response = TestClient(rag_api.app).post(
        "/api/chat", json={"query": "السعر؟", "session_id": "not a safe id"}
    )

    assert response.status_code == 422


def test_chat_rejects_blank_query():
    response = TestClient(rag_api.app).post(
        "/api/chat", json={"query": "   ", "session_id": "chat_123"}
    )

    assert response.status_code == 422


def test_transcribe_audio_calls_qwen_space(monkeypatch):
    asr_client = FakeAsrClient()
    monkeypatch.setattr(rag_api, "get_asr_client", lambda: asr_client)

    response = TestClient(rag_api.app).post(
        "/api/transcribe",
        files={"file": ("voice.wav", BytesIO(wav_sample()), "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json() == {"transcript": "عايز شقة في القاهرة الجديدة"}
    assert asr_client.calls[0]["language"] == "Arabic"
    assert asr_client.calls[0]["do_normalize"] is False
    assert asr_client.calls[0]["api_name"] == "/transcribe"


def test_asr_client_uses_hugging_face_token(monkeypatch):
    import gradio_client

    calls = []

    def fake_client(space, *, hf_token, verbose):
        calls.append((space, hf_token, verbose))
        return FakeAsrClient()

    monkeypatch.setenv("HF_TOKEN", "hf-test-token")
    monkeypatch.setattr(gradio_client, "Client", fake_client)
    rag_api.get_asr_client.cache_clear()
    try:
        rag_api.get_asr_client()
    finally:
        rag_api.get_asr_client.cache_clear()

    assert calls == [(rag_api.ASR_SPACE, "hf-test-token", False)]


def test_transcribe_reports_exhausted_zerogpu_quota(monkeypatch):
    class QuotaLimitedAsrClient:
        def predict(self, **kwargs):
            raise RuntimeError("You have exceeded your ZeroGPU runs limit.")

    monkeypatch.setattr(
        rag_api, "get_asr_client", lambda: QuotaLimitedAsrClient()
    )
    response = TestClient(rag_api.app).post(
        "/api/transcribe",
        files={"file": ("voice.wav", BytesIO(wav_sample()), "audio/wav")},
    )

    assert response.status_code == 503
    assert "HF_TOKEN" in response.json()["detail"]


def test_transcribe_rejects_invalid_wav(monkeypatch):
    monkeypatch.setattr(rag_api, "get_asr_client", lambda: FakeAsrClient())

    response = TestClient(rag_api.app).post(
        "/api/transcribe",
        files={"file": ("voice.wav", BytesIO(b"not audio" * 10), "audio/wav")},
    )

    assert response.status_code == 400


def test_transcribe_rejects_non_wav():
    response = TestClient(rag_api.app).post(
        "/api/transcribe",
        files={"file": ("voice.mp3", BytesIO(b"audio" * 30), "audio/mpeg")},
    )

    assert response.status_code == 415
