from __future__ import annotations

import os
import re
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# =========================================================
# CONFIG
# =========================================================

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR = PROJECT_DIR / "courses"

MODEL_NAME = "gpt-5.4-nano"
MAX_COMPLETION_TOKENS = 1200

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set.")

client = OpenAI(api_key=OPENAI_API_KEY)
embedding_function = embedding_functions.DefaultEmbeddingFunction()


# =========================================================
# LANGUAGE DETECTION
# =========================================================

def is_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", str(text)))


# =========================================================
# SMART FILTERS
# =========================================================

def classify_intent(question: str) -> str:
    prompt = f"""
Classify this student message into ONE of these:

1. small_talk
2. academic
3. irrelevant

Message:
{question}

Answer ONLY one word.
"""

    try:
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_completion_tokens=20,
        )

        output = res.choices[0].message.content.strip().lower()

        if "small" in output:
            return "small_talk"
        if "irrelevant" in output:
            return "irrelevant"
        return "academic"

    except Exception:
        return "academic"


# =========================================================
# HELPERS
# =========================================================

def safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).lower()).strip("_")


def normalize_name(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", str(text).lower())).strip()


def get_course_folders() -> list[Path]:
    if not COURSES_DIR.exists():
        return []
    return [p for p in COURSES_DIR.iterdir() if p.is_dir()]


def build_course_name_map() -> dict[str, str]:
    return {normalize_name(p.name): p.name for p in get_course_folders()}


def resolve_course_folder_name(user_text: str, course_map: dict[str, str]) -> str | None:
    normalized = normalize_name(user_text)

    if normalized in course_map:
        return course_map[normalized]

    for k, v in course_map.items():
        if normalized in k or k in normalized:
            return v

    return None


def get_course_folder(course_name: str) -> Path:
    return COURSES_DIR / course_name


def get_chroma_client(course_dir: Path):
    return chromadb.PersistentClient(
        path=str(course_dir / "outputs" / "chroma_db")
    )


def get_collection_if_exists(client_db, name: str):
    try:
        return client_db.get_collection(
            name=name,
            embedding_function=embedding_function
        )
    except Exception:
        return None


# =========================================================
# RETRIEVAL
# =========================================================

def load_course_collections(course_name: str) -> dict:
    course_dir = get_course_folder(course_name)
    chroma_dir = course_dir / "outputs" / "chroma_db"

    if not chroma_dir.exists():
        return {
            "chunks": None,
            "summaries": None,
            "concepts": None,
        }

    client_db = get_chroma_client(course_dir)
    slug = safe_slug(course_name)

    return {
        "chunks": get_collection_if_exists(client_db, f"{slug}_chunks"),
        "summaries": get_collection_if_exists(client_db, f"{slug}_summaries"),
        "concepts": get_collection_if_exists(client_db, f"{slug}_concepts"),
    }


def query_collection(collection, query: str, k: int):
    if collection is None:
        return [], []

    try:
        res = collection.query(query_texts=[query], n_results=k)
        return res.get("documents", [[]])[0], res.get("metadatas", [[]])[0]
    except Exception:
        return [], []


def retrieve_context(course_name: str, query: str) -> dict:
    col = load_course_collections(course_name)

    return {
        "chunks": query_collection(col["chunks"], query, 5),
        "summaries": query_collection(col["summaries"], query, 2),
        "concepts": query_collection(col["concepts"], query, 3),
    }


# =========================================================
# PROMPT
# =========================================================

def build_context_text(retrieved: dict) -> str:
    parts = []

    for key, (docs, metas) in retrieved.items():
        for doc, meta in zip(docs, metas):
            label = meta.get("relative_path") or key
            parts.append(f"[{label}]\n{doc}")

    return "\n\n".join(parts).strip()


def build_prompt(course_name: str, question: str, context: str, arabic: bool) -> str:
    lang_rule = "Answer in Arabic." if arabic else "Answer in English."

    return f"""
You are a university teaching assistant.

Rules:
- {lang_rule}
- Explain clearly.
- If the student asks a follow-up like "How is it used?", use the previous conversation context.
- DO NOT restart with unrelated definitions.
- DO NOT repeat sections.
- Use clean math formatting: $...$
- Keep spacing readable.
- Use only the provided material and conversation history.
- If partially relevant, answer anyway.
- Only say "not found" if NOTHING exists.

Course:
{course_name}

Material:
{context}

Current Question:
{question}
""".strip()


# =========================================================
# CLEAN OUTPUT
# =========================================================

def clean_answer(text: str) -> str:
    text = str(text or "")

    text = re.sub(r"(Sure!.*?)(\1)+", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\n\s*(?=\\)", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def build_grouped_sources(retrieved: dict, resolved_course: str) -> list[dict]:
    grouped_sources = {}

    for _, metas in retrieved.values():
        for meta in metas:
            course = meta.get("course_name") or resolved_course
            file_name = meta.get("relative_path") or meta.get("file_name") or ""

            if not file_name:
                continue

            if course not in grouped_sources:
                grouped_sources[course] = set()

            grouped_sources[course].add(file_name)

    formatted_sources = []

    for course, files in grouped_sources.items():
        formatted_sources.append({
            "course": course,
            "chapters": sorted(list(files)),
        })

    return formatted_sources


# =========================================================
# MAIN FUNCTION
# =========================================================

def ask_course_question(course_name: str, question: str, history=None) -> dict:
    try:
        question = str(question or "").strip()
        history = history or []

        if not question:
            return {
                "success": False,
                "answer": "",
                "sources": [],
                "message": "Question is empty."
            }

        intent = classify_intent(question)

        if intent == "small_talk":
            arabic = is_arabic(question)
            return {
                "success": True,
                "answer": "مرحبا! كيف أقدر أساعدك؟ 😊" if arabic else "Hi! How can I help you? 😊",
                "sources": []
            }

        if intent == "irrelevant":
            return {
                "success": True,
                "answer": "I can only help with course-related questions.",
                "sources": []
            }

        course_map = build_course_name_map()
        resolved = resolve_course_folder_name(course_name, course_map)

        if not resolved:
            return {
                "success": False,
                "answer": "",
                "sources": [],
                "message": f"Could not match course: {course_name}"
            }

        retrieved = retrieve_context(resolved, question)
        context = build_context_text(retrieved)

        if not context:
            return {
                "success": True,
                "answer": "I could not find this in the provided course material.",
                "sources": []
            }

        arabic = is_arabic(question)
        prompt = build_prompt(resolved, question, context, arabic)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful university teaching assistant. "
                    "Use the previous conversation context when answering follow-up questions. "
                    "Do not switch topics unless the student clearly asks a new topic."
                )
            }
        ]

        for msg in history[-12:]:
            role = msg.get("role")
            content = msg.get("content")

            if role in {"user", "assistant"} and content:
                messages.append({
                    "role": role,
                    "content": str(content)
                })

        messages.append({
            "role": "user",
            "content": prompt
        })

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )

        answer = clean_answer(response.choices[0].message.content)
        formatted_sources = build_grouped_sources(retrieved, resolved)

        return {
            "success": True,
            "answer": answer,
            "sources": formatted_sources
        }

    except Exception as e:
        return {
            "success": False,
            "answer": "",
            "sources": [],
            "message": str(e)
        }


# =========================================================
# CLI
# =========================================================

def main():
    print("Courses:")
    for c in get_course_folders():
        print("-", c.name)

    course = input("\nCourse: ").strip()

    history = []

    while True:
        q = input("\nAsk: ").strip()
        if q.lower() == "exit":
            break

        res = ask_course_question(course, q, history=history)

        print("\n", res.get("answer", ""))

        if res.get("success"):
            history.append({"role": "user", "content": q})
            history.append({"role": "assistant", "content": res.get("answer", "")})

        if res.get("sources"):
            print("\nSources:")
            for source_group in res["sources"]:
                print(f"- {source_group.get('course', course)}")
                for chapter in source_group.get("chapters", []):
                    print(f"  • {chapter}")


if __name__ == "__main__":
    main()
