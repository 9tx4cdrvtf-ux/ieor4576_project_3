"""Orchestrator Agent.

Coordinates the four sub-agents per the PRD pipeline:

  Requirement Checker  ->  Course Retriever  ->  Schedule Planner  ->  Explainer

Sub-agent dispatch is in-process here. The boundaries match the ADK
SequentialRunner pattern, so swapping in google.adk later is mechanical.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import course_retriever, requirement_checker, schedule_planner

PROFILE_DIR = Path(__file__).resolve().parents[1] / "data" / "student_profiles"


def load_profile(student_id: str) -> dict:
    path = PROFILE_DIR / f"{student_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown student_id: {student_id}")
    return json.loads(path.read_text())


def list_profiles() -> list[dict]:
    out: list[dict] = []
    for p in sorted(PROFILE_DIR.glob("*.json")):
        data = json.loads(p.read_text())
        out.append(
            {
                "student_id": data["student_id"],
                "name": data["name"],
                "program": data["program"],
                "year": data.get("year"),
                "graduation_term": data.get("graduation_term"),
                "completed_credits": data.get("total_credits", {}).get("completed"),
                "required_credits": data.get("total_credits", {}).get("required"),
            }
        )
    return out


def plan_schedule(
    *,
    student_id: str,
    selected_days: list[str],
    selected_windows: list[str],
    credit_target: float,
    career_text: str = "",
    career_tags: list[str] | None = None,
    avoid_departments: list[str] | None = None,
    instructor_preference: str | None = None,
) -> dict[str, Any]:
    """Run the full pipeline and return a serialisable result."""
    profile = load_profile(student_id)

    # The request always wins. If the user submits empty career_text and only
    # tags, do NOT silently fall back to the profile's stored career_text —
    # that would let the Explainer / Retriever reference text the user never
    # chose (e.g. profile says "quantitative finance" but user clicked only
    # the Software Engineer tag).
    profile = {
        **profile,
        "career_text": career_text,
        "career_tags": career_tags or [],
    }

    if len(selected_days) < 2:
        return {
            "error": "Please select at least 2 days.",
            "kind": "constraint",
        }
    if not selected_windows:
        return {
            "error": "Please select at least one time window.",
            "kind": "constraint",
        }

    requirements = requirement_checker.score_requirements(profile)
    if not requirements:
        return {
            "error": "All degree requirements appear satisfied.",
            "kind": "info",
            "profile": profile,
        }

    program_key = profile.get("program_key", "")
    pools_by_priority: list[list[dict]] = []
    for req in requirements:
        pool = course_retriever.retrieve_candidates(
            requirement=req,
            career_text=profile.get("career_text", ""),
            career_tags=profile.get("career_tags", []),
            program_key=program_key,
            completed_courses=profile.get("completed_courses", []),
            selected_days=selected_days,
            selected_windows=selected_windows,
            avoid_departments=avoid_departments,
            instructor_preference=instructor_preference,
        )
        pools_by_priority.append(pool)

    plans = schedule_planner.make_plans(
        pools_by_priority,
        profile=profile,
        target_credits=credit_target,
        selected_days=selected_days,
        selected_windows=selected_windows,
    )

    primary_key = next(iter(plans.keys()))
    primary = plans[primary_key]["courses"]

    alternatives_by_code: dict[str, list[dict]] = {}
    primary_codes = {c["code"] for c in primary}
    for pool in pools_by_priority:
        for cand in pool:
            if cand["code"] in primary_codes:
                continue
            same_req = next(
                (p for p in primary if p.get("requirement_key") == cand.get("requirement_key")),
                None,
            )
            if same_req is not None:
                alternatives_by_code.setdefault(same_req["code"], []).append(cand)
        for primary_code, alts in alternatives_by_code.items():
            alternatives_by_code[primary_code] = alts[:1]

    for course in primary:
        course["alternatives"] = alternatives_by_code.get(course["code"], [])

    return {
        "profile": profile,
        "requirements": requirements,
        "plans": plans,
        "primary_plan_key": primary_key,
    }
