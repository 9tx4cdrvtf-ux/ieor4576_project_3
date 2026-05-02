"""Streamlit front-end for the IEOR Course Planner agent."""
import json
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.tools.courses import get_section  # noqa: E402
from agent.tools.progress import compute_progress  # noqa: E402
from agent.tools.student import list_students, load_program_obj, load_student_obj  # noqa: E402
from app.agent_runner import run_sync  # noqa: E402
from app.render import build_ics, candidate_events  # noqa: E402

try:
    from streamlit_calendar import calendar  # type: ignore
    HAS_CALENDAR = True
except Exception:
    HAS_CALENDAR = False

st.set_page_config(page_title="IEOR Course Planner", page_icon="🎓", layout="wide")

CAREER_PRESETS = [
    "Quant Trading",
    "Data Science & ML",
    "Tech PM",
    "Consulting",
    "Supply Chain",
    "Undecided",
    "Other",
]


# ─────────────────────────────────────────
# Session state
# ─────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "current_plan" not in st.session_state:
    st.session_state.current_plan = None
if "last_error" not in st.session_state:
    st.session_state.last_error = None
if "last_events" not in st.session_state:
    st.session_state.last_events = []
if "last_state" not in st.session_state:
    st.session_state.last_state = {}


# ─────────────────────────────────────────
# Sidebar — student picker + preference form + Generate
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### Student profile")
    students = list_students()
    options = {f"{s['name']} ({s['program']})": s["student_id"] for s in students}
    label = st.selectbox("Choose student", list(options.keys()))
    student_id = options[label]
    student = load_student_obj(student_id)
    program = load_program_obj(student.program) if student else None

    if student:
        st.markdown(f"**Program:** {student.program}")
        st.markdown(f"**Target term:** {student.target_term}")
        st.markdown(f"**Completed:** {sum(c.credits for c in student.completed_courses):.1f} credits")
        with st.expander("Completed courses"):
            for c in student.completed_courses:
                st.markdown(f"- `{c.course_code}` {c.title} ({c.credits} cr)")

    st.markdown("---")
    st.markdown("### This term — preferences")
    target_credits = st.slider(
        "Target credits this term",
        float(student.constraints.min_credits_this_term) if student else 6.0,
        21.0,
        12.0,
        step=0.5,
    )
    days_off = st.multiselect(
        "Days off (no class)",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        default=student.preferences.days_off if student else [],
    )
    earliest = st.time_input(
        "Earliest start",
        value=datetime.strptime(
            student.preferences.earliest_start if student else "09:00", "%H:%M"
        ).time(),
    )
    latest = st.time_input(
        "Latest end",
        value=datetime.strptime(
            student.preferences.latest_end if student else "21:00", "%H:%M"
        ).time(),
    )
    modality = st.radio(
        "Modality", ["any", "in-person", "online ok"],
        index=["any", "in-person", "online ok"].index(student.preferences.modality if student else "any"),
        horizontal=True,
    )

    default_career = student.preferences.career_direction if student else "Undecided"
    career_index = CAREER_PRESETS.index(default_career) if default_career in CAREER_PRESETS else 0
    career_choice = st.radio("Career direction", CAREER_PRESETS, index=career_index)
    if career_choice == "Other":
        career_other = st.text_input(
            "Describe your career direction",
            placeholder="e.g. Climate-tech ops, Healthcare analytics…",
        )
        career = career_other.strip() or "Other (unspecified)"
    else:
        career = career_choice

    user_input = st.text_area(
        "Your career preference & anything else",
        key="user_input",
        placeholder=(
            "e.g. interested in financial applications of ML; "
            "prefer project-based courses; avoid Prof. X…"
        ),
        height=120,
    )

    submitted = st.button(
        "🎓 Generate my schedule",
        type="primary",
        use_container_width=True,
    )

    if st.button("Reset", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.current_plan = None
        st.session_state.last_error = None
        st.rerun()


# ─────────────────────────────────────────
# Main — title + progress
# ─────────────────────────────────────────
st.title("🎓 Columbia IEOR Course Planner")
st.caption("Set your preferences in the sidebar, then click Generate.")

if student and program:
    progress = compute_progress(student_id)
    cols = st.columns(3)
    cols[0].metric(
        "Total credits",
        f"{progress['total_credits_completed']:.1f} / {progress['total_credits_required']:.0f}",
        f"{progress['total_credits_remaining']:.1f} remaining",
    )
    cols[1].metric(
        f"{'/'.join(program.department_prefixes)} credits",
        f"{progress['department_credits_completed']:.1f} / {progress['department_credits_required']:.0f}",
        f"{progress['department_credits_remaining']:.1f} remaining",
    )
    cols[2].metric(
        "Core remaining",
        f"{len(progress['core_remaining'])} course(s)",
        ", ".join(c["course_code"] for c in progress["core_remaining"][:3]) or "—",
    )

st.markdown("---")


# ─────────────────────────────────────────
# Run agent on submit
# ─────────────────────────────────────────
if submitted:
    user_msg = (user_input or "").strip() or "Plan my schedule for this term."
    prefs_summary = (
        f"\n\n[UI preferences]\n"
        f"- target_credits: {target_credits}\n"
        f"- days_off: {days_off}\n"
        f"- earliest_start: {earliest.strftime('%H:%M')}\n"
        f"- latest_end: {latest.strftime('%H:%M')}\n"
        f"- modality: {modality}\n"
        f"- career_direction: {career}\n"
    )
    full_msg = f"Student id: {student_id}. {user_msg}{prefs_summary}"

    with st.spinner("Planning your schedule…"):
        try:
            events, state, plan = run_sync(
                user_id=student_id,
                session_id=st.session_state.session_id,
                message=full_msg,
            )
            st.session_state.last_events = events
            st.session_state.last_state = state
            if plan:
                st.session_state.current_plan = plan
                st.session_state.last_error = None
            else:
                st.session_state.last_error = "Agent finished but did not produce a plan."
        except Exception as e:
            st.session_state.last_error = f"Agent error: {e}"


# ─────────────────────────────────────────
# Recommended schedule (full-width)
# ─────────────────────────────────────────
st.markdown("### Recommended schedule")

if st.session_state.last_error:
    st.error(st.session_state.last_error)

# Debug panel — show what the agent actually did when something looks off
if st.session_state.last_events:
    with st.expander("🔍 Agent trace (debug)", expanded=bool(st.session_state.last_error)):
        st.markdown("**Tool calls / sub-agent invocations**")
        for ev in st.session_state.last_events:
            t = ev.get("type")
            if t == "tool_call":
                st.markdown(f"- **call** `{ev['name']}` ({ev.get('author')}) — args: `{ev.get('args')}`")
            elif t == "tool_result":
                resp = ev.get("response")
                preview = json.dumps(resp, default=str)[:300] if resp is not None else "—"
                st.markdown(f"- **result** `{ev['name']}` → `{preview}…`")
            elif t == "text":
                st.markdown(f"- **text** ({ev.get('author')}): {ev.get('text','')[:200]}")
        st.markdown("**Final session.state keys:** " + ", ".join(st.session_state.last_state.keys()) or "(empty)")

plan = st.session_state.current_plan
if not plan or not plan.get("candidates"):
    st.info("No plan yet — fill in preferences in the sidebar and click **Generate my schedule**.")
else:
    if plan.get("summary"):
        st.markdown(f"_{plan['summary']}_")

    tabs = st.tabs([c["name"] for c in plan["candidates"]])
    core_codes = (
        {c["course_code"].upper() for c in load_program_obj(student.program).model_dump()["core_courses"]}
        if student else set()
    )

    for tab, cand in zip(tabs, plan["candidates"]):
        with tab:
            top = st.columns([1, 1])
            top[0].metric("Total credits", f"{cand['total_credits']:.1f}")
            top[1].caption(cand.get("tradeoffs") or "")
            st.markdown(f"**Why:** {cand['rationale']}")

            col_courses, col_cal = st.columns([1, 1])

            with col_courses:
                st.markdown("**Courses**")
                for sk in cand["sections"]:
                    s = get_section(sk)
                    if not s:
                        st.markdown(f"- `{sk}` _(not found in catalog)_")
                        continue
                    days_str = "/".join(d[:3] for d in s["days"]) if s["days"] else "TBA"
                    st.markdown(
                        f"- **{s['course_code']}** {s['short_name'] or s['course_name']} — "
                        f"{s['credits']} cr · {days_str} {s['time_start']:.2f}–{s['time_end']:.2f} · "
                        f"{s['instructor']}"
                    )
                if cand.get("requirement_coverage"):
                    with st.expander("Requirement coverage"):
                        for line in cand["requirement_coverage"]:
                            st.markdown(f"- {line}")

            with col_cal:
                if HAS_CALENDAR:
                    events = candidate_events(cand["sections"], core_codes=core_codes)
                    calendar(
                        events=events,
                        options={
                            "initialView": "timeGridWeek",
                            "slotMinTime": "08:00:00",
                            "slotMaxTime": "22:00:00",
                            "weekends": False,
                            "headerToolbar": False,
                            "allDaySlot": False,
                            "height": 480,
                        },
                        key=f"cal_{cand['name']}",
                    )

            ics = build_ics(
                cand["sections"],
                term_start=date(2026, 1, 20),
                term_end=date(2026, 5, 8),
            )
            st.download_button(
                "Download .ics (any calendar app)",
                data=ics,
                file_name=f"{cand['name'].replace(' ', '_')}.ics",
                mime="text/calendar",
                key=f"ics_{cand['name']}",
            )
