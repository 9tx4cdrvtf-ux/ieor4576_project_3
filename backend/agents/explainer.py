"""Explainer Agent.

Streams a structured per-course recommendation explanation. Each block has
three sentences mapping to PRD §7.6:
  1. Course content
  2. Relevance to career goal (must reference user-supplied keywords)
  3. Role in the overall schedule (paired courses, balance, etc.)

Honesty rule: if a course is selected mainly to clear a requirement and
isn't deeply career-relevant, the explainer must say so.
"""

from __future__ import annotations

import json
from typing import Iterator

from ..utils import llm_client


SYSTEM = (
    "You are CourseCompass's Explainer. For each recommended course, write "
    "three sentences in this exact order:\n"
    "  1) Course content (one sentence).\n"
    "  2) Relevance to the student's career goals. You may ONLY reference "
    "phrases that literally appear in career_text or career_tags. If both "
    "are empty, write 'No specific career goal was provided' and skip to "
    "sentence 3 — do NOT invent a goal, do NOT carry over goals from prior "
    "conversations, and do NOT use synonyms beyond what the student wrote.\n"
    "  3) Role in the overall schedule (e.g., pairs with course X, balances "
    "workload, satisfies requirement Y).\n"
    "If a course is recommended mainly to clear a requirement and is not "
    "directly career-relevant, say so honestly. Never fabricate enthusiasm.\n"
    "Tone is concise and neutral. Do not add headers, bullets, or numbering."
)


def _build_user_prompt(course: dict, profile: dict, full_plan: list[dict]) -> str:
    other = ", ".join(c["code"] for c in full_plan if c["code"] != course["code"]) or "(none)"
    return json.dumps(
        {
            "career_text": profile.get("career_text", ""),
            "career_tags": profile.get("career_tags", []),
            "program": profile.get("program", ""),
            "course": {
                "code": course.get("code"),
                "name": course.get("name"),
                "instructor": course.get("instructor"),
                "description_doc": course.get("description_doc", ""),
                "requirement_label": course.get("requirement_label", ""),
            },
            "other_courses_in_plan": other,
        },
        ensure_ascii=False,
    )


def explain_stream(course: dict, profile: dict, full_plan: list[dict]) -> Iterator[str]:
    user = _build_user_prompt(course, profile, full_plan)
    yield from llm_client.stream(SYSTEM, user)


def explain(course: dict, profile: dict, full_plan: list[dict]) -> str:
    user = _build_user_prompt(course, profile, full_plan)
    return llm_client.chat(SYSTEM, user)
