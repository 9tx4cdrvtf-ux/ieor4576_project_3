"""Pydantic schemas shared across tools and agents."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────
# Student
# ─────────────────────────────────────────

class CompletedCourse(BaseModel):
    course_code: str
    title: str
    credits: float
    term: str


class Constraints(BaseModel):
    min_credits_this_term: float
    max_credits_this_term: float


class Preferences(BaseModel):
    career_direction: str
    days_off: List[str] = Field(default_factory=list)
    earliest_start: str = "09:00"
    latest_end: str = "21:00"
    max_days_on_campus: int = 5
    prefer_compact_schedule: bool = False
    modality: str = "any"
    course_load: str = "balanced"
    free_text_notes: str = ""


class StudentProfile(BaseModel):
    student_id: str
    name: str
    program: str
    start_term: str
    expected_graduation: str
    target_term: str
    completed_courses: List[CompletedCourse]
    constraints: Constraints
    preferences: Preferences


# ─────────────────────────────────────────
# Program
# ─────────────────────────────────────────

class CoreCourse(BaseModel):
    course_code: str
    title: str
    credits: float
    typical_term: str


class ProgramRules(BaseModel):
    program_id: str
    name: str
    total_credits_required: float
    department_credits_required: float
    department_prefixes: List[str]
    core_courses: List[CoreCourse]
    excluded_prefixes: List[str]
    approved_external_schools: List[str]
    eligibility_field: str
    notes: str = ""


# ─────────────────────────────────────────
# Progress
# ─────────────────────────────────────────

class ProgressReport(BaseModel):
    program: str
    total_credits_completed: float
    total_credits_required: float
    total_credits_remaining: float
    department_credits_completed: float
    department_credits_required: float
    department_credits_remaining: float
    core_completed: List[str]
    core_remaining: List[CoreCourse]
    on_track: bool
    notes: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────
# Course sections + plans
# ─────────────────────────────────────────

class CourseSection(BaseModel):
    section_key: str
    course_code: str
    course_name: str
    short_name: str = ""
    instructor: str = "TBA"
    credits: float
    days: List[str] = Field(default_factory=list)
    time_start: float = 0.0
    time_end: float = 0.0
    modality: str = "In-Person"
    location: str = ""
    description: str = ""
    eligibility: str = ""  # "required" / "elective" / "no" for the student's program
    relevance_reason: Optional[str] = None


class Conflict(BaseModel):
    section_a: str
    section_b: str
    day: str
    overlap_start: float
    overlap_end: float


class ValidationReport(BaseModel):
    valid: bool
    total_credits: float
    conflicts: List[Conflict]
    ineligible_sections: List[str]
    over_credit_cap: bool
    under_credit_floor: bool
    messages: List[str]


class ScheduleCandidate(BaseModel):
    name: str = Field(description="Short label like 'Plan A'")
    sections: List[str] = Field(description="List of section_key values for this plan")
    total_credits: float
    rationale: str = Field(description="Why this plan, 2-3 sentences")
    requirement_coverage: List[str] = Field(
        description="Bullet strings describing which requirement buckets this plan advances"
    )
    tradeoffs: str = Field(description="Honest one-line tradeoff vs other plans")


class SchedulePlan(BaseModel):
    candidates: List[ScheduleCandidate] = Field(description="1 to 3 candidate plans, ranked best-first")
    summary: str = Field(description="One paragraph summary across all candidates")


# ─────────────────────────────────────────
# Critic
# ─────────────────────────────────────────

class CandidateCritique(BaseModel):
    candidate_name: str = Field(description="Matches ScheduleCandidate.name (e.g. 'Plan A')")
    verdict: str = Field(description="One of: PASS, WARN, FAIL")
    hard_violations: List[str] = Field(
        default_factory=list,
        description="Objective rule breaks pulled from the ValidationReport (conflicts, ineligible sections, credit cap).",
    )
    soft_concerns: List[str] = Field(
        default_factory=list,
        description="Misalignment with user preferences or career direction (e.g. 'student wants Friday off but Plan has Friday class').",
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="What this plan does well for this specific student.",
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Concrete, actionable swaps if any issue should be fixed.",
    )


class CritiqueReport(BaseModel):
    overall_verdict: str = Field(description="Overall PASS/WARN/FAIL across all candidates")
    candidates: List[CandidateCritique]
    headline: str = Field(description="One-sentence summary the user sees at the top")
