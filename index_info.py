import ast
import pandas as pd
import chromadb
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from chromadb import Documents, Embeddings, EmbeddingFunction

# ─────────────────────────────────────────
# 1. Vertex AI Embedding 
# ─────────────────────────────────────────

class VertexAIEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name="text-embedding-005"):
        # text-embedding-005
        self.model = TextEmbeddingModel.from_pretrained(model_name)

    def __call__(self, input: Documents) -> Embeddings:
        inputs = [TextEmbeddingInput(text, "RETRIEVAL_DOCUMENT") for text in input]
        embeddings = self.model.get_embeddings(inputs)
        return [list(e.values) for e in embeddings]

# ─────────────────────────────────────────
# 2. Helper Functions 
# ─────────────────────────────────────────

def parse_days(day_str):
    try:
        return ast.literal_eval(day_str)
    except Exception:
        return []

def build_text(row):
    parts = [f"Course: {row['Course Name']}"]
    if pd.notna(row['Instructor']):
        parts.append(f"Instructor: {row['Instructor']}")
    parts.append(f"Format: {row['Method of Instruction']} {row['Type']}")
    desc = row['Course Description'] if pd.notna(row['Course Description']) else "No description available."
    parts.append(f"Description: {desc}")
    return "\n".join(parts)

def build_metadata(row, days):
    return {
        "course_code":    str(row['Course Code']),
        "section_key":    str(row['Section key']),
        "course_name":    str(row['Course Name']),
        "instructor":     str(row['Instructor']) if pd.notna(row['Instructor']) else "TBA",
        "points":         float(row['Points']),
        "location":       str(row['Location']),
        "course_type":    str(row['Type']),
        "time_start":     float(row['Time_start']),
        "time_end":       float(row['Time_end']),
        "has_monday":     "Monday"    in days,
        "has_tuesday":    "Tuesday"   in days,
        "has_wednesday":  "Wednesday" in days,
        "has_thursday":   "Thursday"  in days,
        "has_friday":     "Friday"    in days,
        "is_online":      row['Method of Instruction'] == 'On-Line Only',
        "msor":           str(row['MSOR']),
        "msie":           str(row['MSIE']),
        "msba":           str(row['MSBA']),
        "mse":            str(row['MSE']),
        "msfe":           str(row['MSFE']),
    }

# ─────────────────────────────────────────
# 3. Load Data
# ─────────────────────────────────────────

print("Loading data...")
df = pd.read_csv("web_scrawl/Spring2026_course_info_master.csv")
df = df.drop_duplicates(subset="Section key", keep="first")

# ─────────────────────────────────────────
# 4. Initialize ChromaDB with Vertex AI
# ─────────────────────────────────────────

print("Initializing ChromaDB with Vertex AI (text-embedding-005)...")

client = chromadb.PersistentClient(path="./chroma_db")

vertex_ef = VertexAIEmbeddingFunction(model_name="text-embedding-005")

try:
    client.delete_collection("ieor_courses")
    print("   Existing collection deleted")
except Exception:
    pass

collection = client.create_collection(
    name="ieor_courses",
    embedding_function=vertex_ef,
    metadata={"hnsw:space": "cosine"}
)
print("   Collection created")

# ─────────────────────────────────────────
# 5. Process and Batch-Insert
# ─────────────────────────────────────────

ids = []
documents = []
metadatas = []

for _, row in df.iterrows():
    days     = parse_days(row['Day'])
    text     = build_text(row)
    metadata = build_metadata(row, days)
    ids.append(str(row['Section key']))
    documents.append(text)
    metadatas.append(metadata)


BATCH_SIZE = 50
total = len(ids)

for i in range(0, total, BATCH_SIZE):
    collection.add(
        ids=ids[i : i + BATCH_SIZE],
        documents=documents[i : i + BATCH_SIZE],
        metadatas=metadatas[i : i + BATCH_SIZE],
    )
    print(f"   [{i + min(BATCH_SIZE, total - i)}/{total}] embedded with Vertex AI")

print(f"\nDone! {total} courses embedded using text-embedding-005")