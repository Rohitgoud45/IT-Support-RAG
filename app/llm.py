import json
import os
import re
import time
from typing import Optional

from . import config

_clients: dict = {}


def get_active_provider() -> str:
    prov = os.getenv("LLM_PROVIDER", config.LLM_PROVIDER).lower()
    if prov and prov != "auto":
        return prov

    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if config.OPENAI_BASE_URL:
        return "openai"

    return "mock"


def _call_gemini(system: str, user: str, model: str, max_tokens: int) -> str:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if "gemini" not in _clients:
        _clients["gemini"] = genai.Client(api_key=api_key)

    client: genai.Client = _clients["gemini"]
    extra = {}
    if "flash" in model:
        # Flash models "think" by default and those hidden tokens count against
        # max_output_tokens, which can leave short replies (e.g. the judge) empty.
        extra["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    req_config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.0,
        max_output_tokens=max_tokens,
        **extra,
    )
    response = client.models.generate_content(
        model=model,
        contents=user,
        config=req_config,
    )
    return response.text or ""


def _call_openai(system: str, user: str, model: str, max_tokens: int) -> str:
    from openai import OpenAI

    if "openai" not in _clients:
        base_url = config.OPENAI_BASE_URL or None
        api_key = os.getenv("OPENAI_API_KEY") or ("ollama-local" if base_url else "missing-key")
        _clients["openai"] = OpenAI(api_key=api_key, base_url=base_url)

    client: OpenAI = _clients["openai"]
    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""


def _call_anthropic(system: str, user: str, model: str, max_tokens: int) -> str:
    import anthropic

    if "anthropic" not in _clients:
        _clients["anthropic"] = anthropic.Anthropic()

    client: anthropic.Anthropic = _clients["anthropic"]
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0.0,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def _call_mock(system: str, user: str) -> str:
    """Offline demo fallback when no API key is configured."""
    if '{"correct": true|false}' in system or '{"correct": true|false}' in user:
        return json.dumps({"correct": True})
    if '{"faithful": true|false}' in system or '{"faithful": true|false}' in user:
        return json.dumps({"faithful": True})

    # Normal QA prompt: Context:\n[1] (Title)\n...\n\nQuestion: ...
    if "Context:" in user:
        ctx_part = user.split("Context:", 1)[1]
        if "Question:" in ctx_part:
            ctx_text, q_text = ctx_part.split("Question:", 1)
        else:
            ctx_text, q_text = ctx_part, ""

        ctx_clean = ctx_text.strip()
        if ctx_clean and "[" in ctx_clean:
            # Extract actionable lines from context
            lines = [line.strip() for line in ctx_clean.splitlines() if line.strip() and not line.strip().startswith("[")]
            snippet = "\n".join(lines[:4]) if lines else ctx_clean[:200]
            return json.dumps({
                "answerable": True,
                "answer": f"{snippet}\n\n(Note: offline demo mode active. Configure an API key in .env for full LLM answers.)",
                "citations": [1],
            })

    return json.dumps({
        "answerable": False,
        "answer": "",
        "citations": [],
    })


_RETRYABLE = ("429", "rate", "resource_exhausted", "503", "unavailable", "overloaded")


def get_effective_model(model: Optional[str] = None) -> str:
    return model or config.LLM_MODEL or config.get_default_model(get_active_provider())


def _dispatch(provider: str, system: str, user: str, model: str, max_tokens: int) -> str:
    if provider == "gemini":
        return _call_gemini(system, user, model, max_tokens)
    elif provider == "openai":
        return _call_openai(system, user, model, max_tokens)
    elif provider == "anthropic":
        return _call_anthropic(system, user, model, max_tokens)
    elif provider == "mock":
        return _call_mock(system, user)
    raise ValueError(f"Unsupported LLM provider: {provider}")


def call_llm(
    system: str,
    user: str,
    model: Optional[str] = None,
    max_tokens: int = 700,
    retries: int = 4,
    provider: Optional[str] = None,
) -> str:
    active_provider = provider or get_active_provider()
    effective_model = get_effective_model(model)

    for attempt in range(retries + 1):
        try:
            return _dispatch(active_provider, system, user, effective_model, max_tokens)
        except Exception as exc:  # noqa: BLE001 - provider SDKs raise different types
            msg = str(exc).lower()
            daily_quota = "perday" in msg  # resets in hours -- retrying only wastes time
            if attempt == retries or daily_quota or not any(k in msg for k in _RETRYABLE):
                raise
            time.sleep(min(2 ** attempt * 5, 60))  # 5s, 10s, 20s, 40s
    raise RuntimeError("unreachable")


def parse_json(raw: str) -> dict:
    """Pull the first JSON object out of a model reply, tolerating code fences."""
    cleaned = re.sub(r"```(?:json)?", "", raw)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in model output: {raw[:120]}")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc} in text: {raw[start : end + 1]}") from exc
