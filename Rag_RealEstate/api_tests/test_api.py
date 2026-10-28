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
