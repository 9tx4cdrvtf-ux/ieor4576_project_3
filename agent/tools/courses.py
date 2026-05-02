"""Loaders + helpers for the Spring 2026 course catalog CSV."""
import ast
from functools import lru_cache
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = REPO_ROOT / "web_scrawl" / "Spring2026_course_info_master.csv"


def _parse_days(val) -> list[str]:
    if pd.isna(val):
        return []
    if isinstance(val, list):
        return val
    try:
        result = ast.literal_eval(val)
        return list(result) if isinstance(result, list) else []
    except Exception:
        return []


@lru_cache(maxsize=1)
def load_catalog() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df = df.drop_duplicates(subset=["Section key"])
    df["Day"] = df["Day"].apply(_parse_days)
    df["Time_start"] = pd.to_numeric(df["Time_start"], errors="coerce").fillna(0.0)
    df["Time_end"] = pd.to_numeric(df["Time_end"], errors="coerce").fillna(0.0)
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0.0)
    return df


def _s(val, default: str = "") -> str:
    """Coerce to clean string, mapping NaN/None to default."""
    if val is None or (isinstance(val, float) and pd.isna(val)) or pd.isna(val):
        return default
    return str(val)


def _f(val, default: float = 0.0) -> float:
    """Coerce to clean float, mapping NaN/None to default. JSON-safe."""
    try:
        if val is None or pd.isna(val):
            return default
        f = float(val)
        if f != f:  # NaN check (NaN != NaN)
            return default
        return f
    except (TypeError, ValueError):
        return default


def get_section(section_key: str) -> dict | None:
    df = load_catalog()
    rows = df[df["Section key"] == section_key]
    if rows.empty:
        return None
    r = rows.iloc[0]
    return {
        "section_key": _s(r["Section key"]),
        "course_code": _s(r["Course Code"]),
        "course_name": _s(r["Course Name"]),
        "short_name": _s(r.get("Short Name", "")),
        "instructor": _s(r["Instructor"], default="TBA"),
        "credits": _f(r["Points"]),
        "days": list(r["Day"]) if isinstance(r["Day"], list) else [],
        "time_start": _f(r["Time_start"]),
        "time_end": _f(r["Time_end"]),
        "modality": _s(r["Method of Instruction"]),
        "location": _s(r["Location"]),
        "description": _s(r["Course Description"]),
        "msor": _s(r.get("MSOR", "")),
        "msie": _s(r.get("MSIE", "")),
        "msba": _s(r.get("MSBA", "")),
        "mse": _s(r.get("MSE", "")),
        "msfe": _s(r.get("MSFE", "")),
    }
