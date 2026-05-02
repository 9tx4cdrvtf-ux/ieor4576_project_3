"""ScheduleCritic sub-agent: reviews candidate schedules against hard validation
results AND soft student preferences.
"""
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from agent.prompts import CRITIC_INSTRUCTION
from agent.schemas import CritiqueReport

CRITIC_MODEL = LiteLlm(model="vertex_ai/gemini-2.5-pro")

schedule_critic = LlmAgent(
    name="critique_schedule",
    model=CRITIC_MODEL,
    description=(
        "Reviews candidate schedules against (1) objective ValidationReports "
        "and (2) student soft preferences and career direction. Produces a "
        "per-candidate verdict (PASS/WARN/FAIL) with concrete swap suggestions."
    ),
    instruction=CRITIC_INSTRUCTION,
    output_schema=CritiqueReport,
    output_key="current_critique",
)
