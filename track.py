from __future__ import annotations

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import re
import hashlib
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions


# =========================================================
# CONFIG
# =========================================================t

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR = PROJECT_DIR / "courses"
PROGRESS_RESULTS_DIR = PROJECT_DIR / "progress_tracking_results"

MODEL_NAME = "gpt-5.4-nano"
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

def get_llm_client():
    global _openai_client
    if _openai_client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        from openai import OpenAI
        _openai_client = OpenAI(api_key=key)
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
_JACCARD_THRESHOLD = 0.50   # ≥50 % word overlap → near-duplicate
_CONCEPT_THRESHOLD = 0.65   # ≥65 % concept-word overlap → same concept


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
    MAX_DEPTH = 3

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

    questions = generate_questions_for_subtopic(
        course_name=course_name,
        topic_name=topic_name,
        subtopic_name=subtopic_name,
        context_text=context_text,
        previous_question_texts=entry.get("question_history", []),
    )

    progress_data["active_quiz"] = {
        "course_name": course_name,
        "topic_name": topic_name,
        "subtopic_name": subtopic_name,
        "questions": questions,
    }
    save_progress(progress_data)

    return {
        "success": True,
        "message": "Quiz generated successfully.",
        "completed": False,
        "active_quiz": progress_data["active_quiz"],
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

    passed = score > PASS_MARK

    entry["attempt_count"] += 1
    entry["best_score"] = max(entry.get("best_score", 0), score)
    entry["question_history"].extend([q["question"] for q in active_quiz["questions"]])
    entry["attempts"].append({
        "score": score,
        "max_score": 10,
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
        "max_score": 10,
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
