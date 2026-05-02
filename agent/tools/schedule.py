"""Deterministic schedule checks: time conflicts, eligibility, credit caps."""
from agent.schemas import Conflict
from agent.tools._sanitize import nan_safe
from agent.tools.courses import get_section
from agent.tools.student import load_student_obj


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> tuple[float, float] | None:
    s = max(a_start, b_start)
    e = min(a_end, b_end)
    return (s, e) if s < e else None


@nan_safe
def check_conflicts(section_keys: list[str]) -> list[dict]:
    """Find time overlaps between any pair of sections that share at least one weekday.

    Args:
        section_keys: List of section_key strings to check.
    Returns:
        List of conflict dicts, empty if no conflicts.
    """
    sections = [get_section(k) for k in section_keys]
    sections = [s for s in sections if s is not None]
    conflicts: list[dict] = []
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            a, b = sections[i], sections[j]
            shared = set(a["days"]) & set(b["days"])
            for day in shared:
                ov = _overlap(a["time_start"], a["time_end"], b["time_start"], b["time_end"])
                if ov is not None:
                    conflicts.append(
                        Conflict(
                            section_a=a["section_key"],
                            section_b=b["section_key"],
                            day=day,
                            overlap_start=ov[0],
                            overlap_end=ov[1],
                        ).model_dump()
                    )
    return conflicts


@nan_safe
def validate_schedule(section_keys: list[str], student_id: str) -> dict:
    """Run all hard checks on a proposed schedule for a student.

    Checks performed:
      - Time conflicts between any pair of sections
      - Each section is eligible ('required' or 'elective') for the student's program
      - Total credits within the student's [min, max] this-term cap
      - No duplicate course codes (different sections of the same course)

    Args:
        section_keys: List of section_key strings the student plans to take.
        student_id: Student id, e.g. 'user_001'.
    Returns:
        ValidationReport dict with valid flag, totals, and a list of messages.
    """
    student = load_student_obj(student_id)
    if student is None:
        return {"error": f"student '{student_id}' not found"}

    sections = [get_section(k) for k in section_keys]
    sections_clean = [s for s in sections if s is not None]
    missing = [k for k, s in zip(section_keys, sections) if s is None]

    conflicts = check_conflicts([s["section_key"] for s in sections_clean])

    eligibility_field = student.program.lower()
    ineligible: list[str] = []
    for s in sections_clean:
        elig = (s.get(eligibility_field) or "").lower()
        if elig not in ("required", "elective"):
            ineligible.append(s["section_key"])

    total_credits = sum(s["credits"] for s in sections_clean)
    over = total_credits > student.constraints.max_credits_this_term
    under = total_credits < student.constraints.min_credits_this_term

    seen: dict[str, list[str]] = {}
    for s in sections_clean:
        seen.setdefault(s["course_code"], []).append(s["section_key"])
    duplicates = {code: keys for code, keys in seen.items() if len(keys) > 1}

    messages: list[str] = []
    if missing:
        messages.append(f"Could not resolve section keys: {missing}")
    for c in conflicts:
        messages.append(
            f"Conflict on {c['day']} between {c['section_a']} and {c['section_b']}"
        )
    if ineligible:
        messages.append(
            f"Sections not eligible for {student.program}: {ineligible}"
        )
    if over:
        messages.append(
            f"Total {total_credits} credits exceeds your max of {student.constraints.max_credits_this_term}"
        )
    if under:
        messages.append(
            f"Total {total_credits} credits is below your min of {student.constraints.min_credits_this_term}"
        )
    if duplicates:
        messages.append(f"Duplicate course codes (different sections): {duplicates}")

    valid = (
        not conflicts
        and not ineligible
        and not over
        and not under
        and not missing
        and not duplicates
    )

    return {
        "valid": valid,
        "total_credits": total_credits,
        "conflicts": conflicts,
        "ineligible_sections": ineligible,
        "over_credit_cap": over,
        "under_credit_floor": under,
        "duplicate_course_codes": duplicates,
        "messages": messages,
    }
