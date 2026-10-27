import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_contract():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["chunks"], int)
    assert "provider" in data
    assert "model" in data


def test_ask_endpoint_valid_question():
    response = client.post("/api/ask", json={"question": "How often do passwords expire?"})
    assert response.status_code == 200
    data = response.json()
    assert "answerable" in data
    assert "answer" in data
    assert "sources" in data
    assert "retrieved" not in data  # Internal data must be stripped


def test_ask_endpoint_rejects_empty_and_short_questions():
    # Question < 3 chars
    r1 = client.post("/api/ask", json={"question": "ab"})
    assert r1.status_code == 422

    # Empty question
    r2 = client.post("/api/ask", json={"question": ""})
    assert r2.status_code == 422


def test_ask_endpoint_rejects_excessively_long_questions():
    long_q = "How do I fix VPN? " * 35  # > 500 chars
    assert len(long_q) > 500
    response = client.post("/api/ask", json={"question": long_q})
    assert response.status_code == 422


def test_ask_endpoint_handles_upstream_failures(monkeypatch):
    import app.main as main_mod

    def failing_answer(question):
        raise RuntimeError("Embedding model crashed")

    monkeypatch.setattr(main_mod, "answer_question", failing_answer)

    response = client.post("/api/ask", json={"question": "What is the printer address?"})
    assert response.status_code == 502
    assert "Answer generation failed" in response.json()["detail"]
