"""Pure function: derive a ProgressReport from student + program rules.

This is the agent's source of truth for what's required and what's left.
It must never be computed by the LLM — only by this function.
"""
from agent.schemas import ProgressReport, StudentProfile, ProgramRules
from agent.tools.student import load_student_obj, load_program_obj


def _is_department(course_code: str, prefixes: list[str]) -> bool:
    return any(course_code.upper().startswith(p) for p in prefixes)


def compute_progress_report(student: StudentProfile, program: ProgramRules) -> ProgressReport:
    completed_codes = {c.course_code.upper() for c in student.completed_courses}
    total_completed = sum(c.credits for c in student.completed_courses)

    dept_completed = sum(
        c.credits
        for c in student.completed_courses
        if _is_department(c.course_code, program.department_prefixes)
    )

    core_codes = [c.course_code.upper() for c in program.core_courses]
    core_completed = [code for code in core_codes if code in completed_codes]
    core_remaining = [c for c in program.core_courses if c.course_code.upper() not in completed_codes]

    total_remaining = max(program.total_credits_required - total_completed, 0.0)
    dept_remaining = max(program.department_credits_required - dept_completed, 0.0)

    notes: list[str] = []
    if core_remaining:
        notes.append(
            f"Still need {len(core_remaining)} core course(s): "
            + ", ".join(c.course_code for c in core_remaining)
        )
    if dept_remaining > 0:
        notes.append(
            f"Need {dept_remaining:.1f} more credits from {'/'.join(program.department_prefixes)}-prefix departments."
        )
    if total_remaining > 0:
        notes.append(f"Need {total_remaining:.1f} more total credits to graduate.")

    on_track = (
        len(core_remaining) <= 4  # rough heuristic — most cores are early-term
        and total_remaining <= program.total_credits_required
    )

    return ProgressReport(
        program=program.program_id,
        total_credits_completed=total_completed,
        total_credits_required=program.total_credits_required,
        total_credits_remaining=total_remaining,
        department_credits_completed=dept_completed,
        department_credits_required=program.department_credits_required,
        department_credits_remaining=dept_remaining,
        core_completed=core_completed,
        core_remaining=core_remaining,
        on_track=on_track,
        notes=notes,
    )


def compute_progress(student_id: str) -> dict:
    """Compute the student's degree progress against their program requirements.

    Returns a ProgressReport dict including: total/department credit counts,
    which core courses are done vs remaining, and human-readable notes.

    Args:
        student_id: Student id, e.g. 'user_001'.
    """
    student = load_student_obj(student_id)
    if student is None:
        return {"error": f"student '{student_id}' not found"}
    program = load_program_obj(student.program)
    if program is None:
        return {"error": f"program '{student.program}' not found"}
    return compute_progress_report(student, program).model_dump()
