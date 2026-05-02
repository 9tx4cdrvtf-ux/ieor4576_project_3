"""Root coordinator agent: orchestrates tools + planner + critic."""
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from agent.critic import schedule_critic
from agent.planner import schedule_planner
from agent.prompts import COORDINATOR_INSTRUCTION
from agent.tools.progress import compute_progress
from agent.tools.schedule import check_conflicts, validate_schedule
from agent.tools.search import search_courses
from agent.tools.student import get_program, get_student

COORDINATOR_MODEL = LiteLlm(model="vertex_ai/gemini-2.5-flash")


root_agent = LlmAgent(
    name="course_planner_coordinator",
    model=COORDINATOR_MODEL,
    description=(
        "Top-level course planning assistant for Columbia IEOR graduate students. "
        "Loads student profile + program rules, gathers candidate courses via RAG, "
        "delegates schedule generation to a planner sub-agent and critique to a "
        "critic sub-agent."
    ),
    instruction=COORDINATOR_INSTRUCTION,
    tools=[
        get_student,
        get_program,
        compute_progress,
        search_courses,
        check_conflicts,
        validate_schedule,
        AgentTool(agent=schedule_planner),
        AgentTool(agent=schedule_critic),
    ],
)
