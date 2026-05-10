"""
generate_exercises.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Manara – Generate Exercises Module
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils import embedding_functions
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

# ─── Logging ─────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─── Router ──────────────────────────────────────────────────────────────────
exercise_router = APIRouter(prefix="/api", tags=["generate-exercises"])

# ─── Project paths ───────────────────────────────────────────────────────────
PROJECT_DIR = Path(os.environ.get("MANARA_PROJECT_DIR", "/Users/dinaal-memah/Desktop/graduation project 2"))
COURSES_DIR = PROJECT_DIR / "courses"

# ─── OpenAI client (lazy singleton) ─────────────────────────────────────────
_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        import openai as _openai
        _openai_client = _openai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai_client

# ─── ChromaDB helpers (per-course, matching exam1.py pattern) ────────────────

def _safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).strip().lower()).strip("_")


def _get_course_collection(course_name: str, suffix: str):
    """
    Returns a ChromaDB collection for a specific course, using the same
    per-course path pattern as exam1.py:
      courses/<course_name>/outputs/chroma_db/<slug><suffix>
    """
    chroma_dir = COURSES_DIR / course_name / "outputs" / "chroma_db"
    if not chroma_dir.exists():
        return None
    try:
        client = chromadb.PersistentClient(path=str(chroma_dir))
        ef = embedding_functions.DefaultEmbeddingFunction()
        collection_name = f"{_safe_slug(course_name)}{suffix}"
        return client.get_collection(name=collection_name, embedding_function=ef)
    except Exception:
        return None


def query_chroma_for_subtopic(
    course_name: str,
    topic_name: str,
    subtopic_name: str,
    n_results: int = 8,
) -> List[str]:
    """
    Query all three ChromaDB collections (chunks, summaries, concepts)
    for the given course/topic/subtopic, and return combined text passages.
    """
    query_text = f"Topic: {topic_name}\nSubtopic: {subtopic_name}"
    passages: List[str] = []
    seen: set = set()

    for suffix in ("_chunks", "_summaries", "_concepts"):
        collection = _get_course_collection(course_name, suffix)
        if collection is None:
            continue
        try:
            results = collection.query(
                query_texts=[query_text],
                n_results=min(n_results, collection.count()),
                include=["documents"],
            )
            docs: List[str] = results.get("documents", [[]])[0]
            for doc in docs:
                key = doc.strip()[:120]
                if key not in seen:
                    seen.add(key)
                    passages.append(doc.strip())
        except Exception as exc:
            logger.warning("ChromaDB query failed for '%s' suffix='%s': %s", course_name, suffix, exc)

    return passages


def build_context_block(passages: List[str], max_chars: int = 3000) -> str:
    if not passages:
        return "(No additional reference material available.)"
    combined = "\n\n---\n\n".join(passages)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n…[truncated]"
    return combined


def _context_has_material(context: str) -> bool:
    return bool(context and "No additional reference material available" not in context)


# ─── Math / text formatting helper ───────────────────────────────────────────
def normalise_math(text: str) -> str:
    r"""
    Normalise LaTeX delimiters so remark-math / rehype-katex renders correctly.
      \[…\]   →  $$…$$   (display block)
      \(…\)   →  $…$     (inline)
    """
    if not text:
        return text
    text = re.sub(r"\\\[([\s\S]*?)\\\]", lambda m: f"\n$$\n{m.group(1).strip()}\n$$\n", text)
    text = re.sub(r"\\\(([\s\S]*?)\\\)", lambda m: f"${m.group(1)}$", text)
    return text


def _has_problem_signal(question: str) -> bool:
    q = question.lower()
    return any(
        signal in q
        for signal in (
            "?",
            "predict",
            "trace",
            "debug",
            "fix",
            "complete",
            "fill in",
            "what is the output",
            "which option",
            "given",
            "write",
            "choose",
            "compare",
            "explain why",
            "what happens",
            "what value",
            "determine",
            "identify the bug",
        )
    )


def _is_note_like_item(question: str) -> bool:
    q = question.strip().lower()
    note_like_patterns = (
        "definition and structure",
        "examples illustrating",
        "appending to end",
        "introduction to",
        "overview of",
        "syntax of",
        "fundamentals of",
        "types of",
        "components of",
    )
    if any(pattern in q for pattern in note_like_patterns) and not _has_problem_signal(question):
        return True
    # Very short noun-phrase outputs are usually titles/topics, not exercises.
    if len(q.split()) <= 6 and not _has_problem_signal(question):
        return True
    return False


def _is_raw_slide_artifact(question: str) -> bool:
    q = question.strip().lower()
    artifact_patterns = (
        r"\bjan(?:uary)?\s+\d{1,2}\b",
        r"\bfeb(?:ruary)?\s+\d{1,2}\b",
        r"\bmar(?:ch)?\s+\d{1,2}\b",
        r"\bapr(?:il)?\s+\d{1,2}\b",
        r"\bmay\s+\d{1,2}\b",
        r"\bjun(?:e)?\s+\d{1,2}\b",
        r"\bjul(?:y)?\s+\d{1,2}\b",
        r"\baug(?:ust)?\s+\d{1,2}\b",
        r"\bsep(?:tember)?\s+\d{1,2}\b",
        r"\boct(?:ober)?\s+\d{1,2}\b",
        r"\bnov(?:ember)?\s+\d{1,2}\b",
        r"\bdec(?:ember)?\s+\d{1,2}\b",
        r"\bchapter[s]?\s+\d",
        r"\bpage\s+\d",
        r"\bslide\s+\d",
        r"\bpptx?\b",
        r"\.pdf\b",
        r"\bcopyright\b",
    )
    return any(re.search(pattern, q) for pattern in artifact_patterns)


def _concept_family(topic_name: str, subtopic_name: str, context: str) -> str:
    blob = f"{topic_name} {subtopic_name} {context}".lower()
    if "linear search" in blob or "sequential search" in blob:
        return "linear_search"
    if "binary search" in blob or "halving" in blob:
        return "binary_search"
    if "modus" in blob or "inference" in blob or "syllogism" in blob:
        return "inference_rules"
    if "classification" in blob or "classifier" in blob:
        return "classification"
    if "algorithm" in blob:
        return "algorithm"
    if "sort" in blob:
        return "sorting"
    if "recursion" in blob or "recursive" in blob:
        return "recursion"
    return "general"


def _concept_blueprint(family: str, difficulty_request: str) -> str:
    blueprints = {
        "linear_search": (
            "Learning objective: trace sequential/linear search, count comparisons, "
            "distinguish best/worst/average case, and justify complexity from target position."
        ),
        "binary_search": (
            "Learning objective: use sorted-array precondition, middle comparison, halving strategy, "
            "worst-case comparison count, and explain failure on unsorted arrays."
        ),
        "inference_rules": (
            "Learning objective: derive valid conclusions from premises, identify Modus Ponens, "
            "Modus Tollens, Hypothetical Syllogism, Disjunctive Syllogism, and reject invalid inference."
        ),
        "classification": (
            "Learning objective: identify classification tasks, distinguish categories from numeric prediction, "
            "recognize labels/classes, and justify the target variable."
        ),
        "algorithm": (
            "Learning objective: recognize algorithms as finite, clear, unambiguous steps with input/output, "
            "and critique vague or non-terminating procedures."
        ),
        "sorting": (
            "Learning objective: trace sorting behavior, identify sorting method from operations, "
            "and reason about suitability or complexity."
        ),
        "recursion": (
            "Learning objective: identify base case, recursive call, termination, and trace small recursive examples."
        ),
        "general": (
            "Learning objective: test application and reasoning around the weak subtopic using the course terminology."
        ),
    }
    difficulty_notes = {
        "easy": "Easy should use MCQ, true/false, or fill blank for basic understanding and one-step reasoning.",
        "medium": "Medium should use tracing, scenario MCQ, or mini problem solving with small reasoning steps.",
        "hard": "Hard should use analysis, compare/justify, edge cases, or explain why a method succeeds/fails.",
        "mixed": "Mixed should balance easy, medium, and hard with varied formats.",
    }
    return f"{blueprints.get(family, blueprints['general'])}\n{difficulty_notes.get(difficulty_request, difficulty_notes['mixed'])}"


def _difficulty_for_index(difficulty_request: str, index: int) -> str:
    if difficulty_request in {"easy", "medium", "hard"}:
        return difficulty_request.capitalize()
    return ["Easy", "Medium", "Hard", "Medium", "Easy"][index % 5]


def _exercise_type_label(ex_type: str) -> str:
    return {
        "multiple_choice": "MCQ",
        "true_false": "True/False",
        "short_answer": "Short Answer",
        "fill_blank": "Fill in the Blank",
        "code_tracing": "Trace/Walkthrough",
        "scenario": "Scenario-based",
        "mini_problem": "Mini Problem Solving",
    }.get(ex_type, ex_type.replace("_", " ").title())


def _make_exercise(
    title: str,
    ex_type: str,
    difficulty: str,
    question: str,
    answer: str,
    explanation: str,
    choices: Optional[List[str]] = None,
    correct_answer: Optional[str] = None,
) -> "Exercise":
    options = None
    normalized_choices = None
    if choices:
        labels = ("A", "B", "C", "D")
        normalized_choices = [normalise_math(choice) for choice in choices[:4]]
        options = {labels[i]: normalized_choices[i] for i in range(len(normalized_choices))}
        if not correct_answer and answer in labels:
            correct_answer = answer

    return Exercise(
        exercise_id=str(uuid.uuid4()),
        title=title,
        exercise_type="multiple_choice" if ex_type in {"mcq", "multiple_choice", "true_false"} else ex_type,
        type="MCQ" if ex_type in {"mcq", "multiple_choice"} else _exercise_type_label(ex_type),
        difficulty=difficulty,
        question=normalise_math(question),
        options=options,
        choices=normalized_choices,
        correct_answer=correct_answer,
        answer=correct_answer if correct_answer else normalise_math(answer),
        answer_text=normalise_math(
            f"{correct_answer}. {options[correct_answer]}" if correct_answer and options and correct_answer in options else answer
        ),
        explanation=normalise_math(explanation),
    )


# ─── Duplicate detection ──────────────────────────────────────────────────────
class ExerciseDeduplicator:
    def __init__(self) -> None:
        self._seen: set = set()

    def _fingerprint(self, question: str) -> str:
        cleaned = re.sub(r"[^\w\s]", "", question.lower())
        return " ".join(cleaned.split())[:180]

    def is_duplicate(self, question: str) -> bool:
        return self._fingerprint(question) in self._seen

    def register(self, question: str) -> None:
        self._seen.add(self._fingerprint(question))


# ─── JSON extraction ──────────────────────────────────────────────────────────
def extract_json_from_llm_response(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    for pattern in (r"(\[[\s\S]*\])", r"(\{[\s\S]*\})"):
        match = re.search(pattern, raw)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not extract JSON from LLM response. Raw (first 400 chars): {raw[:400]}")


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic models
# ══════════════════════════════════════════════════════════════════════════════

class SubtopicExerciseRequest(BaseModel):
    topic_name: str = Field(..., description="Parent topic name")
    subtopic_name: str = Field(..., description="Weak subtopic the student wants to practise")
    source_course: str = Field("", description="Source course from learning path step")
    num_exercises: int = Field(..., ge=0, le=20)
    difficulty: str = Field(
        default="mixed",
        description="Requested exercise difficulty: easy, medium, hard, or mixed",
    )

    @field_validator("topic_name", "subtopic_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()

    @field_validator("difficulty")
    @classmethod
    def valid_difficulty(cls, v: str) -> str:
        normalized = " ".join(str(v or "mixed").strip().lower().split())
        if normalized not in {"easy", "medium", "hard", "mixed"}:
            raise ValueError("difficulty must be easy, medium, hard, or mixed")
        return normalized


class GenerateExercisesRequest(BaseModel):
    student_id: str = Field(..., description="Student identifier")
    target_course: str = Field(..., description="Target course")
    subtopic_requests: List[SubtopicExerciseRequest]
    regeneration_nonce: Optional[str] = Field(
        default=None,
        description="Client-provided nonce used to force fresh exercise variations",
    )

    @field_validator("student_id", "target_course")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class Exercise(BaseModel):
    exercise_id: str
    title: Optional[str] = None
    exercise_type: str
    type: Optional[str] = None
    difficulty: str = "Medium"
    question: str
    options: Optional[Dict[str, str]] = None
    choices: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    answer: Optional[str] = None
    answer_text: Optional[str] = None
    explanation: Optional[str] = None


class ExerciseGroup(BaseModel):
    subtopic: Optional[str] = None
    topic_name: str
    subtopic_name: str
    source_course: str = ""
    exercises: List[Exercise]


class GenerateExercisesResponse(BaseModel):
    exercise_groups: List[ExerciseGroup]
    total_exercises_generated: int
    student_id: str
    target_course: str


# ══════════════════════════════════════════════════════════════════════════════
# LLM prompt builders
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = """\
You are Manara, an expert university-level interactive practice exercise generator.

