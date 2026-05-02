"""Streamlit front-end for the IEOR Course Planner agent."""
import json
import sys
import uuid
from datetime import date
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


# ─────────────────────────────────────────
# Session state
# ─────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_plan" not in st.session_state:
    st.session_state.current_plan = None


# ─────────────────────────────────────────
# Sidebar — student picker + preference form
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
        value=__import__("datetime").datetime.strptime(
            student.preferences.earliest_start if student else "09:00", "%H:%M"
        ).time(),
    )
    latest = st.time_input(
        "Latest end",
        value=__import__("datetime").datetime.strptime(
            student.preferences.latest_end if student else "21:00", "%H:%M"
        ).time(),
    )
    modality = st.radio(
        "Modality", ["any", "in-person", "online ok"],
        index=["any", "in-person", "online ok"].index(student.preferences.modality if student else "any"),
        horizontal=True,
    )
    career = st.radio(
        "Career direction",
        ["Quant Trading", "Data Science & ML", "Tech PM", "Consulting", "Supply Chain", "Undecided"],
        index=0 if not student else max(
            0,
            ["Quant Trading", "Data Science & ML", "Tech PM", "Consulting", "Supply Chain", "Undecided"].index(student.preferences.career_direction)
            if student.preferences.career_direction in ["Quant Trading", "Data Science & ML", "Tech PM", "Consulting", "Supply Chain", "Undecided"]
            else 0,
        ),
    )
    notes = st.text_area(
        "Anything else?",
        value=student.preferences.free_text_notes if student else "",
        placeholder="e.g. avoid Prof. X, prefer project-based courses…",
    )

    if st.button("Reset chat", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.current_plan = None
        st.rerun()


# ─────────────────────────────────────────
# Main — header + progress
# ─────────────────────────────────────────
st.title("🎓 Columbia IEOR Course Planner")
st.caption("Pick a student, set preferences, then ask the agent to plan your term.")

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
# Chat
# ─────────────────────────────────────────
chat_col, plan_col = st.columns([1, 1])

with chat_col:
    st.markdown("### Chat")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["text"])

    user_msg = st.text_area(
        "Your career preference & any other notes",
        key="user_input",
        placeholder="Your career preference",
        height=100,
        label_visibility="collapsed",
    )
    submitted = st.button(
        "🎓 开始生成课程安排",
        type="primary",
        use_container_width=True,
        disabled=not user_msg.strip(),
    )
    if submitted and user_msg.strip():
        prefs_summary = (
            f"\n\n[UI preferences]\n"
            f"- target_credits: {target_credits}\n"
            f"- days_off: {days_off}\n"
            f"- earliest_start: {earliest.strftime('%H:%M')}\n"
            f"- latest_end: {latest.strftime('%H:%M')}\n"
            f"- modality: {modality}\n"
            f"- career_direction: {career}\n"
            f"- free_text_notes: {notes}\n"
        )
        full_msg = (
            f"Student id: {student_id}. {user_msg}{prefs_summary}"
        )
        st.session_state.messages.append({"role": "user", "text": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        with st.chat_message("assistant"):
            with st.spinner("Planning…"):
                try:
                    events, state = run_sync(
                        user_id=student_id,
                        session_id=st.session_state.session_id,
                        message=full_msg,
                    )
                    final_text_parts = [
                        e["text"] for e in events
                        if e["type"] == "text" and e.get("author") == "course_planner_coordinator"
                    ]
                    reply = "\n\n".join(final_text_parts) or "_(no response)_"
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "text": reply})

                    plan = state.get("current_plan")
                    if plan:
                        if isinstance(plan, str):
                            try:
                                plan = json.loads(plan)
                            except Exception:
                                plan = None
                        if plan:
                            st.session_state.current_plan = plan
                except Exception as e:
                    st.error(f"Agent error: {e}")


# ─────────────────────────────────────────
# Plan rendering
# ─────────────────────────────────────────
with plan_col:
    st.markdown("### Recommended schedule")
    plan = st.session_state.current_plan
    if not plan or not plan.get("candidates"):
        st.info("No plan yet — ask the agent in chat to generate one.")
    else:
        st.markdown(f"_{plan.get('summary', '')}_")
        tabs = st.tabs([c["name"] for c in plan["candidates"]])
        core_codes = (
            {c["course_code"].upper() for c in load_program_obj(student.program).model_dump()["core_courses"]}
            if student else set()
        )

        for tab, cand in zip(tabs, plan["candidates"]):
            with tab:
                st.markdown(f"**Total credits:** {cand['total_credits']:.1f}")
                st.markdown(f"**Why:** {cand['rationale']}")

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
                            "height": 500,
                        },
                        key=f"cal_{cand['name']}",
                    )

                if cand.get("requirement_coverage"):
                    with st.expander("Requirement coverage"):
                        for line in cand["requirement_coverage"]:
                            st.markdown(f"- {line}")
                if cand.get("tradeoffs"):
                    st.caption(f"Trade-off: {cand['tradeoffs']}")

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
