from __future__ import annotations

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import re
import hashlib
import csv
import random
import threading
from pathlib import Path
from typing import Any
from collections import defaultdict

import chromadb
from openai import OpenAI
from chromadb.utils import embedding_functions


# =========================================================
# CONFIG
# =========================================================t

PROJECT_DIR = Path(os.environ.get("MANARA_PROJECT_DIR", "/Users/dinaal-memah/Desktop/graduation project 2"))
COURSES_DIR = PROJECT_DIR / "courses"
PROGRESS_RESULTS_DIR = PROJECT_DIR / "progress_tracking_results"
RELATED_SUBTOPICS_CSV = PROJECT_DIR / "related_subtopics.csv"

MODEL_NAME = "gpt-4o-mini"
MAX_DEPTH = 1     
MAX_COMPLETION_TOKENS = 5000

QUESTIONS_PER_SUBTOPIC = 10
PASS_MARK = 6  # 6 or less = fail, greater than 6 = pass

DIFFICULTY_DISTRIBUTION = {
    "easy": 3,
    "medium": 4,
    "hard": 3,
}

# Temporary thesis-defense demo mode. Set MANARA_DEMO_FORCE_CORRECT_ANSWER_A=0
# after the demo to restore distributed answer labels for mini quizzes.
DEMO_FORCE_CORRECT_ANSWER_A = os.getenv("MANARA_DEMO_FORCE_CORRECT_ANSWER_A", "1").strip().lower() not in {"0", "false", "no", "off"}

_openai_client = None
_openai_client_key_fingerprint = None

def get_llm_client():
    global _openai_client, _openai_client_key_fingerprint
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    fingerprint = f"{key[:7]}...{key[-4:]} len={len(key)}"
    if _openai_client is None or _openai_client_key_fingerprint != fingerprint:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=key)
        _openai_client_key_fingerprint = fingerprint
        print(f"[OPENAI CONFIG] exam1 using OPENAI_API_KEY {fingerprint}")
    return _openai_client


# =========================================================
# HELPERS
# =========================================================

def safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).strip().lower()).strip("_")


