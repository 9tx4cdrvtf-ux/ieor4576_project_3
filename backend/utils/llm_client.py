"""LiteLLM-backed unified model interface.

Allows swapping providers (Vertex AI Gemini, Anthropic Claude, OpenAI GPT)
without touching agent code. Default model is configurable via env.
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterator

DEFAULT_MODEL = os.getenv("LLM_MODEL", "vertex_ai/gemini-2.5-flash")
FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "vertex_ai/gemini-2.5-flash")


def _completion(messages: list[dict], model: str | None = None, **kwargs: Any) -> str:
    """Synchronous completion. Returns the assistant message string."""
    import litellm

    model = model or DEFAULT_MODEL
    try:
        resp = litellm.completion(model=model, messages=messages, **kwargs)
    except Exception:
        if FALLBACK_MODEL and FALLBACK_MODEL != model:
            resp = litellm.completion(model=FALLBACK_MODEL, messages=messages, **kwargs)
        else:
            raise
    return resp["choices"][0]["message"]["content"] or ""


def chat(system: str, user: str, model: str | None = None, **kwargs: Any) -> str:
    return _completion(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
        **kwargs,
    )


def chat_json(system: str, user: str, model: str | None = None, **kwargs: Any) -> dict:
    """Chat that requests a JSON object back. Tolerates code fences."""
    raw = chat(
        system=system + "\n\nReturn ONLY a single JSON object — no prose, no code fences.",
        user=user,
        model=model,
        **kwargs,
    )
    return _parse_json_loose(raw)


def stream(system: str, user: str, model: str | None = None, **kwargs: Any) -> Iterator[str]:
    """Stream tokens from the model as plain strings."""
    import litellm

    m = model or DEFAULT_MODEL
    resp = litellm.completion(
        model=m,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        stream=True,
        **kwargs,
    )
    for chunk in resp:
        try:
            delta = chunk["choices"][0]["delta"].get("content")
        except Exception:
            delta = None
        if delta:
            yield delta


def _parse_json_loose(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
    return json.loads(s)
