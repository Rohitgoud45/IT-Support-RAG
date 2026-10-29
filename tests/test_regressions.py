"""Regression tests for bugs found in code review."""
import importlib

import pytest
from fastapi.testclient import TestClient

from app import config, llm


class _StatusError(Exception):
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code


def test_not_found_mentioning_generate_is_not_retried(monkeypatch):
    calls = []

    def fail(*args):
        calls.append(1)
        raise RuntimeError("404 NOT_FOUND. models/x is not supported for generateContent")

    monkeypatch.setattr(llm, "_dispatch", fail)
    monkeypatch.setattr(llm.time, "sleep", lambda s: pytest.fail("should not back off"))
    with pytest.raises(RuntimeError):
        llm.call_llm("s", "u", provider="gemini")
    assert len(calls) == 1


@pytest.mark.parametrize(
    "exc, expected",
    [
        (_StatusError("Too many requests", 429), True),
        (_StatusError("Overloaded", 529), True),
        (_StatusError("Bad request: rate limit text but 400", 400), False),
        (RuntimeError("429 RESOURCE_EXHAUSTED"), True),
        (RuntimeError("Rate limit reached"), True),
        (RuntimeError("Could not generate an accurate answer"), False),
    ],
)
def test_is_retryable(exc, expected):
    assert llm._is_retryable(exc) is expected


def test_transient_error_is_retried(monkeypatch):
    calls = []

    def flaky(*args):
        calls.append(1)
        if len(calls) < 3:
            raise _StatusError("busy", 503)
        return "ok"

    monkeypatch.setattr(llm, "_dispatch", flaky)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    assert llm.call_llm("s", "u", provider="gemini") == "ok"
    assert len(calls) == 3


def test_string_citations_are_accepted(monkeypatch):
    import app.generate as gen

    hits = [
        {"source": f"d{i}.md", "title": f"D{i}", "text": f"text {i}", "chunk": 0, "distance": 0.2}
        for i in range(3)
    ]
    monkeypatch.setattr(gen, "retrieve", lambda q, k=None: hits)
    monkeypatch.setattr(
        gen,
        "call_llm",
        lambda system, user, model=None: '{"answerable": true, "answer": "x", "citations": ["2", " 3 ", true]}',
    )
    res = gen.answer_question("anything")
    assert [s["id"] for s in res["sources"]] == [2, 3]


def test_upstream_error_details_are_not_leaked(monkeypatch):
    import app.main as main_mod

    def boom(question):
        raise RuntimeError("secret-internal-detail")

    monkeypatch.setattr(main_mod, "answer_question", boom)
    r = TestClient(main_mod.app).post("/api/ask", json={"question": "printer?"})
    assert r.status_code == 502
    assert "secret-internal-detail" not in r.text


@pytest.fixture
def app_with_frontend(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>spa</html>")
    monkeypatch.setattr(config, "FRONTEND_DIST", tmp_path)
    import app.main as main_mod

    yield importlib.reload(main_mod).app
    monkeypatch.undo()
    importlib.reload(main_mod)


def test_unknown_api_route_is_404_not_spa(app_with_frontend):
    c = TestClient(app_with_frontend)
    assert c.get("/api/does-not-exist").status_code == 404
    assert c.get("/some/page").text == "<html>spa</html>"
