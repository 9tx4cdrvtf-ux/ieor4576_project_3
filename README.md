# Columbia IEOR Course Selection Assistant

<加一个overview。。。。。。。。。。。。。。。。。>

---

## Data Collection

### Web Scraping

Course data for Spring 2026 was collected from Columbia University's Directory of Classes (`https://doc.sis.columbia.edu`) using two custom scrapers built with `requests` and `BeautifulSoup`.

**IEOR Courses (`scrawl_ieor.py`)**

Course offering information for the IEOR master’s program is obtained from the Columbia University Student Information System (SIS) at [https://doc.sis.columbia.edu](https://doc.sis.columbia.edu). 


**Non-IEOR & CBS Electives (`scrawl_non_ieor_cbs.py`)**

For approved electives outside IEOR, the course lists are read from [the IEOR MS preapproved electives](http://docs.google.com/spreadsheets/d/1Sy_kMtZ-GGhvICYSlBFmttj7A2vQY2SWIRD6K8_G8ms/edit?pli=1&gid=0#gid=0). 

### Data Overview

Raw scraped files are merged, cleaned, and filtered by `data_cleaning.py` into a single master dataset: `Spring2026_course_info_master.csv`.

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
