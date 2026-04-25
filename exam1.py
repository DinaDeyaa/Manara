from __future__ import annotations

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import chromadb
from openai import OpenAI
from chromadb.utils import embedding_functions

import random


# =========================================================
# CONFIG
# =========================================================

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR = PROJECT_DIR / "courses"

STUDENT_PROFILES_DIR = PROJECT_DIR / "student_profiles"
STUDENT_PROFILES_CSV = STUDENT_PROFILES_DIR / "student_profiles.csv"
STUDENT_PROFILES_JSON = STUDENT_PROFILES_DIR / "student_profiles.json"

EXAM1_RESULTS_DIR = PROJECT_DIR / "exam1_results"

MODEL_NAME = "gpt-5.4-nano"
MAX_COMPLETION_TOKENS = 2200

DIAGNOSTIC_DIFFICULTY_DISTRIBUTION = {
    "easy": 0.30,
    "medium": 0.40,
    "hard": 0.30,
}

DEFAULT_TOP_K_RELATED = 3
DEFAULT_RELATED_SUBTOPICS_LIMIT = 18

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in your environment.")

client = OpenAI(api_key=OPENAI_API_KEY)
embedding_function = embedding_functions.DefaultEmbeddingFunction()


# =========================================================
# HELPERS
# =========================================================

def safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).strip().lower()).strip("_")


