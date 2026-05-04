"""Course Retriever Agent — RAG core.

Performs semantic vector search over the embedded IEOR Spring 2026 course
collection (built by ../../index_info.py) and applies hard filters for the
student's selected days, time windows, and program eligibility.

Scoring (matches PRD §7.4):
  course_score = 0.35 * semantic_similarity
               + 0.25 * requirement_priority_match
               + 0.20 * time_preference_fit
               + 0.10 * instructor_rating_normalized
               + 0.10 * seat_availability
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

CHROMA_PATH = os.getenv(
    "CHROMA_PATH",
    str(Path(__file__).resolve().parents[2] / "chroma_db"),
)
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "ieor_courses")

DAY_FLAG_BY_NAME = {
    "Monday": "has_monday",
    "Tuesday": "has_tuesday",
    "Wednesday": "has_wednesday",
    "Thursday": "has_thursday",
    "Friday": "has_friday",
}

TIME_WINDOWS = {
    "early_morning": (8.0, 10.0),
    "morning": (10.0, 12.0),
    "afternoon": (12.0, 16.0),
    "late_afternoon": (16.0, 18.0),
    "evening": (18.0, 21.0),
}


@lru_cache(maxsize=1)
def _collection():
    import chromadb
    from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
    from chromadb import EmbeddingFunction

    class _VertexEF(EmbeddingFunction):
        def __init__(self, model_name: str = "text-embedding-005") -> None:
            self.model = TextEmbeddingModel.from_pretrained(model_name)

        def __call__(self, input):  # noqa: A002 (chroma signature)
            inputs = [TextEmbeddingInput(t, "RETRIEVAL_QUERY") for t in input]
            return [list(e.values) for e in self.model.get_embeddings(inputs)]

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(name=COLLECTION_NAME, embedding_function=_VertexEF())


def _time_fit(meta: dict, windows: list[tuple[float, float]]) -> float:
    """1.0 if course fits inside any selected window, else 0.0."""
    if not windows:
        return 0.0
    start = float(meta.get("time_start", 0.0))
    end = float(meta.get("time_end", 0.0))
    for w_start, w_end in windows:
        if start >= w_start and end <= w_end + 0.001:
            return 1.0
    return 0.0


def _instructor_norm(meta: dict) -> float:
    # No CULPA data in our metadata; use a mild heuristic so untaught
    # sections (TBA) score slightly lower than known instructors.
    inst = (meta.get("instructor") or "").strip().upper()
    return 0.5 if inst in {"", "TBA"} else 0.8


def _seat_norm(_meta: dict) -> float:
    # Seat counts are not embedded in metadata for this dataset; return a
    # neutral 0.7 so the term doesn't dominate. Hooks into a real seat feed
    # would replace this.
    return 0.7


def retrieve_candidates(
    *,
    requirement: dict,
    career_text: str,
    program_key: str,
    selected_days: list[str],
    selected_windows: list[str],
    avoid_departments: list[str] | None = None,
    instructor_preference: str | None = None,
    n: int = 25,
) -> list[dict]:
    """Run a semantic RAG search and return ranked candidates for a bucket."""
    avoid_departments = [d.upper() for d in (avoid_departments or [])]
    windows = [TIME_WINDOWS[w] for w in selected_windows if w in TIME_WINDOWS]
    day_flags = [DAY_FLAG_BY_NAME[d] for d in selected_days if d in DAY_FLAG_BY_NAME]

    query = f"{requirement.get('label','')}. Career goal: {career_text}".strip()
    where: dict[str, Any] = {}
    program_clauses = [{program_key: "elective"}, {program_key: "required"}] if program_key else []
    if program_clauses:
        where["$or"] = program_clauses

    coll = _collection()
    res = coll.query(
        query_texts=[query],
        n_results=max(n * 2, 30),
        where=where or None,
    )

    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    distances = res.get("distances", [[]])[0]

    out: list[dict] = []
    for doc, meta, dist in zip(docs, metas, distances):
        if day_flags and not any(meta.get(flag) for flag in day_flags):
            continue
        if windows and _time_fit(meta, windows) == 0.0:
            continue
        code = (meta.get("course_code") or "").upper()
        if avoid_departments and any(code.startswith(d) for d in avoid_departments):
            continue

        sem_sim = max(0.0, 1.0 - float(dist))
        time_fit = _time_fit(meta, windows) if windows else 0.5
        req_match = 1.0  # already filtered for this requirement bucket
        score = (
            0.35 * sem_sim
            + 0.25 * req_match
            + 0.20 * time_fit
            + 0.10 * _instructor_norm(meta)
            + 0.10 * _seat_norm(meta)
        )

        if instructor_preference and instructor_preference.lower() in (
            (meta.get("instructor") or "").lower()
        ):
            score += 0.05

        out.append(
            {
                "section_key": meta.get("section_key"),
                "code": code,
                "name": meta.get("course_name"),
                "instructor": meta.get("instructor"),
                "credits": float(meta.get("points") or 0.0),
                "location": meta.get("location"),
                "course_type": meta.get("course_type"),
                "is_online": bool(meta.get("is_online")),
                "time_start": float(meta.get("time_start") or 0.0),
                "time_end": float(meta.get("time_end") or 0.0),
                "days": [
                    name
                    for name, flag in DAY_FLAG_BY_NAME.items()
                    if meta.get(flag)
                ],
                "description_doc": doc,
                "score": round(score, 4),
                "semantic_similarity": round(sem_sim, 4),
                "requirement_key": requirement.get("key"),
                "requirement_label": requirement.get("label"),
            }
        )

    out.sort(key=lambda c: c["score"], reverse=True)
    return out[:n]
