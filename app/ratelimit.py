"""Small in-memory limits so a public demo can't run up the LLM bill.

Per-IP: at most RATE_LIMIT_PER_MIN questions per rolling minute.
Global: at most DAILY_LLM_CALLS model calls per UTC day (questions refused by the
distance guard cost nothing and don't count). Set either to 0 to turn it off.

State lives in this process, so it resets on restart and isn't shared between
replicas. That's fine for a single-container demo.
"""
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import HTTPException, Request

from . import config

_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)
_day = ""
_llm_calls = 0


def client_ip(request: Request) -> str:
    # Hosts like Hugging Face Spaces and Render sit behind a proxy; the first
    # X-Forwarded-For entry is the real visitor.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def per_ip_limit(request: Request) -> None:
    """FastAPI dependency for /api/ask."""
    limit = config.RATE_LIMIT_PER_MIN
    if limit <= 0:
        return
    ip = client_ip(request)
    now = time.monotonic()
    with _lock:
        q = _hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            wait = int(60 - (now - q[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Too many questions. Please wait {wait}s and try again.",
                headers={"Retry-After": str(wait)},
            )
        q.append(now)
        if len(_hits) > 10_000:  # don't let a crawler grow this forever
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > 60]:
                del _hits[k]


class BudgetExceeded(Exception):
    pass


def take_llm_call() -> None:
    """Count one model call against today's budget, or raise BudgetExceeded."""
    global _day, _llm_calls
    cap = config.DAILY_LLM_CALLS
    if cap <= 0:
        return
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _lock:
        if today != _day:
            _day, _llm_calls = today, 0
        if _llm_calls >= cap:
            raise BudgetExceeded()
        _llm_calls += 1


def reset() -> None:
    """For tests."""
    global _day, _llm_calls
    with _lock:
        _hits.clear()
        _day, _llm_calls = "", 0