def normalize_name(text: str) -> str:
    cleaned = re.sub(r"[_\-]+", " ", str(text).strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def normalize_question_text(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text

def extract_question_concept(question: str) -> str:
    q = normalize_question_text(question)

    concept_keywords = [
        "data engineering",
        "data engineer",
        "data science",
        "data scientist",
        "supervised learning",
        "unsupervised learning",
        "reinforcement learning",
        "label",
        "target",
        "feature",
        "data pipeline",
        "pipeline",
        "data warehouse",
        "data visualization",
        "visualization",
        "data modeling",
        "machine learning",
        "database",
        "etl",
        "cleansing",
        "transformation",
        "storage",
    ]

    found = [k for k in concept_keywords if k in q]
    if found:
        return " | ".join(sorted(found[:2]))

    words = q.split()
    return " ".join(words[:8])


def is_too_similar(q1: str, q2: str, threshold: float = 0.55) -> bool:
    w1 = set(normalize_question_text(q1).split())
    w2 = set(normalize_question_text(q2).split())

    if not w1 or not w2:
        return False

    overlap = len(w1 & w2) / max(min(len(w1), len(w2)), 1)
    return overlap >= threshold

def extract_json_block(text: str):
    match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def ask_llm(prompt: str, temperature: float = 0.4) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise academic assistant. "
                    "Return clean structured output only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )
    return response.choices[0].message.content.strip()


def ask_llm_for_json(prompt: str, max_retries: int = 3, temperature: float = 0.4):
    last_response = ""
    for _ in range(max_retries):
        raw = ask_llm(prompt, temperature=temperature)
        parsed = extract_json_block(raw)
        if parsed is not None:
            return parsed
        last_response = raw
    raise ValueError(f"LLM failed to return valid JSON.\nLast response:\n{last_response}")


def deduplicate_question_history(question_texts: list[str]) -> list[str]:
    seen = set()
    unique_questions = []

    for q in question_texts:
        q = str(q).strip()
        if not q:
            continue

        normalized = normalize_question_text(q)
        if normalized in seen:
            continue

        seen.add(normalized)
        unique_questions.append(q)

    return unique_questions


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def extract_chapter_number(text: str) -> int:
    match = re.search(r"ch(\d+)", str(text).lower())
    return int(match.group(1)) if match else 999


# =========================================================
# COURSE DISCOVERY
# =========================================================

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
        if normalized == norm_name or normalized in norm_name or norm_name in normalized:
            return actual_name

    return None


def get_available_courses() -> dict:
    try:
        course_folders = get_course_folders(COURSES_DIR)
        return {
            "success": True,
            "courses": [p.name for p in course_folders],
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "courses": [],
        }


# =========================================================
# STUDENT PROFILE LOADING
# =========================================================

def load_student_profiles_df() -> pd.DataFrame:
    if STUDENT_PROFILES_CSV.exists():
        return pd.read_csv(STUDENT_PROFILES_CSV, dtype=str).fillna("")
    return pd.DataFrame(columns=["student_id", "student_name", "courses_taken"])


def parse_courses_text(courses_text: str) -> list[str]:
    if not str(courses_text).strip():
        return []
    parts = [x.strip() for x in str(courses_text).split("|")]
    return [x for x in parts if x]


def load_student_taken_courses(student_profile: dict) -> list[str]:
    if not isinstance(student_profile, dict):
        return []

    if student_profile.get("courses_taken") and isinstance(student_profile.get("courses_taken"), list):
        return [str(x).strip() for x in student_profile["courses_taken"] if str(x).strip()]

    student_id = str(student_profile.get("student_id", "")).strip()
    if not student_id:
        return []

    df = load_student_profiles_df()
    if df.empty:
        return []

    match = df[df["student_id"].astype(str).str.strip() == student_id]
    if match.empty:
        return []

    return parse_courses_text(match.iloc[0].get("courses_taken", ""))


# =========================================================
# CHROMA HELPERS
# =========================================================

def get_chroma_client(chroma_dir: Path):
    return chromadb.PersistentClient(path=str(chroma_dir))


def get_collection_if_exists(chroma_client, collection_name: str):
    try:
        return chroma_client.get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
    except Exception:
        return None


def get_concepts_collection_for_course(course_name: str):
    course_dir = COURSES_DIR / course_name
    chroma_dir = course_dir / "outputs" / "chroma_db"
    if not chroma_dir.exists():
        return None

    client_db = get_chroma_client(chroma_dir)
    return get_collection_if_exists(client_db, f"{safe_slug(course_name)}_concepts")


def get_chunks_collection_for_course(course_name: str):
    course_dir = COURSES_DIR / course_name
    chroma_dir = course_dir / "outputs" / "chroma_db"
    if not chroma_dir.exists():
        return None

    client_db = get_chroma_client(chroma_dir)
    return get_collection_if_exists(client_db, f"{safe_slug(course_name)}_chunks")


def get_summaries_collection_for_course(course_name: str):
    course_dir = COURSES_DIR / course_name
    chroma_dir = course_dir / "outputs" / "chroma_db"
    if not chroma_dir.exists():
        return None

    client_db = get_chroma_client(chroma_dir)
    return get_collection_if_exists(client_db, f"{safe_slug(course_name)}_summaries")


# =========================================================
# CONCEPT COLLECTION
# =========================================================

def collect_all_concepts() -> pd.DataFrame:
    rows = []

    for course_dir in get_course_folders(COURSES_DIR):
        course_name = course_dir.name
        concepts_file = course_dir / "outputs" / "chapter_concepts.json"

        if not concepts_file.exists():
            continue

        with open(concepts_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for relative_path, content in data.items():
            chapter = str(content.get("chapter", "")).strip()

            for idx, topic in enumerate(content.get("topics", [])):
                topic_name = str(topic.get("topic_name", "")).strip()
                subtopics = [str(x).strip() for x in topic.get("subtopics", []) if str(x).strip()]
                keywords = [str(x).strip() for x in topic.get("keywords", []) if str(x).strip()]

                concept_text = (
                    f"Course: {course_name}\n"
                    f"File: {relative_path}\n"
                    f"Chapter: {chapter}\n"
                    f"Topic: {topic_name}\n"
                    f"Subtopics: {', '.join(subtopics)}\n"
                    f"Keywords: {', '.join(keywords)}"
                )

                rows.append({
                    "course_name": course_name,
                    "relative_path": relative_path,
                    "chapter": chapter,
                    "topic_index": idx,
                    "topic_name": topic_name,
                    "subtopics": subtopics,
                    "keywords": keywords,
                    "concept_text": concept_text,
                })

    return pd.DataFrame(rows)


def flatten_student_taken_subtopics(student_courses: list[str]) -> list[dict]:
    if not student_courses:
        return []

    concepts_df = collect_all_concepts()
    if concepts_df.empty:
        return []

    normalized_student_courses = {normalize_name(c) for c in student_courses}
    rows = []

    for _, row in concepts_df.iterrows():
        course_name = str(row["course_name"]).strip()
        if normalize_name(course_name) not in normalized_student_courses:
            continue

        topic_name = str(row["topic_name"]).strip()
        relative_path = str(row["relative_path"]).strip()
        chapter = str(row["chapter"]).strip()
        keywords = row["keywords"] if isinstance(row["keywords"], list) else []
        subtopics = row["subtopics"] if isinstance(row["subtopics"], list) else []

        for idx, subtopic_name in enumerate(subtopics):
            subtopic_name = str(subtopic_name).strip()
            if not subtopic_name:
                continue

            rows.append({
                "source_course": course_name,
                "source_relative_path": relative_path,
                "source_chapter": chapter,
                "source_topic_name": topic_name,
                "source_subtopic_name": subtopic_name,
                "keywords": keywords,
                "concept_text": (
                    f"Course: {course_name}\n"
                    f"File: {relative_path}\n"
                    f"Chapter: {chapter}\n"
                    f"Topic: {topic_name}\n"
                    f"Subtopic: {subtopic_name}\n"
                    f"Keywords: {', '.join(keywords)}"
                ),
                "source_subtopic_index": idx,
            })

    return rows


# =========================================================
# RELATED PREVIOUS SUBTOPICS FOR TARGET COURSE
# =========================================================

def get_related_previous_subtopics(
    student_profile: dict,
    target_course: str,
    top_k_per_source: int = DEFAULT_TOP_K_RELATED,
    max_total_results: int = DEFAULT_RELATED_SUBTOPICS_LIMIT,
) -> list[dict]:
    student_courses = load_student_taken_courses(student_profile)
    print("\nDEBUG student_courses:", student_courses)

    student_courses_resolved = []
    print("DEBUG target course:", target_course)

    course_name_map = build_course_name_map()

    for c in student_courses:
        resolved = resolve_course_folder_name(c, course_name_map)
        if resolved:
            student_courses_resolved.append(resolved)

    print("DEBUG resolved student courses:", student_courses_resolved)

    target_course_norm = normalize_name(target_course)
    student_courses_resolved = [
        c for c in student_courses_resolved
        if normalize_name(c) != target_course_norm
    ]

    source_subtopics = flatten_student_taken_subtopics(student_courses_resolved)
    print("DEBUG source_subtopics count:", len(source_subtopics))

    if not source_subtopics:
        return []

    target_concepts_collection = get_concepts_collection_for_course(target_course)
    if target_concepts_collection is None:
        return []

    related_rows = []

    for source in source_subtopics:
        try:
            results = target_concepts_collection.query(
                query_texts=[source["concept_text"]],
                n_results=top_k_per_source,
            )
        except Exception:
            continue

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])

        if distances and len(distances[0]) == len(metas):
            dist_list = distances[0]
        else:
            dist_list = [None] * len(metas)

        for doc, meta, dist in zip(docs, metas, dist_list):
            related_rows.append({
                "source_course": source["source_course"],
                "source_relative_path": source["source_relative_path"],
                "source_chapter": source["source_chapter"],
                "source_topic_name": source["source_topic_name"],
                "source_subtopic_name": source["source_subtopic_name"],
                "target_course": str(meta.get("course_name", "")).strip(),
                "target_relative_path": str(meta.get("relative_path", "")).strip(),
                "target_chapter": str(meta.get("chapter", "")).strip(),
                "target_topic_name": str(meta.get("topic_name", "")).strip(),
                "target_concept_text": str(doc).strip(),
                "distance": dist,
            })

    related_rows = sorted(
        related_rows,
        key=lambda x: (
            x["distance"] if x["distance"] is not None else 999999,
            normalize_name(x["source_course"]),
            normalize_name(x["source_topic_name"]),
            normalize_name(x["source_subtopic_name"]),
        )
    )

    seen = set()
    deduped = []

    for item in related_rows:
        key = (
            normalize_name(item["source_course"]),
            normalize_name(item["source_topic_name"]),
            normalize_name(item["source_subtopic_name"]),
        )
        if key in seen:
            continue

        seen.add(key)
        deduped.append(item)

        if len(deduped) >= max_total_results:
            break
    
    print("DEBUG related_rows count:", len(related_rows))
    print("DEBUG deduped related count:", len(deduped))

    if deduped:
       return deduped

    # FALLBACK: if no semantic related matches found,
    # use student previous subtopics directly
    fallback = []
    for source in source_subtopics[:max_total_results]:
        fallback.append({
            "source_course": source["source_course"],
            "source_relative_path": source["source_relative_path"],
            "source_chapter": source["source_chapter"],
            "source_topic_name": source["source_topic_name"],
            "source_subtopic_name": source["source_subtopic_name"],
            "target_course": target_course,
            "target_relative_path": "",
            "target_chapter": "",
            "target_topic_name": source["source_topic_name"],
            "target_concept_text": source["concept_text"],
            "distance": None,
        })

    return fallback


# =========================================================
# TARGET COURSE RETRIEVAL FOR EXERCISES / LEARNING PATH
# =========================================================

def retrieve_target_course_material(
    target_course: str,
    topic_name: str,
    subtopic_name: str,
    n_chunk_results: int = 6,
    n_summary_results: int = 2,
    n_concept_results: int = 3,
) -> dict[str, Any]:
    chunks_collection = get_chunks_collection_for_course(target_course)
    summaries_collection = get_summaries_collection_for_course(target_course)
    concepts_collection = get_concepts_collection_for_course(target_course)

    query_text = (
        f"Course: {target_course}\n"
        f"Topic: {topic_name}\n"
        f"Subtopic: {subtopic_name}\n"
        f"Find the most relevant study material."
    )

    result = {
        "chunks": [],
        "summaries": [],
        "concepts": [],
    }

    if chunks_collection is not None:
        try:
            qr = chunks_collection.query(query_texts=[query_text], n_results=n_chunk_results)
            for doc, meta in zip(qr.get("documents", [[]])[0], qr.get("metadatas", [[]])[0]):
                result["chunks"].append({"text": doc, "metadata": meta})
        except Exception:
            pass

    if summaries_collection is not None:
        try:
            qr = summaries_collection.query(query_texts=[query_text], n_results=n_summary_results)
            for doc, meta in zip(qr.get("documents", [[]])[0], qr.get("metadatas", [[]])[0]):
                result["summaries"].append({"text": doc, "metadata": meta})
        except Exception:
            pass

    if concepts_collection is not None:
        try:
            qr = concepts_collection.query(query_texts=[query_text], n_results=n_concept_results)
            for doc, meta in zip(qr.get("documents", [[]])[0], qr.get("metadatas", [[]])[0]):
                result["concepts"].append({"text": doc, "metadata": meta})
        except Exception:
            pass

    return result


def build_context_text(retrieved: dict[str, Any]) -> str:
    parts = []

    if retrieved["concepts"]:
        parts.append("=== CONCEPTS ===")
        for i, item in enumerate(retrieved["concepts"], start=1):
            meta = item.get("metadata", {})
            parts.append(
                f"[Concept {i}] Topic: {meta.get('topic_name', '')}\n"
                f"File: {meta.get('relative_path', '')}\n"
                f"{item.get('text', '')}"
            )

    if retrieved["summaries"]:
        parts.append("\n=== SUMMARIES ===")
        for i, item in enumerate(retrieved["summaries"], start=1):
            meta = item.get("metadata", {})
            parts.append(
                f"[Summary {i}] File: {meta.get('relative_path', '')}\n"
                f"{item.get('text', '')}"
            )

    if retrieved["chunks"]:
        parts.append("\n=== CHUNKS ===")
        for i, item in enumerate(retrieved["chunks"], start=1):
            meta = item.get("metadata", {})
            parts.append(
                f"[Chunk {i}] File: {meta.get('relative_path', '')} | "
                f"Chapter: {meta.get('chapter', '')}\n"
                f"{item.get('text', '')}"
            )

    return "\n\n".join(parts).strip()


# =========================================================
# DIFFICULTY
# =========================================================

def assign_diagnostic_difficulties(total_questions: int) -> list[str]:
    if total_questions <= 0:
        return []

    easy_count = round(total_questions * DIAGNOSTIC_DIFFICULTY_DISTRIBUTION["easy"])
    medium_count = round(total_questions * DIAGNOSTIC_DIFFICULTY_DISTRIBUTION["medium"])
    hard_count = total_questions - easy_count - medium_count

    difficulties = (
        ["easy"] * easy_count +
        ["medium"] * medium_count +
        ["hard"] * hard_count
    )

    if len(difficulties) < total_questions:
        difficulties.extend(["medium"] * (total_questions - len(difficulties)))
    elif len(difficulties) > total_questions:
        difficulties = difficulties[:total_questions]

    return difficulties


def count_difficulties(items: list[dict]) -> dict:
    counts = {"easy": 0, "medium": 0, "hard": 0}
    for item in items:
        diff = str(item.get("difficulty", "")).strip().lower()
        if diff in counts:
            counts[diff] += 1
    return counts


# =========================================================
# QUESTION GENERATION FOR DIAGNOSTIC EXAM
# =========================================================

def generate_diagnostic_mcq(
    target_course: str,
    source_course: str,
    source_topic_name: str,
    source_subtopic_name: str,
    target_topic_name: str,
    retrieved_target_text: str,
    difficulty: str,
    banned_questions: list[str] | None = None,
    banned_concepts: list[str] | None = None,
) -> dict:
    banned_questions = banned_questions or []
    banned_concepts = banned_concepts or []

    banned_block = ""
    if banned_questions:
        banned_preview = "\n".join(f"- {q}" for q in banned_questions[:200])
        banned_block += f"""

DO NOT REPEAT or reword these previous diagnostic questions:
{banned_preview}
"""

    if banned_concepts:
        concept_preview = "\n".join(f"- {c}" for c in banned_concepts[:100])
        banned_block += f"""

DO NOT generate a question testing these already-used concepts:
{concept_preview}
"""

    prompt = f"""
You are generating a diagnostic multiple-choice question.

CRITICAL ANTI-REPETITION RULES:
- Generate exactly 1 multiple-choice question.
- The question must test a DIFFERENT idea from previous questions.
- Do NOT ask another question with the same meaning using different wording.
- Do NOT repeat the same concept such as:
  - definition of data engineering
  - responsibilities of data engineers
  - data scientist vs data engineer comparison
  - supervised learning label/target idea
- If the previous concept is already used, choose another specific concept from the material.
- Avoid generic wording like "which option best describes".
- Make the question specific to the subtopic.

CONTENT RULES:
- This question is for a diagnostic exam before studying the target course.
- The question MUST be based on the student's previously taken related subtopic.
- Use ONLY the academically relevant relation between:
  - previous course subtopic
  - target course material
- Do NOT use outside knowledge.
- Do NOT invent facts.
- Keep the question academically clear.
- Use difficulty: {difficulty}
- Return ONLY valid JSON.
{banned_block}

Return JSON in this exact format:
{{
  "question": "...",
  "options": {{
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "..."
  }},
  "correct_answer": "A",
  "difficulty": "{difficulty}",
  "explanation": "..."
}}

Student's previous course: {source_course}
Previous topic: {source_topic_name}
Previous related subtopic: {source_subtopic_name}

Target course: {target_course}
Target topic connection: {target_topic_name}

Target course retrieved material:
{retrieved_target_text[:12000]}
"""

    parsed = ask_llm_for_json(prompt, temperature=0.65)

    if not isinstance(parsed, dict):
        raise ValueError("LLM did not return a valid JSON object.")

    question = str(parsed.get("question", "")).strip()
    options = parsed.get("options", {})
    correct_answer = str(parsed.get("correct_answer", "")).strip().upper()
    result_difficulty = str(parsed.get("difficulty", "")).strip().lower()
    explanation = str(parsed.get("explanation", "")).strip()

    if not question:
        raise ValueError("Diagnostic question is empty.")

    if result_difficulty not in {"easy", "medium", "hard"}:
        raise ValueError("Invalid difficulty returned.")

    if not isinstance(options, dict) or set(options.keys()) != {"A", "B", "C", "D"}:
        raise ValueError("Invalid MCQ options returned.")

    if correct_answer not in {"A", "B", "C", "D"}:
        raise ValueError("Invalid correct answer returned.")

    for old_q in banned_questions:
        if is_too_similar(question, old_q):
            raise ValueError("Semantically repeated diagnostic question detected.")

    question_concept = extract_question_concept(question)
    if question_concept in set(banned_concepts):
        raise ValueError("Repeated diagnostic concept detected.")

    return {
        "question": question,
        "options": {
            "A": str(options["A"]).strip(),
            "B": str(options["B"]).strip(),
            "C": str(options["C"]).strip(),
            "D": str(options["D"]).strip(),
        },
        "correct_answer": correct_answer,
        "difficulty": result_difficulty,
        "explanation": explanation,
    }


def build_diagnostic_exam_questions(
    student_profile: dict,
    target_course: str,
    previous_question_history: list[str] | None = None,
) -> list[dict]:
    previous_question_history = previous_question_history or []

    used_questions = {normalize_question_text(q) for q in previous_question_history}
    used_concepts = {extract_question_concept(q) for q in previous_question_history}

    related_items = get_related_previous_subtopics(student_profile, target_course)

    if not related_items:
        raise ValueError("No related previous subtopics were found for this student and target course.")

    random.shuffle(related_items)

    difficulties = assign_diagnostic_difficulties(len(related_items))

    question_rows = []
    subtopic_counts = {}

    for item, difficulty in zip(related_items, difficulties):
        subtopic_key = (
            normalize_name(item["source_course"]),
            normalize_name(item["source_topic_name"]),
            normalize_name(item["source_subtopic_name"]),
        )

        if subtopic_counts.get(subtopic_key, 0) >= 1:
            continue

        retrieved = retrieve_target_course_material(
            target_course=target_course,
            topic_name=item["target_topic_name"],
            subtopic_name=item["source_subtopic_name"],
        )

        context_text = build_context_text(retrieved)

        if not context_text.strip():
            continue

        banned_questions = list(previous_question_history)
        banned_questions.extend(q["question"] for q in question_rows)

        banned_concepts = list(used_concepts)

        try:
            generated = generate_diagnostic_mcq(
                target_course=target_course,
                source_course=item["source_course"],
                source_topic_name=item["source_topic_name"],
                source_subtopic_name=item["source_subtopic_name"],
                target_topic_name=item["target_topic_name"],
                retrieved_target_text=context_text,
                difficulty=difficulty,
                banned_questions=banned_questions,
                banned_concepts=banned_concepts,
            )
        except Exception as e:
            print(f"Skipped diagnostic item '{item['source_subtopic_name']}': {e}")
            continue

        normalized_q = normalize_question_text(generated["question"])
        generated_concept = extract_question_concept(generated["question"])

        if normalized_q in used_questions:
            continue

        if generated_concept in used_concepts:
            continue

        too_similar = False
        for old_row in question_rows:
            if is_too_similar(generated["question"], old_row["question"]):
                too_similar = True
                break

        if too_similar:
            continue

        used_questions.add(normalized_q)
        used_concepts.add(generated_concept)
        subtopic_counts[subtopic_key] = subtopic_counts.get(subtopic_key, 0) + 1

        question_rows.append({
            "question_id": f"q{len(question_rows) + 1}",
            "target_course": target_course,
            "source_course": item["source_course"],
            "source_relative_path": item["source_relative_path"],
            "source_chapter": item["source_chapter"],
            "source_topic_name": item["source_topic_name"],
            "source_subtopic_name": item["source_subtopic_name"],
            "target_course_topic_name": item["target_topic_name"],
            "target_relative_path": item["target_relative_path"],
            "target_chapter": item["target_chapter"],
            "difficulty": generated["difficulty"],
            "question": generated["question"],
            "options": generated["options"],
            "correct_answer": generated["correct_answer"],
            "explanation": generated["explanation"],
        })

    if not question_rows:
        raise ValueError("No diagnostic exam questions could be generated.")

    return question_rows


# =========================================================
# SAVING / LOADING EXAM 1 FILES
# =========================================================

def get_student_part(student_profile: dict | None) -> str:
    if student_profile and student_profile.get("student_id"):
        return safe_slug(student_profile["student_id"])
    return "guest"


def get_exam1_diagnostic_path(student_profile: dict | None, target_course: str) -> Path:
    return EXAM1_RESULTS_DIR / f"exam1_diagnostic_{get_student_part(student_profile)}_{safe_slug(target_course)}.json"


def get_learning_path_path(student_profile: dict | None, target_course: str) -> Path:
    return EXAM1_RESULTS_DIR / f"learning_path_{get_student_part(student_profile)}_{safe_slug(target_course)}.json"


def get_learning_path_exercises_path(student_profile: dict | None, target_course: str) -> Path:
    return EXAM1_RESULTS_DIR / f"learning_path_exercises_{get_student_part(student_profile)}_{safe_slug(target_course)}.json"

def get_exam1_question_history_path(student_profile: dict | None, target_course: str) -> Path:
    return EXAM1_RESULTS_DIR / f"exam1_question_history_{get_student_part(student_profile)}_{safe_slug(target_course)}.json"


def load_exam1_question_history(student_profile: dict | None, target_course: str) -> list[str]:
    path = get_exam1_question_history_path(student_profile, target_course)
    data = load_json_if_exists(path)

    if not data:
        return []

    history = data.get("question_history", [])
    if not isinstance(history, list):
        return []

    return [str(q).strip() for q in history if str(q).strip()]


def save_exam1_question_history(student_profile: dict | None, target_course: str, question_history: list[str]):
    path = get_exam1_question_history_path(student_profile, target_course)
    payload = {
        "student_id": str(student_profile.get("student_id", "")) if student_profile else "",
        "target_course": target_course,
        "question_history": deduplicate_question_history(question_history),
    }
    save_json(path, payload)


def save_json(path: Path, payload: dict):
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# =========================================================
# FRONTEND-FRIENDLY EXAM 1 DISCOVERY
# =========================================================

def get_exam1_available_courses(student_profile: dict) -> dict:
    try:
        taken_courses = load_student_taken_courses(student_profile)
        taken_norm = {normalize_name(c) for c in taken_courses}

        course_folders = get_course_folders(COURSES_DIR)
        available = []

        for p in course_folders:
            if normalize_name(p.name) in taken_norm:
                continue
            available.append(p.name)

        return {
            "success": True,
            "student_id": str(student_profile.get("student_id", "")),
            "student_name": str(student_profile.get("student_name", "")),
            "courses_taken": taken_courses,
            "available_target_courses": available,
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "available_target_courses": [],
        }


# =========================================================
# GENERATE DIAGNOSTIC EXAM
# =========================================================

def generate_diagnostic_exam(
    student_profile: dict,
    target_course: str,
    save_result: bool = True,
) -> dict:
    try:
        if "student_id" not in student_profile or "student_name" not in student_profile:
            return {
                "success": False,
                "message": "student_profile must contain at least student_id and student_name.",
                "questions": [],
            }

        course_name_map = build_course_name_map()
        resolved_target_course = resolve_course_folder_name(target_course, course_name_map)

        if not resolved_target_course:
            return {
                "success": False,
                "message": f"Could not match target course: {target_course}",
                "questions": [],
            }
        
        previous_question_history = load_exam1_question_history(
            student_profile=student_profile,
            target_course=resolved_target_course,
        )

        questions = build_diagnostic_exam_questions(
            student_profile=student_profile,
            target_course=resolved_target_course,
            previous_question_history=previous_question_history,
        )
        difficulty_counts = count_difficulties(questions)

        exam_payload = {
            "student_id": str(student_profile.get("student_id", "")),
            "student_name": str(student_profile.get("student_name", "")),
            "target_course": resolved_target_course,
            "total_questions": len(questions),
            "difficulty_distribution": difficulty_counts,
            "questions": [
                {
                    "question_id": q["question_id"],
                    "source_course": q["source_course"],
                    "source_topic_name": q["source_topic_name"],
                    "source_subtopic_name": q["source_subtopic_name"],
                    "difficulty": q["difficulty"],
                    "question": q["question"],
                    "options": q["options"],
                }
                for q in questions
            ],
            "question_records_full": questions,
        }

        saved_path = None
        if save_result:
            saved_path = get_exam1_diagnostic_path(student_profile, resolved_target_course)
            save_json(saved_path, exam_payload)

        response_payload = {
            "success": True,
            "message": "Diagnostic exam generated successfully.",
            "student_id": exam_payload["student_id"],
            "student_name": exam_payload["student_name"],
            "target_course": exam_payload["target_course"],
            "total_questions": exam_payload["total_questions"],
            "difficulty_distribution": exam_payload["difficulty_distribution"],
            "questions": exam_payload["questions"],
        }

        return response_payload

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "questions": [],
        }


