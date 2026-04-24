from __future__ import annotations

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import re
from pathlib import Path
from typing import Any

import chromadb
from openai import OpenAI
from chromadb.utils import embedding_functions


# =========================================================
# CONFIG
# =========================================================

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR = PROJECT_DIR / "courses"
QB_RESULTS_DIR = PROJECT_DIR / "question_bank_results"

MODEL_NAME = "gpt-5.4-nano"
MAX_COMPLETION_TOKENS = 2500

DIFFICULTY_DISTRIBUTION = {
    "easy": 0.30,
    "medium": 0.40,
    "hard": 0.30,
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in your environment.")

client = OpenAI(api_key=OPENAI_API_KEY)


# =========================================================
# HELPERS
# =========================================================

def safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).strip().lower()).strip("_")


def normalize_name(text: str) -> str:
    cleaned = re.sub(r"[_\-]+", " ", str(text).strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def extract_json_block(text: str):
    match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def ask_llm(prompt: str) -> str:
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
        temperature=0.5,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )
    return response.choices[0].message.content.strip()


def ask_llm_for_json(prompt: str, max_retries: int = 3):
    last_response = ""

    for _ in range(max_retries):
        raw = ask_llm(prompt)
        parsed = extract_json_block(raw)
        if parsed is not None:
            return parsed
        last_response = raw

    raise ValueError(f"LLM failed to return valid JSON.\nLast response:\n{last_response}")


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


def list_available_courses() -> list[dict]:
    courses = []
    for course_dir in get_course_folders(COURSES_DIR):
        courses.append({
            "course_name": course_dir.name,
            "normalized_name": normalize_name(course_dir.name),
        })
    return courses

def list_course_materials(target_course: str) -> list[str]:
    course_dir = COURSES_DIR / target_course
    materials = []

    for path in sorted(course_dir.glob("*.pdf")):
        if path.is_file():
            materials.append(path.name)

    return materials


