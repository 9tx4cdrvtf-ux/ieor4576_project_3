# CourseCompass 

## The User

CourseCompass is built for graduate students in Columbia University's Industrial Engineering and Operations Research (IEOR) master's programs — specifically MSOR, MSIE, MSBA, MSE, and MSFE tracks. These are quantitatively rigorous programs with 30–36 credit requirements, strict track-specific elective rules, and a course catalog that changes every semester.

The concrete user is a first- or second-semester IEOR master's student, likely international, juggling academic requirements they don't fully understand yet, a part-time job search, and a registration deadline. They are analytical by training but unfamiliar with Columbia's advising system, and they have limited access to their academic advisor outside of office hours.

---

## The Problem

Today, a student planning their semester does the following: they open the IEOR course directory, cross-reference it manually against their degree audit, check each section's time slot against their existing commitments, read through course descriptions one by one, and then make a guess. This process takes hours, produces suboptimal schedules, and frequently results in students registering for courses that don't count toward their degree requirements — a mistake they may not discover until the semester is over.

The advising office cannot scale to answer every student's individual scheduling question. Peer advice is unreliable because track requirements differ. There is no tool that combines degree-audit awareness, real-time course availability, personal scheduling constraints, and career-goal alignment into a single recommendation.

CourseCompass solves this by acting as an always-available, constraint-aware course planning agent. A student inputs their completed credits, preferred time windows, career goals, and track, and receives a concrete schedule recommendation with reasoning — in several minutes.




## The Economics

**Business model:** B2B SaaS, licensed to university departments or graduate programs. The natural buyer is the IEOR department or the School of Engineering's student services office, which has a budget for student success tooling and a clear incentive to reduce advising load and improve retention.

**Pricing:** \$8,000 – \$15,000 per program per academic year, depending on enrollment size. IEOR graduate enrollment is approximately 500 students. This works out to roughly $15–30 per student per year — well below what the department spends on marginal advising hours for the same volume of questions.

**Back-of-envelope for one user-month:**

| Item | Estimate |
|---|---|
| Avg sessions per student per month | 3 |
| Avg turns per session | 5 |
| Avg tokens per turn — input | ~2,000 |
| Avg tokens per turn — output | ~500 |
| Total input tokens per student-month | ~30,000 |
| Total output tokens per student-month | ~7,500 |
| Input cost @ $1.25 / 1M tokens | ~$0.038 |
| Output cost @ $10.00 / 1M tokens | ~$0.075 |
| **LLM cost per student-month** | **~$0.11** |
| ChromaDB hosting (amortized per user) | ~$0.02 |
| Infrastructure (Cloud Run, amortized) | ~$0.03 |
| **Total cost to serve per student-month** | **~$0.16** |
| Revenue per student-month ($12,000 / 500 students / 12 months) | **~$2.00** |
| **Gross margin** | **~92%** |

The model breaks if output token volume spikes — at \$10.00/1M, verbose multi-turn responses are the primary cost driver. A single session that generates 5,000 output tokens costs \$0.05 in LLM fees alone, so response length must be kept concise by design. The model also breaks if the contract is negotiated below ~\$5,000/year, at which point margins compress but unit economics still hold at reduced scale.




---

## Token Economics and Technical Choices

Every technical decision in CourseCompass was made to serve this specific user accurately and cheaply.

**RAG over full-context injection.** The course catalog contains ~400 sections with rich descriptions. Injecting the entire catalog into every prompt would cost roughly 80,000–100,000 input tokens per query — approximately $0.10 per turn in input costs alone, making the unit economics unworkable. Instead, ChromaDB indexes all course sections, and the retriever pulls back only the top candidates per query (default `n=40`, before post-filtering). This reduces per-turn context by over 90%.

**Vertex AI `text-embedding-005` for retrieval.** Rather than a generic off-the-shelf embedding model, CourseCompass uses Google's `text-embedding-005` via a custom Chroma embedding function. This keeps the entire stack on Google Cloud (Vertex AI for both embeddings and the Gemini generation model), simplifying auth and latency, and produces higher-quality embeddings for academic course descriptions than smaller open-source alternatives.

**Semantic search with Python-layer post-filtering.** Hard constraints — selected days, time windows, avoided departments, completed courses — are enforced in Python after the vector search returns results, rather than as Chroma `where` pre-filters. The retriever deliberately pulls `n*2` candidates to absorb the attrition from filtering. This design was chosen because the constraint inputs arrive as structured UI selections (not natural language), making rule-based filtering more reliable than embedding constraint text into the query and hoping the vector search respects it.


**Output length discipline.** Given Gemini 1.5 Pro's output pricing of $10.00/1M tokens — eight times the input rate — output verbosity is the dominant cost risk. The Explainer agent streams responses via SSE, which improves perceived responsiveness, but the system prompt instructs the model to return structured, concise per-course explanations rather than lengthy prose. This keeps typical output per turn under 500 tokens, which is the assumption the unit economics above depend on.

**Structured UI inputs eliminate a query-parsing layer.** Because students select constraints through dropdowns and toggles rather than typing free-form text, CourseCompass does not need a separate LLM call to parse "I don't want early mornings" into `time_start >= 9.0`. This saves one LLM call per session — roughly $0.005–0.010 per user-month at current pricing — and eliminates an entire category of parsing errors.