# =========================================================
# SUBMIT / GRADE DIAGNOSTIC EXAM
# =========================================================

def grade_diagnostic_exam(
    exam_payload: dict,
    submitted_answers: list[dict],
) -> dict:
    submitted_map = {}
    for item in submitted_answers:
        qid = str(item.get("question_id", "")).strip()
        ans = str(item.get("student_answer", "")).strip().upper()
        if qid:
            submitted_map[qid] = ans

    full_questions = exam_payload.get("question_records_full", [])
    total_questions = len(full_questions)

    if total_questions == 0:
        raise ValueError("No questions found in saved diagnostic exam.")

    correct_count = 0
    wrong_count = 0
    review_rows = []
    weak_subtopics = []

    for q in full_questions:
        question_id = q["question_id"]
        student_answer = submitted_map.get(question_id, "")
        correct_answer = q["correct_answer"]
        is_correct = student_answer == correct_answer

        if is_correct:
            correct_count += 1
        else:
            wrong_count += 1
            weak_subtopics.append({
                "source_course": q["source_course"],
                "topic_name": q["source_topic_name"],
                "subtopic_name": q["source_subtopic_name"],
                "target_course_topic_name": q["target_course_topic_name"],
                "source_relative_path": q["source_relative_path"],
                "source_chapter": q["source_chapter"],
                "score": 0,
                "max_score": 1,
            })

        review_rows.append({
            "question_id": question_id,
            "source_course": q["source_course"],
            "topic_name": q["source_topic_name"],
            "subtopic_name": q["source_subtopic_name"],
            "difficulty": q["difficulty"],
            "question": q["question"],
            "options": q["options"],
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": q["explanation"],
            "status_color": "green" if is_correct else "red",
        })

    score_percentage = round((correct_count / total_questions) * 100, 2)

    deduped_weak = []
    seen = set()
    for item in weak_subtopics:
        key = (
            normalize_name(item["source_course"]),
            normalize_name(item["topic_name"]),
            normalize_name(item["subtopic_name"]),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped_weak.append(item)

    return {
        "score_percentage": score_percentage,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "questions_review": review_rows,
        "weak_subtopics": deduped_weak,
    }


def submit_diagnostic_exam(
    student_profile: dict,
    target_course: str,
    submitted_answers: list[dict],
) -> dict:
    try:
        course_name_map = build_course_name_map()
        resolved_target_course = resolve_course_folder_name(target_course, course_name_map)

        if not resolved_target_course:
            return {
                "success": False,
                "message": f"Could not match target course: {target_course}",
                "questions_review": [],
            }

        exam_path = get_exam1_diagnostic_path(student_profile, resolved_target_course)
        exam_payload = load_json_if_exists(exam_path)

        if not exam_payload:
            return {
                "success": False,
                "message": "Diagnostic exam file was not found. Generate the exam first.",
                "questions_review": [],
            }

        graded = grade_diagnostic_exam(exam_payload, submitted_answers)

        current_question_texts = [
            q["question"] for q in exam_payload.get("question_records_full", [])
        ]
        full_question_history = deduplicate_question_history(
            load_exam1_question_history(student_profile, resolved_target_course) + current_question_texts
        )
        save_exam1_question_history(student_profile, resolved_target_course, full_question_history)

        result_payload = {
            "student_id": str(student_profile.get("student_id", "")),
            "student_name": str(student_profile.get("student_name", "")),
            "target_course": resolved_target_course,
            "score_percentage": graded["score_percentage"],
            "correct_count": graded["correct_count"],
            "wrong_count": graded["wrong_count"],
            "questions_review": graded["questions_review"],
            "weak_subtopics": graded["weak_subtopics"],
        }

        response_payload = {
            "success": True,
            "message": "Diagnostic exam submitted successfully.",
            **result_payload,
        }

        return response_payload

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "questions_review": [],
        }



