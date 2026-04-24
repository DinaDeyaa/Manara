from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSE_NAME = "Design and Analysis of Algorithms"   # change this when needed

def safe_slug(name: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")

course_dir = PROJECT_DIR / "courses" / COURSE_NAME
chroma_dir = course_dir / "outputs" / "chroma_db"

client = chromadb.PersistentClient(path=str(chroma_dir))
embedding_function = embedding_functions.DefaultEmbeddingFunction()

slug = safe_slug(COURSE_NAME)

print("\n=== 1. Collections ===")
collections = client.list_collections()
for c in collections:
    try:
        print("-", c.name)
    except AttributeError:
        print("-", c)

print("\n=== 2. Vector counts ===")
for suffix in ["_chunks", "_summaries", "_concepts", "_metadata"]:
    name = f"{slug}{suffix}"
    try:
        collection = client.get_collection(name=name, embedding_function=embedding_function)
        print(f"{name}: {collection.count()}")
    except Exception:
        print(f"{name}: NOT FOUND")

print("\n=== 3. Retrieval test ===")
chunks_name = f"{slug}_chunks"
collection = client.get_collection(name=chunks_name, embedding_function=embedding_function)

results = collection.query(
    query_texts=["what is dynamic programming"],
    n_results=3
)

docs = results["documents"][0]
metas = results["metadatas"][0]

for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
    print(f"\nResult {i}")
    print("Source:", meta)
    print("Text:", doc[:500])

print("\n=== 4. Metadata test ===")
meta_name = f"{slug}_metadata"
try:
    meta_collection = client.get_collection(name=meta_name, embedding_function=embedding_function)
    res = meta_collection.get(limit=5)
    for i, meta in enumerate(res["metadatas"], start=1):
        print(f"Metadata {i}: {meta}")
except Exception:
    print("Metadata collection not found.")