from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

# Pydantic needs Sentinel and NoExtraItems from typing_extensions, but Anaconda ships
# an older version and was was missing both of them. The patch just creates them manually. 
#Pydantic/FastAPI use them internally — your project just ensures they exist so Pydantic doesn't crash on startup. 
#You never call them directly yourself.

def _patch_typing_extensions_for_pydantic_core() -> None:
    """Patch Anaconda typing_extensions drift before FastAPI imports Pydantic."""
    try:
        import typing_extensions
    except Exception:
        return

    if not hasattr(typing_extensions, "Sentinel"):
        class Sentinel:
            def __init__(self, name: str, /) -> None:
                self.__name__ = str(name)

            def __repr__(self) -> str:
                return self.__name__

            def __reduce__(self):
                return (Sentinel, (self.__name__,))

        typing_extensions.Sentinel = Sentinel
        if hasattr(typing_extensions, "__all__"):
            typing_extensions.__all__.append("Sentinel")

    if not hasattr(typing_extensions, "NoExtraItems"):
        typing_extensions.NoExtraItems = typing_extensions.Sentinel("NoExtraItems")
        if hasattr(typing_extensions, "__all__"):
            typing_extensions.__all__.append("NoExtraItems")


_patch_typing_extensions_for_pydantic_core()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  #allows react frontend to talk to the backend without the browser blocking it 
from pydantic import BaseModel

import csv
import json
import re as _re
import uuid as _uuid
import random as _random
from datetime import datetime
from collections import defaultdict as _defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from pdf import router as pdf_router
from knowledgegraph import (
    load_graph_for_frontend,
    graph_status,
    invalidate_graph_cache,
    build_knowledge_graph,
    OUTPUT_FILE as _KG_OUTPUT_FILE,
    COURSES_DIR as _KG_COURSES_DIR,
    get_courses_by_prerequisite_distance,
    get_prerequisite_chain,
    get_subtopics_for_course_via_graph,
    get_related_topics_for_course,
    get_semantically_related_subtopics,
    get_all_subtopics_globally,
)

# ---------------------------------------------------------
# project paths
# ---------------------------------------------------------
PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
if str(PROJECT_DIR) not in sys.path:
    sys.path.append(str(PROJECT_DIR))

STUDENT_ACCOUNTS_CSV = PROJECT_DIR / "data" / "students_accounts.csv"
LEARNING_PATHS_CSV   = PROJECT_DIR / "data" / "learning_paths.csv"
_DIAGNOSTIC_SAVE_DIR = PROJECT_DIR / "diagnostic_results"

# ---------------------------------------------------------
# imports from actual files
# ---------------------------------------------------------
from askcourse import ask_course_question

from studentprofile import (
    authenticate_student,
    accept_terms,
    update_phone_number,
    update_completed_courses,
    get_student_profile,
    update_last_active,
    load_study_plan,
)

from qb import (
    get_chapters_for_course,
    generate_question_bank_for_student,
)

try:
    from exam1 import (
        COURSES_DIR,
        get_course_folders,
        build_course_name_map,
        retrieve_course_material,
        build_context_text,
        generate_questions_for_subtopic,
        generate_questions_batch_for_diagnostic,
        build_semantic_diagnostic_clusters,
        retrieve_semantic_cluster_material,
        build_semantic_cluster_context,
        assess_cluster_educational_relevance,
        generate_questions_from_semantic_cluster,
        diagnostic_subtopic_key,
        diagnostic_subtopic_key_from_question,
        force_correct_answer_a,
        is_exam_concept_duplicate,
        classify_readiness_skill_family,
        validate_diagnostic_question_quality,
        is_fatal_openai_error_text,
        create_tracking_progress_from_learning_path,
        load_progress_for_student_and_course,
        generate_quiz_for_current_subtopic,
        submit_quiz_for_current_subtopic,
        delete_tracking_for_student_and_course,
    )
except ImportError as _e:
    raise RuntimeError(
        f"Failed to import from exam1.py: {_e}\n"
        "Check that exam1.py is present and has no syntax errors."
    ) from _e

from generate_exercises import exercise_router