# =========================================================
# LEARNING PATH
# =========================================================

def build_learning_path_from_result(result_payload: dict) -> list[dict]:
    weak_subtopics = result_payload.get("weak_subtopics", [])
    grouped = {}

    for item in weak_subtopics:
        source_course = str(item.get("source_course", "")).strip()
        source_material_pdf = str(item.get("source_relative_path", "")).strip()
        topic_name = str(item.get("topic_name", "")).strip()
        subtopic_name = str(item.get("subtopic_name", "")).strip()

        if not source_course or not topic_name or not subtopic_name:
            continue

        group_key = (
            normalize_name(source_course),
            normalize_name(source_material_pdf),
            normalize_name(topic_name),
        )

        if group_key not in grouped:
            grouped[group_key] = {
                "step_number": 0,
                "source_course": source_course,
                "source_material_pdf": source_material_pdf,
                "topic_name": topic_name,
                "weak_subtopics": [],
            }

        grouped[group_key]["weak_subtopics"].append({
            "subtopic_name": subtopic_name,
            "reason": "Student answered the diagnostic question for this subtopic incorrectly.",
            "score": item.get("score", 0),
            "max_score": item.get("max_score", 1),
        })

    learning_path = sorted(
        grouped.values(),
        key=lambda group: (
            normalize_name(group["source_course"]),
            extract_chapter_number(group["source_material_pdf"]),
            normalize_name(group["source_material_pdf"]),
            normalize_name(group["topic_name"]),
        )
    )

    for idx, group in enumerate(learning_path, start=1):
        group["step_number"] = idx

    for group in learning_path:
        group["weak_subtopics"] = sorted(
            group["weak_subtopics"],
            key=lambda x: normalize_name(x["subtopic_name"])
        )

    return learning_path

