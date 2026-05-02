"""Helpers for rendering schedules and progress in Streamlit."""
from datetime import date, datetime, time, timedelta
from io import StringIO

from agent.tools.courses import get_section

DAY_NUM = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

# arbitrary anchor week for calendar display
_ANCHOR_MONDAY = date(2026, 1, 19)

# bucket → color
_COLORS = {
    "core": "#dc2626",
    "ieor_elective": "#2563eb",
    "external_elective": "#737373",
}


def _decimal_to_time(dec: float) -> time:
    h = int(dec)
    m = int(round((dec - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return time(hour=h, minute=m)


def section_to_events(section_key: str, color: str = "#2563eb") -> list[dict]:
    """Convert one section into FullCalendar event dicts (one per weekday it meets)."""
    s = get_section(section_key)
    if s is None or not s["days"]:
        return []
    events = []
    for day in s["days"]:
        offset = DAY_NUM.get(day)
        if offset is None:
            continue
        d = _ANCHOR_MONDAY + timedelta(days=offset)
        st = datetime.combine(d, _decimal_to_time(s["time_start"]))
        en = datetime.combine(d, _decimal_to_time(s["time_end"]))
        events.append(
            {
                "title": f"{s['course_code']} — {s['short_name'] or s['course_name']}",
                "start": st.isoformat(),
                "end": en.isoformat(),
                "backgroundColor": color,
                "borderColor": color,
                "extendedProps": {
                    "instructor": s["instructor"],
                    "location": s["location"],
                    "section_key": section_key,
                    "credits": s["credits"],
                },
            }
        )
    return events


def candidate_events(
    section_keys: list[str],
    core_codes: set[str] | None = None,
    department_prefixes: tuple[str, ...] = ("IEOR", "CSOR", "ECIE", "SIEO"),
) -> list[dict]:
    core_codes = core_codes or set()
    events: list[dict] = []
    for k in section_keys:
        s = get_section(k)
        if s is None:
            continue
        if s["course_code"].upper() in core_codes:
            color = _COLORS["core"]
        elif any(s["course_code"].upper().startswith(p) for p in department_prefixes):
            color = _COLORS["ieor_elective"]
        else:
            color = _COLORS["external_elective"]
        events.extend(section_to_events(k, color=color))
    return events


def build_ics(section_keys: list[str], term_start: date, term_end: date) -> str:
    """Build a minimal .ics file with weekly recurring events for each section."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//IEOR Course Planner//EN",
        "CALSCALE:GREGORIAN",
    ]
    until = term_end.strftime("%Y%m%dT235959Z")
    for k in section_keys:
        s = get_section(k)
        if s is None or not s["days"]:
            continue
        for day in s["days"]:
            offset = DAY_NUM.get(day)
            if offset is None:
                continue
            # find first occurrence of this weekday on/after term_start
            first = term_start + timedelta(days=(offset - term_start.weekday()) % 7)
            st = datetime.combine(first, _decimal_to_time(s["time_start"]))
            en = datetime.combine(first, _decimal_to_time(s["time_end"]))
            byday = day.upper()[:2]  # MO/TU/WE/TH/FR
            uid = f"{k}-{day}@ieor-planner"
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTSTART:{st.strftime('%Y%m%dT%H%M%S')}",
                    f"DTEND:{en.strftime('%Y%m%dT%H%M%S')}",
                    f"RRULE:FREQ=WEEKLY;BYDAY={byday};UNTIL={until}",
                    f"SUMMARY:{s['course_code']} {s['short_name'] or s['course_name']}",
                    f"LOCATION:{s['location']}",
                    f"DESCRIPTION:Instructor: {s['instructor']} | {s['credits']} credits",
                    "END:VEVENT",
                ]
            )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
