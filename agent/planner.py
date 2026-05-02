"""SchedulePlanner sub-agent: produces structured candidate schedules."""
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from agent.prompts import PLANNER_INSTRUCTION
from agent.schemas import SchedulePlan

PLANNER_MODEL = LiteLlm(model="vertex_ai/gemini-2.5-pro")

schedule_planner = LlmAgent(
    name="propose_schedule",
    model=PLANNER_MODEL,
    description=(
        "Produces 1-3 candidate course schedules for the upcoming term given a "
        "student's progress, preferences, and a candidate course pool."
    ),
    instruction=PLANNER_INSTRUCTION,
    output_schema=SchedulePlan,
    output_key="current_plan",
)