CRITICAL OUTPUT RULE:
Return ONLY actual exercises/questions. Do NOT output summaries, definitions,
notes, topic lists, examples-to-read, study material, or headings such as
"Dictionary Fundamentals", "String Functions", or "Examples".

BAD ITEMS — NEVER GENERATE THESE AS QUESTIONS:
- "Definition and structure of key-value pairs"
- "Examples illustrating usage"
- "Appending to end of list"
- "Introduction to recursion"
- "Syntax of object instantiation"

Rules:
1. Generate EXACTLY the number of exercises requested – no more, no less.
2. Each item must be a real problem the student must solve.
3. Each item must include difficulty: "Easy", "Medium", or "Hard".
4. Vary exercise types: multiple_choice, coding, fill_blank, debugging,
   code_tracing, predict_output, short_answer, scenario.
5. Questions must test understanding, reasoning, problem-solving, debugging,
   code behavior, or transfer of knowledge. Avoid memorization-only recall.
6. For programming topics, include realistic code snippets whenever useful and
   ask for output, bug fixes, code completion, or behavior reasoning.
7. For conceptual topics, use scenario/application-based questions.
8. For multiple_choice: provide exactly 4 options (A, B, C, D) with ONE correct answer.
9. For all non-MCQ exercises: provide a concrete answer in answer_text.
10. Every exercise must include a step-by-step explanation.
11. Use proper LaTeX notation for mathematics: \\( … \\) inline, \\[ … \\] display.
12. Respond ONLY with a valid JSON array – no prose, no markdown fences.
13. Use the provided course material as grounding/context, but DO NOT copy random raw slide sentences.
14. First infer the weak subtopic's learning objective from the material, then write professor-style practice questions.
15. Prefer terminology, notation, examples, and methods used in the slides/material.
16. Do NOT ask about dates, chapter headers, slide numbers, PDF metadata, timestamps, or copied administrative text.
17. Do NOT invent unrelated textbook, internet, or broad-world examples.
18. If context is thin, stay close to the weak subtopic concept and avoid unrelated concepts.

