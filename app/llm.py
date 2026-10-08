import json
import os
import re
from typing import Optional

from . import config

_clients: dict = {}


def get_active_provider() -> str:
    prov = config.LLM_PROVIDER
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
    req_config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.0,
        max_output_tokens=max_tokens,
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


def call_llm(system: str, user: str, model: Optional[str] = None, max_tokens: int = 700) -> str:
    provider = get_active_provider()
    effective_model = model or config.LLM_MODEL or config.get_default_model(provider)

    if provider == "gemini":
        return _call_gemini(system, user, effective_model, max_tokens)
    elif provider == "openai":
        return _call_openai(system, user, effective_model, max_tokens)
    elif provider == "anthropic":
        return _call_anthropic(system, user, effective_model, max_tokens)
    elif provider == "mock":
        return _call_mock(system, user)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


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
