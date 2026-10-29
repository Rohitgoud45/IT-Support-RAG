"""Retrieve -> guard -> generate grounded answer with citations."""
import logging

from . import config
from .llm import call_llm, parse_json
from .retrieval import retrieve

log = logging.getLogger(__name__)

NO_ANSWER_TEXT = (
    "I couldn't find this in the knowledge base, so I won't guess. "
    "Please open a ticket with the help desk."
)

SYSTEM = """You are an IT support assistant. Answer ONLY from the numbered context passages.
Rules:
- If the passages do not contain the answer, set "answerable" to false. Never use outside knowledge.
- Be concise and give steps as a short numbered list when the user needs to do something.
- Cite the passages you used with their numbers.
Reply with a single JSON object and nothing else:
{"answerable": true|false, "answer": "<text>", "citations": [<passage numbers>]}"""


def _format_context(hits: list[dict]) -> str:
    return "\n\n".join(f"[{i}] ({h['title']})\n{h['text']}" for i, h in enumerate(hits, 1))


def _citation_numbers(raw, n_passages: int) -> list[int]:
    """Keep valid 1-based passage numbers; models sometimes send them as strings."""
    if not isinstance(raw, list):
        return []
    nums = []
    for c in raw:
        if isinstance(c, bool):
            continue
        if isinstance(c, str) and c.strip().isdigit():
            c = int(c.strip())
        if isinstance(c, int) and 1 <= c <= n_passages:
            nums.append(c)
    return nums


def _no_answer(retrieved: list[dict]) -> dict:
    return {"answerable": False, "answer": NO_ANSWER_TEXT, "sources": [], "retrieved": retrieved}


def answer_question(question: str, k: int | None = None) -> dict:
    retrieved = retrieve(question, k)
    # Guard 1: nothing close enough -> refuse without calling the LLM.
    relevant = [h for h in retrieved if h["distance"] <= config.MAX_DISTANCE]
    if not relevant:
        return _no_answer(retrieved)

    raw = call_llm(SYSTEM, f"Context:\n{_format_context(relevant)}\n\nQuestion: {question}", config.LLM_MODEL)
    try:
        data = parse_json(raw)
    except ValueError:
        # Often a reply truncated by max_tokens; refuse, but leave a trace.
        log.warning("Unparseable model reply, refusing: %r", raw[:200])
        return _no_answer(retrieved)

    # Guard 2: the model itself says the context does not answer it.
    if not data.get("answerable") or not str(data.get("answer", "")).strip():
        return _no_answer(retrieved)

    cited = _citation_numbers(data.get("citations"), len(relevant)) or [1]
    sources = [
        {
            "id": n,
            "source": relevant[n - 1]["source"],
            "title": relevant[n - 1]["title"],
            "snippet": relevant[n - 1]["text"],
        }
        for n in dict.fromkeys(cited)
    ]
    return {"answerable": True, "answer": data["answer"], "sources": sources, "retrieved": retrieved}
