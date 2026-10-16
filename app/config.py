import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = Path(os.getenv("DOCS_DIR", ROOT / "data" / "docs"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ROOT / "chroma_db"))
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", ROOT / "frontend" / "dist"))
COLLECTION = "it_support"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")

def get_default_model(provider: str) -> str:
    if provider == "gemini":
        return "gemini-3.5-flash"
    elif provider == "openai":
        return "gpt-4o-mini"
    elif provider == "anthropic":
        return "claude-3-5-sonnet-20241022"
    return "mock"

LLM_MODEL = os.getenv("LLM_MODEL", "")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "")

TOP_K = int(os.getenv("TOP_K", "4"))
# Cosine distance cutoff. Chunks farther than this are treated as irrelevant.
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.75"))

CHUNK_STRATEGY = os.getenv("CHUNK_STRATEGY", "paragraph")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