JSON schema for each exercise object:
{
  "title": "<short exercise title, not a topic heading>",
  "exercise_type": "multiple_choice" | "short_answer" | "code_tracing" | "scenario",
  "type": "MCQ" | "Short Answer" | "Trace/Walkthrough" | "Scenario-based",
  "difficulty": "Easy" | "Medium" | "Hard",
  "question": "<actual solvable question/problem>",
  "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
  "choices": ["...", "...", "...", "..."],
  "correct_answer": "A" | "B" | "C" | "D",
  "answer": "<letter for MCQ, concrete answer for non-MCQ>",
  "answer_text": "<correct answer for non-MCQ; optional for MCQ>",
  "explanation": "<step-by-step explanation>"
}
"""


def _build_user_prompt(
    topic_name: str,
    subtopic_name: str,
    num_exercises: int,
    difficulty_request: str,
    context: str,
    already_used_questions: List[str],
    generation_nonce: str,
    variation_profile: str,
) -> str:
    avoid_block = ""
    if already_used_questions:
        avoid_block = (
            "\n\nALREADY USED QUESTIONS (do not repeat these or similar):\n"
            + "\n".join(f"- {q}" for q in already_used_questions[:10])
        )

    family = _concept_family(topic_name, subtopic_name, context)
    concept_blueprint = _concept_blueprint(family, difficulty_request)
    difficulty_guidance = {
        "easy": (
            "Generate ONLY Easy exercises. Use basic understanding, simple scenarios, "
            "straightforward code tracing, or one-step reasoning. Avoid trick cases."
        ),
        "medium": (
            "Generate ONLY Medium exercises. Use application, problem solving, "
            "slight reasoning, debugging, or small transfer scenarios."
        ),
        "hard": (
            "Generate ONLY Hard exercises. Use multi-step reasoning, edge cases, "
            "comparisons, tradeoffs, logic-based scenarios, or deeper debugging."
        ),
        "mixed": (
            "Generate a balanced mix of Easy, Medium, and Hard exercises when possible. "
            "Vary cognitive demand across the set."
        ),
    }.get(difficulty_request, "Generate a balanced mix of Easy, Medium, and Hard exercises when possible.")

    return f"""\
