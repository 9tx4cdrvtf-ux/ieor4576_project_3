"""Tools that simulate the school's Student & Program APIs."""
import json
import os
from pathlib import Path
from typing import Optional

from agent.schemas import ProgramRules, StudentProfile

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDENTS_DIR = REPO_ROOT / "mock_data" / "students"
PROGRAMS_DIR = REPO_ROOT / "mock_data" / "programs"


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_students() -> list[dict]:
    """List all available mock student profiles (id + name + program)."""
    out = []
    for p in sorted(STUDENTS_DIR.glob("*.json")):
        d = _load_json(p)
        out.append({"student_id": d["student_id"], "name": d["name"], "program": d["program"]})
    return out


def get_student(student_id: str) -> dict:
    """Look up a student profile by id. Returns the full StudentProfile as a dict.

    Args:
        student_id: The student id (e.g. 'user_001').
    """
    path = STUDENTS_DIR / f"{student_id}.json"
    if not path.exists():
        return {"error": f"student '{student_id}' not found"}
    profile = StudentProfile(**_load_json(path))
    return profile.model_dump()


def get_program(program_id: str) -> dict:
    """Look up program graduation requirements by program id (e.g. 'MSOR').

    Args:
        program_id: The program code, case-insensitive (e.g. 'MSOR').
    """
    path = PROGRAMS_DIR / f"{program_id.lower()}.json"
    if not path.exists():
        return {"error": f"program '{program_id}' not found"}
    rules = ProgramRules(**_load_json(path))
    return rules.model_dump()


def load_student_obj(student_id: str) -> Optional[StudentProfile]:
    path = STUDENTS_DIR / f"{student_id}.json"
    if not path.exists():
        return None
    return StudentProfile(**_load_json(path))


def load_program_obj(program_id: str) -> Optional[ProgramRules]:
    path = PROGRAMS_DIR / f"{program_id.lower()}.json"
    if not path.exists():
        return None
    return ProgramRules(**_load_json(path))
