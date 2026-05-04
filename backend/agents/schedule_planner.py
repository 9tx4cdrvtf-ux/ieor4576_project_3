"""Schedule Planner Agent.

Generates up to three distinct plans (A/B/C) from candidate pools while
respecting hard / soft conflicts. Uses a structured "detect_conflicts" tool
function — exposed as a callable so it could just as easily be wired up via
LiteLLM tool-use; we keep it in-process for determinism.
"""

from __future__ import annotations

from dataclasses import dataclass

DAY_INDEX = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
}

BUFFER_HOURS = 0.25  # 15 minutes between rooms


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


def _greedy_plan(
    pools: list[list[dict]],
    *,
    target_count: int,
    target_credits: float,
    sort_key,
) -> list[dict]:
    """Greedy fill: walk pools in priority order, picking the best feasible
    candidate, skipping if it conflicts with what we've already committed.
    """
    chosen: list[dict] = []
    used_codes: set[str] = set()
    for pool in pools:
        for cand in sorted(pool, key=sort_key, reverse=True):
            if cand["code"] in used_codes:
                continue
            trial = chosen + [cand]
            report = detect_conflicts(trial)
            if not report["feasible"]:
                continue
            chosen.append(cand)
            used_codes.add(cand["code"])
            break
        if len(chosen) >= target_count:
            break

    if len(chosen) < target_count:
        spillover = [c for pool in pools for c in pool if c["code"] not in used_codes]
        for cand in sorted(spillover, key=sort_key, reverse=True):
            trial = chosen + [cand]
            if detect_conflicts(trial)["feasible"]:
                chosen.append(cand)
                used_codes.add(cand["code"])
            if len(chosen) >= target_count:
                break

    return chosen


def make_plans(
    pools_by_priority: list[list[dict]],
    *,
    target_count: int,
    target_credits: float,
) -> dict:
    """Produce three plans optimized for different goals."""
    plan_a = _greedy_plan(
        pools_by_priority,
        target_count=target_count,
        target_credits=target_credits,
        sort_key=lambda c: c["score"],
    )
    plan_b = _greedy_plan(
        pools_by_priority,
        target_count=target_count,
        target_credits=target_credits,
        sort_key=lambda c: c["semantic_similarity"],
    )

    def commute_key(c: dict):
        return (-len(c.get("days", [])), c["score"])

    plan_c = _greedy_plan(
        pools_by_priority,
        target_count=target_count,
        target_credits=target_credits,
        sort_key=lambda c: -commute_key(c)[0] * 0.5 + c["score"],
    )

    return {
        "plan_a": {"goal": "Maximize requirement coverage", "courses": plan_a},
        "plan_b": {"goal": "Maximize career relevance", "courses": plan_b},
        "plan_c": {"goal": "Minimize commute days", "courses": plan_c},
    }