def normalize_name(text: str) -> str:
    cleaned = re.sub(r"[_\-]+", " ", str(text).strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def diagnostic_subtopic_key(
    source_course: str,
    source_topic_name: str,
    source_subtopic_name: str,
) -> tuple[str, str, str]:
    """
    Stable identity for prerequisite coverage in diagnostic exams.

    One key may contribute at most one question to a diagnostic. This prevents
    semantic repetition where the wording changes but the assessed prerequisite
    subtopic is the same.
    """
    return (
        normalize_name(source_course),
        normalize_name(source_topic_name),
        normalize_name(source_subtopic_name),
    )


def diagnostic_subtopic_key_from_question(question: dict[str, Any]) -> tuple[str, str, str]:
    return diagnostic_subtopic_key(
        question.get("source_course", ""),
        question.get("source_topic_name", ""),
        question.get("source_subtopic_name", ""),
    )


def diagnostic_subtopic_key_from_cluster(cluster: dict[str, Any]) -> tuple[str, str, str]:
    return diagnostic_subtopic_key(
        cluster.get("primary_source_course", ""),
        cluster.get("primary_topic_name", ""),
        cluster.get("primary_subtopic_name", ""),
    )


def question_signature(question_text: str) -> str:
    """Exact-match fingerprint (MD5 of normalised text)."""
    normalized = normalize_name(question_text)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


# ── Semantic / near-duplicate helpers ─────────────────────────────────────────

def _tokenize(text: str) -> set[str]:
    """Lower-case word tokens, stripping punctuation."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard_similarity(a: str, b: str) -> float:
    """Word-level Jaccard similarity between two strings."""
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# Stop-words to ignore when extracting the core concept of a question.
_STOP_WORDS = frozenset({
    "what", "which", "how", "when", "where", "who", "why", "is", "are",
    "the", "a", "an", "of", "in", "to", "that", "does", "do", "can",
    "best", "describes", "refers", "following", "correct", "statement",
    "about", "with", "for", "its", "this", "these", "those", "term",
    "used", "most", "one", "true", "false", "example", "called",
})

def extract_concept_keywords(question_text: str) -> frozenset[str]:
    """
    Return the meaningful content words from a question.
    Two questions sharing many concept keywords likely test the same idea.
    """
    tokens = _tokenize(question_text)
    return frozenset(t for t in tokens if t not in _STOP_WORDS and len(t) > 2)


# Overlap coefficient: divides shared concept words by the SMALLER set size.
# So it says "every word in the smaller question also appears in the bigger one - they're about the same thing."
# More sensitive than Jaccard — catches cases where one question is a shorter
# version of another (e.g. "What is X?" vs "What is X used for in Y context?").
def concept_overlap(a: str, b: str) -> float:
    """
    Overlap coefficient on content-word sets — more sensitive than Jaccard
    for detecting same-concept questions that differ in question framing.
    """
    ka, kb = extract_concept_keywords(a), extract_concept_keywords(b)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / min(len(ka), len(kb))


# Threshold constants
_JACCARD_THRESHOLD = 0.50   # ≥50 % word overlap → near-duplicate (intra-cluster)
_CONCEPT_THRESHOLD = 0.65   # ≥65 % concept-word overlap → same concept (intra-cluster)

# Tighter thresholds for cross-exam concept dedup — applied to (question + answer) text
# so "What is an algorithm?" and "What is defined as a precise sequence of actions?"
# both collapse to the same learning objective even from different clusters/courses.
_EXAM_CONCEPT_JACCARD = 0.42
_EXAM_CONCEPT_OVERLAP = 0.52


_READINESS_SKILL_RULES: list[tuple[str, list[str]]] = [
	# Detects weight/box analogy questions — if already in exam, reject duplicates
    ("HEAVY_BOX_REASONING", [
        r"\b(heavy\s+box|heavier\s+box|boxes)\b",
    ]),
	# Detects "when is binary search suitable?" questions — only one allowed per exam
    ("BINARY_SEARCH_SUITABILITY", [
    ("BINARY_SEARCH_SUITABILITY", [
        r"\bbinary search\b.{0,140}\b(sorted|unsorted|suitable|appropriate|choose|select|array|search space)\b",
        r"\b(sorted|unsorted)\b.{0,140}\bbinary search\b",
    ]),
	# Detects "how many steps does binary search take?" questions — only one allowed per exam
    ("LOGARITHMIC_STEP_COUNT", [
        r"\b(log\s*2|log₂|logarithmic)\b.{0,80}\b(steps?|comparisons?|halvings?|iterations?)\b",
        r"\b(how many|number of)\s+(steps?|comparisons?|halvings?|iterations?)\b",
        r"\b(defective\s+bulb|bulb)\b.{0,120}\b(halv(?:e|ing)|search space|steps?|comparisons?)\b",
    ]),
	# Detects divide and conquer strategy questions — only one allowed per exam
    ("DIVIDE_AND_CONQUER_STRATEGY", [
        r"\bdivide.and.conquer\b.{0,160}\b(strategy|approach|decompos|subproblem|recursive|split|break|selection|suitable)\b",
    ]),
	# Detects formal logic questions (modus ponens etc.) — only one allowed per exam
    ("INFERENCE_CHAIN", [
        r"\b(modus ponens|modus tollens|hypothetical syllogism|disjunctive syllogism|affirming the consequent|denying the antecedent)\b",
        r"\b(which inference rule|what conclusion follows|valid conclusion|derive|premises?)\b",
        r"[¬~]?\s*[pqr]\s*(?:→|->|implies)\s*[pqr]",
    ]),
	# Detects "which algorithm should you use?" questions — only one allowed per exam
    ("ALGORITHM_SELECTION", [
        r"\b(which|select|choose|suitable|appropriate|best)\b.{0,90}\b(algorithm|approach|search|strategy)\b",
        r"\b(binary search|linear search|breadth.first|depth.first|bfs|dfs)\b.{0,120}\b(sorted|unsorted|constraint|scenario|appropriate)\b",
    ]),
	# Detects time complexity questions about search algorithms — only one allowed per exam
    ("SEARCH_COMPLEXITY", [
        r"\b(worst|best|average).?case\b.{0,80}\b(comparisons?|search|linear|binary|complexity)\b",
        r"\b(complexity|runtime|running time)\b.{0,80}\b(search|algorithm)\b",
    ]),
	# Detects recursive decomposition questions — only one allowed per exam
    ("DECOMPOSITION", [
        r"\b(decompos|recursive|subproblem|break.*problem)\b",
    ]),
	# Detects classical programming vs machine learning questions — only one allowed per exam
    ("CLASSICAL_VS_ML", [
        r"\b(machine learning|ml|learns? from examples?|training data|labeled faces?|facial recognition|classification)\b",
        r"\b(classical|rule.based|explicit programming)\b.{0,120}\b(machine learning|examples|training)\b",
    ]),
	# Detects valid/invalid argument questions — only one allowed per exam
    ("VALID_DEDUCTION", [
        r"\b(sound|valid|invalid)\b.{0,100}\b(argument|deduction|inference|conclusion)\b",
    ]),
	# Detects tradeoff/comparison questions — only one allowed per exam
    ("TRADEOFF_COMPARISON", [
        r"\b(trade.?off|compare|comparison|prefer|advantage|disadvantage|constraint)\b",
    ]),
	# Detects "does course X prepare you for course Y?" questions — only one allowed per exam
    ("READINESS_TRANSFER", [
        r"\b(readiness|prepares?|foundation|supports?|enables?)\b.{0,100}\b(target|course|ai|data engineering|machine learning)\b",
    ]),
]


def classify_readiness_skill_family(question_text: str, answer_text: str = "") -> str | None:
    """Classify the academic readiness skill tested by a diagnostic question."""
    combined = normalize_name(f"{question_text} {answer_text}")
    for family, patterns in _READINESS_SKILL_RULES:
        if any(re.search(pattern, combined) for pattern in patterns):
            return family
    return None


def validate_diagnostic_question_quality(
    question: dict[str, Any],
    context_text: str = "",
) -> tuple[bool, str, str | None]:
    """
    Deterministic final gate for generated diagnostic questions.

    This supplements prompt instructions with hard rejection rules for common
    invalid logic, unsupported algorithm assumptions, weak hard questions, and
    grounding drift. It is intentionally conservative: bad questions are easier
    to regenerate than to explain away in a readiness diagnostic.
    """
    q_text = str(question.get("question", "")).strip()
    options = question.get("options", {}) if isinstance(question.get("options", {}), dict) else {}
    correct = str(question.get("correct_answer", "A")).strip().upper()
    answer = str(options.get(correct, options.get("A", ""))).strip()
    explanation = str(question.get("explanation", "")).strip()
    difficulty = str(question.get("difficulty", "")).strip().lower()
    combined = normalize_name(f"{q_text} {answer} {explanation}")
    logic_text = str(f"{q_text} {answer} {explanation}").strip().lower()
    logic_text = re.sub(r"(?:→|->|⇒)", " implies ", logic_text)
    logic_text = re.sub(r"(?:¬|~)", " not ", logic_text)
    logic_text = re.sub(r"\s+", " ", logic_text)
    context_norm = normalize_name(context_text)
    family = classify_readiness_skill_family(q_text, answer)

    if not q_text or not answer:
        return False, "empty question or correct answer", family

    target_course = normalize_name(question.get("diagnostic_target_course", ""))
    source_text = normalize_name(
        " ".join(
            [
                str(question.get("source_course", "")),
                str(question.get("source_topic_name", "")),
                str(question.get("source_subtopic_name", "")),
            ]
        )
    )
    low_readiness_patterns = [
        r"\bthreshold\b.{0,80}\b(print|printing|output|display)\b",
        r"\b(print|prints|printed|output|displays?)\b.{0,80}\b(threshold|passed|failed|true|false)\b",
        r"\b(input|process|processing|output)\b.{0,80}\b(program|ipo|stage|phase)\b",
        r"\b(object instantiation|instantiate|constructor syntax|self keyword|variable declaration|declare a variable)\b",
        r"\bwhat (is|will be) (printed|displayed|output)\b",
        r"\bsyntax\b.{0,80}\b(class|object|variable|method|function)\b",
    ]
    low_source_patterns = [
        "variable declaration",
        "programs typically input processing output",
        "input process output",
        "threshold printing",
        "object instantiation",
    ]
    intro_programming_signal = (
        any(term in target_course or term in source_text for term in ("programming", "coding", "computer science"))
        and any(term in target_course or term in source_text for term in ("intro", "introduction", "fundamental", "beginner", "basic"))
    )
    if any(re.search(pattern, combined) for pattern in low_readiness_patterns):
        if not intro_programming_signal:
            return False, "global low-readiness syntax/trivia question", family
    if any(pattern in source_text for pattern in low_source_patterns):
        if not intro_programming_signal:
            return False, "global low-readiness source subtopic", family

    invalid_logic_patterns = [
        (r"\bnot\s+p\s+implies\s+q\b.{0,160}\bp\b.{0,160}(?:therefore|conclude|concludes?|follows?|claim|claims?).{0,60}\bq\b", "invalid antecedent for ¬p→q"),
        (r"\bp\s+implies\s+q\b.{0,160}\bq\b.{0,160}(?:therefore|conclude|concludes?|follows?|claim|claims?).{0,60}\bp\b", "affirming the consequent"),
        (r"\bp\s+implies\s+q\b.{0,160}\bnot\s+p\b.{0,160}(?:therefore|conclude|concludes?|follows?|claim|claims?).{0,60}\bnot\s+q\b", "denying the antecedent"),
        (r"\bp\s+implies\s+q\b.{0,160}\bq\b.{0,160}(?:claim|claims?|conclude|concludes?|therefore|follows?).{0,60}\bp\b", "claiming p from p→q and q"),
        (r"\bnot\s+p\s+implies\s+q\b.{0,160}\bp\b.{0,160}(?:claim|claims?|conclude|concludes?|therefore|follows?).{0,60}\bq\b", "claiming q from ¬p→q and p"),
        (r"\bp\s+implies\s+q\b.{0,160}\bnot\s+q\b.{0,160}(?:claim|claims?|conclude|concludes?|therefore|follows?).{0,60}\bp\b", "invalid Modus Tollens conclusion"),
        (r"efficient.{0,80}minimi[sz](?:e|es|ing|ed) resources.{0,180}minimi[sz](?:e|es|ing|ed) resources.{0,180}(?:therefore|conclude|follows?|what follows).{0,80}efficient", "affirming the consequent with efficiency/resources"),
    ]
    for pattern, reason in invalid_logic_patterns:
        if re.search(pattern, logic_text) or re.search(pattern, combined):
            return False, reason, family

    logic_signal = any(
        term in logic_text or term in combined
        for term in (
            "premise", "premises", "implies", "conclusion", "conclude", "therefore",
            "modus ponens", "modus tollens", "hypothetical syllogism",
            "disjunctive syllogism", "logical conclusion", "follows from",
        )
    )
    if logic_signal:
        unrelated_premise_pattern = (
            r"\bp\s+implies\s+q.{0,120}\br\s+implies\s+s"
            r".{0,160}(?:therefore|conclude|follows?|claim).{0,80}\b(?:q|s|p|r)\b"
        )
        if re.search(unrelated_premise_pattern, logic_text) and not any(
            bridge in combined
            for bridge in ("q implies r", "q -> r", "q→r", "hypothetical syllogism")
        ):
            return False, "unsupported conclusion from unrelated premises", family

    if "binary search" in combined and ("unsorted" in combined or "not sorted" in combined):
        answer_norm = normalize_name(answer)
        if "binary search" in answer_norm and not any(term in answer_norm for term in ("not", "cannot", "invalid", "inappropriate", "requires sorted", "linear search")):
            return False, "binary search selected for unsorted data", family

    if difficulty == "hard":
        hard_reasoning_terms = (
            "justify", "because", "constraint", "trade", "compare", "comparison",
            "valid", "invalid", "premises", "derive", "two step", "multi step",
            "under the condition", "under these constraints", "fails because",
        )
        weak_hard_patterns = [
            r"\bhow many\b.{0,80}\b(steps?|comparisons?|halvings?|iterations?)\b",
            r"\bif\b.{0,40}\b(doubles?|triples?|quadruples?)\b.{0,100}\b(how many|number of)\b",
            r"\blog\s*2\s*\(?\s*\d+",
        ]
        if any(re.search(pattern, combined) for pattern in weak_hard_patterns) and not any(term in combined for term in hard_reasoning_terms):
            return False, "hard question is arithmetic/size substitution, not reasoning", family
        if re.match(r"\s*(what|which|how many)\b", normalize_name(q_text)) and not any(term in combined for term in hard_reasoning_terms):
            return False, "hard question lacks comparison, justification, constraints, or multi-step reasoning", family
        if not any(term in combined for term in hard_reasoning_terms):
            return False, "hard question lacks explicit reasoning, comparison, constraints, or deduction", family

    drift_terms = (
        "noise robustness", "robust to noise", "tripling the dataset improves",
        "dataset tripling improves", "superior to", "always better", "guarantees better",
    )
    for term in drift_terms:
        if term in combined and term not in context_norm:
            return False, f"unsupported grounding drift: {term}", family

    if ("o(log n)" in combined or "logarithmic" in combined) and not any(term in context_norm for term in ("o(log", "logarithmic", "binary search", "halve", "halving", "divide and conquer")):
        return False, "unsupported logarithmic complexity claim", family

    return True, "accepted", family


def is_near_duplicate(candidate: str, existing_questions: list[str]) -> bool:
    """
    Return True if *candidate* is too similar to any question already accepted.
    Uses both Jaccard word-overlap and concept-keyword overlap.
    """
    for existing in existing_questions:
        if jaccard_similarity(candidate, existing) >= _JACCARD_THRESHOLD:
            return True
        if concept_overlap(candidate, existing) >= _CONCEPT_THRESHOLD:
            return True
    return False


def is_exam_concept_duplicate(candidate_q: str, candidate_a: str, selected: list[dict]) -> bool:
    """
    Cross-exam concept-level dedup.

    Combines question text + correct answer text for a richer signal, then
    compares against every already-selected question using tighter thresholds.

    Catches cases where different clusters/courses generate questions that test
    the same learning objective despite different surface wording, e.g.:
      "What is an algorithm defined as?"
      "What is defined as a precise sequence of actions?"
    Both are testing algorithm-definition recall and should not coexist.
    """
    candidate_combined = (candidate_q + " " + candidate_a).strip()
    for s in selected:
        s_correct = s.get("correct_answer", "A")
        s_answer  = str(s.get("options", {}).get(s_correct, "")).strip()
        existing_combined = (str(s.get("question", "")) + " " + s_answer).strip()
        if jaccard_similarity(candidate_combined, existing_combined) >= _EXAM_CONCEPT_JACCARD:
            return True
        if concept_overlap(candidate_combined, existing_combined) >= _EXAM_CONCEPT_OVERLAP:
            return True
    return False


def ask_llm(prompt: str) -> str:
    response = get_llm_client().chat.completions.create(
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
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        timeout=60,
    )
    return response.choices[0].message.content.strip()


def extract_json_block(text: str):
    match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    if not match:
        return None

    raw = match.group(0)

    # ── Repair invalid JSON escape sequences produced by LLMs ────────────────
    # LLMs emit LaTeX like \( \) \frac \sum inside JSON string values.
    # These are not valid JSON escape sequences and cause json.loads to fail.
    # Valid JSON escapes are only: \" \\ \/ \b \f \n \r \t \uXXXX
    # So replace any \X where X is not one of those with \\X.
    def repair_json_escapes(s: str) -> str:
        return re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)

    try:
        return json.loads(raw)
    except Exception:
        pass

    try:
        return json.loads(repair_json_escapes(raw))
    except Exception:
        return None

def force_correct_answer_a(options: dict, correct_answer: str) -> tuple[dict, str]:
    correct_answer = str(correct_answer).strip().upper()

    if correct_answer not in {"A", "B", "C", "D"}:
        return options, "A"

    if correct_answer == "A":
        return options, "A"

    fixed_options = dict(options)

    fixed_options["A"], fixed_options[correct_answer] = (
        fixed_options[correct_answer],
        fixed_options["A"],
    )

    return fixed_options, "A"

def ask_llm_for_json(prompt: str, max_retries: int = 3):
    last_response = ""

    for attempt in range(1, max_retries + 1):
        raw = ask_llm(prompt)
        parsed = extract_json_block(raw)

        if parsed is not None:
            return parsed

        last_response = raw
        print(f"Retry {attempt}/{max_retries}: invalid JSON returned by model.")

    raise ValueError(f"LLM failed to return valid JSON.\nLast response:\n{last_response}")

def ask_llm_fast(prompt: str, max_tokens: int = 1500, max_retries: int = 2):
    """
    Lighter LLM call used by the diagnostic batch generator.
    Uses fewer max_tokens (MCQ batches are small) and fewer retries
    to minimise latency for the diagnostic exam flow.
    """
    last_response = ""
    for attempt in range(1, max_retries + 1):
        try:
            print(
                "[DIAG LLM] request "
                f"model={MODEL_NAME} attempt={attempt}/{max_retries} "
                f"prompt_chars={len(prompt)} max_tokens={max_tokens}"
            )
            response = get_llm_client().chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise academic question writer. "
                            "Return clean JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=max_tokens,
                timeout=45,
            )
            choice = response.choices[0] if response.choices else None
            raw = (choice.message.content or "").strip() if choice and choice.message else ""
            finish_reason = getattr(choice, "finish_reason", None) if choice else None
            usage = getattr(response, "usage", None)
            print(
                "[DIAG LLM] response "
                f"model={getattr(response, 'model', MODEL_NAME)} "
                f"finish_reason={finish_reason!r} raw_chars={len(raw)} "
                f"usage={usage}"
            )
            if raw:
                print(f"[DIAG LLM] raw_preview={raw[:500]!r}")
            else:
                print(f"[DIAG LLM] empty_raw response={str(response)[:1000]!r}")
            parsed = extract_json_block(raw)
            if parsed is not None:
                parsed_size = len(parsed) if isinstance(parsed, list) else 1
                print(f"[DIAG LLM] parsed type={type(parsed).__name__} size={parsed_size}")
                return parsed
            last_response = raw
            print(
                "[DIAG LLM] parse_failed "
                f"attempt={attempt}/{max_retries} raw_preview={raw[:500]!r}"
            )
        except Exception as e:
            last_response = str(e)
            print(f"[DIAG LLM] exception attempt={attempt}/{max_retries}: {last_response}")
            if is_fatal_openai_error_text(last_response):
                break
    raise ValueError(f"ask_llm_fast failed.\nLast response:\n{last_response}")


def is_fatal_openai_error_text(text: str) -> bool:
    """Errors that retries or alternate semantic clusters cannot fix."""
    lowered = str(text).lower()
    return any(
        marker in lowered
        for marker in (
            "invalid_api_key",
            "incorrect api key",
            "authentication failed",
            "insufficient_quota",
            "billing",
            "unsupported_value",
            "401",
        )
    )


def summarize_openai_error(text: str) -> str:
    lowered = str(text).lower()
    if "invalid_api_key" in lowered or "incorrect api key" in lowered or "401" in lowered:
        return "OpenAI authentication failed. The configured API key is invalid."
    if "insufficient_quota" in lowered or "billing" in lowered:
        return "OpenAI quota or billing is unavailable for question generation."
    if "unsupported_value" in lowered:
        return "OpenAI rejected one of the request parameters for the configured model."
    return "OpenAI question generation failed."


def ask_student_choice() -> str:
    while True:
        answer = input("Your answer (A/B/C/D): ").strip().upper()
        if answer in {"A", "B", "C", "D"}:
            return answer
        print("Invalid choice. Please enter A, B, C, or D.")


def ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(prompt).strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer with y/n.")


# =========================================================
# COURSE FOLDER + CHROMA HELPERS
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


# Cache ChromaDB clients and the embedding function to avoid
# re-opening the same database multiple times per request.
_chroma_client_cache: dict[str, object] = {}
_embedding_function_singleton = None
_chroma_lock = threading.RLock()


def get_chroma_client(chroma_dir: Path):
    key = str(chroma_dir)
    with _chroma_lock:
        if key not in _chroma_client_cache:
            _chroma_client_cache[key] = chromadb.PersistentClient(path=key)
        return _chroma_client_cache[key]


def get_embedding_function():
    global _embedding_function_singleton
    with _chroma_lock:
        if _embedding_function_singleton is None:
            _embedding_function_singleton = embedding_functions.DefaultEmbeddingFunction()
        return _embedding_function_singleton


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
    except Exception as e:
        print(
            f"[CHROMA ERROR] collection={collection_name} "
            f"path={chroma_dir} "
            f"error={e}"
        )
        return None


# =========================================================
# PATH LOADING
# =========================================================
# Later you can tweak this to match your friend's exact path JSON.

def load_generated_path(path_file: Path) -> dict:
    if not path_file.exists():
        raise FileNotFoundError(f"Generated path file not found: {path_file}")

    with open(path_file, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_path_subtopics(path_data: dict) -> list[dict]:
    """
    Expected temporary format:
    {
      "student_id": "...",
      "student_name": "...",
      "target_course": "...",
      "generated_path": [
        {
          "course_name": "Data Engineering",
          "topic_name": "...",
          "subtopic_name": "..."
        }
      ]
    }
    """
    if "generated_path" not in path_data or not isinstance(path_data["generated_path"], list):
        raise ValueError("generated_path list not found in path file.")

    rows = []
    seen = set()

    for item in path_data["generated_path"]:
        course_name = str(item.get("course_name", "")).strip()
        topic_name = str(item.get("topic_name", "")).strip()
        subtopic_name = str(item.get("subtopic_name", "")).strip()

        if not course_name or not topic_name or not subtopic_name:
            continue

        dedup_key = (
            normalize_name(course_name),
            normalize_name(topic_name),
            normalize_name(subtopic_name),
        )
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        rows.append({
            "course_name": course_name,
            "topic_name": topic_name,
            "subtopic_name": subtopic_name,
        })

    if not rows:
        raise ValueError("No valid path subtopics found in generated_path.")

    return rows


# =========================================================
# TARGET COURSE RETRIEVAL
# =========================================================

def retrieve_course_material(
    course_name: str,
    topic_name: str,
    subtopic_name: str,
    n_chunk_results: int = 8,
    n_summary_results: int = 2,
    n_concept_results: int = 3,
) -> dict[str, Any]:
    chunks_collection = get_collection(course_name, "_chunks")
    summaries_collection = get_collection(course_name, "_summaries")
    concepts_collection = get_collection(course_name, "_concepts")

    query_text = (
        f"Topic: {topic_name}\n"
        f"Subtopic: {subtopic_name}\n"
        f"Find the most relevant study material for progress tracking quiz generation."
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
                result["chunks"].append({"text": doc, "metadata": meta})
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
                result["summaries"].append({"text": doc, "metadata": meta})
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
                f"Chapter: {meta.get('chapter', '')} | "
                f"Chunk ID: {meta.get('chunk_id', '')}\n"
                f"{item.get('text', '')}"
            )

    return "\n\n".join(parts).strip()


# =========================================================
# SEMANTIC DIAGNOSTIC ENGINE
# =========================================================

def _norm_course_key(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def _semantic_score(link_count: int, avg_distance: float) -> float:
    """Higher means denser, closer semantic evidence."""
    return round((link_count / (1.0 + link_count)) * (1.0 - min(avg_distance, 1.0)), 4)


def get_related_subtopics_for_diagnostic(
    target_course: str,
    completed_courses: list[str],
    limit: int = 80,
) -> list[dict[str, Any]]:
    """
    Return completed-course subtopics semantically connected to target_course.

    This is the graph-expansion entry point for Manara's diagnostic engine.
    It reads the preprocessing/KG artifact related_subtopics.csv and keeps
    only edges where one side is the target course and the other side is one
    of the student's completed courses.
    """
    target_key = _norm_course_key(target_course)
    completed_lookup = {
        _norm_course_key(course): str(course).strip()
        for course in completed_courses
        if str(course).strip()
    }

    if not target_key or not completed_lookup or not RELATED_SUBTOPICS_CSV.exists():
        print(
            "[DIAG SEMANTIC] expansion unavailable "
            f"target={target_course!r} completed={len(completed_lookup)} "
            f"csv_exists={RELATED_SUBTOPICS_CSV.exists()}"
        )
        return []

    aggregate: dict[tuple[str, str, str], dict[str, Any]] = {}

    try:
        with open(RELATED_SUBTOPICS_CSV, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                source_course = str(row.get("source_course", "")).strip()
                target_course_row = str(row.get("target_course", "")).strip()
                source_key = _norm_course_key(source_course)
                target_row_key = _norm_course_key(target_course_row)

                completed_side = None
                target_side = None

                if source_key == target_key and target_row_key in completed_lookup:
                    completed_side = {
                        "course_name": completed_lookup[target_row_key],
                        "topic_name": str(row.get("target_topic", "")).strip(),
                        "subtopic_name": str(row.get("target_subtopic", "")).strip(),
                    }
                    target_side = {
                        "topic_name": str(row.get("source_topic", "")).strip(),
                        "subtopic_name": str(row.get("source_subtopic", "")).strip(),
                    }
                elif target_row_key == target_key and source_key in completed_lookup:
                    completed_side = {
                        "course_name": completed_lookup[source_key],
                        "topic_name": str(row.get("source_topic", "")).strip(),
                        "subtopic_name": str(row.get("source_subtopic", "")).strip(),
                    }
                    target_side = {
                        "topic_name": str(row.get("target_topic", "")).strip(),
                        "subtopic_name": str(row.get("target_subtopic", "")).strip(),
                    }

                if not completed_side or not target_side:
                    continue
                if not completed_side["topic_name"] or not completed_side["subtopic_name"]:
                    continue

                try:
                    distance = float(str(row.get("distance", "1")).strip())
                except ValueError:
                    distance = 1.0

                key = (
                    _norm_course_key(completed_side["course_name"]),
                    completed_side["topic_name"].strip().lower(),
                    completed_side["subtopic_name"].strip().lower(),
                )
                item = aggregate.setdefault(
                    key,
                    {
                        **completed_side,
                        "chapter": "",
                        "semantic_link_count": 0,
                        "semantic_distance_total": 0.0,
                        "target_course": target_course,
                        "related_target_topics": set(),
                        "related_target_subtopics": set(),
                    },
                )
                item["semantic_link_count"] += 1
                item["semantic_distance_total"] += distance
                if target_side["topic_name"]:
                    item["related_target_topics"].add(target_side["topic_name"])
                if target_side["subtopic_name"]:
                    item["related_target_subtopics"].add(target_side["subtopic_name"])
    except Exception as exc:
        print(f"[DIAG SEMANTIC] could not read related_subtopics.csv: {exc}")
        return []

    related: list[dict[str, Any]] = []
    for item in aggregate.values():
        link_count = max(1, int(item["semantic_link_count"]))
        avg_distance = item["semantic_distance_total"] / link_count
        related.append(
            {
                "course_name": item["course_name"],
                "topic_name": item["topic_name"],
                "subtopic_name": item["subtopic_name"],
                "chapter": item.get("chapter", ""),
                "semantic_link_count": link_count,
                "semantic_avg_distance": round(avg_distance, 4),
                "semantic_score": _semantic_score(link_count, avg_distance),
                "target_course": target_course,
                "related_target_topics": sorted(item["related_target_topics"])[:8],
                "related_target_subtopics": sorted(item["related_target_subtopics"])[:8],
                "diagnostic_source": "semantic_target_expansion",
            }
        )

    related.sort(
        key=lambda x: (
            x.get("semantic_score", 0),
            x.get("semantic_link_count", 0),
            -x.get("semantic_avg_distance", 1),
        ),
        reverse=True,
    )
    print(
        "[DIAG SEMANTIC] expansion "
        f"target={target_course!r} completed={len(completed_lookup)} "
        f"candidates={len(related)} returning={min(len(related), limit)}"
    )
    return related[:limit]


def _cluster_key_for_related_subtopic(row: dict[str, Any]) -> str:
    targets = row.get("related_target_subtopics") or []
    if targets:
        return normalize_name(str(targets[0]))
    topics = row.get("related_target_topics") or []
    if topics:
        return normalize_name(str(topics[0]))
    return normalize_name(row.get("subtopic_name", ""))


def build_semantic_diagnostic_clusters(
    target_course: str,
    completed_courses: list[str],
    max_clusters: int = 10,
    max_related_subtopics: int = 80,
) -> list[dict[str, Any]]:
    """
    Build semantic prerequisite clusters for diagnostic generation.

    A cluster is a target-course concept area plus the strongest completed-
    course concepts that support it.  The diagnostic exam should sample these
    clusters, not isolated local subtopics.
    """
    related = get_related_subtopics_for_diagnostic(
        target_course=target_course,
        completed_courses=completed_courses,
        limit=max_related_subtopics,
    )
    if not related:
        return []

    grouped: dict[str, dict[str, Any]] = {}
    for row in related:
        key = _cluster_key_for_related_subtopic(row)
        if not key:
            key = normalize_name(row.get("subtopic_name", ""))

        cluster = grouped.setdefault(
            key,
            {
                "cluster_id": safe_slug(f"{target_course}_{key}")[:80],
                "target_course": target_course,
                "target_topics": set(),
                "target_subtopics": set(),
                "related_concepts": [],
                "source_courses": set(),
                "semantic_link_count": 0,
                "semantic_score_total": 0.0,
                "semantic_avg_distance_total": 0.0,
            },
        )

        cluster["target_topics"].update(row.get("related_target_topics", []))
        cluster["target_subtopics"].update(row.get("related_target_subtopics", []))
        cluster["source_courses"].add(row["course_name"])
        cluster["semantic_link_count"] += int(row.get("semantic_link_count", 1))
        cluster["semantic_score_total"] += float(row.get("semantic_score", 0))
        cluster["semantic_avg_distance_total"] += float(row.get("semantic_avg_distance", 1))
        cluster["related_concepts"].append(row)

    clusters: list[dict[str, Any]] = []
    for cluster in grouped.values():
        concepts = sorted(
            cluster["related_concepts"],
            key=lambda x: (
                x.get("semantic_score", 0),
                x.get("semantic_link_count", 0),
                -x.get("semantic_avg_distance", 1),
            ),
            reverse=True,
        )
        concept_count = max(1, len(concepts))
        primary = concepts[0]
        source_key = diagnostic_subtopic_key(
            primary["course_name"],
            primary["topic_name"],
            primary["subtopic_name"],
        )
        clusters.append(
            {
                "cluster_id": cluster["cluster_id"],
                "target_course": target_course,
                "target_topics": sorted(cluster["target_topics"])[:8],
                "target_subtopics": sorted(cluster["target_subtopics"])[:8],
                "related_concepts": concepts[:8],
                "source_courses": sorted(cluster["source_courses"]),
                "primary_source_course": primary["course_name"],
                "primary_topic_name": primary["topic_name"],
                "primary_subtopic_name": primary["subtopic_name"],
                "source_subtopic_key": "|".join(source_key),
                "semantic_link_count": cluster["semantic_link_count"],
                "semantic_score": round(cluster["semantic_score_total"] / concept_count, 4),
                "semantic_avg_distance": round(cluster["semantic_avg_distance_total"] / concept_count, 4),
                "diagnostic_source": "semantic_cluster",
            }
        )

    clusters.sort(
        key=lambda x: (
            x.get("semantic_score", 0),
            x.get("semantic_link_count", 0),
            len(x.get("source_courses", [])),
        ),
        reverse=True,
    )

    # ── Debug: per-course stats before selection ────────────────────────────
    by_course_all: dict[str, list] = defaultdict(list)
    for cl in clusters:
        by_course_all[cl["primary_source_course"]].append(cl)
    print(f"[DIAG COVERAGE] target={target_course!r} — course cluster distribution before selection:")
    for crs, crs_clusters in sorted(by_course_all.items(), key=lambda x: -sum(c["semantic_score"] for c in x[1])):
        scores = [c["semantic_score"] for c in crs_clusters]
        subs = [c["primary_subtopic_name"] for c in crs_clusters]
        print(
            f"  course={crs!r} cluster_count={len(crs_clusters)} "
            f"avg_score={sum(scores)/len(scores):.4f} max_score={max(scores):.4f} "
            f"subtopics={subs}"
        )

    # ── Breadth-first selection across source courses ────────────────────────
    # Round-robin: one slot per course per pass before giving any course a second
    # slot. Uniqueness enforced by BOTH the full (course,topic,subtopic) triple AND
    # the subtopic name alone — this prevents near-duplicate questions where the
    # same concept (e.g. "Definition of algorithm") appears under slightly different
    # topic headings or in multiple source courses.
    by_course: dict[str, list] = defaultdict(list)
    for cluster in clusters:  # already sorted by semantic_score desc
        by_course[cluster["primary_source_course"]].append(cluster)

    # Randomise course order so no course always gets priority on ties.
    course_order = list(by_course.keys())
    random.shuffle(course_order)

    selected: list[dict[str, Any]] = []
    seen_cluster_ids: set[str] = set()
    seen_source_subtopic_keys: set[tuple[str, str, str]] = set()
    seen_subtopic_names: set[str] = set()          # uniqueness by name alone
    course_counts: dict[str, int] = defaultdict(int)
    cursors: dict[str, int] = {c: 0 for c in course_order}

    while len(selected) < max_clusters:
        advanced = False
        for course in course_order:
            if len(selected) >= max_clusters:
                break
            pool = by_course[course]
            idx = cursors[course]
            while idx < len(pool):
                cand = pool[idx]
                idx += 1
                cid = cand["cluster_id"]
                skey = diagnostic_subtopic_key_from_cluster(cand)
                subtopic_norm = normalize_name(cand.get("primary_subtopic_name", ""))
                if (
                    cid not in seen_cluster_ids
                    and skey not in seen_source_subtopic_keys
                    and subtopic_norm not in seen_subtopic_names
                ):
                    seen_cluster_ids.add(cid)
                    seen_source_subtopic_keys.add(skey)
                    seen_subtopic_names.add(subtopic_norm)
                    course_counts[course] += 1
                    selected.append(cand)
                    advanced = True
                    break
            cursors[course] = idx
        if not advanced:
            break

    # ── Debug: post-selection coverage summary ───────────────────────────────
    selected_ids = {c["cluster_id"] for c in selected}
    print(f"[DIAG COVERAGE] target={target_course!r} — selection summary:")
    for crs, crs_clusters in sorted(by_course_all.items(), key=lambda x: -sum(c["semantic_score"] for c in x[1])):
        sel = [c for c in crs_clusters if c["cluster_id"] in selected_ids]
        not_sel = [c for c in crs_clusters if c["cluster_id"] not in selected_ids]
        print(
            f"  course={crs!r} total={len(crs_clusters)} selected={len(sel)} skipped={len(not_sel)} "
            f"selected_subtopics={[c['primary_subtopic_name'] for c in sel]}"
        )

    print(
        "[DIAG SEMANTIC] cluster build "
        f"target={target_course!r} related_rows={len(related)} "
        f"clusters={len(clusters)} selected={len(selected)} "
        f"unique_source_subtopics={len(seen_source_subtopic_keys)} "
        f"source_course_counts={dict(course_counts)}"
    )
    for idx, cluster in enumerate(selected[:max_clusters], start=1):
        print(
            "[DIAG SEMANTIC] cluster "
            f"#{idx} id={cluster['cluster_id']} score={cluster['semantic_score']} "
            f"links={cluster['semantic_link_count']} sources={cluster['source_courses']} "
            f"subtopic={cluster['primary_subtopic_name']!r} targets={cluster['target_subtopics'][:3]}"
        )

    return selected[:max_clusters]


def _query_collection_items(
    collection: Any,
    query_text: str,
    n_results: int,
    kind: str,
    course_name: str,
    semantic_concept: dict[str, Any],
) -> list[dict[str, Any]]:
    if collection is None:
        return []
    try:
        with _chroma_lock:
            results = collection.query(query_texts=[query_text], n_results=n_results)
    except Exception as exc:
        print(
            "[DIAG SEMANTIC] retrieval failed "
            f"course={course_name!r} kind={kind} subtopic={semantic_concept.get('subtopic_name')!r}: {exc}"
        )
        return []

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(docs)
    items: list[dict[str, Any]] = []
    for doc, meta, distance in zip(docs, metas, distances):
        try:
            chroma_distance = float(distance) if distance is not None else 1.0
        except (TypeError, ValueError):
            chroma_distance = 1.0
        semantic_score = float(semantic_concept.get("semantic_score", 0))
        rerank_score = semantic_score + max(0.0, 1.0 - min(chroma_distance, 1.0))
        merged_meta = dict(meta or {})
        merged_meta.update(
            {
                "course_name": course_name,
                "semantic_source_topic": semantic_concept.get("topic_name", ""),
                "semantic_source_subtopic": semantic_concept.get("subtopic_name", ""),
                "semantic_score": semantic_score,
                "semantic_link_count": semantic_concept.get("semantic_link_count", 0),
                "chroma_distance": round(chroma_distance, 4),
                "rerank_score": round(rerank_score, 4),
                "retrieval_kind": kind,
            }
        )
        items.append({"text": doc, "metadata": merged_meta, "rerank_score": rerank_score})
    return items


def retrieve_semantic_cluster_material(
    semantic_cluster: dict[str, Any],
    n_chunk_results_per_concept: int = 3,
    n_summary_results_per_concept: int = 1,
    n_concept_results_per_concept: int = 2,
    max_chunks: int = 10,
    max_summaries: int = 4,
    max_concepts: int = 6,
) -> dict[str, Any]:
    """
    Retrieve and rerank material across all completed-course concepts in a
    semantic cluster. This is intentionally multi-course and cluster-centric.
    """
    retrieved = {"chunks": [], "summaries": [], "concepts": []}
    target_text = " ".join(
        [semantic_cluster.get("target_course", "")]
        + semantic_cluster.get("target_topics", [])
        + semantic_cluster.get("target_subtopics", [])
    )

    for concept in semantic_cluster.get("related_concepts", []):
        resolved_course = resolve_course_folder_name(
            concept["course_name"],
            build_course_name_map(),
        )

        if not resolved_course:
            print(
                f"[DIAG SEMANTIC] Could not resolve course folder for "
                f"{concept['course_name']!r}"
            )
            continue

        course_name = resolved_course
        query_text = (
            f"Target course readiness: {target_text}\n"
            f"Completed course: {course_name}\n"
            f"Prerequisite topic: {concept['topic_name']}\n"
            f"Prerequisite subtopic: {concept['subtopic_name']}\n"
            "Retrieve material that can test whether this completed-course "
            "knowledge prepares the student for the target course."
        )
        collections = {
            "chunks": get_collection(course_name, "_chunks"),
            "summaries": get_collection(course_name, "_summaries"),
            "concepts": get_collection(course_name, "_concepts"),
        }
        retrieved["chunks"].extend(
            _query_collection_items(
                collections["chunks"],
                query_text,
                n_chunk_results_per_concept,
                "chunk",
                course_name,
                concept,
            )
        )
        retrieved["summaries"].extend(
            _query_collection_items(
                collections["summaries"],
                query_text,
                n_summary_results_per_concept,
                "summary",
                course_name,
                concept,
            )
        )
        retrieved["concepts"].extend(
            _query_collection_items(
                collections["concepts"],
                query_text,
                n_concept_results_per_concept,
                "concept",
                course_name,
                concept,
            )
        )

    for key, max_items in (
        ("chunks", max_chunks),
        ("summaries", max_summaries),
        ("concepts", max_concepts),
    ):
        retrieved[key].sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        retrieved[key] = retrieved[key][:max_items]

    semantic_cluster["retrieved_material"] = retrieved
    print(
        "[DIAG SEMANTIC] cluster retrieval "
        f"id={semantic_cluster.get('cluster_id')} "
        f"chunks={len(retrieved['chunks'])} summaries={len(retrieved['summaries'])} "
        f"concepts={len(retrieved['concepts'])} "
        f"sources={semantic_cluster.get('source_courses', [])}"
    )
    return retrieved


def build_semantic_cluster_context(
    semantic_cluster: dict[str, Any],
    retrieved: dict[str, Any],
    max_chars: int = 6500,
) -> str:
    parts = [
        "=== SEMANTIC DIAGNOSTIC CLUSTER ===",
        f"Target course: {semantic_cluster.get('target_course', '')}",
        "Target subtopics: " + "; ".join(semantic_cluster.get("target_subtopics", []) or ["N/A"]),
        "Completed source courses: " + "; ".join(semantic_cluster.get("source_courses", []) or ["N/A"]),
        "Related prerequisite concepts:",
    ]
    for concept in semantic_cluster.get("related_concepts", [])[:6]:
        parts.append(
            "- "
            f"{concept.get('course_name')} / {concept.get('topic_name')} / "
            f"{concept.get('subtopic_name')} "
            f"(score={concept.get('semantic_score')}, links={concept.get('semantic_link_count')})"
        )

    def append_items(title: str, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        parts.append(f"\n=== {title} ===")
        for i, item in enumerate(items, start=1):
            meta = item.get("metadata", {})
            parts.append(
                f"[{title.title()} {i}] Course: {meta.get('course_name', '')} | "
                f"Source subtopic: {meta.get('semantic_source_subtopic', '')} | "
                f"File: {meta.get('relative_path', '')} | "
                f"Rerank: {meta.get('rerank_score', '')}\n"
                f"{item.get('text', '')}"
            )

    append_items("concepts", retrieved.get("concepts", []))
    append_items("summaries", retrieved.get("summaries", []))
    append_items("chunks", retrieved.get("chunks", []))
    return "\n\n".join(parts).strip()[:max_chars]


def assess_cluster_educational_relevance(
    cluster: dict[str, Any],
    context_text: str,
) -> tuple[str, str]:
    """
    LLM-based predictive-value filter.

    Asks: "Would MASTERY of this prerequisite concept meaningfully PREDICT
    whether a student can succeed in the target course?"

    This is stronger than asking if the content is 'educationally relevant' —
    it filters for concepts that are genuine readiness indicators, not just
    adjacent knowledge or memorisable definitions.

    Returns (rating, reason):
      HIGH   — strong predictor of target-course success, keep
      MEDIUM — somewhat useful supporting knowledge, keep
      LOW    — poor predictor (memorisation, trivia, rote recall), reject

    Called once per cluster, BEFORE question generation.
    """
    target_course   = cluster.get("target_course", "")
    source_course   = cluster.get("primary_source_course", "")
    source_topic    = cluster.get("primary_topic_name", "")
    source_subtopic = cluster.get("primary_subtopic_name", "")

    context_snippet = context_text[:2500]
    combined_signal = " ".join(
        [
            str(source_course),
            str(source_topic),
            str(source_subtopic),
            str(context_snippet),
        ]
    ).lower()

    low_readiness_patterns = [
        r"\b(object instantiation|instantiate an object|instantiation syntax|constructor syntax)\b",
        r"\b(class creation syntax|create a class|class syntax|self keyword|dunder init)\b",
        r"\b(variable declaration|declare a variable|assignment statement|print statement)\b",
        r"\b(api call|api syntax|library syntax|method call syntax|boilerplate)\b",
        r"\b(database system definition|what is a database|database definitions?|basic definitions?)\b",
        r"\b(simple boolean|boolean recall|true or false|condition is false|programs typically|input[, ]+processing[, ]+(and )?output|input processing output)\b",
        r"\b(definition recall|terminology recall|memorize|recall-only|recall only)\b",
        r"\b(what is|define|definition of)\b.{0,80}\b(algorithm|database|class|object|variable|method|function|interface)\b",
        r"\b(syntax|boilerplate)\b.{0,80}\b(class|object|variable|method|function|api)\b",
    ]
    for pattern in low_readiness_patterns:
        if re.search(pattern, combined_signal, flags=re.IGNORECASE):
            return (
                "LOW",
                "primarily syntax, definition, boilerplate, or recall-only material; weak predictive readiness signal",
            )

    prompt = f"""You are a strict diagnostic exam filter. Your only job is to predict what type of MCQ this slide will produce, then decide whether that question type genuinely predicts readiness for {target_course}.

TARGET COURSE: {target_course}
PREREQUISITE: {source_course} → {source_topic} → {source_subtopic}

SLIDE CONTENT:
{context_snippet}

Return ONLY this JSON (no prose, no fences):
{{"rating": "HIGH" | "MEDIUM" | "LOW", "reason": "one sentence — state the expected question type and why weakness in it would or would not predict difficulty in {target_course}"}}

━━━ EVALUATION PROCEDURE — follow this exact order ━━━

═══ STEP 1: PREDICT THE QUESTION TYPE THIS SLIDE WILL PRODUCE ═══

Read the slide content above. Ask yourself:
"If I generated a grounded multiple-choice question from this exact slide text, what TYPE of question would most likely emerge?"

LOW-VALUE QUESTION TYPES → rate LOW immediately, do not proceed to Step 2:
  • Definition recall — "What is an algorithm?", "What is pseudocode?", "What is a database system?"
  • Terminology recall — "What is this loop type called?", "What is the name of this pattern?"
  • Representation recall — "What does a flowchart show?", "What are the parts of a diagram?"
  • Syntax recall — "How do you declare a variable?", "How do you instantiate an object?", "What does self refer to?"
  • Toy-example recall — sentinel loop, grade-check if/else, print statement, plotting labels
  • IPO/control-flow recall — "What happens when condition is false?", "Programs have Input, Process, Output"
  • Naming a complexity class — "What is the time complexity of linear search?" → O(n) is a name, not reasoning
  • Formula memorization — reciting a formula without any interpretation or application
  • Meta-recall — "What should students memorize about X?", "What is highlighted on the slide?"
  • Course-description facts — "What does this course cover?", "What are the learning objectives?"
  • Slide-wording recall — question answerable by copying one sentence verbatim from the slide

HIGH-VALUE QUESTION TYPES → proceed to Step 2:
  • Reasoning — explaining WHY something works, not just WHAT it is called
  • Application — applying a concept to a described scenario or problem
  • Comparison / trade-off — when to choose A over B and why
  • Inference / deduction — deriving a conclusion from given premises or data
  • Abstraction / decomposition — breaking a problem into components, modelling a system
  • Complexity / scalability intuition — WHEN and WHY performance degrades, not just naming the class
  • Algorithmic thinking — evaluating which approach solves a problem better
  • Mathematical reasoning with interpretation — not reciting a formula, but using it to reason
  • Transfer — applying prerequisite knowledge to a new target-course scenario

MIXED-CONTENT RULE — critical for slides that contain both definitions and reasoning:
If a slide contains one sentence about WHY or HOW surrounded by mostly definitional or listing content:
→ ask "what question would a typical question-writer MOST NATURALLY produce from this slide?"
→ if the answer is a definition or naming question → rate LOW.
→ do NOT cherry-pick the one reasoning sentence to justify a HIGH rating.
The dominant content determines the rating, not the best-case sentence.

If the most likely question is ANY low-value type → rate LOW. Stop here.

═══ STEP 2: PREDICTIVE READINESS VALUE FOR {target_course} ═══

You have confirmed the slide will produce a HIGH-VALUE question type.
Now ask: "Would a student who CANNOT answer this question likely fail, stall, or face major difficulty when learning {target_course}?"

If NO → rate LOW.
If YES → rate HIGH or MEDIUM:
  HIGH: weakness would likely cause failure or major difficulty in target-course concepts
        because the prerequisite transfers directly into reasoning/problem-solving
  MEDIUM: weakness would slow or indirectly weaken understanding, but would not likely block success

HIGH is NOT allowed for semantic relatedness alone.
HIGH requires at least one of:
  • transferable reasoning
  • conceptual dependency
  • problem-solving ability
  • cognitive transfer to target concepts

Even if semantically related, these are almost never HIGH:
  • object instantiation syntax
  • class creation syntax
  • database definitions / basic definitions
  • programming boilerplate
  • API trivia
  • recall-only terminology
  • simple boolean or control-flow recall

Target-course guidance (use the relevant row):
	  Artificial Intelligence    → HIGH: inference, search reasoning, classification intuition, abstraction, logic application, probability reasoning
	                               LOW: "What is an algorithm?", database definitions, object/class syntax, pseudocode recall, flowchart naming, syntax trivia
  Data Engineering           → HIGH: data modeling, schema design, structured vs unstructured, scalability, statistics reasoning, data pipeline logic
                               LOW: sentinel loops, grade examples, plotting labels, formula name without interpretation
  Machine Learning           → HIGH: probability intuition, classification reasoning, overfitting intuition, mathematical reasoning, feature understanding
                               LOW: syntax trivia, terminology memorization, one-formula-definition recall
  Database Systems           → HIGH: normalization reasoning, schema understanding, relational thinking, query logic, trade-offs
                               LOW: memorized SQL syntax wording, recall-only definitions
  Natural Language Processing → HIGH: probability reasoning, sequence modeling intuition, linguistic abstraction, classification judgment
                               LOW: definition recall, syntax trivia
  Data Mining / Analytics    → HIGH: statistical reasoning, pattern recognition logic, model evaluation understanding, abstraction
                               LOW: tool usage trivia, chart label recall, formula name recall

If the target course is not listed: apply the same principle — does mastery of the PREDICTED QUESTION TYPE directly help the student succeed in that course?

━━━ EXAMPLES (apply regardless of topic label) ━━━

TOPIC: Algorithms — SLIDE SAYS "An algorithm is a precise sequence of steps"
→ Expected question: "What is an algorithm?" → definition recall → LOW
→ (Topic is important. Slide is not. Rate the SLIDE.)

TOPIC: Algorithms — SLIDE SHOWS divide-and-conquer with efficiency analysis
→ Expected question: "Why does divide-and-conquer reduce time complexity here?" → reasoning → HIGH for AI/DE
→ Rate HIGH.

TOPIC: Rules of Inference — SLIDE SAYS "memorize: Modus Ponens, Modus Tollens"
→ Expected question: "What is the name of this inference rule?" → terminology recall → LOW

TOPIC: Rules of Inference — SLIDE SHOWS applying Modus Ponens to derive a conclusion
→ Expected question: "Given these premises, which conclusion follows?" → inference/application → HIGH for AI

TOPIC: Loops — SLIDE SHOWS a sentinel-loop grade-processing example
→ Expected question: "What value stops this loop?" → toy-example recall → LOW for any advanced course

TOPIC: Data Modeling — SLIDE DISCUSSES normalization trade-offs with examples
→ Expected question: "Why would denormalization improve read performance at the cost of consistency?" → trade-off reasoning → HIGH for Data Engineering

IMPORTANT: The topic label is irrelevant. Rate what the SLIDE CONTENT will actually produce.
"""

    try:
        response = get_llm_client().chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise academic evaluator. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=80,
            timeout=20,
        )
        raw = (response.choices[0].message.content or "").strip()
        parsed = extract_json_block(raw)
        if isinstance(parsed, dict):
            rating = str(parsed.get("rating", "LOW")).strip().upper()
            reason = str(parsed.get("reason", "")).strip()
            if rating not in {"HIGH", "MEDIUM", "LOW"}:
                print(
                    f"[DIAG RELEVANCE] unrecognized rating={rating!r} from LLM — defaulting to LOW "
                    f"course={source_course!r} subtopic={source_subtopic!r}"
                )
                rating = "LOW"
            return rating, reason
        # LLM returned something unparseable — conservative rejection
        print(
            f"[DIAG RELEVANCE] unparseable LLM response — defaulting to LOW "
            f"course={source_course!r} subtopic={source_subtopic!r} raw={raw[:200]!r}"
        )
    except Exception as exc:
        print(
            f"[DIAG RELEVANCE] filter exception — defaulting to LOW "
            f"course={source_course!r} subtopic={source_subtopic!r} error={exc}"
        )

    # Conservative: prefer a shorter but higher-quality diagnostic over
    # allowing irrelevant content through on any failure.
    return "LOW", "filter failed — conservative rejection"


def generate_questions_from_semantic_cluster(
    semantic_cluster: dict[str, Any],
    n_questions: int,
    difficulty_distribution: dict[str, int],
    previous_question_texts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Generate diagnostic questions from a semantic prerequisite cluster.

    The question tests readiness for the target course, but its source mapping
    remains the completed-course prerequisite concept so weak-subtopic tracking
    and learning-path generation continue to work.
    """
    previous_question_texts = previous_question_texts or []
    retrieved = semantic_cluster.get("retrieved_material") or retrieve_semantic_cluster_material(semantic_cluster)
    context_text = build_semantic_cluster_context(semantic_cluster, retrieved)
    print(
        "[DIAG SEMANTIC] cluster context "
        f"id={semantic_cluster.get('cluster_id')} context_chars={len(context_text)} "
        f"retrieval_sizes={{'chunks': {len(retrieved.get('chunks', []))}, "
        f"'summaries': {len(retrieved.get('summaries', []))}, "
        f"'concepts': {len(retrieved.get('concepts', []))}}}"
    )
    if not context_text.strip():
        print(f"[DIAG SEMANTIC] empty context cluster={semantic_cluster.get('cluster_id')}")
        return []

    primary_course = semantic_cluster.get("primary_source_course", "")
    primary_topic = semantic_cluster.get("primary_topic_name", "")
    primary_subtopic = semantic_cluster.get("primary_subtopic_name", "")
    target_course = semantic_cluster.get("target_course", "")
    target_subtopics = semantic_cluster.get("target_subtopics", [])

    difficulty_list: list[str] = []
    for diff, count in difficulty_distribution.items():
        difficulty_list.extend([diff] * count)
    difficulty_list = difficulty_list[:n_questions]

    # Build cognitive-angle block for multi-question clusters.
    # Each question must test a DIFFERENT dimension of the same subtopic so
    # the student cannot answer Q2 the same way they answered Q1.
    if n_questions == 3:
        cognitive_angle_block = (
            "\nCOGNITIVE ANGLES — each question must test a different dimension:\n"
            "Q1 (READINESS CHECK — not a conceptual question):\n"
            "  Test whether the student can IDENTIFY or APPLY the concept in a concrete situation.\n"
            "  ✅ Present a small scenario and ask which approach fits, or what happens next\n"
            "  ✅ Ask what distinguishes this from a simpler alternative — only if the slide supports it\n"
            "  ❌ Do NOT ask 'Why is X important?', 'Why is X significant?', or 'What is X?'\n"
            "  ❌ Do NOT write a definition, significance, or importance question even at easy difficulty\n"
            "Q2 (APPLIED / SOLVING ⭐ MOST IMPORTANT):\n"
            "  FIRST: scan the retrieved slide text for any of the following:\n"
            "    equations, formulas, statistical calculations, worked examples, step-by-step procedures,\n"
            "    algorithms, pseudocode, trees, graphs, truth tables, SQL schemas, logic derivations.\n"
            "  IF FOUND → Q2 MUST be a genuine SOLVING question:\n"
            "    - Use or adapt a specific value, structure, or example FROM the slide.\n"
            "    - Require the student to COMPUTE, TRACE, DERIVE, or APPLY — not explain.\n"
            "    - Examples of good solving questions:\n"
            "        * 'Using BFS on [specific small tree from slide], what is the traversal order?'\n"
            "        * 'Given x=70, μ=50, σ=10, what is the z-score?' (adapt slide formula)\n"
            "        * 'Given p→q and p is true, what must follow?' (logic derivation)\n"
            "        * 'A relation has attributes A→B, B→C. What normal form violation exists?'\n"
            "        * 'Which SQL query correctly retrieves rows where salary > 50000?' (mini schema)\n"
            "    - Distractors must be plausible wrong answers or traces — NOT conceptual explanations.\n"
            "  IF NOT FOUND → Q2 is an APPLICATION question:\n"
            "    Present a scenario and ask which approach applies or why — ask WHEN or WHICH,\n"
            "    not 'why is X important?' or 'what is X?'.\n"
            "Q3 (REASONING — genuine difficulty required):\n"
            "  This MUST be a question that requires multi-step reasoning — NOT arithmetic scaling.\n"
            "  ❌ Do NOT ask 'if n doubles, how many steps?' — that is arithmetic, not reasoning\n"
            "  ❌ Do NOT ask 'if dataset triples, what happens?' — that is scaling substitution, not reasoning\n"
            "  ✅ IF the slide compares two methods → ask which approach fits a specific scenario and WHY\n"
            "  ✅ IF the slide discusses when an approach is preferred → ask to justify algorithm selection\n"
            "  ✅ IF the slide has a multi-step procedure → ask which step is critical and why (grounded)\n"
            "  ✅ IF the slide uses inference chains → ask a 2-step deduction from multiple premises\n"
            "  ✅ IF none of the above → ask which of two described strategies is suitable given a constraint\n"
            "  A hard question is hard because it requires REASONING, COMPARISON, or MULTI-STEP DEDUCTION.\n"
            "  A hard question is NOT hard just because it uses a larger number.\n"
            "Do NOT write three paraphrased versions of the same question.\n"
            "Do NOT test the same core concept as Q1 or Q2 — each question must probe a DIFFERENT aspect.\n"
        )
    elif n_questions == 2:
        cognitive_angle_block = (
            "\nCOGNITIVE ANGLES — each question must test a different dimension:\n"
            "Q1 (READINESS CHECK — not a conceptual question):\n"
            "  Test whether the student can identify or apply the concept in a concrete situation.\n"
            "  ✅ Small scenario + 'which approach fits?' or 'what is the result?'\n"
            "  ❌ Do NOT ask 'Why is X important?', 'Why is X significant?', or 'What is X?'\n"
            "Q2 (APPLIED / SOLVING or REASONING ⭐):\n"
            "  FIRST: scan the retrieved slide text for any of the following:\n"
            "    equations, formulas, statistical calculations, worked examples, step-by-step procedures,\n"
            "    algorithms, pseudocode, trees, graphs, truth tables, SQL schemas, logic derivations.\n"
            "  IF FOUND → Q2 MUST be a genuine SOLVING question (compute, trace, derive, apply)\n"
            "    using a specific value, structure, or example FROM the slide.\n"
            "  IF NOT FOUND → Q2 is REASONING: ask WHEN, WHY, or WHICH — not just WHAT IS.\n"
            "Do NOT write two paraphrased versions of the same question.\n"
        )
    else:
        cognitive_angle_block = ""

    previous_block = "\n".join(f"- {q}" for q in previous_question_texts[-40:]) or "None"
    prompt = f"""You are Manara's diagnostic exam writer. Your ONLY job is to write questions that are \
DIRECTLY and LITERALLY grounded in the retrieved slide text provided below.

Generate exactly {n_questions} multiple-choice question(s).

SOURCE: {primary_course} → {primary_topic} → {primary_subtopic}
TARGET COURSE CONTEXT (for framing only): {target_course}

DIFFICULTY REQUIRED:
{chr(10).join(f"Q{i+1}: {d}" for i, d in enumerate(difficulty_list))}
{cognitive_angle_block}
⚠️ PREREQUISITE READINESS POLICY — STRICT. READ THIS BEFORE WRITING ANY QUESTION.
This is a PREREQUISITE READINESS diagnostic, NOT a memorization quiz.

STEP 1 — SCAN THE SLIDE NOW for any of:
  worked examples · derivations · formulas · pseudocode · search procedures · inference chains ·
  numeric examples · algorithm traces · divide-and-conquer reasoning · logical proofs · trees · graphs

STEP 2 — IF ANY of the above are present:
  AT LEAST 70% of your generated questions MUST require APPLYING knowledge.
  "Why is X important/significant?" questions are FORBIDDEN as the majority type.

REQUIRED QUESTION STYLES (use these):
  1. Solve or apply the method to a given input
  2. Compute the number of steps, comparisons, or operations
  3. Trace algorithm behavior on a concrete example
  4. Derive logical conclusions from given premises
  5. Select the correct inference rule for a given argument
  6. Compare algorithm suitability for a described scenario
  7. Predict behavior under changed conditions or a different input

FORBIDDEN GENERIC WORDING — never use these as the majority pattern:
  ❌ "Why is X important?"   ❌ "Why is X significant?"
  ❌ "Why does X matter?"    ❌ "What is the purpose of X?"

CONCRETE EXAMPLES:
  BAD:  "Why is divide-and-conquer important?"
  GOOD: "If divide-and-conquer halves a search space of 128 items, how many steps are required?"

  BAD:  "Why are inference rules important?"
  GOOD: "Given p→q, q→r, and p, what conclusion follows?"

  BAD:  "Why does linear search matter?"
  GOOD: "For an unsorted array of 200 elements, what is the worst-case number of comparisons?"

  For LOGIC slides → prefer:
    ✅ Derive the conclusion from given premises
    ✅ Select the inference rule that applies to a stated argument
    ✅ Step-by-step logical deduction
    ❌ NOT "What is Modus Ponens?" or "Why is logical inference useful?"

  For ALGORITHM slides → prefer:
    ✅ Trace the algorithm on a given input and report output/order
    ✅ Count steps or runtime for a specific input size
    ✅ Search order, traversal order, or next state from a concrete input
    ❌ NOT "Why is BFS useful?" or "What is the purpose of a search algorithm?"

Generate questions that resemble exam-solving and readiness assessment, not textbook definition checks.

GROUNDING RULES — all concepts tested must come from the retrieved slide text:
1. Every question must be GROUNDED IN the concepts, reasoning, and facts from the RETRIEVED SLIDE TEXT.
   The idea tested must come from the slide — but the question wording must be clear and student-facing,
   NOT lifted verbatim from the slide. Rephrase slide content into clean academic language.
2. Do NOT invent concepts, definitions, or examples that are not present in the retrieved text.
2b. Do NOT invent scaling behavior. Statements like "if the input doubles, steps double" or "tripling data
    improves accuracy" are ONLY allowed when the slide explicitly states this relationship. Do NOT assume
    any O(n), O(log n), or any other growth relationship unless the slide directly teaches it.
3. You MAY rephrase slide content into clearer academic wording. Do NOT introduce concepts absent from the slide.
4. Do NOT create AI/ML analogies or bridge metaphors unless the retrieved text itself contains them.
5. Do NOT reference the target course content — only use it lightly as framing if needed.
6. Distractors (B, C, D) must be plausible but clearly wrong based on the retrieved text.
7. The explanation MUST cite the specific slide reasoning that justifies the correct answer.
8. Each question must have exactly 4 options: A, B, C, D. Correct answer goes in option A.
9. Avoid repeating or paraphrasing previous questions.
10. Return ONLY a valid JSON array — no prose, no markdown fences.

QUESTION QUALITY RULES — violating these makes the question invalid:
11. SELF-CONTAINED: A student who has NOT seen the slide must fully understand the question.
    Bad: "What is one main concern highlighted?" (depends on seeing the slide)
    Bad: "Why does an algorithm's efficiency matter?" (forbidden conceptual pattern)
    Good: "An algorithm processes 1,000 records in 2 s. If input doubles and the algorithm is linear, how long does it take?"
12. NO VAGUE STEMS: Never write questions like "What is emphasized?", "What is a key theme?",
    "What is one main concern?", "What does the slide focus on?" — these are slide-dependent and vague.
13. DIAGNOSTIC FRAMING: Questions should feel like university readiness assessment, not slide memorization.
    Prefer asking WHY, WHEN, WHICH, or HOW — not just WHAT IS.
    Bad: "What is an algorithm?" / "What is O(n)?" / "What does self mean?"
    Good: "Why would a recursive approach be less efficient than an iterative one for this problem?"
14. GROUNDED REASONING ONLY: Reasoning questions must be supported by relationships or comparisons
    that the slide content EXPLICITLY discusses. Do NOT invent trade-offs, superiority claims,
    or theoretical comparisons that are not present in the retrieved text.
    ALLOWED — slide supports the comparison:
      ✅ "Why would linear search be preferred when data is unsorted?" (slide teaches binary search requires sorted data)
      ✅ "When does divide-and-conquer improve efficiency over a naive approach?" (slide discusses this)
    FORBIDDEN — slide does not establish this:
      ❌ "Why is Modus Ponens superior to Modus Tollens?" (unless the slide explicitly compares them)
      ❌ "Why is OOP better than procedural programming for large systems?" (unless the slide argues this)
      ❌ Any graduate-level inference, synthesis across separate concepts, or invented trade-off not taught in the slide.
    If the slide does not explicitly support a comparison → do not ask about it.
15. SOLVING QUESTIONS (applies to Q2 when slide has procedural/quantitative content):
    The question stem must REQUIRE a computation, trace, or derivation — not an explanation.
    Bad Q2: "Why is BFS useful for shortest-path problems?" (conceptual — not a solving question)
    Good Q2: "Apply BFS to this tree: root A, children B and C, B has child D. What order are nodes visited?"
    Bad Q2: "Why do we use z-scores in statistics?" (conceptual)
    Good Q2: "A value is 70, the mean is 50, and σ=10. What is the z-score?" with numeric MCQ options.

HARD REJECTION RULES — discard and rewrite any question that starts with these phrases:
  ❌ "Why is"          ❌ "Why does"        ❌ "Why is it important"
  ❌ "Why is it significant"               ❌ "Why is it essential"
  ❌ "Why is X crucial"  ❌ "Why is X important"  ❌ "Why is X significant"
These are LOW-QUALITY diagnostic questions. Replace them with an applying, solving, or reasoning question.

DIFFICULTY-LEVEL REQUIREMENTS:
  EASY   → simple application, small computation, basic reasoning, or a direct scenario
           (NOT a conceptual "Why is X important?" question — forbidden at ALL difficulty levels)
  MEDIUM → requires solving a problem or applying a concept to a given input
  HARD   → must require GENUINE REASONING — NOT arithmetic scaling or size substitution:
    ✅ Justify algorithm selection under specific constraints stated in the slide
    ✅ Derive a conclusion from two or more premises in sequence
    ✅ Identify which approach fails under a stated condition (only if slide discusses this)
    ✅ Compare two methods on a specific criterion explicitly discussed in the slide
    ✅ Multi-step inference chain requiring 2+ logical steps
    ❌ "If the dataset is tripled, how many extra steps?" → ARITHMETIC, not hard reasoning → REJECT
    ❌ "If n doubles, how many comparisons?" → SIZE SUBSTITUTION, not reasoning → REJECT
    ❌ Any question a student can solve in under 5 seconds without reasoning → NOT hard → REJECT and rewrite

READINESS VERIFICATION — before finalizing EACH question, internally check:
  1. Does this question test READINESS FOR SUCCESS in the target course, not just prerequisite memorization?
  2. Is the correct answer logically valid and uniquely derivable from the slide premises?
  3. If it is an inference question — is the inference chain sound? Reject if invalid.
  4. Does the question stem avoid all HARD REJECTION phrases above?

SOLVING QUESTION INTEGRITY — for logic, mathematics, algorithms, and procedural topics:
  a. The correct answer MUST be strictly derivable from the retrieved slide content alone.
     Do NOT use procedures, steps, or optimizations that are not explicitly shown in the slide.
  b. Do NOT generate comparison or preference questions ("Which rule is better?", "When is X less effective?")
     unless the slide explicitly compares those methods.
  c. Do NOT invent algorithm variants, edge-case optimizations, or analytical results not taught in the slide.
  d. Do NOT make assumptions about algorithm behaviour, data structures, or mathematical properties
     beyond what the slide states.
  e. Before finalising a solving question, internally verify:
       - Is the correct answer uniquely and unambiguously derivable from the slide?
       - Are all distractors clearly wrong based on the slide (not just slightly different)?
       - Does the question require actual solving, not just recalling a rule name?
  f. For inference-rule topics (Modus Ponens, Modus Tollens, resolution, etc.), PREFER:
       ✅ "Given p→q and p, what conclusion follows?" (derive the conclusion)
       ✅ "Is the argument [p→q, ¬q, ∴ ¬p] valid?" (determine validity)
       ✅ "Which inference rule applies to: p→q, q→r, therefore p→r?" (identify rule)
     AVOID:
       ❌ "Which rule is better?"
       ❌ "When is Modus Ponens less effective than Modus Tollens?"
       ❌ Any invented trade-off or superiority claim between inference rules.

LOGIC INFERENCE VALIDATION — MANDATORY before including any inference question:
Verify the argument matches one of these VALID patterns exactly:
  • Modus Ponens:          p→q,  p          ∴ q          ✅
  • Modus Tollens:         p→q,  ¬q         ∴ ¬p         ✅
  • Hypothetical Syllogism: p→q, q→r        ∴ p→r        ✅
  • Disjunctive Syllogism:  p∨q, ¬p         ∴ q          ✅
  • Addition:              p                ∴ p∨q        ✅
  • Simplification:        p∧q              ∴ p          ✅
  • Conjunction:           p,   q           ∴ p∧q        ✅
If premises and conclusion do NOT exactly match one of the above → the question is INVALID, discard it.
NEVER mix unrelated premises (e.g., ¬p→q, r, p) and assert a conclusion follows.
Distractors must be named but non-applicable rules — not random logical statements.

SKILL-FAMILY DEDUPLICATION — MAX 1 question per skill family in this entire batch:
Each question belongs to exactly one skill family. Generating two questions in the same family is FORBIDDEN,
even if the wording, numbers, or scenario change.

Skill families and what counts as the same family:
  LOGARITHMIC_HALVING  — any question computing steps/comparisons from an input size via halving or log₂
    ❌ "64 items → steps?" AND "1024 items → comparisons?" = SAME family → keep only ONE
    ❌ "128 boxes → divide-and-conquer steps?" is the SAME family as "256 items → halvings?" → ONE only
  INFERENCE_CHAIN      — deriving conclusions from logical premises, or identifying which rule applies
  ALGORITHM_SELECTION  — choosing which algorithm/approach fits a specific scenario
  SEARCH_COMPLEXITY    — reasoning about worst-case or best-case search performance
  DECOMPOSITION        — when/how to decompose a problem (divide-and-conquer, recursion structure)
  CLASSIFICATION       — distinguishing problem types (classification vs regression, supervised vs unsupervised)
  TRADEOFF_COMPARISON  — comparing two methods under specific constraints (only if slide supports it)
  READINESS_TRANSFER   — understanding what concept X enables in the target course

Rule: After writing Q1, identify its family. Q2 and Q3 MUST be in DIFFERENT families.
  ✅ Q1=LOGARITHMIC_HALVING, Q2=ALGORITHM_SELECTION, Q3=INFERENCE_CHAIN → diverse, KEEP all
  ❌ Q1=LOGARITHMIC_HALVING, Q2=LOGARITHMIC_HALVING (different number), Q3=INFERENCE_CHAIN → REJECT Q2
Also: if PREVIOUS QUESTIONS already contain a question in a family → do NOT add another in that family.

FINAL QUALITY GATE — before returning JSON, run this check on EVERY question you have written:
  1. Does it test a UNIQUE readiness skill not already covered by another question in this batch?
  2. Is it in a DIFFERENT skill family from every other question? (see SKILL-FAMILY DEDUPLICATION above)
  3. If labeled HARD — does it require genuine reasoning beyond arithmetic or number substitution?
     If a student can answer it by plugging a number into a formula → it is NOT hard → rewrite it.
  4. Is every claim in the question stem and correct answer directly supported by the slide text?
     If you cannot point to a specific slide sentence that justifies the answer → reject the question.
  5. Does it feel like a university readiness diagnostic, not a definition quiz or slide memorization?
  6. Would a professor say "yes, this tests whether the student is ready for the target course"?
  If ANY answer is NO → discard that question and write a replacement before returning.
  Do NOT return questions that fail this gate — return only questions that pass all 6 checks.

PREVIOUS QUESTIONS (do not repeat):
{previous_block}

JSON format:
[
  {{
    "question": "In the context of [academic topic from slide], why / when / which [reasoning question]?",
    "options": {{"A": "correct reasoning from slide", "B": "plausible but wrong", "C": "plausible but wrong", "D": "plausible but wrong"}},
    "correct_answer": "A",
    "difficulty": "{difficulty_list[0] if difficulty_list else 'medium'}",
    "explanation": "Cite the slide reasoning that makes A correct."
  }}
]

RETRIEVED SLIDE TEXT (use concepts from this material — rephrase into clear academic questions):
{context_text}
"""
    max_tokens = max(1200, 700 * n_questions)
    try:
        parsed = ask_llm_fast(prompt, max_tokens=max_tokens, max_retries=2)
    except ValueError as exc:
        print(f"[DIAG SEMANTIC] question generation failed cluster={semantic_cluster.get('cluster_id')}: {exc}")
        if is_fatal_openai_error_text(str(exc)):
            raise RuntimeError(summarize_openai_error(str(exc))) from exc
        return []

    if not isinstance(parsed, list):
        print(
            "[DIAG SEMANTIC] invalid parsed type "
            f"cluster={semantic_cluster.get('cluster_id')} type={type(parsed).__name__}"
        )
        return []

    questions: list[dict[str, Any]] = []
    existing = list(previous_question_texts)
    for i, raw in enumerate(parsed):
        if not isinstance(raw, dict):
            print(f"[DIAG SEMANTIC] skipped non-dict question cluster={semantic_cluster.get('cluster_id')} index={i}")
            continue
        question_text = str(raw.get("question", "")).strip()
        options = raw.get("options", {})
        correct = str(raw.get("correct_answer", "A")).strip().upper()
        explanation = str(raw.get("explanation", "")).strip()
        difficulty = str(
            raw.get("difficulty", difficulty_list[i] if i < len(difficulty_list) else "medium")
        ).strip().lower()

        if not question_text:
            print(f"[DIAG SEMANTIC] skipped empty question cluster={semantic_cluster.get('cluster_id')} index={i}")
            continue
        if not isinstance(options, dict) or not {"A", "B", "C", "D"}.issubset(options.keys()):
            print(
                "[DIAG SEMANTIC] skipped malformed options "
                f"cluster={semantic_cluster.get('cluster_id')} index={i} options={options!r}"
            )
            continue
        if any(not str(options.get(k, "")).strip() for k in ("A", "B", "C", "D")):
            print(f"[DIAG SEMANTIC] skipped blank option cluster={semantic_cluster.get('cluster_id')} index={i}")
            continue
        if is_near_duplicate(question_text, existing):
            print(f"[DIAG SEMANTIC] skipped duplicate question cluster={semantic_cluster.get('cluster_id')} index={i}")
            continue
        if correct not in {"A", "B", "C", "D"}:
            correct = "A"
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = difficulty_list[i] if i < len(difficulty_list) else "medium"

        options, correct = force_correct_answer_a(options, correct)
        candidate_question = {
            "question": question_text,
            "options": options,
            "correct_answer": correct,
            "difficulty": difficulty,
            "explanation": explanation,
        }
        is_valid, validation_reason, skill_family = validate_diagnostic_question_quality(
            candidate_question,
            context_text=context_text,
        )
        if not is_valid:
            print(
                "[DIAG QUALITY] rejected generated question "
                f"cluster={semantic_cluster.get('cluster_id')} reason={validation_reason} "
                f"question={question_text[:100]!r}"
            )
            continue
        existing.append(question_text)
        # subtopic_question_position: 1-indexed position of this question within its
        # cluster (1=conceptual, 2=application, 3=reasoning). Used by the selection
        # loop to guarantee breadth-first ordering across subtopics.
        position = len(questions) + 1
        questions.append(
            {
                "question": question_text,
                "options": {
                    "A": str(options["A"]).strip(),
                    "B": str(options["B"]).strip(),
                    "C": str(options["C"]).strip(),
                    "D": str(options["D"]).strip(),
                },
                "correct_answer": correct,
                "difficulty": difficulty,
                "explanation": explanation,
                "source_topic_name": primary_topic,
                "source_subtopic_name": primary_subtopic,
                "source_course": primary_course,
                "diagnostic_target_course": target_course,
                "semantic_cluster_id": semantic_cluster.get("cluster_id", ""),
                "source_subtopic_key": semantic_cluster.get(
                    "source_subtopic_key",
                    "|".join(diagnostic_subtopic_key(primary_course, primary_topic, primary_subtopic)),
                ),
                "semantic_score": semantic_cluster.get("semantic_score", 0),
                "semantic_link_count": semantic_cluster.get("semantic_link_count", 0),
                "related_target_subtopics": target_subtopics,
                "source_courses": semantic_cluster.get("source_courses", []),
                "subtopic_question_position": position,
                "readiness_skill_family": skill_family or "",
            }
        )
        if len(questions) >= n_questions:
            break

    print(
        "[DIAG SEMANTIC] generated questions "
        f"cluster={semantic_cluster.get('cluster_id')} requested={n_questions} produced={len(questions)}"
    )
    return questions


# =========================================================
# QUESTION GENERATION
# =========================================================

# =========================================================
# CONCEPT NODE EXTRACTION
# ─────────────────────────────────────────────────────────
# The root cause of semantic repetition is generating all
# questions from the same narrow slice of context.  The LLM
# circles the dominant idea (e.g. "learning improves with
# experience") and produces multiple questions that differ
# only in surface wording but test the same learning
# objective.
#
# The fix:  extract DISTINCT CONCEPT NODES from the material
# first, then generate exactly ONE question per node.  Each
# node is a short, specific, testable idea.  A question that
# covers node X is blocked from also covering any idea too
# close to node X.
# =========================================================

def extract_concept_nodes(
    course_name: str,
    topic_name: str,
    subtopic_name: str,
    context_text: str,
    n: int,
) -> list[dict]:
    """
    Ask the LLM to identify *n* distinct, testable concept nodes from the
    course material.

    Each node is:
      - a SHORT label  (3-8 words, e.g. "definition of supervised learning")
      - a BRIEF description (1-2 sentences drawn only from the material)
      - a QUESTION STYLE hint  (definition | comparison | application |
                                 consequence | example | identification | ordering)

    Returns a list of dicts:
      [{"label": str, "description": str, "style": str}, ...]

    Falls back to a generic list of n placeholder nodes if the LLM fails,
    so the rest of the pipeline always has something to work with.
    """
    prompt = f"""
You are a curriculum designer reading course material.
Your job is to identify exactly {n} DISTINCT, TESTABLE concept nodes.

RULES FOR CONCEPT NODES:
- Each node must be a DIFFERENT idea — not a rephrasing of another node.
- Nodes must come ONLY from the provided material.
- Do NOT create two nodes about the same underlying idea.
  BAD (same idea, different angle):
    - "learning improves with experience"
    - "performance increases through practice"
    - "experience from datasets improves models"
  GOOD (genuinely distinct):
    - "definition of supervised learning"
    - "role of labeled training data"
    - "difference between classification and regression"
    - "overfitting and how to detect it"
- Cover the BREADTH of the material, not just the first paragraph.
- Each node must be independently testable in one MCQ question.
- Assign a question style: definition | comparison | application |
  consequence | example | identification | ordering

Return ONLY valid JSON — a list of exactly {n} objects:
[
  {{
    "label": "short concept label (3-8 words)",
    "description": "1-2 sentence description drawn only from the material.",
    "style": "definition"
  }}
]

Course: {course_name}
Topic: {topic_name}
Subtopic: {subtopic_name}

COURSE MATERIAL:
{context_text[:14000]}
"""
    try:
        parsed = ask_llm_for_json(prompt)
    except ValueError:
        parsed = []

    if not isinstance(parsed, list):
        parsed = []

    # Validate and clean each node
    nodes: list[dict] = []
    valid_styles = {
        "definition", "comparison", "application",
        "consequence", "example", "identification", "ordering",
    }
    for item in parsed:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        description = str(item.get("description", "")).strip()
        style = str(item.get("style", "definition")).strip().lower()
        if style not in valid_styles:
            style = "definition"
        if label and description:
            nodes.append({"label": label, "description": description, "style": style})

    # Deduplicate nodes by label similarity — prevents the LLM from
    # returning near-duplicate nodes even when told not to.
    deduped_nodes: list[dict] = []
    seen_node_texts: list[str] = []
    for node in nodes:
        combined = node["label"] + " " + node["description"]
        if is_near_duplicate(combined, seen_node_texts):
            continue
        # Also check concept-overlap between node labels specifically
        duplicate = False
        for seen in seen_node_texts:
            if concept_overlap(node["label"], seen) >= 0.60:
                duplicate = True
                break
        if duplicate:
            continue
        deduped_nodes.append(node)
        seen_node_texts.append(combined)

    # Pad with placeholder nodes if LLM returned too few
    while len(deduped_nodes) < n:
        idx = len(deduped_nodes) + 1
        deduped_nodes.append({
            "label": f"concept {idx} from {subtopic_name}",
            "description": f"An aspect of {subtopic_name} covered in the course material.",
            "style": "definition",
        })

    return deduped_nodes[:n]


# ── Cluster-level concept guard ────────────────────────────────────────────────

# Tighter threshold for cluster-level blocking — lower than the pairwise
# question threshold because we're comparing a generated question against
# a concept node label (shorter text, so overlap concentrates faster).
_NODE_CLUSTER_THRESHOLD = 0.45


def _question_covers_node(question_text: str, node: dict) -> bool:
    """
    Return True if *question_text* is primarily about the given concept node.
    Checks both Jaccard similarity and concept-keyword overlap against the
    node's label and description combined.
    """
    node_text = node["label"] + " " + node["description"]
    if jaccard_similarity(question_text, node_text) >= _JACCARD_THRESHOLD:
        return True
    if concept_overlap(question_text, node_text) >= _NODE_CLUSTER_THRESHOLD:
        return True
    # Also check just the label — a short, dense match is decisive
    if concept_overlap(question_text, node["label"]) >= 0.55:
        return True
    return False


def _question_invades_claimed_node(
    question_text: str,
    claimed_nodes: list[dict],
    own_node: dict,
) -> bool:
    """
    Return True if *question_text* covers a concept node that has already
    been claimed by another accepted question (i.e. not its own node).
    This is the cluster-level guard that prevents "orbit" repetition.
    """
    for node in claimed_nodes:
        if node is own_node:
            continue
        if _question_covers_node(question_text, node):
            return True
    return False


# ── Post-generation helpers (unchanged logic, kept here for clarity) ──────────

def _assign_correct_answers(questions: list[dict]) -> list[dict]:
    """
    Distribute correct answers across A/B/C/D so the answer pattern is not
    all-A.  Cycles A→B→C→D→A… and swaps option content so correctness is
    preserved.
    """
    if DEMO_FORCE_CORRECT_ANSWER_A:
        result = []
        for q in questions:
            options, correct = force_correct_answer_a(
                dict(q.get("options", {})),
                q.get("correct_answer", "A"),
            )
            result.append({**q, "options": options, "correct_answer": correct})
        return result

    cycle = ["A", "B", "C", "D"]
    result = []
    for i, q in enumerate(questions):
        target_label = cycle[i % 4]
        if target_label == "A":
            result.append(q)
            continue
        opts = dict(q["options"])
        opts["A"], opts[target_label] = opts[target_label], opts["A"]
        result.append({**q, "options": opts, "correct_answer": target_label})
    return result


def _heal_difficulty_distribution(questions: list[dict]) -> list[dict]:
    """
    Re-label difficulties so the final list always satisfies
    DIFFICULTY_DISTRIBUTION without discarding questions.
    """
    target = list(DIFFICULTY_DISTRIBUTION.keys())
    counts = list(DIFFICULTY_DISTRIBUTION.values())
    desired: list[str] = []
    for label, n in zip(target, counts):
        desired.extend([label] * n)
    healed = []
    for q, diff in zip(questions, desired):
        healed.append({**q, "difficulty": diff})
    return healed


# ── Per-node question generation ──────────────────────────────────────────────

def _generate_question_for_node(
    course_name: str,
    topic_name: str,
    subtopic_name: str,
    context_text: str,
    node: dict,
    difficulty_label: str,
    previous_question_texts: list[str],
    accepted_questions: list[dict],
) -> dict | None:
    """
    Generate exactly one MCQ question that tests *node* and nothing else.

    Returns the validated question dict, or None if generation fails after
    retries.  The node's label, description, and style are injected directly
    into the prompt so the LLM cannot drift toward a neighbouring concept.
    """
    previous_block = (
        "\n".join(f"- {q}" for q in previous_question_texts[-40:]).strip() or "None"
    )
    accepted_block = (
        "\n".join(f"- {q['question']}" for q in accepted_questions).strip() or "None"
    )

    MAX_RETRIES = 4
    for attempt in range(MAX_RETRIES):
        prompt = f"""
You are writing ONE multiple-choice question for a progress-tracking quiz.

TARGET CONCEPT — you MUST test ONLY this specific idea:
  Label      : {node["label"]}
  Description: {node["description"]}
  Style      : {node["style"]}

HARD CONSTRAINTS:
- The question must be answerable ONLY from the provided course material.
- Difficulty: {difficulty_label}
- Do NOT drift to other concepts — stay tightly on the target concept above.
- Do NOT repeat or paraphrase any question in the lists below.
- The correct answer goes in option "A"; distractors in B, C, D.
- Return ONLY valid JSON — a single object (not a list).

QUESTIONS ALREADY IN THIS QUIZ (do not repeat their concepts):
{accepted_block}

QUESTIONS FROM PREVIOUS ATTEMPTS (do not repeat or paraphrase):
{previous_block}

Return JSON:
{{
  "question": "...",
  "options": {{
    "A": "...correct answer...",
    "B": "...wrong...",
    "C": "...wrong...",
    "D": "...wrong..."
  }},
  "correct_answer": "A",
  "difficulty": "{difficulty_label}",
  "explanation": "Short explanation based only on the course material."
}}

Course: {course_name}
Topic: {topic_name}
Subtopic: {subtopic_name}

COURSE MATERIAL:
{context_text[:14000]}
"""
        try:
            parsed = ask_llm_for_json(prompt)
        except ValueError:
            continue

        if not isinstance(parsed, dict):
            continue

        question_text = str(parsed.get("question", "")).strip()
        options = parsed.get("options", {})
        correct = str(parsed.get("correct_answer", "")).strip().upper()
        explanation = str(parsed.get("explanation", "")).strip()

        # ── Basic validation ──────────────────────────────────────────────
        if not question_text:
            continue
        if correct not in {"A", "B", "C", "D"}:
            continue
        if not isinstance(options, dict) or set(options.keys()) != {"A", "B", "C", "D"}:
            continue
        if any(not str(v).strip() for v in options.values()):
            continue

        options, correct = force_correct_answer_a(options, correct)

        # ── Exact-match duplicate check ───────────────────────────────────
        sig = question_signature(question_text)
        prev_sigs = {question_signature(q) for q in previous_question_texts}
        acc_sigs = {question_signature(q["question"]) for q in accepted_questions}
        if sig in prev_sigs or sig in acc_sigs:
            continue

        # ── Semantic duplicate check against history and accepted ─────────
        all_existing = previous_question_texts + [q["question"] for q in accepted_questions]
        if is_near_duplicate(question_text, all_existing):
            continue

        # ── Concept coverage check: must cover its own node ───────────────
        if not _question_covers_node(question_text, node):
            # LLM drifted — the question doesn't actually address the target
            # concept.  On the last attempt, accept it anyway rather than
            # returning None, as it's still a valid question about the subtopic.
            if attempt < MAX_RETRIES - 1:
                continue

        return {
            "question": question_text,
            "options": {
                "A": str(options["A"]).strip(),
                "B": str(options["B"]).strip(),
                "C": str(options["C"]).strip(),
                "D": str(options["D"]).strip(),
            },
            "correct_answer": "A",
            "difficulty": difficulty_label,
            "explanation": explanation,
            "concept_node": node["label"],   # kept for diagnostics; stripped before return
        }

    return None



# =========================================================
# DIAGNOSTIC-OPTIMISED BATCH QUESTION GENERATOR
# ─────────────────────────────────────────────────────────
# For the diagnostic exam we only need a small number of
# questions per subtopic.  Instead of the full concept-node
# pipeline (1 LLM call for nodes + N sequential calls for
# questions = N+1 total), we use a single batch call that
# returns all questions at once.
#
# This reduces the LLM call count from ~84 (6 subtopics ×
# 14 calls each) to ~3 (3 subtopics × 1 call each), which
# is the single biggest speed improvement available.
# =========================================================

def generate_questions_batch_for_diagnostic(
    course_name: str,
    topic_name: str,
    subtopic_name: str,
    context_text: str,
    n_questions: int,
    difficulty_distribution: dict,
) -> list[dict]:
    """
    Generate n_questions MCQs for one subtopic in a SINGLE LLM call.

    Used exclusively by the diagnostic exam generator.  It does NOT use
    the concept-node pipeline because:
      - We only need 2-4 questions per subtopic, not 10.
      - A single batch call is 10-13x fewer API roundtrips.
      - The quality difference for 2-4 questions is negligible.

    Returns a list of validated question dicts (may be shorter than
    n_questions if the LLM returns fewer valid ones — caller handles that).
    """
    # Build difficulty list from distribution
    # e.g. {easy:1, medium:1, hard:1} for n=3
    difficulty_list = []
    for diff, count in difficulty_distribution.items():
        difficulty_list.extend([diff] * count)
    difficulty_list = difficulty_list[:n_questions]

    # Truncate context to keep prompt fast — 5000 chars is enough for MCQs
    context_snippet = context_text[:5000]

    prompt = f"""You are a diagnostic exam question writer. Your ONLY job is to write questions that are \
DIRECTLY and LITERALLY grounded in the retrieved slide text provided below.

Generate exactly {n_questions} multiple-choice questions.

COURSE: {course_name}
TOPIC: {topic_name}
SUBTOPIC: {subtopic_name}

DIFFICULTY REQUIRED (one per question, in order):
{chr(10).join(f"Q{i+1}: {d}" for i, d in enumerate(difficulty_list))}

STRICT RULES — violating any rule makes the question invalid:
1. Every question MUST be answerable word-for-word from the RETRIEVED SLIDE TEXT below.
2. Do NOT invent concepts, definitions, or examples that are not explicitly stated in the retrieved text.
3. Do NOT generalize or paraphrase beyond what the text says.
4. Do NOT create analogies or explanatory bridges unless the retrieved text itself contains them.
5. Each question must test a DIFFERENT concept from the material.
6. Distractors (B, C, D) must be plausible but clearly wrong based on the retrieved text.
7. The explanation MUST quote or closely paraphrase the specific sentence(s) from the retrieved text that justify the correct answer.
8. Each question must have exactly 4 options: A, B, C, D. Correct answer goes in option A.
9. Return ONLY a valid JSON array — no prose, no markdown fences.

JSON format:
[
  {{
    "question": "...",
    "options": {{"A": "correct answer from slide text", "B": "wrong", "C": "wrong", "D": "wrong"}},
    "correct_answer": "A",
    "difficulty": "{difficulty_list[0] if difficulty_list else 'medium'}",
    "explanation": "Cite the specific slide text that makes A correct."
  }}
]

RETRIEVED SLIDE TEXT (use ONLY this material — do not go beyond it):
{context_snippet}
"""

    try:
        parsed = ask_llm_fast(prompt, max_tokens=1200, max_retries=2)
    except ValueError as exc:
        print(
            "[DIAG FALLBACK] subtopic batch generation failed "
            f"course={course_name!r} topic={topic_name!r} subtopic={subtopic_name!r}: {exc}"
        )
        if is_fatal_openai_error_text(str(exc)):
            raise RuntimeError(summarize_openai_error(str(exc))) from exc
        return []

    if not isinstance(parsed, list):
        print(
            "[DIAG FALLBACK] subtopic batch invalid parsed type "
            f"course={course_name!r} subtopic={subtopic_name!r} type={type(parsed).__name__}"
        )
        return []

    validated = []
    for i, raw in enumerate(parsed):
        if not isinstance(raw, dict):
            print(f"[DIAG FALLBACK] skipped non-dict question item index={i} type={type(raw).__name__}")
            continue

        question_text = str(raw.get("question", "")).strip()
        options       = raw.get("options", {})
        correct       = str(raw.get("correct_answer", "")).strip().upper()
        explanation   = str(raw.get("explanation", "")).strip()
        difficulty    = str(raw.get("difficulty", difficulty_list[i] if i < len(difficulty_list) else "medium")).strip().lower()

        if not question_text:
            print(f"[DIAG FALLBACK] skipped empty question index={i}")
            continue
        if correct not in {"A", "B", "C", "D"}:
            correct = "A"
        if not isinstance(options, dict) or not {"A", "B", "C", "D"}.issubset(options.keys()):
            print(f"[DIAG FALLBACK] skipped malformed options index={i} options={options!r}")
            continue
        if any(not str(v).strip() for v in options.values()):
            print(f"[DIAG FALLBACK] skipped blank option index={i}")
            continue
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = difficulty_list[i] if i < len(difficulty_list) else "medium"

        options, correct = force_correct_answer_a(options, correct)

        validated.append({
            "question":       question_text,
            "options": {
                "A": str(options["A"]).strip(),
                "B": str(options["B"]).strip(),
                "C": str(options["C"]).strip(),
                "D": str(options["D"]).strip(),
            },
            "correct_answer": correct,
            "difficulty":     difficulty,
            "explanation":    explanation,
        })

        if len(validated) >= n_questions:
            break

    print(
        "[DIAG FALLBACK] subtopic batch validated "
        f"course={course_name!r} subtopic={subtopic_name!r} "
        f"requested={n_questions} produced={len(validated)}"
    )
    return validated

# ── Main quiz generation entry point ──────────────────────────────────────────

def generate_questions_for_subtopic(
    course_name: str,
    topic_name: str,
    subtopic_name: str,
    context_text: str,
    previous_question_texts: list[str],
    _depth: int = 0,
) -> list[dict]:
    """
    Generate exactly QUESTIONS_PER_SUBTOPIC diverse, non-duplicate MCQs.

    New strategy (concept-node-driven):
    ─────────────────────────────────────────────────────────────────
    1. Extract QUESTIONS_PER_SUBTOPIC distinct concept nodes from the
       material using a dedicated LLM call.  Each node is a short,
       specific, independently testable idea drawn from across the
       breadth of the content.

    2. Assign a difficulty label to each node so the distribution
       always satisfies DIFFICULTY_DISTRIBUTION exactly.

    3. Generate ONE question per node — the node's label, description,
       and question style are injected directly into the prompt so the
       LLM cannot drift toward a neighbouring concept cluster.

    4. Apply three deduplication layers per question:
         a. Exact MD5 match against history and accepted questions
         b. Jaccard word-overlap (≥50%) → reject
         c. Concept-keyword overlap (≥65%) → reject
       Plus a cluster-level guard: once a node is claimed by an
       accepted question, no other question may target a semantically
       adjacent node.

    5. If a node's question fails all retries, attempt to regenerate
       it with a relaxed constraint (accept even if the question drifted
       slightly from the node).

    6. Heal the difficulty distribution, distribute answer labels
       A/B/C/D evenly, strip diagnostic metadata before returning.
    """
    MINIMUM_QUESTIONS = 3
    MAX_DEPTH = 1

    # ── Step 1: Extract concept nodes ─────────────────────────────────────
    # Request more nodes than needed so we have spares if some fail generation.
    node_request_count = min(QUESTIONS_PER_SUBTOPIC + 3, QUESTIONS_PER_SUBTOPIC * 2)
    nodes = extract_concept_nodes(
        course_name=course_name,
        topic_name=topic_name,
        subtopic_name=subtopic_name,
        context_text=context_text,
        n=node_request_count,
    )

    # ── Step 2: Assign difficulty labels to nodes ──────────────────────────
    # Build the target sequence: [easy×3, medium×4, hard×3, easy, medium, ...]
    diff_sequence: list[str] = []
    for label, count in DIFFICULTY_DISTRIBUTION.items():
        diff_sequence.extend([label] * count)
    # Extend cyclically in case we have spare nodes
    while len(diff_sequence) < len(nodes):
        diff_sequence.extend(diff_sequence[:QUESTIONS_PER_SUBTOPIC])
    node_difficulties = diff_sequence[:len(nodes)]

    # ── Step 3: Generate one question per node ────────────────────────────
    accepted: list[dict] = []
    claimed_nodes: list[dict] = []   # nodes that have a successfully generated question

    for node, difficulty_label in zip(nodes, node_difficulties):
        if len(accepted) >= QUESTIONS_PER_SUBTOPIC:
            break

        q = _generate_question_for_node(
            course_name=course_name,
            topic_name=topic_name,
            subtopic_name=subtopic_name,
            context_text=context_text,
            node=node,
            difficulty_label=difficulty_label,
            previous_question_texts=previous_question_texts,
            accepted_questions=accepted,
        )

        if q is None:
            print(f"  Node '{node['label']}': generation failed, skipping.")
            continue

        # ── Cluster-level guard ───────────────────────────────────────────
        # Reject if this question's concept overlaps with a node already claimed.
        if _question_invades_claimed_node(q["question"], claimed_nodes, node):
            print(f"  Node '{node['label']}': question invaded another node's cluster, skipping.")
            continue

        accepted.append(q)
        claimed_nodes.append(node)

    # ── Step 4: Fallback if we're short ───────────────────────────────────
    if len(accepted) < QUESTIONS_PER_SUBTOPIC:
        if _depth < MAX_DEPTH:
            print(
                f"WARNING: Only generated {len(accepted)}/{QUESTIONS_PER_SUBTOPIC} "
                f"questions from concept nodes.  Retrying (depth {_depth + 1})."
            )
            return generate_questions_for_subtopic(
                course_name=course_name,
                topic_name=topic_name,
                subtopic_name=subtopic_name,
                context_text=context_text,
                previous_question_texts=previous_question_texts,
                _depth=_depth + 1,
            )
        # Retries exhausted — reduce target count gracefully before giving up
        for fallback_count in [8, 5, 3]:
            if len(accepted) >= fallback_count:
                print(
                    f"INFO: Limited content — reducing to {fallback_count} questions "
                    f"for '{subtopic_name}' (had {len(accepted)} unique questions)."
                )
                accepted = accepted[:fallback_count]
                break
        else:
            raise ValueError(
                f"Could not generate at least {MINIMUM_QUESTIONS} unique questions "
                f"for subtopic '{subtopic_name}'. Only {len(accepted)} could be produced."
            )

    # ── Step 5: Finalise ──────────────────────────────────────────────────
    final = accepted[:QUESTIONS_PER_SUBTOPIC]
    final = _heal_difficulty_distribution(final)
    final = _assign_correct_answers(final)

    # Strip internal diagnostic key before handing off
    for q in final:
        q.pop("concept_node", None)

    return final


# =========================================================
# QUIZ RUNNER
# =========================================================

def run_subtopic_quiz(
    course_name: str,
    topic_name: str,
    subtopic_name: str,
    questions: list[dict],
) -> dict:
    score = 0
    question_records = []

    print("\n" + "=" * 70)
    print("SUBTOPIC QUIZ")
    print("=" * 70)
    print(f"Course   : {course_name}")
    print(f"Topic    : {topic_name}")
    print(f"Subtopic : {subtopic_name}")
    print(f"Questions: {len(questions)}")
    print("Quiz mark : 10")
    print("=" * 70)

    for i, q in enumerate(questions, start=1):
        print("\n" + "-" * 70)
        print(f"Question {i}/{len(questions)}")
        print(f"Difficulty: {q['difficulty'].capitalize()}")
        print("-" * 70)
        print(q["question"])
        print(f"A) {q['options']['A']}")
        print(f"B) {q['options']['B']}")
        print(f"C) {q['options']['C']}")
        print(f"D) {q['options']['D']}")

        student_answer = ask_student_choice()
        is_correct = student_answer == q["correct_answer"]

        if is_correct:
            score += 1
            print("Correct ✅")
        else:
            print(f"Wrong ❌ | Correct answer: {q['correct_answer']}")
            if q.get("explanation"):
                print("Explanation:", q["explanation"])

        question_records.append({
            "question": q["question"],
            "difficulty": q["difficulty"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "student_answer": student_answer,
            "is_correct": is_correct,
            "explanation": q["explanation"],
        })

    passed = score > PASS_MARK

    print("\n" + "=" * 70)
    print(f"Subtopic score: {score}/10")
    print("Result:", "PASSED ✅" if passed else "FAILED ❌")
    print("=" * 70)

    return {
        "score": score,
        "max_score": 10,
        "passed": passed,
        "questions": question_records,
    }


# =========================================================
# PROGRESS STORAGE
# =========================================================

def get_progress_file(student_id: str, target_course: str) -> Path:
    PROGRESS_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"progress_{safe_slug(student_id)}_{safe_slug(target_course)}.json"
    return PROGRESS_RESULTS_DIR / filename

def delete_tracking_for_student_and_course(student_id: str, target_course: str) -> bool:
    if not target_course:
        return False

    progress_file = get_progress_file(student_id, target_course)

    if progress_file.exists():
        progress_file.unlink()
        return True

    return False

def load_or_create_progress(student_profile: dict, target_course: str, path_subtopics: list[dict]) -> dict:
    progress_file = get_progress_file(student_profile["student_id"], target_course)

    if progress_file.exists():
        with open(progress_file, "r", encoding="utf-8") as f:
            return json.load(f)

    payload = {
        "student_id": student_profile["student_id"],
        "student_name": student_profile["student_name"],
        "target_course": target_course,
        "current_index": 0,
        "path_subtopics": path_subtopics,
        "subtopic_progress": [],
        "completed_count": 0,
        "progress_percent": 0.0,
    }

    for item in path_subtopics:
        payload["subtopic_progress"].append({
            "course_name": item["course_name"],
            "topic_name": item["topic_name"],
            "subtopic_name": item["subtopic_name"],
            "status": "not_started",
            "best_score": 0,
            "attempt_count": 0,
            "question_history": [],
            "attempts": [],
        })

    return payload


def save_progress(progress_data: dict) -> Path:
    progress_file = get_progress_file(
        progress_data["student_id"],
        progress_data["target_course"],
    )

    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, indent=2, ensure_ascii=False)

    return progress_file


def update_progress_summary(progress_data: dict):
    completed = 0
    for item in progress_data["subtopic_progress"]:
        if item["status"] == "passed":
            completed += 1

    progress_data["completed_count"] = completed
    total = len(progress_data["subtopic_progress"])
    progress_data["progress_percent"] = round((completed / total) * 100, 2) if total else 0.0


# =========================================================
# MAIN PROGRESS TRACKING LOGIC
# =========================================================

def run_progress_tracking_for_student(student_profile: dict, path_file: Path) -> dict:
    if "student_id" not in student_profile or "student_name" not in student_profile:
        raise ValueError("student_profile must contain at least student_id and student_name.")

    path_data = load_generated_path(path_file)
    path_subtopics = parse_path_subtopics(path_data)

    target_course = str(path_data.get("target_course", "")).strip() or "unknown_target_course"

    course_name_map = build_course_name_map()
    for item in path_subtopics:
        resolved = resolve_course_folder_name(item["course_name"], course_name_map)
        if not resolved:
            raise ValueError(f"Could not match course folder for: {item['course_name']}")
        item["course_name"] = resolved

    progress_data = load_or_create_progress(student_profile, target_course, path_subtopics)

    print("\n" + "=" * 70)
    print("MANARA - PROGRESS TRACKING")
    print("=" * 70)
    print(f"Student       : {student_profile['student_name']}")
    print(f"Target course : {target_course}")
    print(f"Path length   : {len(progress_data['subtopic_progress'])} subtopics")
    print("=" * 70)

    while progress_data["current_index"] < len(progress_data["subtopic_progress"]):
        idx = progress_data["current_index"]
        entry = progress_data["subtopic_progress"][idx]

        course_name = entry["course_name"]
        topic_name = entry["topic_name"]
        subtopic_name = entry["subtopic_name"]

        print("\n" + "=" * 70)
        print(f"Current progress: {idx + 1}/{len(progress_data['subtopic_progress'])}")
        print(f"Course   : {course_name}")
        print(f"Topic    : {topic_name}")
        print(f"Subtopic : {subtopic_name}")
        print(f"Best score so far: {entry['best_score']}/10")
        print("=" * 70)

        retrieved = retrieve_course_material(
            course_name=course_name,
            topic_name=topic_name,
            subtopic_name=subtopic_name,
        )
        context_text = build_context_text(retrieved)

        if not context_text.strip():
            print("No material found for this subtopic. Skipping.")
            entry["status"] = "passed"
            progress_data["current_index"] += 1
            update_progress_summary(progress_data)
            save_progress(progress_data)
            continue

        print("\nPlease wait. A new mini quiz is being generated for this subtopic...")

        questions = generate_questions_for_subtopic(
            course_name=course_name,
            topic_name=topic_name,
            subtopic_name=subtopic_name,
            context_text=context_text,
            previous_question_texts=entry["question_history"],
        )

        result = run_subtopic_quiz(
            course_name=course_name,
            topic_name=topic_name,
            subtopic_name=subtopic_name,
            questions=questions,
        )

        entry["attempt_count"] += 1
        entry["best_score"] = max(entry["best_score"], result["score"])
        entry["attempts"].append(result)
        entry["question_history"].extend([q["question"] for q in result["questions"]])

        if result["passed"]:
            entry["status"] = "passed"
            update_progress_summary(progress_data)
            save_progress(progress_data)

            print(f"\nProgress: {progress_data['completed_count']}/{len(progress_data['subtopic_progress'])} completed")
            print(f"Progress percent: {progress_data['progress_percent']}%")

            wants_retry = ask_yes_no(
                "\nYou passed this subtopic. Do you want to retry to get a higher mark? (y/n): "
            )

            if wants_retry:
                entry["status"] = "in_progress"
                save_progress(progress_data)
                continue

            progress_data["current_index"] += 1
            update_progress_summary(progress_data)
            save_progress(progress_data)

        else:
            entry["status"] = "failed_needs_retry"
            update_progress_summary(progress_data)
            save_progress(progress_data)

            print("\nYou failed this subtopic quiz.")
            print("You must retry this subtopic before moving to the next one.")
            print("A new quiz will be generated for the retry.")

            retry_now = ask_yes_no("Do you want to retry now? (y/n): ")
            if not retry_now:
                print("Your progress has been saved. You can continue later.")
                break

    update_progress_summary(progress_data)
    save_path = save_progress(progress_data)
    progress_data["saved_progress_path"] = str(save_path)

    if progress_data["current_index"] >= len(progress_data["subtopic_progress"]):
        print("\n" + "=" * 70)
        print("PROGRESS TRACKING COMPLETED")
        print("=" * 70)
        print(f"Completed subtopics: {progress_data['completed_count']}")
        print(f"Progress percent   : {progress_data['progress_percent']}%")
        print(f"Saved progress     : {save_path}")

    return progress_data

def load_progress_for_student_and_course(student_profile: dict, target_course: str) -> dict:
    progress_file = get_progress_file(student_profile["student_id"], target_course)

    if not progress_file.exists():
        return {
            "success": False,
            "message": "No saved tracking progress found for this course.",
        }

    with open(progress_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["learning_path_steps"] = len(data.get("subtopic_progress", []))
    data["completed_steps"] = data.get("completed_count", 0)

    return {
        "success": True,
        "message": "Tracking progress loaded successfully.",
        **data,
    }

def create_tracking_progress_from_learning_path(student_profile: dict, learning_path_payload: dict) -> dict:
    target_course = str(learning_path_payload.get("target_course", "")).strip()
    learning_path = learning_path_payload.get("learning_path", []) or []

    if not target_course:
        raise ValueError("target_course missing from learning path payload.")

    path_subtopics = []

    for step in learning_path:
        source_course = str(step.get("source_course", "")).strip()
        topic_name = str(step.get("topic_name", "")).strip()

        for weak in step.get("weak_subtopics", []):
            subtopic_name = str(weak.get("subtopic_name", "")).strip()

            if source_course and topic_name and subtopic_name:
                path_subtopics.append({
                    "course_name": source_course,
                    "topic_name": topic_name,
                    "subtopic_name": subtopic_name,
                })

    if not path_subtopics:
        raise ValueError("No weak subtopics found to track.")

    progress_data = load_or_create_progress(student_profile, target_course, path_subtopics)
    update_progress_summary(progress_data)
    save_path = save_progress(progress_data)

    progress_data["learning_path_steps"] = len(progress_data.get("subtopic_progress", []))
    progress_data["completed_steps"] = progress_data.get("completed_count", 0)

    return {
        "success": True,
        "message": "Tracking progress created successfully.",
        **progress_data,
        "saved_progress_path": str(save_path),
    }

def _get_current_entry(progress_data: dict) -> dict | None:
    idx = progress_data.get("current_index", 0)
    subtopics = progress_data.get("subtopic_progress", [])
    if idx < 0 or idx >= len(subtopics):
        return None
    return subtopics[idx]


def generate_quiz_for_current_subtopic(student_profile: dict, target_course: str) -> dict:
    progress_result = load_progress_for_student_and_course(student_profile, target_course)
    if not progress_result.get("success"):
        return progress_result

    progress_data = progress_result
    entry = _get_current_entry(progress_data)

    if entry is None:
        return {
            "success": True,
            "message": "Tracking completed.",
            "completed": True,
            **progress_data,
        }

    course_name = entry["course_name"]
    topic_name = entry["topic_name"]
    subtopic_name = entry["subtopic_name"]

    retrieved = retrieve_course_material(
        course_name=course_name,
        topic_name=topic_name,
        subtopic_name=subtopic_name,
    )
    context_text = build_context_text(retrieved)

    if not context_text.strip():
        return {
            "success": False,
            "message": "No material found for this subtopic.",
        }

    try:
        questions = generate_questions_for_subtopic(
            course_name=course_name,
            topic_name=topic_name,
            subtopic_name=subtopic_name,
            context_text=context_text,
            previous_question_texts=entry.get("question_history", []),
        )
    except ValueError as e:
        return {"success": False, "message": str(e)}

    quiz_note = None
    if len(questions) < QUESTIONS_PER_SUBTOPIC:
        quiz_note = (
            f"Limited content found for this topic. "
            f"A smaller personalized quiz of {len(questions)} questions was generated."
        )

    progress_data["active_quiz"] = {
        "course_name": course_name,
        "topic_name": topic_name,
        "subtopic_name": subtopic_name,
        "questions": questions,
        "quiz_note": quiz_note,
    }
    save_progress(progress_data)

    return {
        "success": True,
        "message": quiz_note or "Quiz generated successfully.",
        "completed": False,
        "active_quiz": progress_data["active_quiz"],
        "quiz_note": quiz_note,
        "progress_percent": progress_data.get("progress_percent", 0),
        "completed_count": progress_data.get("completed_count", 0),
        "total_subtopics": len(progress_data.get("subtopic_progress", [])),
    }


def submit_quiz_for_current_subtopic(
    student_profile: dict,
    target_course: str,
    submitted_answers: list[dict],
) -> dict:
    progress_result = load_progress_for_student_and_course(student_profile, target_course)
    if not progress_result.get("success"):
        return progress_result

    progress_data = progress_result
    active_quiz = progress_data.get("active_quiz")
    entry = _get_current_entry(progress_data)

    if not active_quiz or not entry:
        return {
            "success": False,
            "message": "No active quiz found.",
        }

    submitted_map = {
        str(item.get("question_id", "")).strip(): str(item.get("student_answer", "")).strip().upper()
        for item in submitted_answers
    }

    score = 0
    question_records = []

    for i, q in enumerate(active_quiz["questions"], start=1):
        qid = f"q{i}"
        student_answer = submitted_map.get(qid, "")
        is_correct = student_answer == q["correct_answer"]

        if is_correct:
            score += 1

        question_records.append({
            "question_id": qid,
            "question": q["question"],
            "options": q["options"],
            "difficulty": q["difficulty"],
            "correct_answer": q["correct_answer"],
            "student_answer": student_answer,
            "is_correct": is_correct,
            "explanation": q["explanation"],
        })

    max_score = len(active_quiz["questions"])
    # Scale pass threshold proportionally (original: need >6/10 = 60% threshold)
    scaled_pass_mark = max(1, int(max_score * 0.6))
    passed = score > scaled_pass_mark

    entry["attempt_count"] += 1
    entry["best_score"] = max(entry.get("best_score", 0), score)
    entry["question_history"].extend([q["question"] for q in active_quiz["questions"]])
    entry["attempts"].append({
        "score": score,
        "max_score": max_score,
        "passed": passed,
        "questions": question_records,
    })
    entry["status"] = "passed" if passed else "failed_needs_retry"

    if passed:
        progress_data["current_index"] += 1

    progress_data["active_quiz"] = None
    update_progress_summary(progress_data)
    save_progress(progress_data)

    progress_data["learning_path_steps"] = len(progress_data.get("subtopic_progress", []))
    progress_data["completed_steps"] = progress_data.get("completed_count", 0)

    return {
        "success": True,
        "message": "Quiz submitted successfully.",
        "passed": passed,
        "score": score,
        "max_score": max_score,
        "questions_review": question_records,
        "progress_percent": progress_data.get("progress_percent", 0),
        "completed_count": progress_data.get("completed_count", 0),
        "total_subtopics": len(progress_data.get("subtopic_progress", [])),
        "tracking_completed": progress_data["current_index"] >= len(progress_data.get("subtopic_progress", [])),
    }


# =========================================================
# OPTIONAL TERMINAL TEST
# =========================================================

def main():
    test_profile = {
        "student_id": "test_001",
        "student_name": "Test Student",
    }

    print("=" * 70)
    print("MANARA - PROGRESS TRACKING TEST MODE")
    print("=" * 70)

    path_file_input = input("Enter generated path JSON file path: ").strip()
    if not path_file_input:
        print("No path file entered.")
        return

    progress_result = run_progress_tracking_for_student(
        student_profile=test_profile,
        path_file=Path(path_file_input),
    )

    print("\nSaved progress:")
    print(progress_result["saved_progress_path"])


if __name__ == "__main__":
    main()
