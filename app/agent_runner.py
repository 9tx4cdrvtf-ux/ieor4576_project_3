"""Thin wrapper around google-adk Runner for use from Streamlit."""
import asyncio
from typing import AsyncIterator

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


async def stream_agent(user_id: str, session_id: str, message: str) -> AsyncIterator[dict]:
    """Yield dicts {type, text} as the agent emits events."""
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
                    yield {
                        "type": "tool_result",
                        "name": part.function_response.name,
                        "author": event.author,
                    }


async def get_state(user_id: str, session_id: str) -> dict:
    sess = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    return dict(sess.state) if sess else {}


def run_sync(user_id: str, session_id: str, message: str) -> tuple[list[dict], dict]:
    """Synchronous helper for Streamlit: returns (events, final_state)."""
    async def _go():
        events = []
        async for ev in stream_agent(user_id, session_id, message):
            events.append(ev)
        state = await get_state(user_id, session_id)
        return events, state

    return asyncio.run(_go())
