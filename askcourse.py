from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# =========================================================
# CONFIG
# =========================================================

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR = PROJECT_DIR / "courses"

MODEL_NAME = "gpt-4o-mini"
MAX_COMPLETION_TOKENS = 1200

# Client is initialised lazily so Uvicorn reload never crashes on import.
_openai_client = None

def _get_llm_client():
    global _openai_client
    if _openai_client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        _openai_client = OpenAI(api_key=key)
    return _openai_client

embedding_function = embedding_functions.DefaultEmbeddingFunction()


# =========================================================
# CHAT SESSION STORE
# ─────────────────────────────────────────────────────────
# Keeps conversation histories strictly isolated per chat.
#
# Each "New Chat" press calls new_chat_session() which:
#   • Generates a fresh UUID (chat_id)
#   • Creates an empty, independent history list
#   • Records course name and creation timestamp
#
# Every ask_course_question call must pass that chat_id.
# The store looks up only that session's history — no other
# session's messages can ever appear in the context window.
#
# clear_chat_session() wipes a session's history without
# deleting its metadata (useful for "clear" without "new").
#
# delete_chat_session() fully removes the session entry so
# the object can be garbage-collected.
# =========================================================

class ChatSessionStore:
    """
    In-process, per-session conversation store.

    All state is held in a plain dict keyed by UUID strings.
    Nothing is shared between sessions.
    """

    def __init__(self) -> None:
        # { chat_id: { "course_name": str, "history": list[dict], "created_at": str } }
        self._sessions: dict[str, dict] = {}

    # ── Session lifecycle ──────────────────────────────────────────────────

    def new_chat_session(self, course_name: str) -> str:
        """
        Create a completely fresh chat session.

        Returns the new chat_id.  The caller should replace whatever
        chat_id it was holding with this new value and clear any
        client-side state (input box, displayed messages, etc.).
        """
        chat_id = str(uuid.uuid4())
        self._sessions[chat_id] = {
            "course_name": str(course_name).strip(),
            "history": [],          # starts empty — no bleed-in from any other session
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return chat_id

    def get_session(self, chat_id: str) -> dict | None:
        """Return the raw session dict, or None if the id is unknown."""
        return self._sessions.get(chat_id)

    def get_history(self, chat_id: str) -> list[dict]:
        """
        Return the history list for this session.
        Returns [] (not an error) for unknown IDs so callers never crash.
        """
        session = self._sessions.get(chat_id)
        if session is None:
            return []
        return session["history"]

    def append_turn(
        self,
        chat_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """
        Append one question/answer pair to this session only.
        Silently no-ops for unknown IDs (prevents ghost writes).
        """
        session = self._sessions.get(chat_id)
        if session is None:
            return
        session["history"].append({"role": "user",      "content": str(user_message)})
        session["history"].append({"role": "assistant", "content": str(assistant_message)})

    def clear_chat_session(self, chat_id: str) -> bool:
        """
        Wipe the history of an existing session without deleting it.
        Use this for a "clear conversation" action within the same chat tab.
        Returns True if the session existed, False otherwise.
        """
        session = self._sessions.get(chat_id)
        if session is None:
            return False
        session["history"] = []
        return True

    def delete_chat_session(self, chat_id: str) -> bool:
        """
        Fully remove a session (e.g. when the user closes the tab).
        Returns True if the session existed and was removed.
        """
        if chat_id in self._sessions:
            del self._sessions[chat_id]
            return True
        return False

    def list_sessions(self) -> list[dict]:
        """
        Return a summary of all active sessions (for debugging / admin).
        Never exposes history content — only metadata.
        """
        return [
            {
                "chat_id":     cid,
                "course_name": s["course_name"],
                "turn_count":  len(s["history"]) // 2,
                "created_at":  s["created_at"],
            }
            for cid, s in self._sessions.items()
        ]


# Single process-level store instance.
# Web frameworks that fork workers should instantiate one store per worker
# (or use a shared backend such as Redis) — but for Manara's current
# single-process architecture this is the correct pattern.
chat_store = ChatSessionStore()


# =========================================================
# MATH COMPLETENESS RULES
# Injected into every prompt to prevent stopping one step early
# =========================================================

MATH_COMPLETENESS_RULES = """
MATHEMATICAL COMPLETENESS — MANDATORY RULES:

You must ALWAYS fully evaluate every mathematical expression to a final numeric result.
Never stop at an unevaluated limit, sum, integral, or series expression.

TELESCOPING SERIES — required final steps:
  WRONG (incomplete):
    \\lim_{N\\to\\infty}\\left(2 - \\frac{2}{2N+1}\\right)
    "...and the remaining term tends to 0."

  CORRECT (complete):
    \\[
    \\lim_{N \\to \\infty} S_N
    = \\lim_{N \\to \\infty}\\left(2 - \\frac{2}{2N+1}\\right)
    = 2 - 0
    = 2.
    \\]
    \\[
    \\therefore \\sum_{n=1}^{\\infty}\\left(\\frac{2}{2n-1} - \\frac{2}{2n+1}\\right) = 2.
    \\]

GEOMETRIC SERIES — always state the evaluated sum, e.g. = \\frac{a}{1-r} = [number].

IMPROPER INTEGRALS — always evaluate the limit and write = [number] or = \\infty.

LIMITS — always substitute and simplify to a final value; never leave as \\lim_{...}.

GENERAL RULE — every solution must end with one of:
  - A standalone final numeric answer on its own line.
  - A "\\therefore [original expression] = [value]." conclusion line.
  - Never end mid-evaluation with a limit or sum still unevaluated.
"""
# =========================================================
# LANGUAGE DETECTION
# =========================================================

def is_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", str(text)))


# =========================================================
# SMART FILTERS
# =========================================================

def classify_intent(question: str, history: list[dict] | None = None) -> str:
    """
    Classify the student's message as small_talk | academic | irrelevant.

    The classifier receives the last two turns of conversation history so
    that short follow-ups like "where do i use it?" or "give an example"
    are never mis-classified as irrelevant just because they lack keywords.
    """

    # ── Fast-path: if there is prior conversation and the message is short,
    #    it is almost certainly a follow-up — skip the LLM call entirely.
    # ─────────────────────────────────────────────────────────────────────
    FOLLOW_UP_TRIGGERS = {
        # pronouns / references
        "it", "this", "that", "them", "they", "its", "their",
        # continuation phrases
        "where", "when", "why", "how", "what", "which", "who",
        "give", "show", "explain", "example", "examples",
        "more", "continue", "go on", "elaborate", "expand",
        "and", "also", "what about", "how about",
    }
    words = set(re.findall(r"[a-z]+", question.lower()))
    has_prior_context = bool(history)
    is_short = len(question.split()) <= 10

    if has_prior_context and is_short and words & FOLLOW_UP_TRIGGERS:
        return "academic"

    # ── Also never return small_talk mid-conversation ─────────────────────
    # A student who has been discussing course material and then types "how"
    # or "what" is asking a follow-up, not saying hello.  The small_talk
    # bucket only makes sense for the very first message with no history.
    # We enforce this here so it cannot be overridden by the LLM classifier.
    _AMBIGUOUS_ALONE = {"how", "what", "why", "when", "where", "who", "which",
                        "ok", "okay", "yes", "no", "sure", "and", "so", "but"}
    if has_prior_context and words <= _AMBIGUOUS_ALONE:
        return "academic"

    # ── Build a context snippet for the LLM classifier ────────────────────
    context_block = ""
    if history:
        recent = history[-4:]   # last 2 turns (user + assistant each)
        lines = []
        for msg in recent:
            role = str(msg.get("role", "")).strip()
            content = str(msg.get("content", "")).strip()
            if role and content:
                lines.append(f"{role.capitalize()}: {content[:300]}")
        if lines:
            context_block = (
                "Recent conversation context:\n"
                + "\n".join(lines)
                + "\n\n"
            )

    prompt = f"""
You are classifying a student message in an academic chatbot.

{context_block}Classify the NEW student message into ONE of these categories:

1. small_talk   — greetings, thanks, chitchat with no academic content
2. academic     — any question or follow-up about course topics, including
                  short follow-ups that reference something discussed above
3. irrelevant   — completely off-topic, unrelated to any academic subject

IMPORTANT: If the message is a short follow-up (uses "it", "this", "that",
"where", "how", "why", "give an example", etc.) AND there is conversation
context above, classify it as "academic".

New message:
{question}

Answer ONLY one word: small_talk, academic, or irrelevant.
"""

    try:
        res = _get_llm_client().chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
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


def _enrich_query(question: str, history: list[dict]) -> str:
    """
    When a student sends a very short or vague follow-up (e.g. "how", "what",
    "explain more"), the raw question is useless as a vector search query.
    This function prepends the last assistant topic so ChromaDB gets a
    meaningful query string.

    Examples
    --------
    question="how",  last topic="ETL"  →  "how ETL"
    question="explain more",  last topic="Data Engineer responsibilities"
        →  "explain more Data Engineer responsibilities"
    question="what is ETL?"  →  returned unchanged (already specific)
    """
    words = set(re.findall(r"[a-z]+", question.lower()))
    _VAGUE = {"how", "what", "why", "when", "where", "who", "which",
              "explain", "more", "elaborate", "example", "examples",
              "and", "so", "ok", "okay", "yes", "sure", "continue",
              "go", "on", "tell", "me", "give", "show", "describe"}

    # Only enrich if the question is short AND mostly vague words
    meaningful = words - _VAGUE
    if len(question.split()) > 8 or meaningful:
        return question  # specific enough on its own

    # Extract topic from the last user message that was longer/more specific
    for msg in reversed(history):
        if msg.get("role") == "user":
            prev = str(msg.get("content", "")).strip()
            if len(prev.split()) > 3:
                return f"{question} {prev}"[:300]

    # Fall back to appending last assistant snippet (first 80 chars)
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            snippet = str(msg.get("content", "")).strip()[:80]
            if snippet:
                return f"{question} {snippet}"

    return question


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

PRONOUN AND FOLLOW-UP RESOLUTION — MANDATORY:
- When the student uses a pronoun or vague reference ("it", "this", "that", "them", "how does it work", "where do I use it"), ALWAYS resolve it to the most recently discussed topic in the conversation history.
- NEVER ask the student what they meant. Just answer based on the most recent topic.
- NEVER end your response with a clarifying question like "Which X did you mean — A, B, or C?".
- NEVER offer a menu of possible interpretations.
- If you are 90%+ confident what the student means from context, answer it directly and completely.
- Only ask a clarifying question if the message is genuinely ambiguous AND there is zero relevant context in the conversation history.

{MATH_COMPLETENESS_RULES}

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

def ask_course_question(
    course_name: str,
    question: str,
    chat_id: Optional[str] = None,
    history: Optional[list] = None,
) -> dict:
    """
    Answer one student question, maintaining strict per-session memory.

    Parameters
    ----------
    course_name : str
        The course the student is asking about.
    question : str
        The student's current message.
    chat_id : str | None
        The UUID returned by chat_store.new_chat_session().
        When provided, history is loaded from and saved to the store
        automatically — the caller does NOT need to manage the list.
        When None (legacy / CLI mode), the function falls back to the
        caller-supplied `history` list exactly as before.
    history : list | None
        Explicit history list.  Only used when chat_id is None.
        Ignored (and never mutated) when chat_id is provided.

    Returns
    -------
    dict with keys:
        success        bool
        answer         str
        sources        list
        chat_id        str   — always present; same value that was passed in
                               (or "" when operating in legacy mode)
        message        str   — only present on failure
    """
    try:
        question = str(question or "").strip()

        # ── Resolve which history to use ───────────────────────────────────
        # If a valid chat_id is given, load history exclusively from that
        # session.  Any caller-supplied `history` list is ignored so that
        # there is exactly one source of truth per conversation.
        using_store = False
        if chat_id:
            session = chat_store.get_session(chat_id)
            if session is None:
                # chat_id was given but is unknown (e.g. expired / never created)
                return {
                    "success": False,
                    "answer": "",
                    "sources": [],
                    "chat_id": chat_id,
                    "message": (
                        f"Unknown chat_id '{chat_id}'. "
                        "Call new_chat_session() to start a fresh conversation."
                    ),
                }
            active_history = session["history"]
            using_store = True
        else:
            # Legacy / CLI path — caller manages history externally
            active_history = list(history or [])

        if not question:
            return {
                "success": False,
                "answer": "",
                "sources": [],
                "chat_id": chat_id or "",
                "message": "Question is empty.",
            }

        intent = classify_intent(question, history=active_history)

        if intent == "small_talk":
            arabic = is_arabic(question)
            small_talk_answer = (
                "مرحبا! كيف أقدر أساعدك؟ 😊" if arabic else "Hi! How can I help you? 😊"
            )
            # Small-talk turns are recorded so follow-ups stay in context
            if using_store:
                chat_store.append_turn(chat_id, question, small_talk_answer)
            return {
                "success": True,
                "answer": small_talk_answer,
                "sources": [],
                "chat_id": chat_id or "",
            }

        if intent == "irrelevant":
            irrelevant_answer = "I can only help with course-related questions."
            if using_store:
                chat_store.append_turn(chat_id, question, irrelevant_answer)
            return {
                "success": True,
                "answer": irrelevant_answer,
                "sources": [],
                "chat_id": chat_id or "",
            }

        course_map = build_course_name_map()
        resolved = resolve_course_folder_name(course_name, course_map)

        if not resolved:
            return {
                "success": False,
                "answer": "",
                "sources": [],
                "chat_id": chat_id or "",
                "message": f"Could not match course: {course_name}",
            }

        retrieved = retrieve_context(resolved, _enrich_query(question, active_history))
        context = build_context_text(retrieved)

        if not context:
            not_found_answer = "I could not find this in the provided course material."
            if using_store:
                chat_store.append_turn(chat_id, question, not_found_answer)
            return {
                "success": True,
                "answer": not_found_answer,
                "sources": [],
                "chat_id": chat_id or "",
            }

        arabic = is_arabic(question)
        prompt = build_prompt(resolved, question, context, arabic)

        # ── Build messages list from THIS session's history only ───────────
        # active_history is either the store-managed list (chat_id mode) or
        # the caller-supplied list (legacy mode).  In both cases it contains
        # only messages that belong to this conversation — never messages from
        # any other chat.
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful university teaching assistant. "
                    "Use the previous conversation context when answering follow-up questions. "
                    "Do not switch topics unless the student clearly asks a new topic.\n\n"
                    + MATH_COMPLETENESS_RULES
                ),
            }
        ]

        for msg in active_history[-12:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": str(content)})

        messages.append({"role": "user", "content": prompt})

        response = _get_llm_client().chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )

        answer = clean_answer(response.choices[0].message.content)
        formatted_sources = build_grouped_sources(retrieved, resolved)

        # ── Persist this turn back into the session store ──────────────────
        # Only the current session is written to.  No other session is
        # touched.  The caller never needs to track history manually when
        # using chat_id mode.
        if using_store:
            chat_store.append_turn(chat_id, question, answer)

        return {
            "success": True,
            "answer": answer,
            "sources": formatted_sources,
            "chat_id": chat_id or "",
        }

    except Exception as e:
        return {
            "success": False,
            "answer": "",
            "sources": [],
            "chat_id": chat_id or "",
            "message": str(e),
        }