def generate_learning_path_from_graded_result(
    student_profile: dict,
    graded_result_payload: dict,
    save_result: bool = True,
) -> dict:
    try:
        learning_path = build_learning_path_from_result(graded_result_payload)

        if not learning_path:
            return {
                "success": True,
                "message": "No weak subtopics found. Learning path is empty.",
                "target_course": graded_result_payload["target_course"],
                "learning_path": [],
                "actions": {
                    "download_pdf_available": False,
                    "generate_exercises_available": False,
                    "track_progress_available": True,
                },
            }

        payload = {
            "student_id": str(student_profile.get("student_id", "")),
            "student_name": str(student_profile.get("student_name", "")),
            "target_course": graded_result_payload["target_course"],
            "learning_path": learning_path,
            "actions": {
                "download_pdf_available": True,
                "generate_exercises_available": True,
                "track_progress_available": True,
            },
        }

        saved_path = None
        if save_result:
            saved_path = get_learning_path_path(student_profile, graded_result_payload["target_course"])
            save_json(saved_path, payload)

        response_payload = {
            "success": True,
            "message": "Learning path generated successfully.",
            **payload,
        }

        if saved_path:
            response_payload["saved_learning_path_path"] = str(saved_path)

        return response_payload

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "learning_path": [],
        }


