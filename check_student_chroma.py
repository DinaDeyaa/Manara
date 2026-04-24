from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

BASE = Path("/Users/dinaal-memah/Desktop/graduation project 2")

CHROMA_DIR = BASE / "student_profiles" / "chroma_db"

STUDENT_COLLECTION = "student_profiles_full"


client = chromadb.PersistentClient(path=str(CHROMA_DIR))
embedding_function = embedding_functions.DefaultEmbeddingFunction()

collection = client.get_collection(
    name=STUDENT_COLLECTION,
    embedding_function=embedding_function
)

print("Count:", collection.count())

sample = collection.get(limit=3)

print("\nIDs:")
print(sample["ids"])

print("\nMetadatas:")
print(sample["metadatas"])

print("\nSample documents:")
for doc in sample["documents"]:
    print("-" * 60)
    print(doc[:800])

print("\nRetrieval test:")
results = collection.query(
    query_texts=["student with low risk and high database score"],
    n_results=3
)

print("\nRetrieved documents:")
for doc in results["documents"][0]:
    print("-" * 60)
    print(doc[:800])

print("\nRetrieved metadata:")
for meta in results["metadatas"][0]:
    print(meta)