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
MAX_COMPLETION_TOKENS = 1200  # high but safe (no infinite looping)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set.")

client = OpenAI(api_key=OPENAI_API_KEY)
embedding_function = embedding_functions.DefaultEmbeddingFunction()

# =========================================================
# LANGUAGE DETECTION
# =========================================================

def is_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text))

# =========================================================
# SMART FILTERS
# =========================================================

def classify_intent(question: str):
    prompt = f"""
Classify this student message into ONE of these:

1. small_talk
2. academic
3. irrelevant

Message:
{question}

Answer ONLY one word.
"""

    res = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    output = res.choices[0].message.content.strip().lower()

    if "small" in output:
        return "small_talk"
    elif "irrelevant" in output:
        return "irrelevant"
    else:
        return "academic"

# =========================================================
# HELPERS
# =========================================================

def safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name.lower()).strip("_")


def normalize_name(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", text.lower())).strip()


def get_course_folders():
    return [p for p in COURSES_DIR.iterdir() if p.is_dir()]


def build_course_name_map():
    return {normalize_name(p.name): p.name for p in get_course_folders()}


def resolve_course_folder_name(user_text, course_map):
    normalized = normalize_name(user_text)

    if normalized in course_map:
        return course_map[normalized]

    for k, v in course_map.items():
        if normalized in k or k in normalized:
            return v

    return None


def get_course_folder(course_name):
    return COURSES_DIR / course_name


def get_chroma_client(course_dir):
    return chromadb.PersistentClient(
        path=str(course_dir / "outputs" / "chroma_db")
    )


def get_collection_if_exists(client, name):
    try:
        return client.get_collection(name=name, embedding_function=embedding_function)
    except:
        return None

# =========================================================
# RETRIEVAL
# =========================================================

def load_course_collections(course_name):
    course_dir = get_course_folder(course_name)
    client = get_chroma_client(course_dir)
    slug = safe_slug(course_name)

    return {
        "chunks": get_collection_if_exists(client, f"{slug}_chunks"),
        "summaries": get_collection_if_exists(client, f"{slug}_summaries"),
        "concepts": get_collection_if_exists(client, f"{slug}_concepts"),
    }


def query_collection(collection, query, k):
    if not collection:
        return [], []

    res = collection.query(query_texts=[query], n_results=k)
    return res.get("documents", [[]])[0], res.get("metadatas", [[]])[0]


def retrieve_context(course_name, query):
    col = load_course_collections(course_name)

    return {
        "chunks": query_collection(col["chunks"], query, 5),
        "summaries": query_collection(col["summaries"], query, 2),
        "concepts": query_collection(col["concepts"], query, 3),
    }

# =========================================================
# PROMPT
# =========================================================

def build_context_text(retrieved):
    parts = []

    for key, (docs, metas) in retrieved.items():
        for doc, meta in zip(docs, metas):
            label = meta.get("relative_path", key)
            parts.append(f"[{label}]\n{doc}")

    return "\n\n".join(parts)


def build_prompt(course_name, question, context, arabic):
    lang_rule = "Answer in Arabic." if arabic else "Answer in English."

    return f"""
You are a university teaching assistant.

Rules:
- {lang_rule}
- Explain clearly (Definition → Idea → Example)
- DO NOT repeat sections
- DO NOT restart explanation
- Use clean math formatting: $...$
- Keep spacing readable
- If partially relevant → answer anyway
- Only say "not found" if NOTHING exists

Material:
{context}

Question:
{question}
"""

# =========================================================
# CLEAN OUTPUT (CRITICAL FIX)
# =========================================================

def clean_answer(text: str) -> str:
    # remove duplicated blocks
    text = re.sub(r"(Sure!.*?)(\1)+", r"\1", text, flags=re.DOTALL)

    # fix latex newlines
    text = re.sub(r"\n\s*(?=\\)", " ", text)

    # fix spacing
    text = re.sub(r"\s{2,}", " ", text)

    # fix smashed words
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    return text.strip()

# =========================================================
# MAIN FUNCTION
# =========================================================

def ask_course_question(course_name, question):
    try:
        question = question.strip()
        if not question:
            return {"success": False, "answer": "", "sources": []}

        # ✅ intent
        intent = classify_intent(question)

        if intent == "small_talk":
            arabic = is_arabic(question)
            return {
                "success": True,
                "answer": "مرحبا! كيف أقدر أساعدك؟ 😊" if arabic
                          else "Hi! How can I help you? 😊",
                "sources": []
            }

        if intent == "irrelevant":
            return {
                "success": True,
                "answer": "I can only help with course-related questions.",
                "sources": []
            }

        # ✅ continue normal RAG flow
        course_map = build_course_name_map()
        resolved = resolve_course_folder_name(course_name, course_map)

        if not resolved:
            return {"success": False, "answer": "", "sources": []}

        retrieved = retrieve_context(resolved, question)
        context = build_context_text(retrieved)

        if not context.strip():
            return {
                "success": True,
                "answer": "I could not find this in the provided course material.",
                "sources": []
            }

        arabic = is_arabic(question)
        prompt = build_prompt(resolved, question, context, arabic)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_completion_tokens=MAX_COMPLETION_TOKENS
        )

        answer = clean_answer(response.choices[0].message.content)

        sources = []
        for _, metas in retrieved.values():
            sources.extend(metas)

        seen = set()
        unique = []
        for s in sources:
            key = s.get("relative_path")
            if key and key not in seen:
                seen.add(key)
                unique.append(s)

        return {
            "success": True,
            "answer": answer,
            "sources": unique
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