def get_learning_path(student_profile: dict, target_course: str) -> dict:
    try:
        course_name_map = build_course_name_map()
        resolved_target_course = resolve_course_folder_name(target_course, course_name_map)

        if not resolved_target_course:
            return {"success": False, "message": f"Could not match target course: {target_course}"}

        path_file = get_learning_path_path(student_profile, resolved_target_course)
        data = load_json_if_exists(path_file)

        if not data:
            return {"success": False, "message": "Learning path not found."}

        return {
            "success": True,
            "message": "Learning path loaded successfully.",
            **data,
        }

    except Exception as e:
        return {"success": False, "message": str(e)}


# =========================================================
# EXERCISES GENERATION
# =========================================================

def detect_code_in_context(context_text: str) -> bool:
    text = context_text.lower()

    code_signals = [
        "def ",
        "class ",
        "public static void",
        "#include",
        "int main",
        "for(",
        "for (",
        "while(",
        "while (",
        "select *",
        "insert into",
        "update ",
        "create table",
        "python",
        "java",
        "c++",
        "javascript",
        "sql",
        "code",
        "program",
        "function",
        "algorithm",
        "pseudocode",
    ]

    return any(signal in text for signal in code_signals)


def choose_exercise_type(index: int, has_code: bool) -> str:
    if has_code:
        pattern = ["multiple_choice", "essay", "coding"]
    else:
        pattern = ["multiple_choice", "essay"]
    return pattern[index % len(pattern)]


