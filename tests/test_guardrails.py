import pytest

from app import config
from app.generate import answer_question, NO_ANSWER_TEXT


def test_distance_guardrail_rejects_distant_chunks(monkeypatch):
    """Stage 1 Guardrail: Chunks with cosine distance > MAX_DISTANCE must be refused immediately."""
    import app.generate as gen

    # Mock retrieval returning chunks with high cosine distance (e.g. 0.88 > 0.75)
    monkeypatch.setattr(
        gen,
        "retrieve",
        lambda q, k=None: [
            {"id": "doc1_0", "source": "unrelated.md", "title": "Unrelated", "text": "Recipe text", "distance": 0.88}
        ],
    )

    # Even if LLM would otherwise answer, Stage 1 distance cutoff must block it
    res = answer_question("How do I make pancakes?")
    assert res["answerable"] is False
    assert res["answer"] == NO_ANSWER_TEXT
    assert res["sources"] == []


def test_distance_guardrail_passes_close_chunks(monkeypatch):
    """Stage 1 Guardrail: Chunks with cosine distance <= MAX_DISTANCE must pass to generation."""
    import app.generate as gen

    monkeypatch.setattr(
        gen,
        "retrieve",
        lambda q, k=None: [
            {"id": "doc1_0", "source": "vpn.md", "title": "VPN Guide", "text": "Use TCP profile.", "distance": 0.35}
        ],
    )
    monkeypatch.setattr(
        gen,
        "call_llm",
        lambda system, user, **kw: '{"answerable": true, "answer": "Switch to TCP.", "citations": [1]}',
    )

    res = answer_question("How do I fix VPN 809?")
    assert res["answerable"] is True
    assert res["answer"] == "Switch to TCP."
    assert len(res["sources"]) == 1
    assert res["sources"][0]["source"] == "vpn.md"


def test_model_guardrail_refusal_when_answerable_false(monkeypatch):
    """Stage 2 Guardrail: If model flags answerable=false, return standardized refusal."""
    import app.generate as gen

    monkeypatch.setattr(
        gen,
        "retrieve",
        lambda q, k=None: [
            {"id": "doc1_0", "source": "policy.md", "title": "Policy", "text": "Work hours policy.", "distance": 0.50}
        ],
    )
    monkeypatch.setattr(
        gen,
        "call_llm",
        lambda system, user, **kw: '{"answerable": false, "answer": "", "citations": []}',
    )

    res = answer_question("What is the overtime rate?")
    assert res["answerable"] is False
    assert res["answer"] == NO_ANSWER_TEXT
    assert res["sources"] == []


def test_model_guardrail_refusal_on_empty_answer_text(monkeypatch):
    """Stage 2 Guardrail: If model sets answerable=true but returns empty/whitespace answer, refuse."""
    import app.generate as gen

    monkeypatch.setattr(
        gen,
        "retrieve",
        lambda q, k=None: [
            {"id": "doc1_0", "source": "policy.md", "title": "Policy", "text": "Some text", "distance": 0.40}
        ],
    )
    monkeypatch.setattr(
        gen,
        "call_llm",
        lambda system, user, **kw: '{"answerable": true, "answer": "   ", "citations": [1]}',
    )

    res = answer_question("Tell me something")
    assert res["answerable"] is False
    assert res["answer"] == NO_ANSWER_TEXT


def test_citation_boundary_sanitization(monkeypatch):
    """Ensure citations out of bounds (e.g. index 99 when only 1 chunk was retrieved) default safely."""
    import app.generate as gen

    monkeypatch.setattr(
        gen,
        "retrieve",
        lambda q, k=None: [
            {"id": "doc1_0", "source": "printer.md", "title": "Printers", "text": "Print server info.", "distance": 0.25}
        ],
    )
    # Model returns citation [99, "invalid", 0]
    monkeypatch.setattr(
        gen,
        "call_llm",
        lambda system, user, **kw: '{"answerable": true, "answer": "Use printer.", "citations": [99, 0]}',
    )

    res = answer_question("Which printer?")
    assert res["answerable"] is True
    # Falls back to citation [1]
    assert len(res["sources"]) == 1
    assert res["sources"][0]["id"] == 1


def test_citation_deduplication(monkeypatch):
    """Ensure duplicate citations [1, 1, 1] are cleanly deduplicated in sources list."""
    import app.generate as gen

    monkeypatch.setattr(
        gen,
        "retrieve",
        lambda q, k=None: [
            {"id": "doc1_0", "source": "wifi.md", "title": "WiFi", "text": "SSID is Corp-Secure.", "distance": 0.20}
        ],
    )
    monkeypatch.setattr(
        gen,
        "call_llm",
        lambda system, user, **kw: '{"answerable": true, "answer": "Join Corp-Secure.", "citations": [1, 1, 1]}',
    )

    res = answer_question("What is wifi?")
    assert res["answerable"] is True
    assert len(res["sources"]) == 1
