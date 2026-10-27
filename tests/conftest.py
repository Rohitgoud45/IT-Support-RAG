import os
import pytest


@pytest.fixture(autouse=True)
def default_mock_llm(monkeypatch):
    """Ensure test suite runs deterministically, fast, and offline without external API quota leaks."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
