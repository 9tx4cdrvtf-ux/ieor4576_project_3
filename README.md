# Columbia IEOR Course Selection Assistant

An agentic course-planning assistant for Columbia University IEOR graduate
students. Pick a student profile, set your preferences, and the agent will
load your degree progress, search the Spring 2026 catalog by topic and
constraints, generate 1–3 candidate schedules, run an internal critique pass
to validate against both objective rules and your preferences, and present
the final plan as an interactive calendar with one-click `.ics` export.

**Live demo:** _(deploy URL pending)_

---

## Architecture

```
            ┌─────────────────────────────┐
            │   Streamlit UI (form+chat)  │
            └──────────────┬──────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   Coordinator (LlmAgent)    │  Gemini 2.5 Flash
            │   Google ADK + LiteLLM      │
            └─┬────────────┬────────────┬─┘
              │            │            │
   ┌──────────▼──┐  ┌──────▼─────┐  ┌──▼──────────────────┐
   │ Tools (Py)  │  │ RAG search │  │ propose_schedule    │  Gemini 2.5 Pro
   │             │  │ ChromaDB + │  │ critique_schedule   │  (sub-agents)
   │ get_student │  │ Vertex AI  │  │ structured output   │
   │ get_program │  │ embeddings │  │ via output_schema   │
   │ compute_…   │  │            │  └─────────────────────┘
   │ check_…     │  └────────────┘
   │ validate_…  │
   └─────────────┘
```

### Class concepts used

1. **RAG with metadata filtering** — semantic search over Spring 2026 catalog
   combined with hard filters (program eligibility, days off, time-of-day,
   modality). See [agent/tools/search.py](agent/tools/search.py) and
   [index_info.py](index_info.py).
2. **Tool use / function calling** — six deterministic Python tools for the
   coordinator. See [agent/coordinator.py:18-29](agent/coordinator.py).
3. **Multi-agent orchestration** — root coordinator delegates to two
   specialist sub-agents (planner + critic) wrapped as `AgentTool`. See
   [agent/coordinator.py](agent/coordinator.py),
   [agent/planner.py](agent/planner.py), [agent/critic.py](agent/critic.py).
4. **Structured output / schema-bound LLM** — sub-agents emit Pydantic-
   typed JSON (`SchedulePlan`, `CritiqueReport`) via ADK's `output_schema`.
   See [agent/schemas.py](agent/schemas.py).
5. **Hybrid symbolic + LLM (critic loop)** — hard constraints (time
   conflicts, eligibility, credit caps) live in pure Python
   ([agent/tools/schedule.py](agent/tools/schedule.py)); soft preferences
   (career fit, "no Friday class", compactness) go through the critic
   sub-agent. The coordinator runs at most one internal refinement pass on
   critic feedback before presenting to the user.

---

## Run locally

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Auth to Vertex AI (one-time)
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=<your-project>
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=TRUE

# 3. Launch
streamlit run app/streamlit_app.py
```

The first launch builds nothing new — the ChromaDB index in `chroma_db/`
is pre-built. To re-embed from scratch (after editing the catalog), run
`python index_info.py`.

---

## Repo layout

```
agent/
  schemas.py              # Pydantic models shared everywhere
  prompts.py              # All LLM instructions in one file
  coordinator.py          # Root LlmAgent — tool + sub-agent wiring
  planner.py              # propose_schedule sub-agent
  critic.py               # critique_schedule sub-agent (internal use only)
  tools/
    student.py            # get_student / get_program (mock school API)
    progress.py           # compute_progress (deterministic)
    courses.py            # CSV loader for Spring 2026 catalog
    search.py             # ChromaDB semantic search w/ metadata filters
    schedule.py           # check_conflicts / validate_schedule
app/
  streamlit_app.py        # Streamlit front-end
  agent_runner.py         # ADK Runner wrapper
  render.py               # Calendar event + .ics builder
mock_data/
  programs/msor.json      # MSOR graduation rules
  students/user_*.json    # Mock student profiles
chroma_db/                # Pre-built vector index (commit-tracked)
web_scrawl/               # Original scrapers + cleaned catalog CSV
index_info.py             # Re-build the ChromaDB index
```

---

## Data Collection

### Web Scraping

Course data for Spring 2026 was collected from Columbia University's Directory of Classes (`https://doc.sis.columbia.edu`) using two custom scrapers built with `requests` and `BeautifulSoup`.