# =========================================================
# CLI
# =========================================================

def main():
    print("Courses:")
    for c in get_course_folders():
        print("-", c.name)

    course = input("\nCourse: ").strip()

    # ── Start a brand-new session ──────────────────────────────────────────
    chat_id = chat_store.new_chat_session(course)
    print(f"\n[New chat started — session {chat_id[:8]}…]")
    print("Commands: 'exit' to quit | 'new' to start a fresh chat\n")

    while True:
        q = input("Ask: ").strip()

        if q.lower() == "exit":
            chat_store.delete_chat_session(chat_id)
            break

        if q.lower() == "new":
            # ── "New Chat" pressed ─────────────────────────────────────────
            # Delete the old session entirely (no memory leaks into new one)
            chat_store.delete_chat_session(chat_id)
            # Create a completely fresh session with a new UUID
            chat_id = chat_store.new_chat_session(course)
            print(f"\n[New chat started — session {chat_id[:8]}…]\n")
            continue

        # Pass chat_id — the store manages history automatically.
        # No manual history list needed; no risk of passing a stale one.
        res = ask_course_question(course, q, chat_id=chat_id)

        print("\n", res.get("answer", ""))

        if not res.get("success") and res.get("message"):
            print(f"[Error: {res['message']}]")

        if res.get("sources"):
            print("\nSources:")
            for source_group in res["sources"]:
                print(f"- {source_group.get('course', course)}")
                for chapter in source_group.get("chapters", []):
                    print(f"  • {chapter}")

        turn_count = len(chat_store.get_history(chat_id)) // 2
        print(f"[Session {chat_id[:8]}… | {turn_count} turn(s) in this chat]\n")


if __name__ == "__main__":
    main()
