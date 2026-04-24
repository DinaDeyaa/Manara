from __future__ import annotations

import os
import re
from pathlib import Path
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# =========================================================
# CONFIG
# =========================================================

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR = PROJECT_DIR / "courses"

MODEL_NAME = "gpt-5.4-nano"
MAX_COMPLETION_TOKENS = 500

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in your environment.")

client = OpenAI(api_key=OPENAI_API_KEY)
embedding_function = embedding_functions.DefaultEmbeddingFunction()

# =========================================================
# SMART FILTER (FIX MAIN ISSUE)
# =========================================================

def is_small_talk(question: str) -> bool:
    q = question.lower().strip()

    small_talk = [
        "hi", "hello", "hey",
        "thanks", "thank you",
        "good morning", "good evening",
        "how are you"
    ]

    return q in small_talk


def is_irrelevant_question(question: str) -> bool:
    """
    Detect questions that are NOT course-related
    """
    q = question.lower()

    non_academic = [
        "mansaf", "food", "recipe",
        "weather", "movie", "song",
        "football", "match", "restaurant"
    ]

    return any(word in q for word in non_academic)


# =========================================================
# HELPERS
# =========================================================

def safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).strip().lower()).strip("_")


def normalize_name(text: str) -> str:
    cleaned = re.sub(r"[_\-]+", " ", str(text).strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def get_course_folders(courses_dir: Path) -> list[Path]:
    if not courses_dir.exists():
        raise FileNotFoundError(f"Courses folder not found: {courses_dir}")
    return sorted([p for p in courses_dir.iterdir() if p.is_dir()])


def build_course_name_map() -> dict[str, str]:
    mapping = {}
    for course_dir in get_course_folders(COURSES_DIR):
        mapping[normalize_name(course_dir.name)] = course_dir.name
    return mapping


def resolve_course_folder_name(user_text: str, course_name_map: dict[str, str]) -> str | None:
    normalized = normalize_name(user_text)

    if normalized in course_name_map:
        return course_name_map[normalized]

    for norm_name, actual_name in course_name_map.items():
        if normalized in norm_name or norm_name in normalized:
            return actual_name

    return None


def get_course_folder(course_name: str) -> Path:
    course_dir = COURSES_DIR / course_name
    if not course_dir.exists():
        raise FileNotFoundError(f"Course folder not found: {course_dir}")
    return course_dir


def get_chroma_client(course_dir: Path):
    chroma_dir = course_dir / "outputs" / "chroma_db"
    if not chroma_dir.exists():
        raise FileNotFoundError(f"Chroma DB not found: {chroma_dir}")
    return chromadb.PersistentClient(path=str(chroma_dir))


def get_collection_if_exists(chroma_client, collection_name: str):
    try:
        return chroma_client.get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
    except Exception:
        return None


def extract_chapter_number(text: str) -> int:
    match = re.search(r"ch(\d+)", text.lower())
    return int(match.group(1)) if match else 999


def deduplicate_sources(sources: list[dict]) -> list[dict]:
    seen = set()
    unique_sources = []

    for s in sources:
        if not isinstance(s, dict):
            continue

        key = s.get("relative_path") or s.get("file_name")
        if not key or key in seen:
            continue

        seen.add(key)
        unique_sources.append(s)

    return sorted(
        unique_sources,
        key=lambda x: (
            extract_chapter_number(x.get("chapter", "") or x.get("relative_path", "")),
            str(x.get("relative_path", ""))
        )
    )


# =========================================================
# RETRIEVAL
# =========================================================

def load_course_collections(course_name: str):
    course_dir = get_course_folder(course_name)
    chroma_client = get_chroma_client(course_dir)

    slug = safe_slug(course_name)

    return {
        "chunks": get_collection_if_exists(chroma_client, f"{slug}_chunks"),
        "summaries": get_collection_if_exists(chroma_client, f"{slug}_summaries"),
        "concepts": get_collection_if_exists(chroma_client, f"{slug}_concepts"),
        "metadata": get_collection_if_exists(chroma_client, f"{slug}_metadata"),
    }


def query_collection(collection, query: str, top_k: int):
    if collection is None:
        return [], []

    results = collection.query(query_texts=[query], n_results=top_k)
    return results.get("documents", [[]])[0], results.get("metadatas", [[]])[0]


def retrieve_context(course_name: str, query: str):
    collections = load_course_collections(course_name)

    return {
        "chunks": query_collection(collections["chunks"], query, 5),
        "summaries": query_collection(collections["summaries"], query, 2),
        "concepts": query_collection(collections["concepts"], query, 3),
        "metadata": query_collection(collections["metadata"], query, 2),
    }


# =========================================================
# PROMPT
# =========================================================

def build_context_text(retrieved: dict) -> str:
    parts = []

    for key, (docs, metas) in retrieved.items():
        for doc, meta in zip(docs, metas):
            label = meta.get("relative_path", key)
            parts.append(f"[{key.upper()} | {label}]\n{doc}")

    return "\n\n".join(parts)


def build_prompt(course_name: str, question: str, context_text: str) -> str:
    return f"""
Answer ONLY using this material.

If not found, say:
"I could not find this in the provided course material."

Material:
{context_text}

Question:
{question}
"""


# =========================================================
# MAIN API
# =========================================================

def ask_course_question(course_name: str, question: str) -> dict:
    try:
        question = question.strip()

        if not question:
            return {"success": False, "message": "Empty question", "answer": "", "sources": []}

        # ✅ SMALL TALK FIX
        if is_small_talk(question):
            return {
                "success": True,
                "message": "Small talk",
                "answer": f"Hi! Ask me anything about {course_name} 👋",
                "sources": [],
            }

        # ✅ IRRELEVANT FIX
        if is_irrelevant_question(question):
            return {
                "success": True,
                "message": "Irrelevant",
                "answer": "I could not find this in the provided course material.",
                "sources": [],
            }

        course_map = build_course_name_map()
        resolved = resolve_course_folder_name(course_name, course_map)

        if not resolved:
            return {"success": False, "message": "Course not found", "answer": "", "sources": []}

        retrieved = retrieve_context(resolved, question)
        context = build_context_text(retrieved)

        if not context.strip():
            return {
                "success": True,
                "answer": "I could not find this in the provided course material.",
                "sources": [],
            }

        prompt = build_prompt(resolved, question, context)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_completion_tokens=MAX_COMPLETION_TOKENS
        )

        answer = response.choices[0].message.content.strip()

        sources = []
        for _, metas in retrieved.values():
            sources.extend(metas)

        sources = deduplicate_sources(sources)

        if "I could not find this in the provided course material." in answer:
            sources = []

        return {
            "success": True,
            "answer": answer,
            "sources": sources,
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "answer": "",
            "sources": [],
        }


# =========================================================
# CLI
# =========================================================

def main():
    print("Courses:")
    for c in get_course_folders(COURSES_DIR):
        print("-", c.name)

    course = input("\nCourse: ")

    while True:
        q = input("\nAsk: ")
        if q == "exit":
            break

        res = ask_course_question(course, q)
        print("\n", res["answer"])

        if res["sources"]:
            print("\nSources:")
            for s in res["sources"]:
                print("-", s.get("relative_path", ""))


if __name__ == "__main__":
    main()