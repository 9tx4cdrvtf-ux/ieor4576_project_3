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


def get_section(section_key: str) -> dict | None:
    df = load_catalog()
    rows = df[df["Section key"] == section_key]
    if rows.empty:
        return None
    r = rows.iloc[0]
    return {
        "section_key": r["Section key"],
        "course_code": r["Course Code"],
        "course_name": r["Course Name"],
        "short_name": r.get("Short Name", ""),
        "instructor": r["Instructor"] if pd.notna(r["Instructor"]) else "TBA",
        "credits": float(r["Points"]),
        "days": list(r["Day"]),
        "time_start": float(r["Time_start"]),
        "time_end": float(r["Time_end"]),
        "modality": r["Method of Instruction"],
        "location": r["Location"] if pd.notna(r["Location"]) else "",
        "description": r["Course Description"] if pd.notna(r["Course Description"]) else "",
        "msor": r.get("MSOR", ""),
        "msie": r.get("MSIE", ""),
        "msba": r.get("MSBA", ""),
        "mse": r.get("MSE", ""),
        "msfe": r.get("MSFE", ""),
    }
