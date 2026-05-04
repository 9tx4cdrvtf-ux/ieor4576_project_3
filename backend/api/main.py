"""CourseCompass FastAPI entry point.

Endpoints:
  GET  /api/profiles                     -> list available student profiles
  GET  /api/profiles/{student_id}        -> full profile + degree progress
  POST /api/generate                     -> run pipeline, return all 3 plans
  POST /api/explain/stream               -> SSE token stream for one course
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents import explainer, orchestrator

app = FastAPI(title="CourseCompass API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    student_id: str
    selected_days: list[str]
    selected_windows: list[str]
    credit_target: float = 12.0
    career_text: str = ""
    career_tags: list[str] = []
    avoid_departments: list[str] = []
    instructor_preference: Optional[str] = None


class ExplainRequest(BaseModel):
    student_id: str
    course: dict
    full_plan: list[dict]
    career_text: str = ""
    career_tags: list[str] = []


@app.get("/api/profiles")
def get_profiles() -> dict:
    return {"profiles": orchestrator.list_profiles()}


@app.get("/api/profiles/{student_id}")
def get_profile(student_id: str) -> dict:
    try:
        return orchestrator.load_profile(student_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/generate")
def generate_schedule(req: GenerateRequest) -> dict:
    try:
        return orchestrator.plan_schedule(
            student_id=req.student_id,
            selected_days=req.selected_days,
            selected_windows=req.selected_windows,
            credit_target=req.credit_target,
            career_text=req.career_text,
            career_tags=req.career_tags,
            avoid_departments=req.avoid_departments,
            instructor_preference=req.instructor_preference,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # planner / LLM / RAG failures
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/api/explain/stream")
def explain_stream(req: ExplainRequest) -> StreamingResponse:
    try:
        profile = orchestrator.load_profile(req.student_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # The student JSONs no longer carry career fields, so we splice in the
    # user's runtime input here. Without this the Explainer would always say
    # "no career goal provided" even when the user clicked tags.
    profile = {
        **profile,
        "career_text": req.career_text,
        "career_tags": req.career_tags,
    }

    def gen():
        try:
            for token in explainer.explain_stream(req.course, profile, req.full_plan):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as exc:  # surface errors to the client
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
