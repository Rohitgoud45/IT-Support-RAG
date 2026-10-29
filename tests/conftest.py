import os
import shutil
import tempfile

import pytest

# Point the app at a throwaway index *before* any app module is imported, so tests
# never read or overwrite the developer's chroma_db/ and pass on a fresh clone.
_TMP = tempfile.mkdtemp(prefix="itrag-test-")
os.environ["CHROMA_DIR"] = os.path.join(_TMP, "chroma")
os.environ["FRONTEND_DIST"] = os.path.join(_TMP, "no-frontend")


@pytest.fixture(scope="session", autouse=True)
def test_index():
    """Build the index once from data/docs into the temp dir."""
    from app.ingest import ingest

    assert ingest(reset=True) > 0
    yield
    shutil.rmtree(_TMP, ignore_errors=True)  # Chroma may still hold files open on Windows


@pytest.fixture(autouse=True)
def default_mock_llm(monkeypatch):
    """Ensure test suite runs deterministically, fast, and offline without external API quota leaks."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
