"""Schedule Planner Agent.

The planner is an LLM-driven agent. It receives the candidate pool from the
Course Retriever and is responsible for choosing the final course list. The
LLM has access to a `detect_conflicts` tool (function-calling) so it can
verify any tentative pick and revise after seeing real conflict reports.

Three plans are produced (A/B/C) by issuing the same loop with different
optimization objectives, matching PRD §7.5. The deterministic greedy
algorithm is kept as a safety fallback when the LLM fails or returns
conflicting picks even after retries.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass

from ..utils import llm_client

DAY_INDEX = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}
# Strict overlap only by default. Set PLANNER_BUFFER_MINUTES > 0 if you want a
# room-transition buffer (PRD originally suggested 15 min; that turned out to
# block too many legitimate back-to-back picks at Columbia's 10:10/11:40 grid).
BUFFER_HOURS = float(os.getenv("PLANNER_BUFFER_MINUTES", "0")) / 60.0

LLM_TEMPERATURE = float(os.getenv("PLANNER_TEMPERATURE", "0.7"))
LLM_MAX_TOOL_TURNS = int(os.getenv("PLANNER_MAX_TOOL_TURNS", "3"))
LLM_MAX_REVISIONS = int(os.getenv("PLANNER_MAX_REVISIONS", "2"))
PLANS_TO_GENERATE = [p.strip() for p in os.getenv("PLANS_TO_GENERATE", "plan_a").split(",") if p.strip()]


@dataclass
class _Block:
    course: dict
    day: str
    start: float
    end: float


def _expand_blocks(course: dict) -> list[_Block]:
    return [
        _Block(course=course, day=d, start=course["time_start"], end=course["time_end"])
        for d in course.get("days", [])
    ]


def detect_conflicts(courses: list[dict]) -> dict:
    """Tool: return hard/soft conflict report for a candidate plan."""
    blocks: list[_Block] = []
    for c in courses:
        blocks.extend(_expand_blocks(c))

    hard: list[str] = []
    by_day: dict[str, list[_Block]] = {}
    seen_codes: set[str] = set()

    for c in courses:
        if c["code"] in seen_codes:
            hard.append(f"Duplicate course {c['code']}")
        seen_codes.add(c["code"])

    for b in blocks:
        by_day.setdefault(b.day, []).append(b)

    for day, day_blocks in by_day.items():
        day_blocks.sort(key=lambda b: b.start)
        for i in range(len(day_blocks) - 1):
            cur, nxt = day_blocks[i], day_blocks[i + 1]
            if nxt.start < cur.end + BUFFER_HOURS:
                hard.append(
                    f"Time overlap on {day}: {cur.course['code']} ({cur.start}-{cur.end}) "
                    f"vs {nxt.course['code']} ({nxt.start}-{nxt.end})"
                )

    soft: list[str] = []
    for day, day_blocks in by_day.items():
        if len(day_blocks) > 3:
            soft.append(f"{day} has {len(day_blocks)} courses (>3)")
        if day_blocks:
            span = max(b.end for b in day_blocks) - min(b.start for b in day_blocks)
            if span > 8.0:
                soft.append(f"{day} spans {span:.1f}h (>8h)")
        consecutive = 0.0
        last_end = None
        for b in sorted(day_blocks, key=lambda b: b.start):
            if last_end is not None and b.start <= last_end + BUFFER_HOURS:
                consecutive += b.end - b.start
            else:
                consecutive = b.end - b.start
            if consecutive > 3.0:
                soft.append(f"{day} has >3h consecutive class")
                break
            last_end = b.end

    return {"hard": hard, "soft": soft, "feasible": len(hard) == 0}


# ─────────────────────────────────────────
# LLM-driven planner with tool use
# ─────────────────────────────────────────

DETECT_CONFLICTS_TOOL = {
    "type": "function",
    "function": {
        "name": "detect_conflicts",
        "description": (
            "Check whether a tentative list of courses has hard or soft "
            "scheduling conflicts. Returns {hard, soft, feasible}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "section_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "section_key values for the courses being considered",
                }
            },
            "required": ["section_keys"],
        },
    },
}

PLAN_GOALS = {
    "plan_a": (
        "Maximize coverage of the student's unfulfilled degree requirements, "
        "favoring graduation-blockers."
    ),
    "plan_b": (
        "Maximize semantic alignment with the student's career_text and "
        "career_tags, even at the cost of leaving one requirement bucket uncovered."
    ),
    "plan_c": (
        "Minimize the number of distinct days the student must come to campus "
        "while still satisfying the credit target."
    ),
}


def _candidate_compact(c: dict) -> dict:
    """Trim a candidate dict to the fields the LLM actually needs."""
    return {
        "section_key": c["section_key"],
        "code": c["code"],
        "name": c["name"],
        "instructor": c.get("instructor"),
        "credits": c["credits"],
        "days": c.get("days", []),
        "time_start": c["time_start"],
        "time_end": c["time_end"],
        "score": c.get("score"),
        "semantic_similarity": c.get("semantic_similarity"),
        "program_approved": c.get("program_approved", False),
        "program_status": c.get("program_status", ""),
        "is_topics_course": c.get("is_topics_course", False),
        "requirement_label": c.get("requirement_label"),
        "requirement_key": c.get("requirement_key"),
    }


def _llm_pick_one_plan(
    *,
    plan_key: str,
    goal: str,
    pools: list[list[dict]],
    profile: dict,
    target_credits: float,
    selected_days: list[str],
    selected_windows: list[str],
    seed_nudge: int,
) -> tuple[list[dict], str]:
    """Have the LLM pick courses with tool access. Returns (picks, rationale)."""
    by_key: dict[str, dict] = {c["section_key"]: c for pool in pools for c in pool}
    flat_candidates = list(by_key.values())

    completed_list = ", ".join(profile.get("completed_courses", [])) or "(none)"
    system = (
        "You are CourseCompass's Schedule Planner agent. You receive a candidate "
        "pool of course sections (already pre-filtered to the student's selected "
        "days and time windows) and you must choose a final list that satisfies "
        "ALL hard constraints below. Soft preferences are tie-breakers.\n\n"
        "HARD CONSTRAINTS (any violation is unacceptable):\n"
        "  H1. Never pick a course the student has already completed. "
        f"Completed: [{completed_list}]\n"
        "  H2. If any candidate has program_status='required' (i.e. it is a "
        "required core course for the student's program AND they have not "
        "completed it), include it. Required courses come first; electives fill "
        "remaining credits.\n"
        f"  H3. Total credits should be approximately {target_credits} (±2). "
        "Pick as many or as few sections as needed — typically 3–6.\n"
        "  H4. Zero hard scheduling conflicts. A hard conflict is when two "
        "sections share ANY day AND their time ranges overlap. Back-to-back "
        "classes (one ending exactly when the next starts) are FINE.\n\n"
        "SOFT PREFERENCES (rank by these once H1–H4 are satisfied):\n"
        f"  S1. Optimize for: {goal}\n"
        "  S2. Prefer high semantic_similarity to the student's career_text / "
        "career_tags.\n"
        "  S3. Avoid is_topics_course=true (generic 'Topics in X' courses with "
        "placeholder descriptions). Only include such a course if no concrete "
        "alternative covers the same requirement and you say so in the rationale.\n"
        "  S4. If a course has program_approved=false, you may still pick it "
        "for cross-discipline interests — but you MUST flag this in the "
        "rationale (e.g. 'not on the MSOR approved list; needs waiver').\n\n"
        "WORKFLOW:\n"
        "  1. Build a tentative list. Check pairwise: if two share a day, "
        "ensure time_end of one ≤ time_start of the other.\n"
        "  2. Call the detect_conflicts tool with the section_keys.\n"
        "  3. If feasible=false, swap conflicting sections and call again.\n"
        "  4. When feasible=true, return ONLY JSON: {'section_keys': [...], "
        "'rationale': '...'}. No prose, no code fences."
    )

    student_brief = {
        "name": profile.get("name"),
        "program": profile.get("program"),
        "completed_courses": profile.get("completed_courses", []),
        "career_text": profile.get("career_text", ""),
        "career_tags": profile.get("career_tags", []),
        "selected_days": selected_days,
        "selected_windows": selected_windows,
        "target_credits": target_credits,
        "plan_key": plan_key,
        "seed_nudge": seed_nudge,  # encourages variation across regenerations
        "candidates": [_candidate_compact(c) for c in flat_candidates],
    }
    user_msg = (
        "Pick a course list optimizing the stated goal. The seed_nudge is a "
        "tie-breaker: prefer slightly different ordering than your last run "
        "when given a different seed. Here is the input:\n\n"
        + json.dumps(student_brief, ensure_ascii=False)
    )

    import litellm

    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_msg},
    ]

    revisions_left = LLM_MAX_REVISIONS

    for _ in range(LLM_MAX_TOOL_TURNS + LLM_MAX_REVISIONS):
        resp = litellm.completion(
            model=llm_client.DEFAULT_MODEL,
            messages=messages,
            tools=[DETECT_CONFLICTS_TOOL],
            tool_choice="auto",
            temperature=LLM_TEMPERATURE,
        )
        msg = resp["choices"][0]["message"]
        messages.append(msg if isinstance(msg, dict) else msg.model_dump())

        tool_calls = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)

        if not tool_calls:
            content = msg["content"] if isinstance(msg, dict) else msg.content
            try:
                picks, rationale = _parse_picks(content or "", by_key)
            except (json.JSONDecodeError, ValueError) as exc:
                if revisions_left <= 0:
                    raise
                revisions_left -= 1
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your reply could not be parsed as JSON ({exc}). "
                            "Re-emit ONLY the JSON object with keys "
                            "'section_keys' and 'rationale'."
                        ),
                    }
                )
                continue

            report = detect_conflicts(picks)
            if report["feasible"] and len(picks) > 0:
                return picks, rationale

            if revisions_left <= 0:
                raise RuntimeError(
                    f"final pick still infeasible after revisions: {report['hard']}"
                )
            revisions_left -= 1
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your final answer is NOT feasible. The detect_conflicts "
                        "tool reports these hard conflicts that you must resolve:\n"
                        + json.dumps(report, ensure_ascii=False)
                        + "\n\nReplace the conflicting sections with non-overlapping "
                        "alternatives from the candidate pool, call detect_conflicts "
                        "again to verify, then return the corrected JSON."
                    ),
                }
            )
            continue

        for call in tool_calls:
            name = call["function"]["name"] if isinstance(call, dict) else call.function.name
            args_raw = call["function"]["arguments"] if isinstance(call, dict) else call.function.arguments
            call_id = call["id"] if isinstance(call, dict) else call.id
            try:
                args = json.loads(args_raw or "{}")
            except json.JSONDecodeError:
                args = {}
            if name == "detect_conflicts":
                picks = [by_key[k] for k in args.get("section_keys", []) if k in by_key]
                report = detect_conflicts(picks)
            else:
                report = {"error": f"unknown tool {name}"}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": json.dumps(report),
                }
            )

    raise RuntimeError("Planner exceeded max iterations without a feasible answer")


def _parse_picks(text: str, by_key: dict[str, dict]) -> tuple[list[dict], str]:
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end > start:
        s = s[start : end + 1]
    obj = json.loads(s)
    keys = obj.get("section_keys") or []
    rationale = obj.get("rationale", "")
    picks = [by_key[k] for k in keys if k in by_key]
    return picks, rationale


# ─────────────────────────────────────────
# Public entry — pure LLM, no fallback
# ─────────────────────────────────────────


def make_plans(
    pools_by_priority: list[list[dict]],
    *,
    profile: dict,
    target_credits: float,
    selected_days: list[str],
    selected_windows: list[str],
) -> dict:
    """Produce one or more plans using the LLM planner.

    Pure LLM — no deterministic fallback. If the LLM cannot produce a feasible
    plan within the configured retries, the exception propagates so the caller
    can surface it to the UI. Which plans to run is controlled by the
    PLANS_TO_GENERATE env var (default: plan_a only, for speed).
    """
    seed = random.randint(0, 10_000)
    plans: dict[str, dict] = {}

    for plan_key in PLANS_TO_GENERATE:
        if plan_key not in PLAN_GOALS:
            continue
        goal = PLAN_GOALS[plan_key]
        picks, rationale = _llm_pick_one_plan(
            plan_key=plan_key,
            goal=goal,
            pools=pools_by_priority,
            profile=profile,
            target_credits=target_credits,
            selected_days=selected_days,
            selected_windows=selected_windows,
            seed_nudge=seed + ord(plan_key[-1]),
        )
        report = detect_conflicts(picks)
        if not report["feasible"] or len(picks) == 0:
            raise RuntimeError(
                f"Plan {plan_key} infeasible after retries: {report['hard']}"
            )
        plans[plan_key] = {
            "goal": goal,
            "courses": picks,
            "rationale": rationale,
            "source": "llm",
        }

    return plans
