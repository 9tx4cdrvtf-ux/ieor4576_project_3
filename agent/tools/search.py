"""Semantic + metadata-filtered search over the Spring 2026 course catalog.

Wraps the existing ChromaDB collection built by index_info.py.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import chromadb
from chromadb import Documents, Embeddings, EmbeddingFunction
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

from agent.tools.courses import get_section

REPO_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = REPO_ROOT / "chroma_db"
COLLECTION = "ieor_courses"


class _VertexQueryEmbedding(EmbeddingFunction):
    """Query-time embedding: uses RETRIEVAL_QUERY task type."""

    def __init__(self, model_name: str = "text-embedding-005"):
        self.model = TextEmbeddingModel.from_pretrained(model_name)

    def __call__(self, input: Documents) -> Embeddings:
        inputs = [TextEmbeddingInput(text, "RETRIEVAL_QUERY") for text in input]
        embeddings = self.model.get_embeddings(inputs)
        return [list(e.values) for e in embeddings]


@lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION, embedding_function=_VertexQueryEmbedding())


_DAY_FLAGS = {
    "Monday": "has_monday",
    "Tuesday": "has_tuesday",
    "Wednesday": "has_wednesday",
    "Thursday": "has_thursday",
    "Friday": "has_friday",
}


def search_courses(
    query: str,
    program: str = "MSOR",
    max_results: int = 12,
    days_off: Optional[list[str]] = None,
    earliest_start: Optional[float] = None,
    latest_end: Optional[float] = None,
    exclude_online: bool = False,
) -> list[dict]:
    """Semantic search over Spring 2026 courses, filtered by hard constraints.

    Use this to find courses matching a topic or career direction. The query
    should be a plain-language description (e.g. "machine learning for finance",
    "operations research consulting"). Hard filters (program eligibility, time
    of day, days off, modality) are applied as metadata filters before ranking.

    Args:
        query: Plain-language description of what the student is looking for.
        program: Student's program code (MSOR/MSIE/MSBA/MSE/MSFE) — only
            courses where this program field is 'required' or 'elective'
            are returned.
        max_results: Number of candidate courses to return (default 12).
        days_off: List of weekday names the student wants free (e.g. ['Friday']).
        earliest_start: Earliest acceptable class start time as decimal hours
            (e.g. 10.0 = 10:00 AM).
        latest_end: Latest acceptable class end time as decimal hours
            (e.g. 18.0 = 6:00 PM).
        exclude_online: If True, only return in-person sections.

    Returns:
        List of dicts with course details (section_key, course_code,
        course_name, instructor, credits, days, times, modality, description,
        eligibility for the student's program).
    """
    where_clauses: list[dict] = []

    program_field = program.lower()
    if program_field in {"msor", "msie", "msba", "mse", "msfe"}:
        where_clauses.append({program_field: {"$in": ["required", "elective"]}})

    if days_off:
        for day in days_off:
            flag = _DAY_FLAGS.get(day)
            if flag:
                where_clauses.append({flag: False})

    if earliest_start is not None:
        where_clauses.append({"time_start": {"$gte": float(earliest_start)}})
    if latest_end is not None:
        where_clauses.append({"time_end": {"$lte": float(latest_end)}})
    if exclude_online:
        where_clauses.append({"is_online": False})

    where: Optional[dict] = None
    if len(where_clauses) == 1:
        where = where_clauses[0]
    elif len(where_clauses) > 1:
        where = {"$and": where_clauses}

    coll = _get_collection()
    res = coll.query(
        query_texts=[query],
        n_results=max_results,
        where=where,
    )

    out: list[dict] = []
    if not res.get("ids") or not res["ids"][0]:
        return out

    metas = res["metadatas"][0]
    distances = res.get("distances", [[None] * len(metas)])[0]

    for meta, dist in zip(metas, distances):
        section_key = meta.get("section_key")
        full = get_section(section_key) if section_key else None
        if full is None:
            continue
        full["eligibility"] = full.get(program.lower(), "")
        full["similarity"] = round(1.0 - float(dist), 3) if dist is not None else None
        out.append(full)

    return out
