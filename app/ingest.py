"""Load docs -> chunk -> embed -> store. Run: python -m app.ingest"""
import re

from . import config
from .chunking import chunk_text
from .store import get_collection, reset_collection


def _title(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, flags=re.M)
    return m.group(1).strip() if m else fallback


def ingest(reset: bool = True) -> int:
    files = sorted(p for p in config.DOCS_DIR.rglob("*") if p.suffix in {".md", ".txt"})
    if not files:
        print(f"No .md/.txt files found in {config.DOCS_DIR}")
        return 0
    col = reset_collection() if reset else get_collection()
    ids, docs, metas = [], [], []
    for path in files:
        text = path.read_text(encoding="utf-8")
        title = _title(text, path.stem)
        rel = str(path.relative_to(config.DOCS_DIR))
        for i, chunk in enumerate(
            chunk_text(text, config.CHUNK_STRATEGY, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        ):
            ids.append(f"{rel}::{i}")
            docs.append(chunk)
            metas.append({"source": rel, "title": title, "chunk": i})
    col.add(ids=ids, documents=docs, metadatas=metas)
    print(f"Ingested {len(files)} files into {len(ids)} chunks ({config.CHUNK_STRATEGY} strategy).")
    return len(ids)


if __name__ == "__main__":
    ingest()
