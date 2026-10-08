from . import config
from .store import get_collection


def retrieve(question: str, k: int | None = None) -> list[dict]:
    """Return top-k chunks, closest first, each with its cosine distance."""
    col = get_collection()
    if col.count() == 0:
        return []
    res = col.query(query_texts=[question], n_results=k or config.TOP_K)
    hits = []
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append(
            {
                "text": text,
                "source": meta["source"],
                "title": meta["title"],
                "chunk": meta["chunk"],
                "distance": float(dist),
            }
        )
    return hits