**IEOR Courses (`scrawl_ieor.py`)**

Course offering information for the IEOR master’s program is obtained from the Columbia University Student Information System (SIS) at [https://doc.sis.columbia.edu](https://doc.sis.columbia.edu). 


**Non-IEOR & CBS Electives (`scrawl_non_ieor_cbs.py`)**

For approved electives outside IEOR, the course lists are read from [the IEOR MS preapproved electives](http://docs.google.com/spreadsheets/d/1Sy_kMtZ-GGhvICYSlBFmttj7A2vQY2SWIRD6K8_G8ms/edit?pli=1&gid=0#gid=0). 

### Data Overview

Raw scraped files are merged, cleaned, and filtered by `data_cleaning.py` into a single dataset: `Spring2026_course_info_master.csv`.

**Cleaning steps include:**
- Merging IEOR, non-IEOR, and CBS course tables with their respective program eligibility tables (MSOR, MSIE, MSBA, MSE, MSFE approval status)
- Filtering to graduate-level courses only (course number 4000–8999); removing undergraduate, PhD-level research seminar, and manually excluded courses
- Dropping courses that are not approved for any IEOR MS program, research/zero-credit courses, and rows missing a `Section key`
- Splitting the combined `Day/Time` field into structured `Day` (list of full weekday names), `Time_start`, and `Time_end` (decimal hours, 24-hour format)

**Final dataset:** 412 course sections across 22 columns.

| Column | Description |
|---|---|
| `Section key` | Unique identifier for each section (e.g., `20261IEOR4004E001`) |
| `Course Code` | Department + course number (e.g., `IEOR4004`) |
| `Course Name` | Full course title |
| `Section` | Section number (e.g., `001`) |
| `Short Name` | Abbreviated course title |
| `Points` | Credit points |
| `Location` | Classroom building and room |
| `Enrollment` | Current enrollment and capacity |
| `Instructor` | Instructor name |
| `Type` | Section type (`LECTURE`, `SEMINAR`, etc.) |
| `Method of Instruction` | `In-Person` or `On-Line Only` |
| `Course Description` | Full course description text |
| `Division` | Academic division (e.g., SEAS Graduate) |
| `MSOR` / `MSIE` / `MSBA` / `MSE` / `MSFE` | Program eligibility (`elective`, `required`, or `no`) |
| `Day` | List of meeting days (e.g., `['Monday', 'Wednesday']`) |
| `Time_start` / `Time_end` | Start/end time as decimal hours (e.g., `13.167` = 1:10 PM) |

---

## RAG Embedding

Course data is embedded into a vector database using `index_info.py` to enable semantic retrieval.

**Embedding Model**

Each course section is converted to a free-text document combining its name, instructor, instruction format, and full description. These documents are embedded using Google's `text-embedding-005` model via the Vertex AI API, with the `RETRIEVAL_DOCUMENT` task type for optimized retrieval performance.

**Vector Store**

Embeddings are stored in a local [ChromaDB](https://www.trychroma.com/) persistent collection (`ieor_courses`) using cosine similarity as the distance metric. Sections are deduplicated by `Section key` before indexing. 

**Metadata Filtering**

Each embedding is stored alongside rich metadata to support structured filtering at query time:

| Metadata Field | Type | Description |
|---|---|---|
| `course_code` | string | Department + course number |
| `course_name` | string | Full course title |
| `instructor` | string | Instructor name (`TBA` if unknown) |
| `points` | float | Credit points |
| `course_type` | string | `LECTURE`, `SEMINAR`, etc. |
| `time_start` / `time_end` | float | Decimal start/end hours |
| `has_monday` … `has_friday` | bool | Per-day availability flags |
| `is_online` | bool | Whether the course is online-only |
| `msor` / `msie` / `msba` / `mse` / `msfe` | string | Program eligibility |

This allows the assistant to combine semantic search (e.g., "courses about machine learning") with hard filters (e.g., only Thursday courses, only MSOR-eligible, only in-person) in a single retrieval step.
