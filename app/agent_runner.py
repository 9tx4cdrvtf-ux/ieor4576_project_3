"""Thin wrapper around google-adk Runner for use from Streamlit."""
import asyncio
import json
import os
from typing import Any, AsyncIterator

# Silence ADK's "use native Gemini instead of LiteLLM" advice — we chose
# LiteLLM intentionally for future model-portability.
os.environ.setdefault("ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS", "true")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agent.coordinator import root_agent

APP_NAME = "ieor_course_planner"

_session_service = InMemorySessionService()
_runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=_session_service,
)


async def ensure_session(user_id: str, session_id: str) -> None:
    existing = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if existing is None:
        await _session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )


def _coerce_response(raw: Any) -> Any:
    """function_response.response can be dict, str, or proto. Normalize to Python."""
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return raw
    # protobuf-ish — try to_dict / dict()
    for attr in ("to_dict", "model_dump"):
        if hasattr(raw, attr):
            try:
                return getattr(raw, attr)()
            except Exception:
                pass
    try:
        return dict(raw)
    except Exception:
        return str(raw)


async def stream_agent(user_id: str, session_id: str, message: str) -> AsyncIterator[dict]:
    """Yield dicts {type, ...} as the agent emits events."""
    await ensure_session(user_id, session_id)
    content = genai_types.Content(role="user", parts=[genai_types.Part(text=message)])
    async for event in _runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    yield {"type": "text", "text": part.text, "author": event.author}
                elif getattr(part, "function_call", None):
                    yield {
                        "type": "tool_call",
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args or {}),
                        "author": event.author,
                    }
                elif getattr(part, "function_response", None):
                    fr = part.function_response
                    yield {
                        "type": "tool_result",
                        "name": fr.name,
                        "response": _coerce_response(getattr(fr, "response", None)),
                        "author": event.author,
                    }


async def get_state(user_id: str, session_id: str) -> dict:
    sess = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    return dict(sess.state) if sess else {}


def _extract_plan(events: list[dict]) -> dict | None:
    """Find the latest propose_schedule tool result and return its payload as dict.

    AgentTool-wrapped sub-agents do NOT honor output_key into session.state;
    we have to scrape the function_response from the event stream instead.
    """
    plan = None
    for ev in events:
        if ev.get("type") != "tool_result" or ev.get("name") != "propose_schedule":
            continue
        resp = ev.get("response")
        # Some ADK wrappers wrap the result in {"result": {...}} or {"output": {...}}
        if isinstance(resp, dict):
            for key in ("result", "output", "value"):
                if key in resp and isinstance(resp[key], (dict, str)):
                    resp = resp[key]
                    break
        if isinstance(resp, str):
            try:
                resp = json.loads(resp)
            except Exception:
                continue
        if isinstance(resp, dict) and "candidates" in resp:
            plan = resp
    return plan


def run_sync(user_id: str, session_id: str, message: str) -> tuple[list[dict], dict, dict | None]:
    """Synchronous helper for Streamlit: returns (events, final_state, plan)."""
    async def _go():
        events = []
        async for ev in stream_agent(user_id, session_id, message):
            events.append(ev)
        state = await get_state(user_id, session_id)
        return events, state

    events, state = asyncio.run(_go())
    plan = state.get("current_plan") or _extract_plan(events)
    if isinstance(plan, str):
        try:
            plan = json.loads(plan)
        except Exception:
            plan = None
    return events, state, plan