def generate_exercise_for_subtopic(
    target_course: str,
    topic_name: str,
    subtopic_name: str,
    context_text: str,
    required_type: str,
) -> dict:
    prompt = f"""
You are generating a practice exercise for a student's weak subtopic.

IMPORTANT RULES:
- Use ONLY the provided course material.
- Do NOT use outside knowledge.
- Do NOT invent facts.
- Generate exactly 1 exercise.
- Required exercise type: {required_type}
- Return ONLY valid JSON.

Return JSON in this exact format:
{{
  "exercise_type": "{required_type}",
  "question": "...",
  "options": {{
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "..."
  }},
  "correct_answer": "A",
  "answer_text": "",
  "explanation": "..."
}}

Rules:
- If exercise_type = multiple_choice:
  - include options A/B/C/D
  - include correct_answer
  - answer_text can be empty
- If exercise_type = essay or coding:
  - options must be {{}}
  - correct_answer can be ""
  - answer_text must contain the answer
- explanation should always exist

Target course: {target_course}
Topic: {topic_name}
Weak subtopic: {subtopic_name}

COURSE MATERIAL:
{context_text[:14000]}
"""

    parsed = ask_llm_for_json(prompt, temperature=0.45)

    if not isinstance(parsed, dict):
        raise ValueError("LLM did not return a valid JSON object.")

    exercise_type = str(parsed.get("exercise_type", "")).strip().lower()
    question = str(parsed.get("question", "")).strip()
    options = parsed.get("options", {})
    correct_answer = str(parsed.get("correct_answer", "")).strip().upper()
    answer_text = str(parsed.get("answer_text", "")).strip()
    explanation = str(parsed.get("explanation", "")).strip()

    if exercise_type != required_type:
        raise ValueError(f"Wrong exercise type returned: {exercise_type}")

    if not question:
        raise ValueError("Exercise question is empty.")

    cleaned = {
        "exercise_type": exercise_type,
        "question": question,
        "options": {},
        "correct_answer": "",
        "answer_text": answer_text,
        "explanation": explanation,
        "answer_hidden": True,
    }

    if exercise_type == "multiple_choice":
        if not isinstance(options, dict) or set(options.keys()) != {"A", "B", "C", "D"}:
            raise ValueError("Invalid MCQ exercise options returned.")
        if correct_answer not in {"A", "B", "C", "D"}:
            raise ValueError("Invalid MCQ exercise correct answer returned.")

        cleaned["options"] = {
            "A": str(options["A"]).strip(),
            "B": str(options["B"]).strip(),
            "C": str(options["C"]).strip(),
            "D": str(options["D"]).strip(),
        }
        cleaned["correct_answer"] = correct_answer
    else:
        if not answer_text:
            raise ValueError("Essay/coding exercise is missing answer_text.")

    return cleaned


def generate_learning_path_exercises(
    student_profile: dict,
    target_course: str,
    subtopic_requests: list[dict],
    save_result: bool = True,
) -> dict:
    try:
        course_name_map = build_course_name_map()
        resolved_target_course = resolve_course_folder_name(target_course, course_name_map)

        if not resolved_target_course:
            return {
                "success": False,
                "message": f"Could not match target course: {target_course}",
                "exercise_groups": [],
            }

        learning_path_result = get_learning_path(student_profile, resolved_target_course)
        if not learning_path_result.get("success"):
            return {
                "success": False,
                "message": "Learning path not found. Generate the learning path first.",
                "exercise_groups": [],
            }

        learning_path = learning_path_result.get("learning_path", [])
        if not learning_path:
            return {
                "success": False,
                "message": "Learning path is empty. No weak subtopics available.",
                "exercise_groups": [],
            }

        available_map = {}

        for item in learning_path:
            topic_name = str(item.get("topic_name", "")).strip()

            for weak in item.get("weak_subtopics", []):
                subtopic_name = str(weak.get("subtopic_name", "")).strip()
                key = (normalize_name(topic_name), normalize_name(subtopic_name))
                available_map[key] = {
                    "topic_name": topic_name,
                    "subtopic_name": subtopic_name,
                    "source_course": item.get("source_course", ""),
                    "source_material_pdf": item.get("source_material_pdf", ""),
                }

        exercise_groups = []

        for request in subtopic_requests:
            topic_name = str(request.get("topic_name", "")).strip()
            subtopic_name = str(request.get("subtopic_name", "")).strip()
            num_exercises = int(request.get("num_exercises", 0))

            if not topic_name or not subtopic_name or num_exercises <= 0:
                continue

            key = (normalize_name(topic_name), normalize_name(subtopic_name))
            if key not in available_map:
                continue

            retrieved = retrieve_target_course_material(
                target_course=resolved_target_course,
                topic_name=topic_name,
                subtopic_name=subtopic_name,
            )
            context_text = build_context_text(retrieved)

            if not context_text.strip():
                continue

            has_code = detect_code_in_context(context_text)
            exercises = []

            for i in range(num_exercises):
                required_type = choose_exercise_type(i, has_code)

                try:
                    exercise = generate_exercise_for_subtopic(
                        target_course=resolved_target_course,
                        topic_name=topic_name,
                        subtopic_name=subtopic_name,
                        context_text=context_text,
                        required_type=required_type,
                    )
                except Exception as e:
                    print(f"Skipped exercise for '{subtopic_name}': {e}")
                    continue

                exercises.append({
                    "exercise_id": f"{safe_slug(topic_name)}_{safe_slug(subtopic_name)}_{len(exercises)+1}",
                    **exercise,
                })

            exercise_groups.append({
                "topic_name": topic_name,
                "subtopic_name": subtopic_name,
                "requested_count": num_exercises,
                "generated_count": len(exercises),
                "exercises": exercises,
            })

        payload = {
            "student_id": str(student_profile.get("student_id", "")),
            "student_name": str(student_profile.get("student_name", "")),
            "target_course": resolved_target_course,
            "exercise_groups": exercise_groups,
        }

        saved_path = None
        if save_result:
            saved_path = get_learning_path_exercises_path(student_profile, resolved_target_course)
            save_json(saved_path, payload)

        response_payload = {
            "success": True,
            "message": "Exercises generated successfully.",
            **payload,
        }

        if saved_path:
            response_payload["saved_exercises_path"] = str(saved_path)

        return response_payload

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "exercise_groups": [],
        }