Topic: {topic_name}
	Subtopic: {subtopic_name}
	Number of exercises to generate: {num_exercises}
	Requested difficulty: {difficulty_request.title()}
	Difficulty guidance: {difficulty_guidance}
	Detected concept family: {family}
	Concept exercise blueprint:
	{concept_blueprint}
	Generation nonce: {generation_nonce}
	Variation profile for this click: {variation_profile}

Reference material for this subtopic:
\"\"\"
{context}
\"\"\"{avoid_block}

	HARD GROUNDING RULE:
	Use the provided course material context above to understand what the course teaches about this weak subtopic.
	Do not copy random slide sentences. Do not turn PDF text into meaningless fill-in-the-blank questions.
	Generate real educational exercises a professor could ask to test understanding of the weak concept.
	Do not invent unrelated concepts, outside examples, or internet-style textbook questions.
	Prefer terminology, notation, examples, and phrasing used in the retrieved slides/material.
	If context is insufficient, ask a narrower question that stays close to the retrieved material.

	Generate exactly {num_exercises} NEW interactive practice exercises for the subtopic "{subtopic_name}".
	Make every question domain-specific to "{subtopic_name}" and "{topic_name}".
	If the subtopic name sounds definition-heavy, convert it into an applied scenario or misconception check instead of asking for a bare definition.
	Difficulty must be obeyed exactly: if Easy, all items Easy; if Medium, all items Medium; if Hard, all items Hard; if Mixed, use a balanced mix.
	Use a natural distribution of question types:
	- Easy: MCQ, True/False, Fill in the Blank
	- Medium: Scenario, MCQ with reasoning, Trace/Walkthrough, Mini Problem Solving
	- Hard: Short Answer, Analysis, Compare/Justify, Explain reasoning
	Do not reuse common/default examples if another realistic scenario, number, input, code snippet, or comparison can test the same skill.
	Use the generation nonce to intentionally vary wording, values, scenarios, examples, and the difficulty mix when Mixed is requested.
	Each generated item must be a question/problem, not a note, summary, definition, or topic label.
	Return ONLY a JSON array of exercise objects matching the schema in the system prompt. No extra text.
	"""


# ══════════════════════════════════════════════════════════════════════════════
# Core generation logic
# ══════════════════════════════════════════════════════════════════════════════

_LLM_MODEL = "gpt-5.4-nano"
_MAX_RETRIES = 2
_TEMPERATURE = 0.85

_VARIATION_PROFILES = [
    "scenario-based transfer with different concrete values",
    "debugging and misconception-focused variants",
    "code tracing or output prediction when programming is relevant",
    "comparison/tradeoff questions with realistic constraints",
    "short problem-solving tasks with changed examples and numbers",
]


def _fallback_exercise(
    topic_name: str,
    subtopic_name: str,
    source_course: str,
    context: str,
    index: int,
    generation_nonce: str,
    difficulty_request: str,
) -> Exercise:
    """Last-resort professor-style exercise based on the weak concept, not raw slide text."""
    difficulty = _difficulty_for_index(difficulty_request, index)
    rng = random.Random(f"{generation_nonce}:{topic_name}:{subtopic_name}:{index}:{difficulty_request}")
    family = _concept_family(topic_name, subtopic_name, context)

    if family == "linear_search":
        arrays = [
            ([10, 20, 30, 40, 50, 60, 70, 80, 90], 90, "worst", 9),
            ([7, 13, 22, 31, 48, 55], 7, "best", 1),
            ([4, 9, 15, 16, 23, 42, 58], 16, "average", 4),
            ([5, 11, 19, 23, 37, 41], 100, "worst", 6),
            ([3, 6, 9, 12, 15, 18, 21], 12, "average", 4),
            ([2, 8, 14, 20, 26], 2, "best", 1),
        ]
        arr, target, case, comparisons = arrays[index % len(arrays)]
        if difficulty == "Easy":
            easy_variants = [
                (
                    f"In linear search, the target {target} is searched for in {arr}. Which case is represented?",
                    ["Best case", "Average case", "Worst case", "Binary search case"],
                    {"best": "A", "average": "B", "worst": "C"}[case],
                    f"Linear search checks items from left to right. This is the {case} case because the search needs {comparisons} comparison(s).",
                ),
                (
                    f"True or False: linear search may need to inspect every item in {arr} if the target is absent.",
                    ["True", "False", "Only if the array is sorted", "Only for binary search"],
                    "A",
                    "The statement is true. If the target is absent, linear search cannot stop early unless it has checked the whole list.",
                ),
            ]
            question, choices, answer_letter, explanation = easy_variants[index % len(easy_variants)]
            return _make_exercise(
                "Linear Search Case",
                "multiple_choice",
                difficulty,
                question,
                answer_letter,
                explanation,
                choices,
                answer_letter,
            )
        if difficulty == "Hard":
            contrast_target = arr[0] if target != arr[0] else arr[-1]
            contrast_comparisons = arr.index(contrast_target) + 1
            contrast_case = "best" if contrast_comparisons == 1 else "worst" if contrast_comparisons == len(arr) else "average"
            return _make_exercise(
                "Linear Search Comparison",
                "scenario",
                difficulty,
                f"Compare the number of comparisons linear search makes for target {contrast_target} versus target {target} in {arr}. What cases do they represent?",
                f"Searching for {contrast_target} is {contrast_case} case with {contrast_comparisons} comparison(s); searching for {target} is {case} case with {comparisons} comparison(s).",
                "The key idea is that linear search has no jumping strategy; it inspects elements sequentially until the target is found or the list ends.",
            )
        return _make_exercise(
            "Linear Search Walkthrough",
            "short_answer",
            difficulty,
            f"Linear search scans {arr} from left to right looking for {target}. How many comparisons are made, and why?",
            f"{comparisons} comparisons.",
            f"The algorithm compares against each item before reaching the target or exhausting the list, so this example demonstrates the {case} case.",
        )

    if family == "inference_rules":
        scenarios = [
            ("If it rains, the ground is wet.", "It rains.", "The ground is wet.", "Modus Ponens"),
            ("If a program has a syntax error, it will not compile.", "The program compiled.", "The program has no syntax error.", "Modus Tollens"),
            ("If p then q. If q then r.", "p is true.", "r is true.", "Hypothetical Syllogism followed by Modus Ponens"),
            ("p or q.", "not p.", "q.", "Disjunctive Syllogism"),
            ("If a student studies, then the student passes.", "The student did not pass.", "The student did not study.", "Modus Tollens"),
        ]
        p1, p2, conclusion, rule = scenarios[index % len(scenarios)]
        if difficulty == "Easy":
            return _make_exercise(
                "Inference Identification",
                "multiple_choice",
                difficulty,
                f"Given the premises: '{p1}' and '{p2}' What conclusion follows?",
                "A",
                f"The premises match {rule}, so the valid conclusion is: {conclusion}",
                [conclusion, "The first premise is false.", "The converse must be true.", "No conclusion can be drawn."],
                "A",
            )
        if difficulty == "Hard" and index % 2 == 1:
            return _make_exercise(
                "Invalid Inference Check",
                "scenario",
                difficulty,
                "A student argues: 'If p then q. q is true. Therefore p is true.' Is this valid? Explain the mistake.",
                "It is invalid; this is affirming the consequent.",
                "From p -> q and q, p does not necessarily follow. q could be true for another reason, so the argument does not match Modus Ponens.",
            )
        return _make_exercise(
            "Valid Deduction",
            "scenario",
            difficulty,
            f"Premise 1: {p1}\nPremise 2: {p2}\nState the valid conclusion and name the inference rule.",
            f"{conclusion} ({rule}).",
            f"The conclusion is supported because the premises follow the structure of {rule}.",
        )

    if family == "binary_search":
        size = [32, 64, 128, 256, 512][index % 5]
        comparisons = size.bit_length() - 1
        if difficulty == "Easy":
            easy_variants = [
                (
                    "Which condition must hold before binary search can be applied correctly?",
                    ["The array must contain only positive numbers", "The array must be sorted", "The target must be at the middle", "The array must have no duplicate values"],
                    "B",
                    "Binary search depends on ordering information to decide which half of the array can be discarded.",
                ),
                (
                    "True or False: binary search can safely discard half of the search space because the array is sorted.",
                    ["True", "False", "Only if the target is absent", "Only for arrays of even size"],
                    "A",
                    "The statement is true. Sorted order is what makes the half-elimination step valid.",
                ),
                (
                    "In binary search, which element is usually checked first?",
                    ["The first element", "The last element", "The middle element", "A random element"],
                    "C",
                    "Binary search starts at the middle so it can decide whether to continue in the left or right half.",
                ),
            ]
            question, choices, answer_letter, explanation = easy_variants[index % len(easy_variants)]
            return _make_exercise(
                "Binary Search Requirement",
                "multiple_choice",
                difficulty,
                question,
                answer_letter,
                explanation,
                choices,
                answer_letter,
            )
        if difficulty == "Hard":
            hard_cases = [
                ([4, 30, 12, 50, 8, 20, 16], 8),
                ([25, 3, 40, 7, 18, 60, 1], 3),
                ([14, 2, 31, 9, 45, 20, 6], 6),
            ]
            unsorted, target_value = hard_cases[index % len(hard_cases)]
            return _make_exercise(
                "Binary Search Failure Case",
                "scenario",
                difficulty,
                f"Explain why binary search can fail on the unsorted array {unsorted} when searching for {target_value}. Use the first middle comparison in your explanation.",
                f"Binary search can discard the half containing {target_value} because the array is not ordered, so the middle comparison gives misleading information.",
                "Binary search relies on sorted order to decide which half cannot contain the target. Without sorted order, eliminating half the array is not logically justified.",
            )
        return _make_exercise(
            "Binary Search Halving",
            "mini_problem",
            difficulty,
            f"A sorted array has {size} elements. In the worst case, about how many comparisons does binary search need, and why?",
            f"About {comparisons} comparisons.",
            f"Binary search halves the remaining search space each step, so the worst case is about log2({size}) = {comparisons}.",
        )

    if family == "classification":
        hard_variants = [
            (
                "A system predicts whether a student will pass or fail, while another predicts the exact final grade. Which task is classification, and why?",
                "Pass/fail prediction is classification; exact grade prediction is regression.",
                "Classification chooses among discrete labels or categories. Predicting an exact numeric value is regression.",
            ),
            (
                "A model labels support tickets as urgent, normal, or low priority. Explain why this is classification and identify the target variable.",
                "It is classification because the output is one of three labels; the target variable is ticket priority.",
                "The key feature is that the output is categorical, not a continuous number.",
            ),
            (
                "Two tasks are proposed: predicting tomorrow's temperature and deciding whether an image contains a cat. Which one is classification?",
                "Deciding whether an image contains a cat is classification.",
                "The image task maps input to a class label such as cat/not cat, while temperature prediction is numeric.",
            ),
        ]
        if difficulty == "Hard":
            question, answer, explanation = hard_variants[index % len(hard_variants)]
            return _make_exercise("Classification Reasoning", "scenario", difficulty, question, answer, explanation)
        if difficulty == "Medium":
            medium_variants = [
                (
                    "A dataset contains emails and the desired output is one of two labels: spam or not spam. What is the target variable, and why is this classification?",
                    "The target variable is the spam/not spam label; it is classification because the output is categorical.",
                    "Classification problems predict discrete classes. Here the model is choosing between two labels rather than predicting a numeric value.",
                ),
                (
                    "A system labels medical images as normal, benign, or malignant. Identify the type of learning problem and justify your answer.",
                    "It is a classification problem because the output is one of a fixed set of categories.",
                    "The important clue is the discrete label set: normal, benign, or malignant.",
                ),
            ]
            question, answer, explanation = medium_variants[index % len(medium_variants)]
            return _make_exercise("Classification Application", "scenario", difficulty, question, answer, explanation)
        return _make_exercise(
            "Classification Problem",
            "multiple_choice",
            difficulty,
            "Which of the following is a classification problem?",
            "B",
            "Spam detection assigns an email to a category: spam or not spam.",
            ["Predicting house price", "Determining whether an email is spam", "Calculating average GPA", "Sorting numbers"],
            "B",
        )

    if family == "algorithm":
        if difficulty == "Hard":
            hard_variants = [
                (
                    "A solution says: 'Repeat the previous step until the answer looks correct.' Why is this a weak algorithmic description?",
                    "The stopping condition is ambiguous, so the steps are not precise enough.",
                    "A proper algorithm should have clear, finite, unambiguous steps that different people can follow consistently.",
                ),
                (
                    "An instruction says: 'Sort the data in a smart way.' Which algorithm property is missing, and how would you improve the instruction?",
                    "The steps are not explicit or unambiguous; it should specify the exact sorting method and stopping condition.",
                    "Algorithms must describe a clear sequence of operations, not rely on vague judgment.",
                ),
                (
                    "A procedure has clear steps but may run forever for some inputs. Which required property of an algorithm is violated?",
                    "Finiteness is violated.",
                    "An algorithm must terminate after a finite number of steps for valid inputs.",
                ),
            ]
            question, answer, explanation = hard_variants[index % len(hard_variants)]
            return _make_exercise("Algorithm Precision", "scenario", difficulty, question, answer, explanation)
        if difficulty == "Medium":
            medium_variants = [
                (
                    "A procedure receives a list of numbers, repeatedly compares adjacent values, and stops after the list is sorted. Which parts correspond to input, processing, and output?",
                    "Input: the list of numbers. Processing: repeated comparisons and swaps. Output: the sorted list.",
                    "An algorithm can be analyzed by identifying what data enters, what steps transform it, and what result is produced.",
                ),
                (
                    "Two students describe a solution. One gives numbered finite steps; the other says 'solve it using intuition.' Which description is closer to an algorithm, and why?",
                    "The numbered finite steps are closer to an algorithm because they are clear and executable.",
                    "Algorithms require precise, finite instructions that can be followed consistently.",
                ),
            ]
            question, answer, explanation = medium_variants[index % len(medium_variants)]
            return _make_exercise("Algorithm Structure", "scenario", difficulty, question, answer, explanation)
        easy_variants = [
            (
                "Which option best describes an algorithm?",
                ["A random process", "A finite sequence of steps to solve a problem", "A hardware storage device", "A programming language only"],
                "B",
                "An algorithm is a finite sequence of clear steps for solving a problem.",
            ),
            (
                "True or False: an algorithm should have clear steps that another person can follow.",
                ["True", "False", "Only if it is written in Python", "Only if it uses a loop"],
                "A",
                "The statement is true. Clarity and unambiguity are core properties of an algorithm.",
            ),
            (
                "Which property is missing if a procedure may continue forever for some input?",
                ["Input", "Finiteness", "Formatting", "Storage"],
                "B",
                "An algorithm must terminate after a finite number of steps.",
            ),
        ]
        question, choices, answer_letter, explanation = easy_variants[index % len(easy_variants)]
        return _make_exercise(
            "Algorithm Recognition",
            "multiple_choice",
            difficulty,
            question,
            answer_letter,
            explanation,
            choices,
            answer_letter,
        )

    if family == "sorting":
        return _make_exercise(
            "Sorting Method",
            "multiple_choice",
            difficulty,
            "A list is sorted by repeatedly selecting the smallest remaining value and placing it next. Which method does this describe?",
            "A",
            "Selection sort repeatedly selects the smallest unsorted element and moves it into position.",
            ["Selection sort", "Binary search", "Hashing", "Breadth-first search"],
            "A",
        )

    if family == "recursion":
        return _make_exercise(
            "Recursive Base Case",
            "short_answer",
            difficulty,
            "A recursive factorial function reaches factorial(1). What role does this condition play?",
            "It is the base case that stops recursive calls.",
            "The base case prevents infinite recursion and gives the function a known result to build back from.",
        )

    return _make_exercise(
        f"{subtopic_name} Application",
        "scenario",
        difficulty,
        f"Create a small exam-style example that applies '{subtopic_name}' from {source_course or 'the course'}, then state the correct answer.",
        "A correct response must apply the weak subtopic directly and justify the answer from the course concept.",
        "This checks whether the learner can use the concept, not just repeat a title or copied slide sentence.",
    )


async def _generate_exercises_for_subtopic(
    topic_name: str,
    subtopic_name: str,
    num_exercises: int,
    difficulty_request: str,
    source_course: str,
    deduplicator: ExerciseDeduplicator,
    request_nonce: Optional[str] = None,
) -> List[Exercise]:
    import openai as _openai  # import here so it's in scope for exception handling

    passages = query_chroma_for_subtopic(source_course, topic_name, subtopic_name)
    context = build_context_block(passages)
    logger.info(
        "[EXERCISE RAG] course=%r topic=%r subtopic=%r passages=%d context_chars=%d difficulty=%s requested=%d",
        source_course,
        topic_name,
        subtopic_name,
        len(passages),
        len(context),
        difficulty_request,
        num_exercises,
    )
    if not _context_has_material(context):
        logger.warning(
            "[EXERCISE RAG] no retrieved course material for course=%r topic=%r subtopic=%r; generation will stay in thin-context mode",
            source_course,
            topic_name,
            subtopic_name,
        )

    client = get_openai_client()
    exercises: List[Exercise] = []
    already_used: List[str] = []
    generation_nonce = f"{request_nonce or uuid.uuid4().hex}-{uuid.uuid4().hex}"
    variation_profile = random.choice(_VARIATION_PROFILES)

    for attempt in range(_MAX_RETRIES + 1):
        remaining = num_exercises - len(exercises)
        if remaining <= 0:
            break

        prompt = _build_user_prompt(
            topic_name=topic_name,
            subtopic_name=subtopic_name,
            num_exercises=remaining,
            difficulty_request=difficulty_request,
            context=context,
            already_used_questions=already_used,
            generation_nonce=f"{generation_nonce}-{attempt}",
            variation_profile=variation_profile,
        )

        try:
            response = await client.chat.completions.create(
                model=_LLM_MODEL,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
            )
        except _openai.OpenAIError as exc:
            logger.error("OpenAI API error for subtopic '%s': %s", subtopic_name, exc)
            break

        raw = response.choices[0].message.content or ""

        try:
            parsed = extract_json_from_llm_response(raw)
        except ValueError as exc:
            logger.warning("JSON extraction failed (attempt %d) for '%s': %s", attempt + 1, subtopic_name, exc)
            if attempt == _MAX_RETRIES:
                break
            continue

        if not isinstance(parsed, list):
            logger.warning("LLM did not return a list for '%s'", subtopic_name)
            continue

        for raw_ex in parsed:
            if not isinstance(raw_ex, dict):
                continue

            question = str(raw_ex.get("question", "")).strip()
            if not question:
                continue

            if deduplicator.is_duplicate(question):
                continue

            ex_type = str(raw_ex.get("exercise_type") or raw_ex.get("type") or "short_answer").lower()
            ex_type = ex_type.replace("-", "_").replace(" ", "_")
            type_aliases = {
                "mcq": "multiple_choice",
                "multiple_choice": "multiple_choice",
                "multiplechoice": "multiple_choice",
                "true_false": "multiple_choice",
                "true/false": "multiple_choice",
                "fill_blank": "short_answer",
                "fill_in_the_blank": "short_answer",
                "short": "short_answer",
                "short_answer": "short_answer",
                "mini_problem": "scenario",
                "mini_problem_solving": "scenario",
                "problem_solving": "scenario",
                "trace": "code_tracing",
                "walkthrough": "code_tracing",
                "trace/walkthrough": "code_tracing",
                "trace_walkthrough": "code_tracing",
                "scenario_based": "scenario",
                "scenario": "scenario",
            }
            ex_type = type_aliases.get(ex_type, ex_type)
            allowed_types = {
                "multiple_choice",
                "coding",
                "fill_blank",
                "debugging",
                "code_tracing",
                "predict_output",
                "mini_problem",
                "true_false",
                "fill_blank",
                "short_answer",
                "scenario",
                "essay",
            }
            if ex_type not in allowed_types:
                ex_type = "short_answer"

            title = str(raw_ex.get("title", "")).strip() or None
            difficulty = str(raw_ex.get("difficulty", "Medium")).strip().capitalize()
            if difficulty not in {"Easy", "Medium", "Hard"}:
                difficulty = "Medium"
            if difficulty_request in {"easy", "medium", "hard"}:
                difficulty = difficulty_request.capitalize()

            if _is_note_like_item(question):
                logger.info("Rejected note-like exercise for '%s': %s", subtopic_name, question[:120])
                continue
            if _is_raw_slide_artifact(question):
                logger.info("Rejected raw slide artifact exercise for '%s': %s", subtopic_name, question[:120])
                continue

            options: Optional[Dict[str, str]] = None
            correct_answer: Optional[str] = None
            answer_text: Optional[str] = None

            if ex_type == "multiple_choice":
                raw_opts = raw_ex.get("options") or {}
                if isinstance(raw_opts, dict):
                    options = {k: str(v) for k, v in raw_opts.items() if k in ("A", "B", "C", "D")}
                if (not options) and isinstance(raw_ex.get("choices"), list):
                    labels = ("A", "B", "C", "D")
                    options = {
                        labels[i]: str(choice)
                        for i, choice in enumerate(raw_ex["choices"][:4])
                    }
                ca = str(raw_ex.get("correct_answer", "")).upper().strip()
                if not ca:
                    raw_answer = str(raw_ex.get("answer", "")).strip()
                    ca = raw_answer[:1].upper() if raw_answer else ""
                correct_answer = ca if ca in ("A", "B", "C", "D") else None

                if not options or len(options) < 2 or correct_answer is None:
                    # Broken MCQ → fall back to essay
                    ex_type = "essay"
                    options = None
                    correct_answer = None
                    answer_text = str(raw_ex.get("answer_text") or raw_ex.get("answer") or "").strip() or f"See explanation: {str(raw_ex.get('explanation', '')).strip()}"
            else:
                # essay or coding — ensure answer_text is not None
                raw_answer = str(raw_ex.get("answer_text") or raw_ex.get("answer") or "").strip()
                answer_text = raw_answer if raw_answer else str(raw_ex.get("explanation", "")).strip() or "See explanation below."

            explanation = str(raw_ex.get("explanation", "")).strip() or None

            ex = Exercise(
                exercise_id=str(uuid.uuid4()),
                title=normalise_math(title) if title else None,
                exercise_type=ex_type,
                type={
                    "multiple_choice": "MCQ",
                    "short_answer": "Short Answer",
                    "code_tracing": "Trace/Walkthrough",
                    "scenario": "Scenario-based",
                }.get(ex_type, ex_type.replace("_", " ").title()),
                difficulty=difficulty,
                question=normalise_math(question),
                options={k: normalise_math(v) for k, v in options.items()} if options else None,
                choices=[normalise_math(options[k]) for k in ("A", "B", "C", "D") if options and k in options] if options else None,
                correct_answer=correct_answer,
                answer=correct_answer if correct_answer else (normalise_math(answer_text) if answer_text else None),
                answer_text=normalise_math(answer_text) if answer_text else None,
                explanation=normalise_math(explanation) if explanation else None,
            )

            deduplicator.register(question)
            already_used.append(question)
            exercises.append(ex)

            if len(exercises) >= num_exercises:
                break

    if len(exercises) < num_exercises:
        logger.warning(
            "Requested %d exercises for '%s' but generated only %d.",
            num_exercises, subtopic_name, len(exercises),
        )
        fallback_attempt = 0
        while len(exercises) < num_exercises:
            fallback = _fallback_exercise(
                topic_name=topic_name,
                subtopic_name=subtopic_name,
                source_course=source_course,
                context=context,
                index=len(exercises) + fallback_attempt,
                generation_nonce=generation_nonce,
                difficulty_request=difficulty_request,
            )
            if not deduplicator.is_duplicate(fallback.question):
                if "retrieved course material" in fallback.question.lower() or "limited" in fallback.question.lower():
                    logger.warning(
                        "[EXERCISE FALLBACK] thin context fallback used for course=%r topic=%r subtopic=%r",
                        source_course,
                        topic_name,
                        subtopic_name,
                    )
                deduplicator.register(fallback.question)
                exercises.append(fallback)
            else:
                fallback_attempt += 1
                if fallback_attempt > max(20, num_exercises * 5):
                    fallback.question = normalise_math(f"{fallback.question}\n\nFocus on a different part of the reasoning than the previous exercise.")
                    deduplicator.register(fallback.question)
                    exercises.append(fallback)
                generation_nonce = uuid.uuid4().hex

    return exercises[:num_exercises]


# ══════════════════════════════════════════════════════════════════════════════
# Public orchestration function
# ══════════════════════════════════════════════════════════════════════════════

async def generate_exercises_for_student(
    student_id: str,
    target_course: str,
    subtopic_requests: List[SubtopicExerciseRequest],
    regeneration_nonce: Optional[str] = None,
) -> GenerateExercisesResponse:
    subtopic_requests = [req for req in subtopic_requests if req.num_exercises > 0]
    if not subtopic_requests:
        raise ValueError("At least one subtopic request is required.")

    deduplicator = ExerciseDeduplicator()

    tasks = [
        _generate_exercises_for_subtopic(
            topic_name=req.topic_name,
            subtopic_name=req.subtopic_name,
            num_exercises=req.num_exercises,
            difficulty_request=req.difficulty,
            source_course=req.source_course or target_course,
            deduplicator=deduplicator,
            request_nonce=regeneration_nonce,
        )
        for req in subtopic_requests
    ]

    results: List[List[Exercise]] = await asyncio.gather(*tasks, return_exceptions=False)

    exercise_groups: List[ExerciseGroup] = []
    total = 0

    for req, exercises in zip(subtopic_requests, results):
        group = ExerciseGroup(
            subtopic=req.subtopic_name,
            topic_name=req.topic_name,
            subtopic_name=req.subtopic_name,
            source_course=req.source_course,
            exercises=exercises,
        )
        exercise_groups.append(group)
        total += len(exercises)

    logger.info(
        "generate_exercises_for_student: student=%s course=%s groups=%d total=%d",
        student_id, target_course, len(exercise_groups), total,
    )

    return GenerateExercisesResponse(
        exercise_groups=exercise_groups,
        total_exercises_generated=total,
        student_id=student_id,
        target_course=target_course,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI endpoint
# ══════════════════════════════════════════════════════════════════════════════

@exercise_router.post(
    "/generate-exercises",
    response_model=GenerateExercisesResponse,
    summary="Generate practice exercises for weak subtopics",
    status_code=status.HTTP_200_OK,
)
async def generate_exercises_endpoint(
    body: GenerateExercisesRequest,
) -> GenerateExercisesResponse:
    try:
        result = await generate_exercises_for_student(
            student_id=body.student_id,
            target_course=body.target_course,
            subtopic_requests=body.subtopic_requests,
            regeneration_nonce=body.regeneration_nonce,
        )
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error in generate_exercises_endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating exercises.",
        ) from exc