# ---------------------------------------------------------
# app
# ---------------------------------------------------------
app = FastAPI(title="Manara API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_router, prefix="/api")
app.include_router(exercise_router)   # exercise_router already has prefix="/api"

# ---------------------------------------------------------
# request models
# ---------------------------------------------------------
class LoginRequest(BaseModel):
    student_id: str
    password: str

class TermsRequest(BaseModel):
    student_id: str
    accepted: bool

class PhoneRequest(BaseModel):
    student_id: str
    phone_number: str = ""
    whatsapp_opt_in: bool = False

class ProfileSetupRequest(BaseModel):
    student_id: str
    phone_number: str = ""
    courses_taken: list[str]

class Exam1GenerateRequest(BaseModel):
    student_id: str
    target_course: str

class SubmittedAnswer(BaseModel):
    question_id: str
    student_answer: str

class Exam1SubmitRequest(BaseModel):
    student_id: str
    target_course: str
    submitted_answers: list[SubmittedAnswer]

class LearningPathRequest(BaseModel):
    student_id: str
    graded_result_payload: dict[str, Any]

class ExerciseRequestItem(BaseModel):
    topic_name: str
    subtopic_name: str
    num_exercises: int

class Exam1ExercisesRequest(BaseModel):
    student_id: str
    target_course: str
    subtopic_requests: list[ExerciseRequestItem]

class AskCourseRequest(BaseModel):
    course_name: str
    question: str
    history: list[dict] = []
    student_id: str = ""   # optional — used to record streak activity

class QuestionBankGenerateRequest(BaseModel):
    course_name: str
    chapter_name: str

class TrackStartRequest(BaseModel):
    student_id: str
    learning_path_payload: dict[str, Any]

class TrackSubmittedAnswer(BaseModel):
    question_id: str
    student_answer: str

class TrackSubmitRequest(BaseModel):
    student_id: str
    target_course: str
    submitted_answers: list[TrackSubmittedAnswer]

# ---------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------
def load_students_from_csv() -> dict[str, dict[str, Any]]:
    students: dict[str, dict[str, Any]] = {}
    if not STUDENT_ACCOUNTS_CSV.exists():
        return students
    with open(STUDENT_ACCOUNTS_CSV, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = str(row.get("student_id", "")).strip()
            if not sid:
                continue
            students[sid] = {
                "student_id":     sid,
                "student_name":   str(row.get("student_name", "")).strip(),
                "password":       str(row.get("password", "")).strip(),
                "terms_accepted": str(row.get("terms_accepted", "False")).strip().lower() == "true",
                "phone_number":   str(row.get("phone_number", "")).strip(),
                "courses_taken":  [c.strip() for c in str(row.get("courses_taken", "")).split("|") if c.strip()],
            }
    return students

def save_students_to_csv(students: dict[str, dict[str, Any]]) -> None:
    fieldnames = ["student_id","student_name","password","terms_accepted","phone_number","courses_taken"]
    with open(STUDENT_ACCOUNTS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in students.values():
            writer.writerow({
                "student_id":    s.get("student_id", ""),
                "student_name":  s.get("student_name", ""),
                "password":      s.get("password", ""),
                "terms_accepted": str(s.get("terms_accepted", False)),
                "phone_number":  s.get("phone_number", ""),
                "courses_taken": "|".join(s.get("courses_taken", [])),
            })

def get_student(student_id: str) -> dict[str, Any] | None:
    return load_students_from_csv().get(student_id)

def update_student(student_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    students = load_students_from_csv()
    student  = students.get(student_id)
    if not student:
        return None
    student.update(updates)
    students[student_id] = student
    save_students_to_csv(students)
    return student

def load_learning_paths() -> list:
    paths = []
    if not LEARNING_PATHS_CSV.exists():
        return paths
    with open(LEARNING_PATHS_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            paths.append({
                "student_id":    row["student_id"],
                "target_course": row["target_course"],
                "path_data":     json.loads(row["path_data"]),
                "created_at":    row["created_at"],
            })
    return paths

def save_learning_paths(paths: list) -> None:
    fieldnames = ["student_id","target_course","path_data","created_at"]
    LEARNING_PATHS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(LEARNING_PATHS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in paths:
            writer.writerow({
                "student_id":    p["student_id"],
                "target_course": p["target_course"],
                "path_data":     json.dumps(p["path_data"]),
                "created_at":    p["created_at"],
            })

def save_learning_path_internal(student_id: str, path_data: dict) -> None:
    paths = load_learning_paths()
    new_path = {
        "student_id":    student_id,
        "target_course": path_data.get("target_course", ""),
        "path_data":     path_data,
        "created_at":    datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    paths = [p for p in paths
             if not (p["student_id"] == new_path["student_id"]
                     and p["target_course"] == new_path["target_course"])]
    paths.append(new_path)
    save_learning_paths(paths)

def build_exam1_profile(student_id: str) -> dict[str, Any]:
    student = get_student_profile(student_id) or get_student(student_id)
    if not student:
        raise ValueError(f"Student {student_id} not found.")
    return {
        "student_id":   student["student_id"],
        "student_name": student["student_name"],
        "courses_taken": student.get("courses_taken", []),
    }

# ---------------------------------------------------------
# diagnostic / path / progress  (built from exam1.py's API)
# ---------------------------------------------------------
SAMPLE_COURSES = [
    "Introduction to Computer Science",
    "Structured Programming",
    "Object Oriented Programming",
    "Data Structures and Introduction to Algorithms",
    "Database Systems",
]


def _dedupe_course_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    clean: list[str] = []
    for name in names:
        course = str(name).strip()
        key = course.casefold()
        if course and key not in seen:
            seen.add(key)
            clean.append(course)
    return sorted(clean, key=str.casefold)


def _course_names_from_folders() -> list[str]:
    return _dedupe_course_names([p.name for p in get_course_folders(COURSES_DIR)])


def _course_names_from_study_plan() -> list[str]:
    study_plan = load_study_plan()
    return _dedupe_course_names(list(study_plan.get("courses", {}).keys()))


def _seed_sample_course_folders() -> list[str]:
    COURSES_DIR.mkdir(parents=True, exist_ok=True)
    for course_name in SAMPLE_COURSES:
        course_dir = COURSES_DIR / course_name
        (course_dir / "metadata").mkdir(parents=True, exist_ok=True)
        course_info = course_dir / "metadata" / "course_info.json"
        if not course_info.exists():
            course_info.write_text(
                json.dumps(
                    {
                        "course_name": course_name,
                        "source": "auto_seeded_sample",
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
    return SAMPLE_COURSES


def get_available_courses() -> dict:
    sources_checked: list[str] = []
    try:
        courses = _course_names_from_folders()
        sources_checked.append(f"folders:{len(courses)}")
        source = "course_folders"

        if not courses:
            courses = _course_names_from_study_plan()
            sources_checked.append(f"study_plan:{len(courses)}")
            source = "study_plan"

        if not courses:
            courses = _dedupe_course_names(_seed_sample_course_folders())
            sources_checked.append(f"sample_seed:{len(courses)}")
            source = "sample_seed"

        print(
            "[COURSES API] /api/courses/all "
            f"source={source} count={len(courses)} checked={sources_checked}"
        )
        return {
            "success": True,
            "courses": courses,
            "count": len(courses),
            "source": source,
        }
    except Exception as exc:
        print(f"[COURSES API] Failed to load courses: {exc}")
        raise HTTPException(status_code=500, detail=f"Could not load courses: {exc}") from exc

def get_exam1_available_courses(student_profile: dict) -> dict:
    try:
        all_courses = get_available_courses().get("courses", [])
        taken       = set(student_profile.get("courses_taken", []))
        available   = [c for c in all_courses if c not in taken]
        return {"success": True, "available_target_courses": available}
    except Exception:
        return {"success": True, "available_target_courses": []}

def _collect_subtopics_from_taken_courses(courses_taken: list[str]) -> list[dict]:
    """
    Return all subtopics across the given courses.

    Strategy (graph-first with JSON fallback):
    1. If the knowledge graph is built, query it via get_subtopics_for_course_via_graph().
       This is fast (in-memory graph traversal, no disk I/O beyond first load).
    2. If the graph is not available for a course, fall back to reading
       chapter_concepts.json directly.  This ensures the diagnostic always
       works even before the graph has been built.
    """
    subtopics = []
    for course_name in courses_taken:
        graph_results = get_subtopics_for_course_via_graph(course_name)
        if graph_results:
            subtopics.extend(graph_results)
            continue

        # Fallback: read raw JSON (graph not built or course not in graph)
        concepts_file = COURSES_DIR / course_name / "outputs" / "chapter_concepts.json"
        if not concepts_file.exists():
            continue
        try:
            with open(concepts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        for rel_path, file_content in data.items():
            chapter = file_content.get("chapter", "")
            for topic in file_content.get("topics", []):
                topic_name = topic.get("topic_name", "").strip()
                for sub in topic.get("subtopics", []):
                    sub = sub.strip()
                    if topic_name and sub:
                        subtopics.append({
                            "course_name":   course_name,
                            "topic_name":    topic_name,
                            "subtopic_name": sub,
                            "chapter":       chapter,
                        })
    return subtopics


# ── Per-subtopic worker ───────────────────────────────────────────────────────

def _generate_diag_questions_for_subtopic(item: dict) -> list[dict]:
    """
    Worker function called in a thread pool by generate_diagnostic_exam.

    Retrieves ChromaDB context and generates exactly ONE question for the
    given subtopic using a single batch LLM call.  Returns [] on any
    failure so the pool can still collect results from other subtopics.

    Each question carries source_subtopic_name so that wrong answers can
    be traced back to their exact subtopic throughout the pipeline.

    The caller pre-assigns a difficulty_hint in the item dict so the
    overall exam has the correct 3-easy / 4-medium / 3-hard distribution.
    """
    try:
        retrieved = retrieve_course_material(
            course_name=item["course_name"],
            topic_name=item["topic_name"],
            subtopic_name=item["subtopic_name"],
        )
        context = build_context_text(retrieved)
        print(
            "[DIAG FALLBACK] retrieval "
            f"course={item.get('course_name')!r} topic={item.get('topic_name')!r} "
            f"subtopic={item.get('subtopic_name')!r} "
            f"chunks={len(retrieved.get('chunks', []))} "
            f"summaries={len(retrieved.get('summaries', []))} "
            f"concepts={len(retrieved.get('concepts', []))} "
            f"context_chars={len(context)}"
        )
        if not context.strip():
            print(f"[DIAG FALLBACK] empty context for subtopic={item.get('subtopic_name')!r}")
            return []

        # 1 question per subtopic — the caller pre-assigns the difficulty.
        # This guarantees 1 question = 1 unique subtopic throughout the pipeline.
        difficulty_hint = item.get("difficulty_hint", "medium")
        course_label = item["course_name"]
        if item.get("target_course"):
            course_label = f"{item['course_name']} as semantic prerequisite for {item['target_course']}"
        qs = generate_questions_batch_for_diagnostic(
            course_name=course_label,
            topic_name=item["topic_name"],
            subtopic_name=item["subtopic_name"],
            context_text=context,
            n_questions=1,
            difficulty_distribution={difficulty_hint: 1},
        )

        validated_qs = []
        for q in qs:
            is_valid, validation_reason, skill_family = validate_diagnostic_question_quality(q, context_text=context)
            if not is_valid:
                print(
                    "[DIAG QUALITY] rejected fallback question "
                    f"subtopic={item.get('subtopic_name')!r} reason={validation_reason} "
                    f"question={str(q.get('question', ''))[:90]!r}"
                )
                continue
            q["readiness_skill_family"] = skill_family or ""
            validated_qs.append(q)
        qs = validated_qs

        for q in qs:
            q["source_topic_name"]    = item["topic_name"]
            q["source_subtopic_name"] = item["subtopic_name"]   # CRITICAL: subtopic mapping
            q["source_course"]        = item["course_name"]
            q["source_subtopic_key"] = "|".join(
                diagnostic_subtopic_key(
                    item["course_name"],
                    item["topic_name"],
                    item["subtopic_name"],
                )
            )
            q["diagnostic_target_course"] = item.get("target_course", "")
            q["semantic_score"] = item.get("semantic_score", 0)
            q["semantic_link_count"] = item.get("semantic_link_count", 0)
            q["related_target_subtopics"] = item.get("related_target_subtopics", [])

        print(
            "[DIAG FALLBACK] generated "
            f"subtopic={item.get('subtopic_name')!r} count={len(qs)}"
        )
        return qs

    except Exception as e:
        print(f"[DIAG FALLBACK] exception subtopic='{item.get('subtopic_name', '?')}': {type(e).__name__}: {e}")
        if is_fatal_openai_error_text(str(e)):
            raise
        return []


def _generate_diag_questions_for_semantic_cluster(cluster: dict) -> list[dict]:
    """
    Worker for Manara's semantic diagnostic engine.

    Pipeline:
      1. Retrieve slide material from ChromaDB (chunks + summaries + concepts)
      2. Educational relevance filter — LLM rates content HIGH/MEDIUM/LOW.
         LOW-rated clusters may attempt one lightweight prerequisite check,
         but the deterministic quality gate still rejects toy syntax / trivia.
      3. Generate 1–3 grounded questions from approved material; count depends on rating:
           HIGH   → 3 questions (conceptual, application, reasoning)
           MEDIUM → 2 questions (understanding, application/reasoning)
           LOW    → 1 guarded easy question attempt
      4. HIGH clusters regenerate weak output up to 3 attempts; MEDIUM/LOW may
         naturally shrink when validators reject weak questions.
      5. Fallback: if semantic generation produces nothing, try subtopic batch generator.
    """
    max_regen_attempts = 3

    def _low_cluster_should_generate_question(reason: str, context: str) -> bool:
        """LOW means weak signal, not always zero signal.

        Keep one guarded question only for weak-but-conceptual prerequisites
        such as classification basics, mathematical reasoning, or search
        intuition. Skip LOW clusters that are primarily syntax, boilerplate,
        terminology, or beginner programming recall.
        """
        low_signal = " ".join(
            [
                str(cluster.get("primary_source_course", "")),
                str(cluster.get("primary_topic_name", "")),
                str(cluster.get("primary_subtopic_name", "")),
                str(reason),
                context[:1600],
            ]
        ).lower()
        conceptual_low_patterns = [
            r"\bclassification\b",
            r"\bmathematical reasoning\b|\bmath reasoning\b|\bprobability\b|\blinear algebra\b",
            r"\bsearch intuition\b|\bsearch reasoning\b|\bsequential search\b|\blinear search\b|\bheuristic\b",
        ]
        trivial_low_patterns = [
            r"\bsyntax\b|\bboilerplate\b|\bapi trivia\b|\bapi syntax\b",
            r"\bobject instantiation\b|\binstantiation syntax\b|\bclass creation\b|\bclass syntax\b",
            r"\bvariable declaration\b|\bassignment statement\b|\bprint statement\b",
            r"\bdatabase terminology\b|\bdatabase definitions?\b|\bbasic definitions?\b|\bwhat is a database\b",
            r"\bcontrol-flow basics?\b|\bif statements?\b|\bcondition is false\b|\bsimple boolean\b|\bboolean recall\b",
            r"\binput/output\b|\binput[, ]+processing[, ]+(and )?output\b|\bprograms typically\b",
            r"\bmemorization-only\b|\bmemorisation-only\b|\brecall-only\b|\bdefinition recall\b|\bterminology recall\b",
        ]
        if any(_re.search(pattern, low_signal) for pattern in conceptual_low_patterns):
            return True
        if any(_re.search(pattern, low_signal) for pattern in trivial_low_patterns):
            return False
        return True

    try:
        retrieved = retrieve_semantic_cluster_material(cluster)
        retrieval_sizes = {k: len(v) for k, v in retrieved.items()}

        # Build context text once — reused for both the relevance filter and question generation.
        context_text = ""
        try:
            context_text = build_semantic_cluster_context(cluster, retrieved)
        except Exception as ctx_exc:
            print(f"[DIAG WORKER] context build error cluster={cluster.get('cluster_id')}: {ctx_exc}")

        print(
            "[DIAG WORKER] semantic start "
            f"cluster={cluster.get('cluster_id')} "
            f"retrieval_sizes={retrieval_sizes} context_chars={len(context_text)}"
        )

        # ── Stage 2: Educational relevance filter ────────────────────────────
        # Rating determines question density. LOW clusters are no longer hard
        # dropped here: some weak semantic links still contain one useful
        # prerequisite readiness check. The downstream quality gate remains
        # strict and rejects toy syntax / definition-only questions.
        rel_rating = "LOW"
        if context_text.strip():
            rel_rating, rel_reason = assess_cluster_educational_relevance(cluster, context_text)
            print(
                f"[DIAG RELEVANCE] Course: {cluster.get('primary_source_course', '?')} | "
                f"Topic: {cluster.get('primary_topic_name', '?')} | "
                f"Subtopic: {cluster.get('primary_subtopic_name', '?')} | "
                f"Decision: {rel_rating} | "
                f"Reason: {rel_reason}"
            )
        else:
            print(
                f"[DIAG RELEVANCE] Course: {cluster.get('primary_source_course', '?')} | "
                f"Subtopic: {cluster.get('primary_subtopic_name', '?')} | "
                f"Decision: SKIP (empty context)"
            )
            return []

        # ── Stage 3: Generate questions from approved material ────────────────
        # HIGH → 3 questions covering conceptual, application, reasoning angles.
        # MEDIUM → 2 questions covering understanding and application/reasoning.
        # LOW → 1 only for weak-but-conceptual prerequisites; syntax/trivia
        # LOW clusters produce zero questions.
        if rel_rating == "HIGH":
            n_per_cluster = 3
            diff_dist = {"easy": 1, "medium": 1, "hard": 1}
        elif rel_rating == "MEDIUM":
            n_per_cluster = 2
            diff_dist = {"medium": 1, "hard": 1}
        else:
            if not _low_cluster_should_generate_question(rel_reason, context_text):
                print(
                    "[DIAG RELEVANCE] LOW cluster skipped as trivia/recall "
                    f"cluster={cluster.get('cluster_id')} "
                    f"source={cluster.get('primary_source_course', '?')}/"
                    f"{cluster.get('primary_subtopic_name', '?')} "
                    f"reason={rel_reason}"
                )
                return []
            n_per_cluster = 1
            diff_dist = {"easy": 1}
            print(
                "[DIAG RELEVANCE] LOW cluster allowed one guarded fallback attempt "
                f"cluster={cluster.get('cluster_id')} "
                f"source={cluster.get('primary_source_course', '?')}/"
                f"{cluster.get('primary_subtopic_name', '?')}"
            )

        # Store rating on cluster so selection loop can use it for priority sorting.
        cluster["_rel_rating"] = rel_rating

        qs: list[dict] = []
        attempts = max_regen_attempts if rel_rating == "HIGH" else 1
        for attempt in range(1, attempts + 1):
            batch = generate_questions_from_semantic_cluster(
                semantic_cluster=cluster,
                n_questions=n_per_cluster,
                difficulty_distribution=diff_dist,
            )
            if batch:
                existing_signatures = {
                    (str(q.get("question", "")).strip().lower(), str(q.get("correct_answer", "")).strip())
                    for q in qs
                }
                for q in batch:
                    sig = (
                        str(q.get("question", "")).strip().lower(),
                        str(q.get("correct_answer", "")).strip(),
                    )
                    if sig not in existing_signatures:
                        qs.append(q)
                        existing_signatures.add(sig)
                    if len(qs) >= n_per_cluster:
                        break
            if len(qs) >= n_per_cluster or rel_rating != "HIGH":
                break
            print(
                "[DIAG REGEN] HIGH cluster under-produced; retrying "
                f"cluster={cluster.get('cluster_id')} attempt={attempt + 1}/{attempts} "
                f"produced={len(qs)} target={n_per_cluster}"
            )
        qs = qs[:n_per_cluster]
        for idx, q in enumerate(qs, start=1):
            q["semantic_relevance_rating"] = rel_rating
            q["subtopic_question_position"] = idx
        print(f"[DIAG WORKER] semantic result cluster={cluster.get('cluster_id')} rating={rel_rating} requested={n_per_cluster} produced={len(qs)}")
        if qs:
            return qs

        # ── Stage 4: Fallback (subtopic batch generator) ─────────────────────
        # Only trigger if retrieval found something — no point falling back to
        # the same empty ChromaDB for a subtopic that already returned nothing.
        if any(retrieval_sizes.values()):
            fallback_item = {
                "course_name": cluster.get("primary_source_course", ""),
                "topic_name": cluster.get("primary_topic_name", ""),
                "subtopic_name": cluster.get("primary_subtopic_name", ""),
                "target_course": cluster.get("target_course", ""),
                "semantic_score": cluster.get("semantic_score", 0),
                "semantic_link_count": cluster.get("semantic_link_count", 0),
                "related_target_subtopics": cluster.get("target_subtopics", []),
                "difficulty_hint": "medium",
            }
            print(
                "[DIAG WORKER] semantic empty; falling back to subtopic "
                f"cluster={cluster.get('cluster_id')} "
                f"fallback={fallback_item.get('course_name')!r}/{fallback_item.get('subtopic_name')!r}"
            )
            fallback_qs = _generate_diag_questions_for_subtopic(fallback_item)
            print(
                "[DIAG WORKER] fallback result "
                f"cluster={cluster.get('cluster_id')} count={len(fallback_qs)}"
            )
            return fallback_qs

        return []
    except Exception as e:
        if is_fatal_openai_error_text(str(e)):
            raise
        print(f"[DIAG WORKER] exception cluster='{cluster.get('cluster_id', '?')}': {type(e).__name__}: {e}")
        return []


def _select_semantically_diverse_subtopics(
    all_subtopics: list[dict],
    n: int = 10,
) -> list[dict]:
    """
    Select up to `n` subtopics from `all_subtopics`.

    When semantic scores are present, this is strongest-first with a soft
    per-course cap.  That keeps the diagnostic focused on high-confidence
    prerequisite evidence while still preventing a single completed course from
    monopolising the exam.

    When semantic scores are unavailable, it falls back to the older round-robin
    strategy across courses, giving a broad completed-course sample.

    Why round-robin for fallback instead of random or prerequisite-sorted:
      - Random: may accidentally draw 8 subtopics from one course, skewing
        the diagnostic toward that course and missing broader weaknesses.
      - Prerequisite-sorted: biases toward foundational courses and ignores
        the student's actual enrolled course, violating the design principle
        that prerequisites are metadata only, not the primary intelligence.
      - Round-robin: guarantees at most ceil(n / num_courses) subtopics per
        course, ensuring the exam samples breadth across the full curriculum.

    Within each fallback course the subtopics are shuffled so repeated calls
    return different orderings.

    Returns at most `n` deduplicated (course_name, subtopic_name) items.
    """
    if not all_subtopics:
        return []

    # Group by course, shuffle within each group
    from collections import defaultdict as _dd
    by_course: dict[str, list[dict]] = _dd(list)
    for item in all_subtopics:
        by_course[item["course_name"]].append(item)

    semantic_ranked = any("semantic_score" in item for item in all_subtopics)
    if semantic_ranked:
        ranked = sorted(
            all_subtopics,
            key=lambda x: (
                x.get("semantic_score", 0),
                x.get("semantic_link_count", 0),
                -x.get("semantic_avg_distance", 1),
            ),
            reverse=True,
        )
        max_score = ranked[0].get("semantic_score", 0) if ranked else 0
        # Prefer high-confidence edges. If there are not enough, gracefully
        # widen the pool so the API can still generate a full diagnostic.
        confidence_floor = max(0.25, max_score * 0.55)
        preferred_pool = [
            item for item in ranked
            if item.get("semantic_score", 0) >= confidence_floor
        ]
        pool = preferred_pool if len(preferred_pool) >= n else ranked

        selected: list[dict] = []
        seen_keys: set[tuple[str, str]] = set()
        course_counts: dict[str, int] = _defaultdict(int)
        per_course_cap = max(2, int(n * 0.6))

        def add_candidate(item: dict, enforce_cap: bool) -> bool:
            key = (item["course_name"], item["subtopic_name"])
            if key in seen_keys:
                return False
            if enforce_cap and course_counts[item["course_name"]] >= per_course_cap:
                return False
            seen_keys.add(key)
            course_counts[item["course_name"]] += 1
            selected.append(item)
            return True

        for item in pool:
            if len(selected) >= n:
                break
            add_candidate(item, enforce_cap=True)

        for item in ranked:
            if len(selected) >= n:
                break
            add_candidate(item, enforce_cap=False)

        print(
            "[DIAG] Semantic subtopic selection "
            f"input={len(all_subtopics)} preferred={len(preferred_pool)} "
            f"selected={len(selected)} course_counts={dict(course_counts)}"
        )
        return selected

    for course_items in by_course.values():
        _random.shuffle(course_items)

    # Round-robin across courses until we have n or run out
    courses = list(by_course.keys())
    _random.shuffle(courses)          # randomise course order each call
    cursors  = {c: 0 for c in courses}
    selected: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()

    while len(selected) < n:
        advanced = False
        for course in courses:
            if len(selected) >= n:
                break
            idx = cursors[course]
            pool = by_course[course]
            if idx >= len(pool):
                continue
            cursors[course] += 1
            item = pool[idx]
            key  = (item["course_name"], item["subtopic_name"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            selected.append(item)
            advanced = True
        if not advanced:
            break   # all pools exhausted

    return selected


def normalize_readiness_family(
    question: dict,
    source_topic: str = "",
    source_subtopic: str = "",
    target_course: str = "",
) -> str:
    """Map raw readiness labels and text into course-independent families."""
    text = " ".join(
        [
            str(question.get("question", "")),
            str(question.get("explanation", "")),
            str(question.get("readiness_skill_family", "")),
            str(source_topic or question.get("source_topic_name", "")),
            str(source_subtopic or question.get("source_subtopic_name", "")),
            str(target_course or question.get("diagnostic_target_course", "")),
        ]
    ).lower()

    family_rules: list[tuple[str, list[str]]] = [
        (
            "PROGRAMMING_SYNTAX_OR_TRIVIA",
            [
                r"\b(object instantiation|instantiate an object|constructor syntax|class syntax|class creation)\b",
                r"\b(variable syntax|variable declaration|declare a variable|assignment statement)\b",
                r"\b(print statement|what is printed|what will be output|boilerplate|api syntax|method call syntax)\b",
                r"\b(input[- /]?processing[- /]?output|input/output|simple if|if statement output|condition is false)\b",
            ],
        ),
        (
            "RECURSION_FOUNDATION",
            [
                r"\b(recursion|recursive|base case|recursive call|call stack|factorial|fibonacci)\b",
                r"\brecursive arrays?|recursive functions?|recursion tracing\b",
            ],
        ),
        (
            "SEARCH_AND_HALVING",
            [
                r"\b(binary search|halving|halve|search[- ]space reduction|logarithmic comparisons?)\b",
                r"\bdivide[- ]and[- ]conquer|heavy[- ]box|search complexity|best[- ]first search\b",
            ],
        ),
        (
            "SORTING_ALGORITHMS",
            [
                r"\b(selection sort|bubble sort|insertion sort|merge sort|quick ?sort)\b",
                r"\b(radix sort|counting sort|bucket sort|sorting suitability|sorting complexity)\b",
            ],
        ),
        (
            "GRAPH_REASONING",
            [
                r"\b(graph degree|adjacency matrix|adjacency list|graph representation|graph traversal)\b",
                r"\b(nodes?|edges?|vertices|dfs|bfs)\b",
            ],
        ),
        (
            "LOGIC_INFERENCE",
            [
                r"\b(modus ponens|modus tollens|hypothetical syllogism|disjunctive syllogism)\b",
                r"\b(logical premises?|logical conclusions?|inference chain|derive conclusions?)\b",
            ],
        ),
        (
            "DATA_MODELING",
            [
                r"\b(database schema|database instance|data model|entities|relationships|constraints)\b",
                r"\b(schema design|relational model|normalization|entity relationship|er diagram)\b",
            ],
        ),
        (
            "CLASSIFICATION_AND_ML_FOUNDATION",
            [
                r"\b(classification|labeled data|labelled data|supervised prediction|learning from data)\b",
                r"\b(classical algorithms? vs|machine learning|examples of faces|training examples?)\b",
            ],
        ),
    ]
    for family, patterns in family_rules:
        if any(_re.search(pattern, text) for pattern in patterns):
            return family

    raw_family = str(question.get("readiness_skill_family", "")).strip().upper()
    return raw_family or "UNCLASSIFIED"


def generate_diagnostic_exam(
    student_profile: dict,
    target_course: str,
    save_result: bool = True,
) -> dict:
    """
    Generate an adaptive personalised diagnostic exam.

    Architecture: semantic prerequisite graph × closeness-weighted questions
    ─────────────────────────────────────────────────────
    In the primary path, exam1.py builds semantic prerequisite clusters from
    related_subtopics.csv / KG output, retrieves multi-course prerequisite
    material, and generates 1–3 readiness questions per cluster. Each question
    still maps back to a primary completed-course subtopic so weak-subtopic
    tracking and learning paths remain stable.

    Speed strategy (maintained from previous optimisation):
    1. PARALLEL generation via ThreadPoolExecutor.
       All selected semantic prerequisite clusters are processed. LLM calls overlap.

    2. CLOSENESS-WEIGHTED allocation:
       HIGH → 3 questions, MEDIUM → 2 questions, LOW → 1 guarded question.

    3. SEMANTIC GRAPH expansion — target-course relationships are resolved
       before retrieval.  Questions are generated from completed-course
       semantic clusters related to the target course.

    4. CACHED ChromaDB clients — no re-opening per call.

    5. ADAPTIVE LENGTH — final size emerges from prerequisite complexity,
       with 40 as the only global hard cap.
    """
    courses_taken = student_profile.get("courses_taken", [])
    if not courses_taken:
        raise ValueError("No completed courses found. Cannot generate diagnostic exam.")

    semantic_clusters = build_semantic_diagnostic_clusters(
        target_course=target_course,
        completed_courses=courses_taken,
        max_clusters=40,
        max_related_subtopics=80,
    )
    print(
        "[DIAG] semantic clusters "
        f"student={student_profile.get('student_id')} target={target_course!r} "
        f"completed_courses={len(courses_taken)} count={len(semantic_clusters)}"
    )

    if semantic_clusters:
        # Pass all selected semantic prerequisite clusters to generation. The
        # relevance filter determines how many questions each subtopic deserves:
        # HIGH=3, MEDIUM=2, LOW=1 guarded attempt.
        candidate_clusters = semantic_clusters
        sampling_mode = "semantic_prerequisite_readiness"
        adaptive_question_cap = 40
    else:
        # Fallback only when semantic links are unavailable for this target or
        # the graph/CSV has not been generated. This preserves the existing API
        # behavior without pretending random completed-course sampling is the
        # primary architecture.
        candidate_subtopics = _collect_subtopics_from_taken_courses(courses_taken)
        sampling_mode = "completed_course_fallback"
        adaptive_question_cap = 40

    if sampling_mode == "semantic_prerequisite_readiness":
        candidates_count = len(candidate_clusters)
        # All clusters pass to generation — difficulty is derived per-cluster
        # inside the worker based on relevance rating (HIGH→easy/medium/hard,
        # MEDIUM→medium/hard).
        deduped = list(candidate_clusters)
    else:
        candidates_count = len(candidate_subtopics)
        deduped = _select_semantically_diverse_subtopics(candidate_subtopics, n=adaptive_question_cap)

    if not deduped:
        raise ValueError(
            "No course material found for your completed courses. "
            "Please ensure course data is loaded."
        )

    print(
        "[DIAG] Diagnostic sampling "
        f"student={student_profile.get('student_id')} target={target_course!r} "
        f"mode={sampling_mode} candidates={candidates_count} clusters_to_generate={len(deduped)}"
    )

    # For fallback path only: assign a light difficulty spread across available
    # subtopics. The semantic path derives difficulty from closeness-weighted
    # cluster generation, not from a fixed exam quota.
    if sampling_mode == "completed_course_fallback":
        fallback_count = min(adaptive_question_cap, len(deduped))
        n_easy = max(1, fallback_count * 3 // 10)
        n_hard = max(1, fallback_count * 3 // 10)
        n_medium = fallback_count - n_easy - n_hard
        diag_difficulties = ["easy"] * n_easy + ["medium"] * n_medium + ["hard"] * n_hard
        _random.shuffle(diag_difficulties)
        sampled: list[dict] = []
        for item, diff in zip(deduped, diag_difficulties):
            sampled.append({**item, "difficulty_hint": diff})
    else:
        # Semantic path: clusters carry no pre-assigned difficulty; worker handles it.
        sampled = list(deduped)

    print(
        "[DIAG] sampled units "
        f"mode={sampling_mode} sampled={len(sampled)} "
        f"labels={[item.get('cluster_id') or item.get('subtopic_name') for item in sampled]}"
    )

    if not sampled:
        raise ValueError("No unique subtopics available to sample. Check course data.")

    # ── Parallel generation — one LLM call per subtopic ──────────────────────
    # max_workers=10 so all subtopics run simultaneously regardless of count.
    all_questions: list[dict] = []
    worker_errors: list[str] = []
    worker = (
        _generate_diag_questions_for_semantic_cluster
        if sampling_mode == "semantic_prerequisite_readiness"
        else _generate_diag_questions_for_subtopic
    )

    with ThreadPoolExecutor(max_workers=min(30, len(sampled))) as pool:
        futures = {pool.submit(worker, item): item for item in sampled}
        for future in as_completed(futures):
            try:
                qs = future.result(timeout=90)
                item = futures[future]
                label = item.get("cluster_id") or item.get("subtopic_name", "?")
                print(f"[DIAG] worker completed label={label} question_count={len(qs)}")
                if not qs:
                    worker_errors.append(f"Worker returned 0 questions for {label}")
                all_questions.extend(qs)
            except Exception as e:
                item = futures[future]
                label = item.get("cluster_id") or item.get("subtopic_name", "?")
                err_msg = str(e)
                worker_errors.append(err_msg)
                print(f"[DIAG] Thread failed for '{label}': {err_msg}")

    print(
        "[DIAG] worker aggregate "
        f"mode={sampling_mode} total_questions={len(all_questions)} "
        f"errors={len(worker_errors)}"
    )

    if not all_questions:
        if worker_errors:
            fatal_errors = [e for e in worker_errors if is_fatal_openai_error_text(e)]
            if fatal_errors:
                raise ValueError(fatal_errors[0])
            raise ValueError(
                "Could not generate questions. Semantic retrieval completed, "
                f"but question generation returned no valid questions. First error: {worker_errors[0]}"
            )
        raise ValueError("Could not generate questions. Check that course materials are loaded.")

    # ── Final coverage guards ─────────────────────────────────────────────────
    #
    # Guard 0: deterministic quality validation rejects invalid logic, invalid
    #           algorithm assumptions, weak hard questions, and grounding drift.
    # Guard 1: per prerequisite subtopic, allow the closeness allocation:
    #          HIGH=3, MEDIUM=2, LOW=1, while rejecting repeated cognitive angle.
    # Guard 3:  concept-level dedup — (question + answer) text similarity.
    #           Unchanged; catches same learning objective from different clusters.
    # Guard 4: adaptive skill-family balancing. A normalized readiness family
    #          can occupy at most ~20% of the selected exam, minimum cap 3.
    #
    # Breadth-first ordering: sort all questions by subtopic_question_position
    # (1=conceptual, 2=application, 3=reasoning) BEFORE grouping by course.
    # This ensures the round-robin loop processes all Q1s first, then Q2s, then
    # Q3s — so every subtopic gets at least one question before any subtopic
    # gets a second question. Prerequisite coverage is always maximised first.
    #
    # Final total cap: 40 questions. There is no fixed target count; exam size
    # emerges from semantic prerequisite graph complexity and quality filtering.
    #
    effective_cap = adaptive_question_cap

    # Sort by closeness first so the 40-question hard cap, when needed, keeps
    # HIGH relationships before MEDIUM and LOW while still preferring breadth
    # before second/third questions within the same closeness tier.
    rating_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_questions.sort(key=lambda q: (
        rating_rank.get(str(q.get("semantic_relevance_rating", "")).upper(), 1),
        q.get("subtopic_question_position", 1),
        {"hard": 0, "medium": 1, "easy": 2}.get(str(q.get("difficulty", "medium")).lower(), 1),
        -float(q.get("semantic_score", 0)),
    ))

    selected: list[dict] = []
    subtopic_key_counts: dict[tuple[str, str, str], int] = _defaultdict(int)
    subtopic_name_counts: dict[str, int] = _defaultdict(int)
    family_counts: dict[tuple[str, str], int] = _defaultdict(int)
    course_question_counts: dict[str, int] = _defaultdict(int)
    skill_family_counts: dict[str, int] = _defaultdict(int)  # Guard 4
    family_balance_counts: dict[str, int] = _defaultdict(int)
    subtopic_skill_families: dict[tuple[str, str, str], set[str]] = _defaultdict(set)
    subtopic_question_angles: dict[tuple[str, str, str], set[int]] = _defaultdict(set)
    reduction_family_count = 0
    difficulty_counts: dict[str, int] = _defaultdict(int)
    rejected_subtopic_cap = 0
    rejected_family_cap = 0
    rejected_course_cap = 0
    rejected_concept_dup = 0
    rejected_skill_family = 0
    rejected_quality = 0
    rejected_reduction_family = 0
    rejected_angle_dup = 0
    rejected_logic_invalid = 0
    rejected_syntax_trivia = 0

    final_candidate_count = min(effective_cap, len(all_questions))
    adaptive_skill_family_cap = max(3, round(final_candidate_count * 0.18))
    syntax_trivia_cap = max(1, round(final_candidate_count * 0.05))

    def _max_questions_for_closeness(q: dict) -> int:
        rating = str(q.get("semantic_relevance_rating", "")).strip().upper()
        if rating == "HIGH":
            return 3
        if rating == "MEDIUM":
            return 2
        return 1

    def _syntax_trivia_allowed(q: dict) -> bool:
        signal = " ".join(
            [
                str(q.get("diagnostic_target_course", "")),
                str(q.get("source_course", "")),
                str(q.get("source_topic_name", "")),
                str(q.get("source_subtopic_name", "")),
            ]
        ).lower()
        intro_programming_signal = (
            any(term in signal for term in ("programming", "coding", "computer science"))
            and any(term in signal for term in ("intro", "introduction", "fundamental", "beginner", "basic"))
        )
        direct_skill_signal = any(
            term in signal
            for term in ("syntax", "class", "object", "variable", "control structure", "input", "output")
        )
        return intro_programming_signal and direct_skill_signal

    def _record_accepted(q: dict, key: tuple[str, str, str], subtopic_norm: str, fam_key: tuple[str, str], course_key_lower: str, q_skill_family: str) -> None:
        nonlocal reduction_family_count
        subtopic_key_counts[key] += 1
        if subtopic_norm:
            subtopic_name_counts[subtopic_norm] += 1
        if fam_key[0] and fam_key[1]:
            family_counts[fam_key] += 1
        if course_key_lower:
            course_question_counts[course_key_lower] += 1
        diff = str(q.get("difficulty", "medium")).strip().lower()
        if diff not in {"easy", "medium", "hard"}:
            diff = "medium"
            q["difficulty"] = diff
        difficulty_counts[diff] += 1
        balanced_family = normalize_readiness_family(q, q.get("source_topic_name", ""), q.get("source_subtopic_name", ""), q.get("diagnostic_target_course", ""))
        family_balance_counts[balanced_family] += 1
        q["normalized_readiness_family"] = balanced_family
        q["balanced_readiness_family"] = balanced_family
        if q_skill_family:
            skill_family_counts[q_skill_family] += 1
            subtopic_skill_families[key].add(q_skill_family)
            q["readiness_skill_family"] = q_skill_family
            if balanced_family == "SEARCH_AND_HALVING":
                reduction_family_count += 1
        try:
            angle = int(q.get("subtopic_question_position", 1))
        except Exception:
            angle = 1
        subtopic_question_angles[key].add(angle)

    def _is_redundant_candidate(q: dict, q_text: str, q_answer: str, q_skill_family: str) -> bool:
        """
        Concept dedup should block repeated readiness skills, not broad academic
        coverage that merely uses a similar question template.

        The text-level duplicate detector is intentionally conservative, so this
        wrapper only treats a candidate as redundant when the similar existing
        question also overlaps by subtopic key, exact readiness family, or the
        shared halving/search-space reduction super-family.
        """
        if not selected or not is_exam_concept_duplicate(q_text, q_answer, selected):
            return False

        q_key = diagnostic_subtopic_key_from_question(q)
        try:
            q_angle = int(q.get("subtopic_question_position", 1))
        except Exception:
            q_angle = 1
        for existing in selected:
            existing_key = diagnostic_subtopic_key_from_question(existing)
            existing_family = str(existing.get("readiness_skill_family") or "")
            try:
                existing_angle = int(existing.get("subtopic_question_position", 1))
            except Exception:
                existing_angle = 1
            if existing_key == q_key:
                return existing_angle == q_angle or (q_skill_family and existing_family == q_skill_family)
        return False

    # Group by course — do NOT shuffle within course, to preserve position ordering.
    questions_by_course: dict[str, list[dict]] = _defaultdict(list)
    for q in all_questions:
        course_key = str(q.get("source_course", "")).strip() or "unknown"
        questions_by_course[course_key].append(q)

    for q in all_questions:
        if len(selected) >= effective_cap:
            break
        q_text = str(q.get("question", ""))
        q_answer = str(q.get("options", {}).get(q.get("correct_answer", "A"), ""))

        # Guard 0: deterministic final quality gate.
        is_valid, validation_reason, validation_family = validate_diagnostic_question_quality(q)
        if not is_valid:
            rejected_quality += 1
            reason_norm = str(validation_reason).lower()
            if any(term in reason_norm for term in ("affirming", "denying", "invalid", "premise", "modus", "conclusion", "antecedent")):
                rejected_logic_invalid += 1
            if any(term in reason_norm for term in ("syntax", "trivia", "boilerplate", "input", "output", "recall")):
                rejected_syntax_trivia += 1
            print(
                "[DIAG QUALITY] rejected final candidate "
                f"reason={validation_reason} question={q_text[:80]!r}"
            )
            continue
        # Guard 1: per prerequisite subtopic, use closeness allocation.
        key = diagnostic_subtopic_key_from_question(q)
        q_skill_family = str(q.get("readiness_skill_family") or validation_family or classify_readiness_skill_family(q_text, q_answer) or "")
        if subtopic_key_counts[key] >= _max_questions_for_closeness(q):
            rejected_subtopic_cap += 1
            print(
                "[DIAG] rejected closeness subtopic cap "
                f"key={key} rating={q.get('semantic_relevance_rating', '')!r} "
                f"count={subtopic_key_counts[key]} "
                f"question={str(q.get('question', ''))[:80]!r}"
            )
            continue
        try:
            q_angle = int(q.get("subtopic_question_position", 1))
        except Exception:
            q_angle = 1
        if q_angle in subtopic_question_angles[key]:
            rejected_angle_dup += 1
            print(
                "[DIAG] rejected repeated cognitive angle within subtopic "
                f"key={key} angle={q_angle}"
            )
            continue
        subtopic_norm = " ".join(str(q.get("source_subtopic_name", "")).strip().lower().split())
        fam_key = (
            str(q.get("source_course", "")).strip().lower(),
            str(q.get("source_topic_name", "")).strip().lower(),
        )
        course_key_lower = str(q.get("source_course", "")).strip().lower()

        # Guard 3: concept-level dedup across the full exam
        # Compares (question + correct answer) text — catches questions that test
        # the same learning objective despite coming from different clusters/courses.
        if _is_redundant_candidate(q, q_text, q_answer, q_skill_family):
            rejected_concept_dup += 1
            print(
                "[DIAG] rejected concept duplicate "
                f"subtopic={subtopic_norm!r} question={q_text[:80]!r}"
            )
            continue

        balanced_family = normalize_readiness_family(q, q.get("source_topic_name", ""), q.get("source_subtopic_name", ""), q.get("diagnostic_target_course", ""))
        if balanced_family == "PROGRAMMING_SYNTAX_OR_TRIVIA":
            if not _syntax_trivia_allowed(q):
                rejected_syntax_trivia += 1
                print(
                    "[DIAG] rejected global syntax/trivia family "
                    f"source={q.get('source_course', '')}/{q.get('source_subtopic_name', '')} "
                    f"target={q.get('diagnostic_target_course', '')}"
                )
                continue
            if family_balance_counts[balanced_family] >= syntax_trivia_cap:
                rejected_syntax_trivia += 1
                rejected_family_cap += 1
                print(
                    "[DIAG] rejected syntax/trivia strong cap "
                    f"count={family_balance_counts[balanced_family]} cap={syntax_trivia_cap}"
                )
                continue
        if family_balance_counts[balanced_family] >= adaptive_skill_family_cap:
            rejected_family_cap += 1
            print(
                "[DIAG] rejected adaptive normalized-family cap "
                f"family={balanced_family!r} count={family_balance_counts[balanced_family]} "
                f"cap={adaptive_skill_family_cap} question={q_text[:80]!r}"
            )
            continue

        _record_accepted(q, key, subtopic_norm, fam_key, course_key_lower, q_skill_family)
        selected.append(q)

    print(
        "[DIAG] final prerequisite coverage "
        f"candidate_questions={len(all_questions)} selected={len(selected)} "
        f"adaptive_skill_family_cap={adaptive_skill_family_cap} "
        f"unique_subtopic_keys={len(subtopic_key_counts)} "
        f"source_courses={len(questions_by_course)} "
        f"rejected_subtopic_cap={rejected_subtopic_cap} "
        f"rejected_family_cap={rejected_family_cap} "
        f"rejected_course_cap={rejected_course_cap} "
        f"rejected_concept_dup={rejected_concept_dup} "
        f"rejected_skill_family={rejected_skill_family} "
        f"rejected_reduction_family={rejected_reduction_family} "
        f"rejected_angle_dup={rejected_angle_dup} "
        f"rejected_logic_invalid={rejected_logic_invalid} "
        f"rejected_syntax_trivia={rejected_syntax_trivia} "
        f"rejected_quality={rejected_quality} "
        f"difficulty_counts={dict(difficulty_counts)} "
        f"skill_families={dict(skill_family_counts)} "
        f"normalized_family_distribution={dict(family_balance_counts)} "
        f"course_counts={dict(course_question_counts)}"
    )

    if not selected:
        raise ValueError(
            "Could not generate questions with unique prerequisite subtopic coverage. "
            "Semantic generation returned questions, but all failed coverage selection."
        )
    print(
        "[DIAG ADAPTIVE] returning adaptive diagnostic "
        f"selected={len(selected)} cap={effective_cap} "
        f"semantic_clusters={len(semantic_clusters)}"
    )

    formatted = []
    for i, q in enumerate(selected):
        options, correct_answer = force_correct_answer_a(
            dict(q.get("options", {})),
            q.get("correct_answer", "A"),
        )
        formatted.append({
            "question_id":          f"q{i + 1}",
            "question":             q.get("question", ""),
            "difficulty":           q.get("difficulty", "medium"),
            "options":              options,
            "correct_answer":       correct_answer,
            "explanation":          q.get("explanation", ""),
            "source_topic_name":    q.get("source_topic_name", ""),
            "source_subtopic_name": q.get("source_subtopic_name", ""),  # CRITICAL field
            "source_course":        q.get("source_course", ""),
            "source_subtopic_key":  q.get(
                "source_subtopic_key",
                "|".join(diagnostic_subtopic_key_from_question(q)),
            ),
            "diagnostic_target_course": q.get("diagnostic_target_course", target_course),
            "semantic_score":       q.get("semantic_score", 0),
            "semantic_link_count":  q.get("semantic_link_count", 0),
            "semantic_relevance_rating": q.get("semantic_relevance_rating", ""),
            "related_target_subtopics": q.get("related_target_subtopics", []),
            "readiness_skill_family": q.get("readiness_skill_family", ""),
            "balanced_readiness_family": q.get("balanced_readiness_family", ""),
            "normalized_readiness_family": q.get("normalized_readiness_family", q.get("balanced_readiness_family", "")),
        })

    exam = {
        "exam_id":       str(_uuid.uuid4()),
        "student_id":    student_profile["student_id"],
        "target_course": target_course,
        "sampling_mode":  sampling_mode,
        "questions":     formatted,
        "requested_question_count": len(formatted),
        "generated_question_count": len(formatted),
        "adaptive_question_cap": effective_cap,
        "is_partial": False,
        "warning": "",
        "quality_summary": {
            "candidate_questions": len(all_questions),
            "selected_questions": len(selected),
            "difficulty_counts": dict(difficulty_counts),
            "rejected_quality": rejected_quality,
            "rejected_concept_duplicates": rejected_concept_dup,
            "rejected_subtopic_cap": rejected_subtopic_cap,
            "rejected_normalized_family_cap": rejected_family_cap,
            "rejected_reduction_family": rejected_reduction_family,
            "rejected_angle_duplicates": rejected_angle_dup,
            "rejected_logic_invalid": rejected_logic_invalid,
            "rejected_syntax_trivia": rejected_syntax_trivia,
            "skill_families": dict(skill_family_counts),
            "normalized_family_distribution": dict(family_balance_counts),
            "final_family_distribution": dict(family_balance_counts),
            "adaptive_family_cap": adaptive_skill_family_cap,
            "adaptive_skill_family_cap": adaptive_skill_family_cap,
            "source_course_counts": dict(course_question_counts),
            "semantic_clusters": len(semantic_clusters),
            "adaptive_question_cap": effective_cap,
        },
    }

    if save_result:
        try:
            _DIAGNOSTIC_SAVE_DIR.mkdir(parents=True, exist_ok=True)
            path = _DIAGNOSTIC_SAVE_DIR / f"{student_profile['student_id']}_{target_course.replace(' ','_')}_exam.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(exam, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DIAG] Could not save exam: {e}")

    return exam

def submit_diagnostic_exam(
    student_profile: dict,
    target_course: str,
    submitted_answers: list[dict],
) -> dict:
    student_id = student_profile["student_id"]
    save_path  = _DIAGNOSTIC_SAVE_DIR / f"{student_id}_{target_course.replace(' ','_')}_exam.json"

    if not save_path.exists():
        raise ValueError("Exam not found. Please generate the diagnostic exam first.")

    with open(save_path, "r", encoding="utf-8") as f:
        exam = json.load(f)

    questions  = {q["question_id"]: q for q in exam.get("questions", [])}
    answer_map = {a["question_id"]: a["student_answer"] for a in submitted_answers}

    correct_count    = 0
    wrong_count      = 0
    questions_review = []

    # Track per-subtopic correct/total for mastery scoring.
    # Key: "<source_course>/<source_topic_name>/<source_subtopic_name>"
    subtopic_totals:  dict[str, int] = _defaultdict(int)
    subtopic_correct: dict[str, int] = _defaultdict(int)

    for qid, q in questions.items():
        student_ans = answer_map.get(qid, "")
        is_correct  = student_ans == q["correct_answer"]
        if is_correct:
            correct_count += 1
        else:
            wrong_count += 1

        # Build mastery key — same triple used for learning path generation.
        course   = q.get("source_course", "")
        topic    = q.get("source_topic_name", "")
        subtopic = q.get("source_subtopic_name", "")
        mastery_key = f"{course}/{topic}/{subtopic}"
        subtopic_totals[mastery_key] += 1
        if is_correct:
            subtopic_correct[mastery_key] += 1

        questions_review.append({
            "question_id":          qid,
            "question":             q.get("question", ""),
            "options":              q.get("options", {}),
            "correct_answer":       q.get("correct_answer", ""),
            "student_answer":       student_ans,
            "is_correct":           is_correct,
            "explanation":          q.get("explanation", ""),
            "source_topic_name":    topic,
            "source_subtopic_name": subtopic,
            "source_course":        course,
        })

    total     = len(questions)
    score_pct = round((correct_count / total) * 100) if total > 0 else 0

    # ── Subtopic mastery scoring ──────────────────────────────────────────────
    # Weakness is determined by number of wrong answers, scaled by subtopic size:
    #   3-question subtopics: weak if wrong_answers >= 2  (so 2/3 correct = NOT weak)
    #   2-question subtopics: weak if wrong_answers >= 2  (so 1/2 correct = NOT weak)
    #   1-question subtopics: weak if wrong_answers >= 1  (any wrong = weak)
    #
    # Mastery levels:
    #   strong    = all correct
    #   partial   = some correct, NOT weak (e.g. 2/3 or 1/2)
    #   weak      = is_weak AND at least one correct (e.g. 1/3)
    #   deficient = 0 correct (and is_weak)
    subtopic_mastery: dict[str, dict] = {}
    for mkey, total_q in subtopic_totals.items():
        n_correct = subtopic_correct.get(mkey, 0)
        n_wrong   = total_q - n_correct
        # Weakness threshold: 1-question subtopics fail on 1 wrong; larger ones on 2+.
        is_weak = (n_wrong >= 1) if total_q == 1 else (n_wrong >= 2)
        if n_correct == total_q:
            level = "strong"
        elif is_weak and n_correct == 0:
            level = "deficient"
        elif is_weak:
            level = "weak"
        else:
            level = "partial"
        subtopic_mastery[mkey] = {
            "correct":  n_correct,
            "total":    total_q,
            "n_wrong":  n_wrong,
            "level":    level,
            "is_weak":  is_weak,
        }

    # ── weak_by_topic: subtopics the student should revisit ───────────────────
    # Derived directly from is_weak flag — consistent with mastery scoring above.
    weak_by_topic: dict[str, list[str]] = {}
    for mkey, mastery in subtopic_mastery.items():
        if mastery["is_weak"]:
            parts    = mkey.split("/", 2)
            m_course = parts[0] if len(parts) > 0 else ""
            m_topic  = parts[1] if len(parts) > 1 else ""
            m_sub    = parts[2] if len(parts) > 2 else ""
            if m_course and m_topic:
                weak_by_topic.setdefault(m_course, []).append(m_sub or m_topic)

    result = {
        "student_id":        student_id,
        "target_course":     target_course,
        "score_percentage":  score_pct,
        "correct_count":     correct_count,
        "wrong_count":       wrong_count,
        "total_questions":   total,
        "questions_review":  questions_review,
        "weak_by_topic":     weak_by_topic,
        "subtopic_mastery":  subtopic_mastery,
    }

    try:
        _DIAGNOSTIC_SAVE_DIR.mkdir(parents=True, exist_ok=True)
        graded_path = _DIAGNOSTIC_SAVE_DIR / f"{student_id}_{target_course.replace(' ','_')}_graded.json"
        with open(graded_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[DIAG] Could not save graded result: {e}")

    return result

def generate_learning_path_from_graded_result(
    student_profile: dict,
    graded_result_payload: dict,
    save_result: bool = True,
) -> dict:
    target_course    = graded_result_payload.get("target_course", "")
    questions_review = graded_result_payload.get("questions_review", [])
    subtopic_mastery = graded_result_payload.get("subtopic_mastery", {})

    weak_map: dict = _defaultdict(set)

    if subtopic_mastery:
        # Primary path: use mastery scores computed during submission.
        # is_weak is already stored on each mastery entry using the wrong-answer rule:
        #   1-question subtopic: weak if 1 wrong
        #   2-question subtopic: weak if 2 wrong  (1/2 correct = NOT weak)
        #   3-question subtopic: weak if 2+ wrong (2/3 correct = NOT weak)
        for mkey, mastery in subtopic_mastery.items():
            # Support both new (is_weak flag) and legacy (ratio-based) entries.
            if "is_weak" in mastery:
                is_weak = mastery["is_weak"]
            else:
                n_correct = mastery.get("correct", 0)
                n_total   = mastery.get("total", 1)
                n_wrong   = n_total - n_correct
                is_weak   = (n_wrong >= 1) if n_total == 1 else (n_wrong >= 2)
            if is_weak:
                parts    = mkey.split("/", 2)
                m_course = parts[0] if len(parts) > 0 else ""
                m_topic  = parts[1] if len(parts) > 1 else ""
                m_sub    = parts[2] if len(parts) > 2 else ""
                if m_course and m_topic:
                    weak_map[(m_course, m_topic)].add(m_sub if m_sub else m_topic)
    else:
        # Fallback: subtopic_mastery absent (legacy graded result from before this change).
        # Use any wrong answer as weak indicator, as before.
        for q in questions_review:
            if not q.get("is_correct", True):
                course   = q.get("source_course", "")
                topic    = q.get("source_topic_name", "")
                subtopic = q.get("source_subtopic_name", "")
                if course and topic:
                    weak_map[(course, topic)].add(subtopic if subtopic else topic)

    if not weak_map:
        # Perfect score — no weak areas. The frontend handles this case
        # by never calling this endpoint (Generate Learning Path button is hidden).
        # Return an empty path as a safety net.
        return {
            "student_id":    student_profile["student_id"],
            "target_course": target_course,
            "learning_path": [],
        }

    learning_path = []
    for (course, topic), subtopics in weak_map.items():
        material_pdf = ""
        try:
            mat_file = COURSES_DIR / course / "metadata" / "materials_index.json"
            if mat_file.exists():
                mats = json.load(open(mat_file))
                material_pdf = mats.get("materials", [{}])[0].get("file_name", "")
        except Exception:
            pass

        # ── Semantic neighbours: subtopics from other courses that are
        #    semantically similar to each weak subtopic in this step.
        #    These help the student explore connected concepts across the
        #    full curriculum, not just within the course they are weak in.
        semantic_neighbors: list[dict] = []
        seen_neighbor_keys: set[tuple[str, str]] = set()
        for sub in sorted(subtopics):
            try:
                neighbors = get_semantically_related_subtopics(
                    course_name=course,
                    subtopic_name=sub,
                    limit=3,
                )
                for nb in neighbors:
                    key = (nb.get("target_course", ""), nb.get("target_subtopic", ""))
                    if key not in seen_neighbor_keys:
                        seen_neighbor_keys.add(key)
                        semantic_neighbors.append(nb)
            except Exception as e:
                print(f"[PATH] Could not fetch semantic neighbors for '{sub}': {e}")

        learning_path.append({
            "source_course":       course,
            "source_material_pdf": material_pdf,
            "topic_name":          topic,
            "weak_subtopics":      [{"subtopic_name": s} for s in sorted(subtopics)],
            "semantic_neighbors":  semantic_neighbors,
        })

    # ── Step numbering ────────────────────────────────────────────────────────
    # Steps are ordered by insertion order (i.e. the order wrong answers were
    # encountered in the exam).  Prerequisites are METADATA only and must NOT
    # impose a curriculum ordering on the learning path.  The student and the
    # AI tutor can re-order steps as appropriate for their learning style.
    for i, step in enumerate(learning_path, start=1):
        step["step_number"] = i

    result = {
        "student_id":    student_profile["student_id"],
        "target_course": target_course,
        "learning_path": learning_path,
    }

    if save_result:
        try:
            _DIAGNOSTIC_SAVE_DIR.mkdir(parents=True, exist_ok=True)
            path_file = _DIAGNOSTIC_SAVE_DIR / f"{student_profile['student_id']}_{target_course.replace(' ','_')}_path.json"
            with open(path_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[PATH] Could not save learning path: {e}")

    return result

def generate_learning_path_exercises(
    student_profile: dict,
    target_course: str,
    subtopic_requests: list[dict],
    save_result: bool = True,
) -> dict:
    courses_taken   = student_profile.get("courses_taken", [])
    exercise_groups = []

    for req in subtopic_requests:
        topic_name    = req.get("topic_name", "")
        subtopic_name = req.get("subtopic_name", "")
        num_exercises = int(req.get("num_exercises", 3))
        source_course = req.get("source_course", courses_taken[0] if courses_taken else "")

        exercises = []
        try:
            retrieved = retrieve_course_material(source_course, topic_name, subtopic_name)
            context   = build_context_text(retrieved)
            qs = generate_questions_for_subtopic(
                course_name=source_course,
                topic_name=topic_name,
                subtopic_name=subtopic_name,
                context_text=context,
                previous_question_texts=[],
            )
            for q in qs[:num_exercises]:
                exercises.append({
                    "exercise_id":    str(_uuid.uuid4()),
                    "exercise_type":  "multiple_choice",
                    "difficulty":     q.get("difficulty", "medium"),
                    "question":       q.get("question", ""),
                    "options":        q.get("options", {}),
                    "correct_answer": q.get("correct_answer", ""),
                    "explanation":    q.get("explanation", ""),
                })
        except Exception as e:
            print(f"[EXERCISES] Error for '{subtopic_name}': {e}")

        exercise_groups.append({
            "topic_name":    topic_name,
            "subtopic_name": subtopic_name,
            "source_course": source_course,
            "exercises":     exercises,
        })

    return {"exercise_groups": exercise_groups}

def get_all_progress_for_student(student_profile: dict) -> dict:
    student_id    = student_profile.get("student_id", "")
    saved_paths   = load_learning_paths()
    student_paths = [p for p in saved_paths if p.get("student_id") == student_id]

    progress_list = []
    for p in student_paths:
        target_course = p.get("target_course", "")
        path_data     = p.get("path_data", {})
        learning_path = path_data.get("learning_path", [])
        weak_count    = sum(len(step.get("weak_subtopics", [])) for step in learning_path)

        try:
            tracking = load_progress_for_student_and_course(student_profile, target_course)
        except Exception:
            tracking = {}

        if tracking.get("success"):
            completed  = tracking.get("completed_count", 0)
            best_score = tracking.get("best_score", 0)
            status = "completed" if completed >= weak_count and weak_count > 0 else "in_progress"
        else:
            completed = 0; best_score = 0; status = "not_started"

        progress_list.append({
            "target_course":        target_course,
            "course_name":          target_course,
            "topic_name":           path_data.get("topic_name", target_course),
            "status":               status,
            "weak_subtopics_count": weak_count,
            "completed_steps":      completed,
            "best_score":           best_score,
        })

    return {"progress": progress_list}

# ---------------------------------------------------------
# routes
# ---------------------------------------------------------
@app.get("/api/health")
def health():
    return {"success": True, "message": "Manara API is running."}

@app.get("/api/courses/all")
def api_get_all_courses():
    return get_available_courses()

@app.post("/api/auth/login")
def api_login(payload: LoginRequest):
    try:
        student = authenticate_student(payload.student_id, payload.password)
        available_target_courses = []
        try:
            profile = build_exam1_profile(payload.student_id)
            available_target_courses = get_exam1_available_courses(profile).get("available_target_courses", [])
        except Exception:
            pass
        return {
            "success": True,
            "message": "Login successful.",
            "student": {
                "student_id":     student["student_id"],
                "student_name":   student["student_name"],
                "terms_accepted": student.get("terms_accepted", False),
                "phone_number":   student.get("phone_number", ""),
                "courses_taken":  student.get("courses_taken", []),
                "whatsapp_opt_in": student.get("whatsapp_opt_in", False),
                "activity_dates": student.get("activity_dates", []),
            },
            "available_target_courses": available_target_courses,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/student/terms")
def api_save_terms(payload: TermsRequest):
    try:
        student = accept_terms(payload.student_id)
        return {"success": True, "message": "Terms updated.", "terms_accepted": student["terms_accepted"], "student": student}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/student/phone")
def api_save_phone(payload: PhoneRequest):
    try:
        student = update_phone_number(
            student_id=payload.student_id,
            phone_number=payload.phone_number,
            whatsapp_opt_in=payload.whatsapp_opt_in,
        )
        return {"success": True, "message": "Phone saved.", "phone_number": student["phone_number"], "student": student}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/student/profile-setup")
def api_profile_setup(payload: ProfileSetupRequest):
    try:
        update_phone_number(payload.student_id, payload.phone_number, bool(payload.phone_number.strip()))
        student = update_completed_courses(payload.student_id, payload.courses_taken)
        profile = build_exam1_profile(payload.student_id)
        available = get_exam1_available_courses(profile).get("available_target_courses", [])
        return {
            "success": True,
            "message": "Profile saved.",
            "student": {
                "student_id":    student["student_id"],
                "student_name":  student["student_name"],
                "terms_accepted": student["terms_accepted"],
                "phone_number":  student["phone_number"],
                "courses_taken": student["courses_taken"],
            },
            "available_target_courses": available,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/api/student/activity/{student_id}")
def api_student_activity(student_id: str):
    """Lightweight endpoint — returns only activity_dates for streak display."""
    try:
        profile = get_student_profile(student_id)
        if not profile:
            return {"success": False, "activity_dates": []}
        return {"success": True, "activity_dates": profile.get("activity_dates", [])}
    except Exception as e:
        return {"success": False, "activity_dates": [], "message": str(e)}

@app.get("/api/exam1/available-courses/{student_id}")
def api_exam1_available_courses(student_id: str):
    profile = build_exam1_profile(student_id)
    return get_exam1_available_courses(profile)

@app.post("/api/exam1/generate")
def api_exam1_generate(payload: Exam1GenerateRequest):
    try:
        profile = build_exam1_profile(payload.student_id)
        return generate_diagnostic_exam(student_profile=profile, target_course=payload.target_course, save_result=True)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"[EXAM1 GENERATE] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Exam generation failed. Check server logs.")

@app.post("/api/exam1/submit")
def api_exam1_submit(payload: Exam1SubmitRequest):
    profile = build_exam1_profile(payload.student_id)
    submitted_answers = [{"question_id": i.question_id, "student_answer": i.student_answer} for i in payload.submitted_answers]
    result = submit_diagnostic_exam(student_profile=profile, target_course=payload.target_course, submitted_answers=submitted_answers)
    try:
        update_last_active(payload.student_id)  # diagnostic exam submitted = real learning
    except Exception:
        pass
    return result

@app.post("/api/exam1/learning-path")
def api_exam1_learning_path(payload: LearningPathRequest):
    profile = build_exam1_profile(payload.student_id)
    result  = generate_learning_path_from_graded_result(student_profile=profile, graded_result_payload=payload.graded_result_payload, save_result=True)
    save_learning_path_internal(payload.student_id, result)
    delete_tracking_for_student_and_course(payload.student_id, result.get("target_course", ""))
    return result

@app.post("/api/exam1/exercises")
def api_exam1_exercises(payload: Exam1ExercisesRequest):
    profile = build_exam1_profile(payload.student_id)
    subtopic_requests = [{"topic_name": i.topic_name, "subtopic_name": i.subtopic_name, "num_exercises": i.num_exercises} for i in payload.subtopic_requests]
    result = generate_learning_path_exercises(student_profile=profile, target_course=payload.target_course, subtopic_requests=subtopic_requests)
    try:
        update_last_active(payload.student_id)  # exercises requested = real learning
    except Exception:
        pass
    return result

@app.get("/api/progress/student/{student_id}")
def progress_for_student(student_id: str):
    try:
        profile = build_exam1_profile(student_id)
        raw     = get_all_progress_for_student(profile)
        progress_list = raw.get("progress", [])
        fixed = []
        for item in progress_list:
            tracking = load_progress_for_student_and_course(profile, item.get("target_course", ""))
            if tracking.get("success"):
                item["learning_path_steps"] = len(tracking.get("subtopic_progress", []))
                item["completed_steps"]     = tracking.get("completed_count", 0)
            else:
                item["learning_path_steps"] = item.get("weak_subtopics_count", 0)
                item["completed_steps"]     = 0
            fixed.append(item)
        return {"success": True, "progress": fixed}
    except Exception as e:
        return {"success": False, "message": str(e), "progress": []}

@app.post("/api/ask-course")
def api_ask_course(payload: AskCourseRequest):
    result = ask_course_question(payload.course_name, payload.question, history=payload.history)
    try:
        if payload.student_id:
            update_last_active(payload.student_id)  # chatbot used = real learning
    except Exception:
        pass
    return result

@app.get("/api/qb/chapters/{course_name}")
def api_qb_chapters(course_name: str):
    try:
        result = get_chapters_for_course(course_name)
        return {"success": True, "course_name": result["course_name"], "chapters": result["materials"]}
    except Exception as e:
        return {"success": False, "message": str(e), "chapters": []}

@app.post("/api/qb/generate")
def api_qb_generate(payload: QuestionBankGenerateRequest):
    try:
        result = generate_question_bank_for_student(student_profile=None, target_course=payload.course_name, chapter_name=payload.chapter_name, save_result=True)
        return {"success": True, "message": "Question bank generated.", "target_course": result["target_course"], "chapter": result["chapter"], "total_questions": result["total_questions"], "questions": result["questions"]}
    except Exception as e:
        return {"success": False, "message": str(e), "questions": []}

@app.post("/api/track/start")
def api_track_start(payload: TrackStartRequest):
    try:
        profile = build_exam1_profile(payload.student_id)
        delete_tracking_for_student_and_course(payload.student_id, payload.learning_path_payload.get("target_course", ""))
        return create_tracking_progress_from_learning_path(student_profile=profile, learning_path_payload=payload.learning_path_payload)
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/api/track/{student_id}/{target_course}")
def api_track_load(student_id: str, target_course: str):
    try:
        profile = build_exam1_profile(student_id)
        return load_progress_for_student_and_course(profile, target_course)
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/track/quiz/{student_id}/{target_course}")
def api_track_generate_quiz(student_id: str, target_course: str):
    try:
        profile = build_exam1_profile(student_id)
        return generate_quiz_for_current_subtopic(profile, target_course)
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/track/submit")
def api_track_submit(payload: TrackSubmitRequest):
    try:
        profile = build_exam1_profile(payload.student_id)
        submitted_answers = [{"question_id": i.question_id, "student_answer": i.student_answer} for i in payload.submitted_answers]
        result = submit_quiz_for_current_subtopic(profile, payload.target_course, submitted_answers)
        try:
            update_last_active(payload.student_id)  # learning path quiz submitted = real learning
        except Exception:
            pass
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/learning-path/save")
def save_learning_path_api(payload: dict):
    try:
        paths    = load_learning_paths()
        new_path = {"student_id": payload["student_id"], "target_course": payload["path_data"].get("target_course", ""), "path_data": payload["path_data"], "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
        paths    = [p for p in paths if not (p["student_id"] == new_path["student_id"] and p["target_course"] == new_path["target_course"])]
        paths.append(new_path)
        save_learning_paths(paths)
        return {"success": True, "message": "Path saved"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/api/learning-path/student/{student_id}")
def get_learning_paths_api(student_id: str):
    try:
        paths = [p for p in load_learning_paths() if p["student_id"] == student_id]
        return {"success": True, "paths": paths}
    except Exception as e:
        return {"success": False, "message": str(e), "paths": []}

@app.get("/api/reminders/students")
def get_students_for_reminders():
    return {"students": []}

# ---------------------------------------------------------
# knowledge graph endpoints
# ---------------------------------------------------------

@app.get("/api/knowledge-graph")
def get_knowledge_graph():
    """
    Return the real semantic knowledge graph for InsideManarasBrainPage.

    When is_real=False the nodes/edges lists are EMPTY.
    The frontend InsideManarasBrainPage should show a "not built" state,
    NOT inject fake/demo data.
    """
    try:
        graph_data = load_graph_for_frontend()
        is_real    = graph_data.get("is_real", False)
        nodes      = graph_data.get("nodes", [])
        edges      = graph_data.get("edges", [])
        error_msg  = graph_data.get("error")
        debug      = graph_data.get("debug", {})
        print(
            "[KG API] /api/knowledge-graph "
            f"nodes={len(nodes)} edges={len(edges)} debug={debug}"
        )
        return {
            "success":    True,
            "is_real":    is_real,
            "nodes":      nodes,
            "edges":      edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "debug":      debug,
            "message":    error_msg,
        }
    except Exception as e:
        print(f"[KG] Unexpected error in /api/knowledge-graph: {e}")
        raise HTTPException(status_code=500, detail=f"Knowledge graph error: {e}")


@app.get("/api/graph/status")
def get_graph_status():
    """Return graph health: triple count, build time, node counts."""
    try:
        return {"success": True, **graph_status()}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/graph/rebuild")
def rebuild_graph():
    """
    Rebuild the knowledge graph from course data and reload the cache.
    Call after updating course materials.
    Runs synchronously — may take 10-60 seconds.
    """
    try:
        g = build_knowledge_graph(_KG_COURSES_DIR)
        _KG_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        g.serialize(destination=str(_KG_OUTPUT_FILE), format="turtle")
        invalidate_graph_cache()
        return {"success": True, "message": "Knowledge graph rebuilt.", **graph_status()}
    except Exception as e:
        print(f"[KG] Rebuild failed: {e}")
        raise HTTPException(status_code=500, detail=f"Graph rebuild failed: {e}")


@app.get("/api/graph/prerequisites/{course_name}")
def get_prerequisites_endpoint(course_name: str):
    """Return prerequisite courses ordered by BFS distance from course_name."""
    try:
        results = get_courses_by_prerequisite_distance(course_name)
        return {
            "success":       True,
            "target_course": course_name,
            "prerequisites": [{"course": n, "distance": d} for n, d in results],
        }
    except Exception as e:
        return {"success": False, "message": str(e), "prerequisites": []}
