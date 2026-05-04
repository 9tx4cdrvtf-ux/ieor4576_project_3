"""Requirement Checker Agent.

Scores unfulfilled degree-requirement buckets by priority. The score is
purely deterministic — no LLM call is needed for this step, which keeps
graduation-blocker logic auditable.
"""

from __future__ import annotations

from typing import Any


def _semesters_remaining(profile: dict) -> int:
    """Rough estimate of semesters remaining given graduation_term."""
    grad = (profile.get("graduation_term") or "").lower()
    if "spring" in grad:
        return 1
    if "fall" in grad:
        return 2
    return 4


def score_requirements(profile: dict) -> list[dict]:
    """Return the unfulfilled requirement buckets sorted by priority desc.

    priority = 100 * is_graduation_blocker
             + (5 - semesters_remaining) * 20
             + remaining_count * 10
    """
    semesters_left = _semesters_remaining(profile)
    out: list[dict] = []
    reqs: dict[str, Any] = profile.get("degree_requirements", {}) or {}
    for key, bucket in reqs.items():
        remaining = max(
            0,
            int(bucket.get("required_count", 0)) - int(bucket.get("completed_count", 0)),
        )
        if remaining <= 0:
            continue
        is_blocker = bool(bucket.get("graduation_blocker", False))
        priority = (
            (100 if is_blocker else 0)
            + max(0, (5 - semesters_left)) * 20
            + remaining * 10
        )
        out.append(
            {
                "key": key,
                "label": bucket.get("label", key),
                "remaining": remaining,
                "graduation_blocker": is_blocker,
                "priority": priority,
                "completed_codes": bucket.get("completed_codes", []),
                "remaining_examples": bucket.get("remaining_examples", []),
            }
        )
    out.sort(key=lambda b: b["priority"], reverse=True)
    return out
