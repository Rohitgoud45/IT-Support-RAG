from fastapi.testclient import TestClient

from app import config, generate, ratelimit
from app.main import app

client = TestClient(app)
HIT = [{"text": "Use Northwind-TCP.", "source": "vpn.md", "title": "VPN", "chunk": 0, "distance": 0.2}]
FAR = [{"text": "x", "source": "x.md", "title": "X", "chunk": 0, "distance": 0.99}]


def test_per_ip_limit_returns_429(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MIN", 2)
    monkeypatch.setattr(generate, "retrieve", lambda q, k=None: FAR)
    for _ in range(2):
        assert client.post("/api/ask", json={"question": "vpn?"}).status_code == 200
    r = client.post("/api/ask", json={"question": "vpn?"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_limit_is_per_forwarded_ip(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MIN", 1)
    monkeypatch.setattr(generate, "retrieve", lambda q, k=None: FAR)
    a = {"X-Forwarded-For": "1.1.1.1, 10.0.0.1"}
    b = {"X-Forwarded-For": "2.2.2.2"}
    assert client.post("/api/ask", json={"question": "vpn?"}, headers=a).status_code == 200
    assert client.post("/api/ask", json={"question": "vpn?"}, headers=a).status_code == 429
    assert client.post("/api/ask", json={"question": "vpn?"}, headers=b).status_code == 200


def test_zero_disables_rate_limit(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MIN", 0)
    monkeypatch.setattr(generate, "retrieve", lambda q, k=None: FAR)
    for _ in range(20):
        assert client.post("/api/ask", json={"question": "vpn?"}).status_code == 200


def test_daily_budget_counts_only_llm_calls(monkeypatch):
    monkeypatch.setattr(config, "DAILY_LLM_CALLS", 1)
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MIN", 0)
    # Distance refusals are free and never touch the budget.
    monkeypatch.setattr(generate, "retrieve", lambda q, k=None: FAR)
    for _ in range(3):
        assert client.post("/api/ask", json={"question": "cookies?"}).status_code == 200
    # First real LLM call uses the budget, the second is refused with 503.
    monkeypatch.setattr(generate, "retrieve", lambda q, k=None: HIT)
    assert client.post("/api/ask", json={"question": "vpn?"}).status_code == 200
    r = client.post("/api/ask", json={"question": "vpn?"})
    assert r.status_code == 503
    assert "budget" in r.json()["detail"]


def test_response_includes_timing_and_distance(monkeypatch):
    monkeypatch.setattr(generate, "retrieve", lambda q, k=None: FAR)
    data = client.post("/api/ask", json={"question": "cookies?"}).json()
    assert data["refused_by"] == "distance"
    assert data["best_distance"] == 0.99
    assert data["max_distance"] == config.MAX_DISTANCE
    assert isinstance(data["latency_ms"], int)
