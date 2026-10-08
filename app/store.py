import chromadb

from . import config

_client = None


def _client_instance():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return _client


def get_collection():
    # Uses Chroma's built-in embedding model (all-MiniLM-L6-v2, runs locally via ONNX).
    return _client_instance().get_or_create_collection(
        name=config.COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def reset_collection():
    try:
        _client_instance().delete_collection(config.COLLECTION)
    except Exception:
        pass
    return get_collection()
