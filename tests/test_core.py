import pytest
from fastapi.testclient import TestClient

from app.chunking import chunk_fixed, chunk_paragraph, chunk_text
from app.generate import answer_question, NO_ANSWER_TEXT
from app.llm import parse_json, get_active_provider, call_llm
from app.main import app
from app.retrieval import retrieve


def test_paragraph_chunks_respect_size_and_keep_content():
    text = "\n\n".join(f"Paragraph {i} " + "word " * 40 for i in range(10))
    chunks = chunk_paragraph(text, size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 500 + 50 + 2 for c in chunks)
    assert "Paragraph 0" in chunks[0] and "Paragraph 9" in chunks[-1]


def test_fixed_chunks_overlap():
    text = "a" * 1000
    chunks = chunk_fixed(text, size=400, overlap=100)
    assert chunks[0] == "a" * 400
    assert len(chunks) == 4  # starts at 0, 300, 600, 900


def test_empty_text():
    assert chunk_fixed("") == []
    assert chunk_paragraph("   \n\n  ") == []


def test_unknown_strategy():
    with pytest.raises(ValueError):
        chunk_text("x", strategy="nope")


def test_parse_json_handles_fences_and_prose():
    raw = 'Sure!\n```json\n{"answerable": true, "answer": "hi", "citations": [1]}\n```'
    assert parse_json(raw)["citations"] == [1]


def test_parse_json_rejects_garbage():
    with pytest.raises(ValueError):
        parse_json("no json here")
    with pytest.raises(ValueError):
        parse_json("{not valid}")


def test_provider_detection_and_mock_fallback():
    prov = get_active_provider()
    assert prov in {"gemini", "openai", "anthropic", "mock"}


def test_call_llm_mock_returns_valid_json():
    res = call_llm(
        system="You are IT assistant.",
        user="Context:\n[1] (VPN)\nRestart VPN client and reconnect.\n\nQuestion: How to fix VPN?",
        provider="mock",
    )
    data = parse_json(res)
    assert "answerable" in data
    assert isinstance(data["citations"], list)



def test_retrieval_returns_relevant_chunks():
    hits = retrieve("VPN error 809", k=2)
    assert len(hits) > 0
    assert "vpn-troubleshooting.md" in [h["source"] for h in hits]
    assert hits[0]["distance"] >= 0.0


def test_answer_question_refusal_on_unrelated_topic():
    res = answer_question("What is the recipe for chocolate chip cookies?")
    assert res["answerable"] is False
    assert res["answer"] == NO_ANSWER_TEXT
    assert res["sources"] == []


def test_answer_question_on_known_topic():
    res = answer_question("What does VPN error 809 mean and how do I fix it?")
    assert res["answerable"] is True
    assert len(res["sources"]) > 0


def test_api_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["chunks"] > 0
    assert "provider" in data
    assert "model" in data


def test_api_ask_endpoint():
    client = TestClient(app)
    response = client.post("/api/ask", json={"question": "How often do passwords expire?"})
    assert response.status_code == 200
    data = response.json()
    assert "answerable" in data
    assert "answer" in data
    assert "sources" in data