def normalize_question_text(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def load_previous_qb_question_history(
    student_profile: dict | None,
    target_course: str,
    chapter_name: str,
) -> list[str]:
    save_path = get_question_bank_result_path(student_profile, target_course, chapter_name)

    if not save_path.exists():
        return []

    try:
        with open(save_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    history = data.get("question_history", [])
    if isinstance(history, list):
        return [str(q).strip() for q in history if str(q).strip()]

    old_questions = []
    for item in data.get("questions", []):
        q = str(item.get("question", "")).strip()
        if q:
            old_questions.append(q)

    seen = set()
    unique_questions = []
    for q in old_questions:
        nq = normalize_question_text(q)
        if nq and nq not in seen:
            seen.add(nq)
            unique_questions.append(q)

    return unique_questions


def deduplicate_question_history(question_texts: list[str]) -> list[str]:
    seen = set()
    unique_questions = []

    for q in question_texts:
        q = str(q).strip()
        if not q:
            continue

        nq = normalize_question_text(q)
        if nq in seen:
            continue

        seen.add(nq)
        unique_questions.append(q)

    return unique_questions

# =========================================================
# CHROMA HELPERS
# =========================================================

def get_chroma_client(chroma_dir: Path):
    return chromadb.PersistentClient(path=str(chroma_dir))


def get_embedding_function():
    return embedding_functions.DefaultEmbeddingFunction()


def get_collection(course_name: str, suffix: str):
    course_dir = COURSES_DIR / course_name
    chroma_dir = course_dir / "outputs" / "chroma_db"

    if not chroma_dir.exists():
        return None

    client_db = get_chroma_client(chroma_dir)
    embedding_function = get_embedding_function()
    collection_name = f"{safe_slug(course_name)}{suffix}"

    try:
        return client_db.get_collection(
            name=collection_name,
            embedding_function=embedding_function,
        )
    except Exception:
        return None


# =========================================================
# COURSE CONCEPTS / CHAPTERS
# =========================================================

def load_course_concepts_json(target_course: str) -> dict:
    concepts_path = COURSES_DIR / target_course / "outputs" / "chapter_concepts.json"

    if not concepts_path.exists():
        raise FileNotFoundError(f"chapter_concepts.json not found for course: {target_course}")

    with open(concepts_path, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_material_name(target_course: str, material_text: str) -> str | None:
    wanted = normalize_name(material_text)
    materials = list_course_materials(target_course)

    normalized_map = {normalize_name(m): m for m in materials}

    if wanted in normalized_map:
        return normalized_map[wanted]

    for norm_m, actual_m in normalized_map.items():
        if wanted == norm_m or wanted in norm_m or norm_m in wanted:
            return actual_m

    return None


def load_chapter_subtopics(target_course: str, chapter_name: str) -> list[dict]:
    concepts_data = load_course_concepts_json(target_course)
    rows = []
    seen = set()

    for relative_path, content in concepts_data.items():
        if Path(relative_path).name != chapter_name:
            continue

        chapter = str(content.get("chapter", "")).strip()

        for topic_idx, topic in enumerate(content.get("topics", [])):
            topic_name = str(topic.get("topic_name", "")).strip()
            subtopics = topic.get("subtopics", [])
            keywords = topic.get("keywords", [])

            if not topic_name:
                continue

            for subtopic_idx, subtopic_name in enumerate(subtopics):
                subtopic_name = str(subtopic_name).strip()
                if not subtopic_name:
                    continue

                dedup_key = (
                    normalize_name(topic_name),
                    normalize_name(subtopic_name),
                    chapter,
                    str(relative_path),
                )

                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                rows.append({
                    "course_name": target_course,
                    "relative_path": relative_path,
                    "chapter": chapter,
                    "topic_index": topic_idx,
                    "subtopic_index": subtopic_idx,
                    "topic_name": topic_name,
                    "subtopic_name": subtopic_name,
                    "keywords": keywords,
                })

    if not rows:
        raise ValueError(f"No subtopics found for course '{target_course}' in chapter '{chapter_name}'.")

    return rows


# =========================================================
# RETRIEVAL
# =========================================================

def retrieve_course_material(
    target_course: str,
    topic_name: str,
    subtopic_name: str,
    chapter_name: str,
    n_chunk_results: int = 6,
    n_summary_results: int = 2,
    n_concept_results: int = 3,
) -> dict[str, Any]:
    chunks_collection = get_collection(target_course, "_chunks")
    summaries_collection = get_collection(target_course, "_summaries")
    concepts_collection = get_collection(target_course, "_concepts")

    query_text = (
        f"Course: {target_course}\n"
        f"Chapter: {chapter_name}\n"
        f"Topic: {topic_name}\n"
        f"Subtopic: {subtopic_name}\n"
        f"Find the most relevant material for building a question bank question."
    )

    result = {
        "chunks": [],
        "summaries": [],
        "concepts": [],
    }

    if chunks_collection is not None:
        try:
            chunk_results = chunks_collection.query(
                query_texts=[query_text],
                n_results=n_chunk_results,
            )
            docs = chunk_results.get("documents", [[]])[0]
            metas = chunk_results.get("metadatas", [[]])[0]

            for doc, meta in zip(docs, metas):
                meta_relative_path = str(meta.get("relative_path", "")).strip()
                if chapter_name and Path(meta_relative_path).name != chapter_name:
                    continue
                result["chunks"].append({
                    "text": doc,
                    "metadata": meta,
                })
        except Exception:
            pass

    if summaries_collection is not None:
        try:
            summary_results = summaries_collection.query(
                query_texts=[query_text],
                n_results=n_summary_results,
            )
            docs = summary_results.get("documents", [[]])[0]
            metas = summary_results.get("metadatas", [[]])[0]

            for doc, meta in zip(docs, metas):
                meta_relative_path = str(meta.get("relative_path", "")).strip()
                if chapter_name and Path(meta_relative_path).name != chapter_name:
                    continue
                result["summaries"].append({
                    "text": doc,
                    "metadata": meta,
                })
        except Exception:
            pass

    if concepts_collection is not None:
        try:
            concept_results = concepts_collection.query(
                query_texts=[query_text],
                n_results=n_concept_results,
            )
            docs = concept_results.get("documents", [[]])[0]
            metas = concept_results.get("metadatas", [[]])[0]

            for doc, meta in zip(docs, metas):
                meta_relative_path = str(meta.get("relative_path", "")).strip()
                if chapter_name and Path(meta_relative_path).name != chapter_name:
                    continue
                result["concepts"].append({
                    "text": doc,
                    "metadata": meta,
                })
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
                f"[Concept {i}] "
                f"Topic: {meta.get('topic_name', '')}\n"
                f"File: {meta.get('relative_path', '')}\n"
                f"{item.get('text', '')}"
            )

    if retrieved["summaries"]:
        parts.append("\n=== SUMMARIES ===")
        for i, item in enumerate(retrieved["summaries"], start=1):
            meta = item.get("metadata", {})
            parts.append(
                f"[Summary {i}] "
                f"File: {meta.get('relative_path', '')}\n"
                f"{item.get('text', '')}"
            )

    if retrieved["chunks"]:
        parts.append("\n=== CHUNKS ===")
        for i, item in enumerate(retrieved["chunks"], start=1):
            meta = item.get("metadata", {})
            parts.append(
                f"[Chunk {i}] "
                f"File: {meta.get('relative_path', '')} | "
                f"Chapter: {meta.get('chapter', '')} | "
                f"Chunk ID: {meta.get('chunk_id', '')}\n"
                f"{item.get('text', '')}"
            )

    return "\n\n".join(parts).strip()


# =========================================================
# DIFFICULTY ASSIGNMENT
# =========================================================

def assign_difficulties_to_subtopics(subtopics: list[dict]) -> list[str]:
    total = len(subtopics)
    if total == 0:
        return []

    easy_count = round(total * DIFFICULTY_DISTRIBUTION["easy"])
    medium_count = round(total * DIFFICULTY_DISTRIBUTION["medium"])
    hard_count = total - easy_count - medium_count

    difficulties = (
        ["easy"] * easy_count +
        ["medium"] * medium_count +
        ["hard"] * hard_count
    )

    if len(difficulties) < total:
        difficulties.extend(["medium"] * (total - len(difficulties)))
    elif len(difficulties) > total:
        difficulties = difficulties[:total]

    return difficulties

def detect_code_in_context(context_text: str) -> bool:
    text = context_text.lower()

    strong_code_signals = [
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
        "from sklearn",
        "import pandas",
        "import numpy",
        "console.log(",
        "printf(",
        "return ",
        "{",
        "};",
    ]

    return any(signal in text for signal in strong_code_signals)

def choose_question_type(index: int, total: int, has_code: bool) -> str:
    if has_code:
        pattern = ["multiple_choice", "essay", "coding"]
    else:
        pattern = ["multiple_choice", "essay", "multiple_choice"]

    return pattern[index % len(pattern)]


# =========================================================
# QUESTION GENERATION
# =========================================================

def generate_question_for_subtopic(
    target_course: str,
    chapter_name: str,
    topic_name: str,
    subtopic_name: str,
    difficulty: str,
    context_text: str,
    required_question_type: str,
    banned_questions: list[str] | None = None,
) -> dict:
    banned_questions = banned_questions or []

    banned_block = ""
    if banned_questions:
        banned_preview = "\n".join(f"- {q}" for q in banned_questions[:200])
        banned_block = f"""

DO NOT REPEAT any of these previously generated questions for this student in this same course chapter:
{banned_preview}

If a new question is too similar in wording or meaning to any of the above, do NOT use it.
"""

    prompt = f"""
You are generating a question bank question for a university course.

IMPORTANT RULES:
- Use ONLY the provided course material.
- Do NOT use outside knowledge.
- Do NOT invent facts not supported by the context.
- Generate exactly 1 question for this subtopic.
- The question must clearly belong to the given subtopic.
- You MUST generate this exact question type: {required_question_type}

- If the question contains math, use valid LaTeX formatting.
- Wrap inline math with $...$.
- Wrap displayed equations with $$...$$.
- Use symbols like \sum, \lim, \infty (NOT plain text).
- Always escape LaTeX with double backslashes.
-Example: $\\sum_{{n=1}}^{{\\infty}} a_n$
-NOT: $\\sum_{{n=1}}^{{\\infty}} a_n$
- ALWAYS wrap math expressions with $...$
- NEVER output raw LaTeX like s_n or \sum without $
{banned_block}

Return JSON in this exact format:
{{
  "question_type": "{required_question_type}",
  "question": "...",
  "difficulty": "{difficulty}",
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

Rules for fields:
- If question_type = multiple_choice:
  - must include options A/B/C/D
  - must include correct_answer as A/B/C/D
  - answer_text can be empty
- If question_type = essay or coding:
  - options must be {{}}
  - correct_answer can be ""
  - answer_text must contain the model answer / expected answer
- explanation should always exist

Target course: {target_course}
Chapter: {chapter_name}
Topic: {topic_name}
Subtopic: {subtopic_name}
Required difficulty: {difficulty}
Required question type: {required_question_type}

COURSE MATERIAL:
{context_text[:14000]}
"""

    parsed = ask_llm_for_json(prompt)

    if not isinstance(parsed, dict):
        raise ValueError(f"LLM did not return a valid JSON object for subtopic: {subtopic_name}")

    question_type = str(parsed.get("question_type", "")).strip().lower()
    question = str(parsed.get("question", "")).strip()
    result_difficulty = str(parsed.get("difficulty", "")).strip().lower()
    options = parsed.get("options", {})
    correct_answer = str(parsed.get("correct_answer", "")).strip().upper()
    answer_text = str(parsed.get("answer_text", "")).strip()
    explanation = str(parsed.get("explanation", "")).strip()

    banned_normalized = {normalize_question_text(q) for q in banned_questions}

    if question_type not in {"multiple_choice", "essay", "coding"}:
        raise ValueError(f"Invalid question_type for subtopic: {subtopic_name}")

    if question_type != required_question_type:
        raise ValueError(
            f"Model returned wrong type '{question_type}' instead of '{required_question_type}' "
            f"for subtopic: {subtopic_name}"
        )

    if not question:
        raise ValueError(f"Empty question for subtopic: {subtopic_name}")

    if normalize_question_text(question) in banned_normalized:
        raise ValueError(f"Repeated old question detected for subtopic: {subtopic_name}")

    if result_difficulty not in {"easy", "medium", "hard"}:
        raise ValueError(f"Invalid difficulty for subtopic: {subtopic_name}")

    cleaned = {
        "question_type": question_type,
        "question": question,
        "difficulty": result_difficulty,
        "options": {},
        "correct_answer": "",
        "answer_text": answer_text,
        "explanation": explanation,
    }

    if question_type == "multiple_choice":
        if not isinstance(options, dict) or set(options.keys()) != {"A", "B", "C", "D"}:
            raise ValueError(f"Invalid multiple choice options for subtopic: {subtopic_name}")
        if correct_answer not in {"A", "B", "C", "D"}:
            raise ValueError(f"Invalid correct_answer for subtopic: {subtopic_name}")

        cleaned["options"] = {
            "A": str(options["A"]).strip(),
            "B": str(options["B"]).strip(),
            "C": str(options["C"]).strip(),
            "D": str(options["D"]).strip(),
        }
        cleaned["correct_answer"] = correct_answer

    else:
        cleaned["options"] = {}
        cleaned["correct_answer"] = ""
        if not cleaned["answer_text"]:
            raise ValueError(f"{question_type} question missing answer_text for subtopic: {subtopic_name}")

    return cleaned


# =========================================================
# QUESTION BANK BUILD
# =========================================================

def build_question_bank_questions(
    target_course: str,
    chapter_name: str,
    previous_question_history: list[str] | None = None,
) -> list[dict]:
    subtopics = load_chapter_subtopics(target_course, chapter_name)
    difficulties = assign_difficulties_to_subtopics(subtopics)

    previous_question_history = previous_question_history or []
    used_questions_this_attempt = {
        normalize_question_text(q) for q in previous_question_history
    }

    question_rows = []

    for idx, (item, difficulty) in enumerate(zip(subtopics, difficulties)):
        retrieved = retrieve_course_material(
            target_course=target_course,
            topic_name=item["topic_name"],
            subtopic_name=item["subtopic_name"],
            chapter_name=chapter_name,
        )

        context_text = build_context_text(retrieved)
        if not context_text.strip():
            continue

        has_code = detect_code_in_context(context_text)
        required_question_type = choose_question_type(
            index=idx,
            total=len(subtopics),
            has_code=has_code,
        )

        banned_questions_for_this_subtopic = list(previous_question_history)
        banned_questions_for_this_subtopic.extend(
            q["question"] for q in question_rows
        )

        try:
            generated = generate_question_for_subtopic(
                target_course=target_course,
                chapter_name=chapter_name,
                topic_name=item["topic_name"],
                subtopic_name=item["subtopic_name"],
                difficulty=difficulty,
                context_text=context_text,
                required_question_type=required_question_type,
                banned_questions=banned_questions_for_this_subtopic,
            )
        except Exception as e:
            print(f"Skipped subtopic '{item['subtopic_name']}': {e}")
            continue

        normalized_q = normalize_question_text(generated["question"])
        if normalized_q in used_questions_this_attempt:
            continue

        used_questions_this_attempt.add(normalized_q)

        question_rows.append({
            "course_name": target_course,
            "chapter": chapter_name,
            "relative_path": item["relative_path"],
            "topic_name": item["topic_name"],
            "subtopic_name": item["subtopic_name"],
            "question_type": generated["question_type"],
            "difficulty": generated["difficulty"],
            "question": generated["question"],
            "options": generated["options"],
            "correct_answer": generated["correct_answer"],
            "answer_text": generated["answer_text"],
            "explanation": generated["explanation"],
        })

    if not question_rows:
        raise ValueError("No question bank questions could be generated.")

    return question_rows


# =========================================================
# SAVE
# =========================================================

def get_question_bank_result_path(student_profile: dict | None, target_course: str, chapter_name: str) -> Path:
    student_part = "guest"
    if student_profile and student_profile.get("student_id"):
        student_part = safe_slug(student_profile["student_id"])

    filename = (
        f"qb_{student_part}_{safe_slug(target_course)}_{safe_slug(chapter_name)}.json"
    )
    return QB_RESULTS_DIR / filename


def save_question_bank_result(
    student_profile: dict | None,
    target_course: str,
    chapter_name: str,
    question_bank_payload: dict,
    question_history: list[str],
) -> Path:
    QB_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = get_question_bank_result_path(student_profile, target_course, chapter_name)

    question_bank_payload["question_history"] = deduplicate_question_history(question_history)

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(question_bank_payload, f, indent=2, ensure_ascii=False)

    return save_path


# =========================================================
# FRONTEND-FRIENDLY PUBLIC API
# =========================================================

def get_question_bank_dropdown_data() -> dict:
    data = {
        "courses": []
    }

    for course in list_available_courses():
        course_name = course["course_name"]
        try:
            materials = list_course_materials(course_name)
        except Exception:
            materials = []

        data["courses"].append({
            "course_name": course_name,
            "materials": materials,
        })

    return data


def get_chapters_for_course(course_name: str) -> dict:
    course_name_map = build_course_name_map()
    resolved_course = resolve_course_folder_name(course_name, course_name_map)

    if not resolved_course:
        raise ValueError(f"Could not match course: {course_name}")

    materials = list_course_materials(resolved_course)

    return {
        "course_name": resolved_course,
        "materials": materials,
    }


def generate_question_bank_for_student(
    student_profile: dict | None,
    target_course: str,
    chapter_name: str,
    save_result: bool = True,
) -> dict:
    course_name_map = build_course_name_map()
    resolved_target_course = resolve_course_folder_name(target_course, course_name_map)

    if not resolved_target_course:
        raise ValueError(f"Could not match target course: {target_course}")

    resolved_chapter = resolve_material_name(resolved_target_course, chapter_name)

    if not resolved_chapter:
        raise ValueError(
            f"Could not match slide file '{chapter_name}' in course '{resolved_target_course}'"
        )

    previous_question_history = load_previous_qb_question_history(
        student_profile=student_profile,
        target_course=resolved_target_course,
        chapter_name=resolved_chapter,
    )

    questions = build_question_bank_questions(
        target_course=resolved_target_course,
        chapter_name=resolved_chapter,
        previous_question_history=previous_question_history,
    )

    current_questions = [q["question"] for q in questions]
    full_question_history = deduplicate_question_history(
        previous_question_history + current_questions
    )

    payload = {
        "student_id": student_profile.get("student_id", "") if student_profile else "",
        "student_name": student_profile.get("student_name", "") if student_profile else "",
        "target_course": resolved_target_course,
        "chapter": resolved_chapter,
        "total_questions": len(questions),
        "questions": questions,
        "question_history": full_question_history,
    }

    if save_result:
        save_path = save_question_bank_result(
            student_profile=student_profile,
            target_course=resolved_target_course,
            chapter_name=resolved_chapter,
            question_bank_payload=payload,
            question_history=full_question_history,
        )
        payload["saved_result_path"] = str(save_path)

    return payload

def regenerate_question_bank_for_student(
    student_profile: dict | None,
    target_course: str,
    chapter_name: str,
    save_result: bool = True,
) -> dict:
    """
    Same as generate_question_bank_for_student, but intended for the frontend
    'Generate New Questions' button.
    Since question_history is loaded from the saved file, it will try to avoid
    repeating the old chapter questions.
    """
    return generate_question_bank_for_student(
        student_profile=student_profile,
        target_course=target_course,
        chapter_name=chapter_name,
        save_result=save_result,
    )


# =========================================================
# OPTIONAL TERMINAL TEST
# =========================================================

def main():
    print("=" * 70)
    print("MANARA - QUESTION BANK TEST MODE")
    print("=" * 70)

    course_name = input("Enter course name: ").strip()
    if not course_name:
        print("No course name entered.")
        return

    course_name_map = build_course_name_map()
    resolved_course = resolve_course_folder_name(course_name, course_name_map)

    if not resolved_course:
        print(f"Could not match course: {course_name}")
        return

    try:
        materials = list_course_materials(resolved_course)
    except Exception as e:
        print(e)
        return

    print("\nAvailable slide files:")
    for material in materials:
        print("-", material)

    material_name = input("\nEnter slide file name: ").strip()
    if not material_name:
        print("No slide file name entered.")
        return

    test_profile = {
        "student_id": "test_001",
        "student_name": "Test Student",
    }

    try:
        result = generate_question_bank_for_student(
            student_profile=test_profile,
            target_course=resolved_course,
            chapter_name=material_name,
            save_result=True,
        )
    except Exception as e:
        print(f"\nError: {e}")
        return

    print("\n" + "=" * 70)
    print("QUESTION BANK GENERATED")
    print("=" * 70)
    print("Course         :", result["target_course"])
    print("Selected file  :", result["chapter"])
    print("Total questions:", result["total_questions"])

    for idx, q in enumerate(result["questions"], start=1):
        print("\n" + "-" * 70)
        print(f"Question {idx}")
        print("Topic      :", q["topic_name"])
        print("Subtopic   :", q["subtopic_name"])
        print("Type       :", q["question_type"])
        print("Difficulty :", q["difficulty"])
        print("Question   :", q["question"])

        if q["question_type"] == "multiple_choice":
            print("A)", q["options"]["A"])
            print("B)", q["options"]["B"])
            print("C)", q["options"]["C"])
            print("D)", q["options"]["D"])
            print("Correct answer:", q["correct_answer"])
        else:
            print("Answer text:", q["answer_text"])

        print("Explanation:", q["explanation"])

    if "saved_result_path" in result:
        print("\nSaved result:")
        print(result["saved_result_path"])


if __name__ == "__main__":
    main()