# =========================================================
# PROGRESS
# =========================================================

def get_progress_for_student(student_profile: dict, target_course: str) -> dict:
    try:
        course_name_map = build_course_name_map()
        resolved_target_course = resolve_course_folder_name(target_course, course_name_map)
        if not resolved_target_course:
            return {"success": False, "message": f"Could not match target course: {target_course}"}

        learning_path = get_learning_path(student_profile, resolved_target_course)
        exercises_data = load_json_if_exists(
            get_learning_path_exercises_path(student_profile, resolved_target_course)
        )

        generated_exercise_count = 0
        if exercises_data:
            for group in exercises_data.get("exercise_groups", []):
                generated_exercise_count += len(group.get("exercises", []))

        weak_subtopics_count = 0
        learning_path_steps = 0

        if learning_path.get("success"):
            learning_path_steps = len(learning_path.get("learning_path", []))
            for step in learning_path.get("learning_path", []):
                weak_subtopics_count += len(step.get("weak_subtopics", []))

        return {
            "success": True,
            "message": "Progress loaded successfully.",
            "target_course": resolved_target_course,
            "diagnostic_score_percentage": None,
            "weak_subtopics_count": weak_subtopics_count,
            "learning_path_steps": learning_path_steps,
            "generated_exercises_count": generated_exercise_count,
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

def get_all_progress_for_student(student_profile: dict) -> dict:
    try:
        student_id = str(student_profile.get("student_id", "")).strip()
        if not student_id:
            return {"success": False, "message": "Missing student_id", "progress": []}

        progress_rows = []

        if not EXAM1_RESULTS_DIR.exists():
            return {"success": True, "progress": []}

        pattern = f"learning_path_{safe_slug(student_id)}_*.json"

        for path_file in EXAM1_RESULTS_DIR.glob(pattern):
            data = load_json_if_exists(path_file)
            if not data:
                continue

            target_course = str(data.get("target_course", "")).strip()
            learning_path = data.get("learning_path", []) or []

            course_name_map = build_course_name_map()
            resolved_target_course = resolve_course_folder_name(target_course, course_name_map) or target_course

            exercises_data = load_json_if_exists(
                get_learning_path_exercises_path(student_profile, resolved_target_course)
            )

            generated_exercise_count = 0
            if exercises_data:
                for group in exercises_data.get("exercise_groups", []):
                    generated_exercise_count += len(group.get("exercises", []))

            weak_subtopics_count = 0
            for step in learning_path:
                weak_subtopics_count += len(step.get("weak_subtopics", []))

            progress_rows.append({
                "target_course": target_course,
                "learning_path_steps": len(learning_path),
                "completed_steps": 0,
                "weak_subtopics_count": weak_subtopics_count,
                "generated_exercises_count": generated_exercise_count,
            })

        progress_rows = sorted(progress_rows, key=lambda x: normalize_name(x["target_course"]))

        return {
            "success": True,
            "message": "Progress loaded successfully.",
            "progress": progress_rows,
        }

    except Exception as e:
        return {"success": False, "message": str(e), "progress": []}


# =========================================================
# CLI TEST
# =========================================================

def main():

    print("\nAll real course folders:")
    for p in get_course_folders(COURSES_DIR):
        print("-", p.name)

    test_profile = {
    "student_id": "test_001",
    "student_name": "Test Student",
    "courses_taken": ["Introduction to Data Science", "Database Systems"]
    }
    print("\nStudent taken courses:", load_student_taken_courses(test_profile))

    print("=" * 70)
    print("MANARA - EXAM 1 DIAGNOSTIC TEST MODE")
    print("=" * 70)

    available = get_exam1_available_courses(test_profile)
    print("\nAvailable target courses:")
    for c in available.get("available_target_courses", [])[:30]:
        print("-", c)

    target_course = input("\nEnter target course: ").strip()
    if not target_course:
        print("No target course entered.")
        return

    print("\nStudent taken courses:", load_student_taken_courses(test_profile))
    generated = generate_diagnostic_exam(test_profile, target_course, save_result=True)
    print("\nGenerate exam success:", generated["success"])
    print("Message:", generated["message"])

    if not generated["success"]:
        return

    print(f"\nTarget course: {generated['target_course']}")
    print("Total questions:", generated["total_questions"])
    print("Difficulty distribution:", generated["difficulty_distribution"])

    submitted_answers = []
    for q in generated["questions"]:
        print("\n" + "-" * 70)
        print(f"{q['question_id']} | Difficulty: {q['difficulty']}")
        print(f"From course : {q['source_course']}")
        print(f"Topic       : {q['source_topic_name']}")
        print(f"Subtopic    : {q['source_subtopic_name']}")
        print(q["question"])
        print("A)", q["options"]["A"])
        print("B)", q["options"]["B"])
        print("C)", q["options"]["C"])
        print("D)", q["options"]["D"])

        ans = input("Your answer (A/B/C/D): ").strip().upper()
        submitted_answers.append({
            "question_id": q["question_id"],
            "student_answer": ans,
        })

    result = submit_diagnostic_exam(
        student_profile=test_profile,
        target_course=generated["target_course"],
        submitted_answers=submitted_answers,
    )

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print("Success:", result["success"])
    print("Message:", result["message"])

    if not result["success"]:
        return

    print("Score percentage:", result["score_percentage"])
    print("Correct:", result["correct_count"])
    print("Wrong  :", result["wrong_count"])

    lp = generate_learning_path_from_graded_result(
        student_profile=test_profile,
        graded_result_payload=result,
        save_result=True,
    )

    print("\nLearning path success:", lp["success"])
    print("Message:", lp["message"])

    if lp.get("learning_path"):
        print("\nLearning path:")
    
        for step in lp["learning_path"]:
            print(f"\n{step['step_number']}. {step['source_course']}")
            print(f"   Material: {step['source_material_pdf']}")
            print(f"   {step['topic_name']}")
            print("   Weak subtopics:")

            for weak in step.get("weak_subtopics", []):
                print(f"   - {weak['subtopic_name']}")


if __name__ == "__main__":
    main()
