"""
related_subtopic_analysis.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Manara – Semantic Subtopic Similarity Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generates related_subtopics.csv — the data file that drives Manara's
semantic knowledge graph edges.

Architecture (redesigned):
──────────────────────────
Previously this module worked at TOPIC granularity:
  • one row per topic
  • concept_text bundled all subtopics together
  • CSV had source_topic / target_topic columns only
  • knowledgegraph.py created Topic ↔ Topic edges

Now it works at TRUE SUBTOPIC granularity:
  • one row per (course, topic, subtopic) triple
  • each subtopic has its own focused embedding text
  • an ephemeral ChromaDB collection holds ALL subtopics globally
  • cross-course cosine-distance queries find semantically similar subtopics
  • CSV has source_subtopic / target_subtopic columns
  • knowledgegraph.py creates BOTH Topic↔Topic AND Subtopic↔Subtopic edges

The SUBTOPIC is the fundamental semantic unit in Manara because:
  – diagnostic exams evaluate subtopics
  – weak areas are subtopics
  – learning paths are sequences of subtopics
  – exercises are generated per subtopic
  – ChromaDB retrieval is scoped to subtopics

Public API (unchanged, now subtopic-accurate):
  run_related_subtopics_analysis()     → builds and saves the CSV
  get_related_subtopics_for_topic()    → subtopics related to a topic
  get_related_subtopics_for_course()   → subtopics related to a course
  get_related_subtopics_for_subtopic() → subtopics similar to one subtopic
  get_available_courses()
  get_topics_for_course()
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import chromadb
from chromadb.utils import embedding_functions


# =========================================================
# CONFIG
# =========================================================

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR  = PROJECT_DIR / "courses"
OUTPUT_FILE  = PROJECT_DIR / "related_subtopics.csv"

# ChromaDB batch limit for the default embedding function
_CHROMA_BATCH_SIZE = 500

# Similarity threshold — pairs with distance > this are excluded
SIMILARITY_THRESHOLD: float = 0.5


# =========================================================
# HELPERS
# =========================================================

def safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")


def get_course_folders(courses_dir: Path) -> list[Path]:
    if not courses_dir.exists():
        return []
    return sorted([p for p in courses_dir.iterdir() if p.is_dir()])


# =========================================================
# SUBTOPIC COLLECTION  (primary semantic unit)
# =========================================================

def collect_all_subtopics() -> pd.DataFrame:
    """
    Build one row per (course, topic, subtopic) triple across ALL courses.

    Each row carries a focused embedding text:
        SUBTOPIC: <name>
        TOPIC: <parent topic>
        COURSE: <course name>
        KEYWORDS: <comma-separated keywords from parent topic>

    This fine-grained text ensures the embedding captures the specific
    concept of the subtopic, not a blend of all subtopics in the topic.

    Returns
    -------
    DataFrame with columns:
        course_name, topic_name, subtopic_name, chapter, keywords,
        embedding_text
    """
    rows: list[dict] = []

    for course_dir in get_course_folders(COURSES_DIR):
        course_name    = course_dir.name
        concepts_file  = course_dir / "outputs" / "chapter_concepts.json"

        if not concepts_file.exists():
            continue

        try:
            with open(concepts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ANALYSIS] Could not read concepts for {course_name}: {e}")
            continue

        for relative_path, content in data.items():
            chapter = content.get("chapter", "")

            for topic in content.get("topics", []):
                topic_name = str(topic.get("topic_name", "")).strip()
                keywords   = [str(k).strip() for k in topic.get("keywords", []) if str(k).strip()]
                subtopics  = topic.get("subtopics", [])

                if not topic_name:
                    continue

                for raw_sub in subtopics:
                    subtopic_name = str(raw_sub).strip()
                    if not subtopic_name:
                        continue

                    embedding_text = (
                        f"SUBTOPIC: {subtopic_name}\n"
                        f"TOPIC: {topic_name}\n"
                        f"COURSE: {course_name}\n"
                        f"KEYWORDS: {', '.join(keywords)}"
                    )

                    rows.append({
                        "course_name":    course_name,
                        "topic_name":     topic_name,
                        "subtopic_name":  subtopic_name,
                        "chapter":        chapter,
                        "keywords":       keywords,
                        "embedding_text": embedding_text,
                    })

    df = pd.DataFrame(rows)
    print(f"[ANALYSIS] Collected {len(df)} subtopics across "
          f"{df['course_name'].nunique() if not df.empty else 0} courses.")
    return df


# =========================================================
# TOPIC-LEVEL COLLECTION  (kept for backward compatibility)
# =========================================================

def collect_all_concepts() -> pd.DataFrame:
    """
    Legacy topic-level collection.  Kept to support public API functions
    (get_related_subtopics_for_topic, etc.) that still work at topic level.

    Returns one row per topic with a concept_text bundling all subtopics.
    """
    rows: list[dict] = []

    for course_dir in get_course_folders(COURSES_DIR):
        course_name   = course_dir.name
        concepts_file = course_dir / "outputs" / "chapter_concepts.json"

        if not concepts_file.exists():
            continue

        try:
            with open(concepts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        for relative_path, content in data.items():
            chapter  = content.get("chapter", "")
            for idx, topic in enumerate(content.get("topics", [])):
                topic_name = str(topic.get("topic_name", "")).strip()
                subtopics  = topic.get("subtopics", [])
                keywords   = topic.get("keywords",  [])

                concept_text = (
                    f"Course: {course_name}\n"
                    f"File: {relative_path}\n"
                    f"Chapter: {chapter}\n"
                    f"Topic: {topic_name}\n"
                    f"Subtopics: {', '.join(subtopics)}\n"
                    f"Keywords: {', '.join(keywords)}"
                )

                rows.append({
                    "course_name":    course_name,
                    "relative_path":  relative_path,
                    "chapter":        chapter,
                    "topic_index":    idx,
                    "topic_name":     topic_name,
                    "subtopics":      subtopics,
                    "keywords":       keywords,
                    "concept_text":   concept_text,
                })

    return pd.DataFrame(rows)


# =========================================================
# SEMANTIC SIMILARITY  (subtopic level — primary)
# =========================================================

def find_related_subtopics_semantic(
    df:    pd.DataFrame,
    top_k: int = 3,
) -> pd.DataFrame:
    """
    Find cross-course semantically similar subtopics using embedding similarity.

    Strategy
    ────────
    1. Load ALL subtopics from df into an ephemeral ChromaDB collection.
       Each document is the subtopic's focused embedding_text.

    2. For each source subtopic, query the collection to find the top-k
       most similar subtopics from OTHER courses.

    3. Filter pairs by SIMILARITY_THRESHOLD and exclude same-course matches.

    This uses the same DefaultEmbeddingFunction as ChromaDB retrieval
    elsewhere in Manara, so the embedding space is consistent.

    Returns
    -------
    DataFrame with columns:
        source_course, source_topic, source_subtopic,
        target_course, target_topic, target_subtopic,
        distance
    """
    if df.empty:
        return pd.DataFrame()

    ef = embedding_functions.DefaultEmbeddingFunction()

    # Build ephemeral collection
    chroma_client = chromadb.EphemeralClient()
    try:
        collection = chroma_client.create_collection(
            name="subtopic_similarity",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as e:
        print(f"[ANALYSIS] Could not create ephemeral collection: {e}")
        return pd.DataFrame()

    # Prepare documents — one per subtopic
    ids       = [f"sub_{i}" for i in range(len(df))]
    texts     = df["embedding_text"].tolist()
    metadatas = [
        {
            "course_name":   row["course_name"],
            "topic_name":    row["topic_name"],
            "subtopic_name": row["subtopic_name"],
        }
        for _, row in df.iterrows()
    ]

    # Batch-add to collection
    total = len(ids)
    for start in range(0, total, _CHROMA_BATCH_SIZE):
        end = min(start + _CHROMA_BATCH_SIZE, total)
        collection.add(
            ids=ids[start:end],
            documents=texts[start:end],
            metadatas=metadatas[start:end],
        )
    print(f"[ANALYSIS] Embedded {total} subtopics into ephemeral collection.")

    # Number of unique courses — used to fetch enough candidates per query
    # so we can always find top_k cross-course results even if the same
    # course dominates the nearest-neighbour list.
    n_courses = df["course_name"].nunique()
    fetch_n   = min(top_k * max(n_courses, 3), total)

    all_rows:  list[dict] = []
    n_subtopics = len(df)

    for i, (_, source_row) in enumerate(df.iterrows(), start=1):
        if i == 1 or i % 50 == 0 or i == n_subtopics:
            print(f"[ANALYSIS] Querying subtopic {i}/{n_subtopics}: "
                  f"'{source_row['subtopic_name']}' ({source_row['course_name']})")

        source_course   = source_row["course_name"]
        source_topic    = source_row["topic_name"]
        source_subtopic = source_row["subtopic_name"]
        query_text      = source_row["embedding_text"]

        try:
            results = collection.query(
                query_texts=[query_text],
                n_results=fetch_n,
                include=["metadatas", "distances"],
            )
        except Exception as e:
            print(f"[ANALYSIS] Query failed for '{source_subtopic}': {e}")
            continue

        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        cross_course_found = 0
        for meta, dist in zip(metas, dists):
            if cross_course_found >= top_k:
                break
            if meta.get("course_name") == source_course:
                continue   # skip same course
            if dist > SIMILARITY_THRESHOLD:
                continue   # skip dissimilar pairs

            all_rows.append({
                "source_course":   source_course,
                "source_topic":    source_topic,
                "source_subtopic": source_subtopic,
                "target_course":   meta.get("course_name",   ""),
                "target_topic":    meta.get("topic_name",    ""),
                "target_subtopic": meta.get("subtopic_name", ""),
                "distance":        round(float(dist), 6),
            })
            cross_course_found += 1

    result_df = pd.DataFrame(all_rows)
    if not result_df.empty:
        result_df = result_df.sort_values(
            by=["source_course", "source_subtopic", "distance"],
            ascending=[True, True, True],
        ).reset_index(drop=True)

    return result_df


# =========================================================
# LEGACY TOPIC-LEVEL SIMILARITY  (kept for public API methods)
# =========================================================

def _get_concepts_collection(course_dir: Path, course_name: str):
    chroma_dir = course_dir / "outputs" / "chroma_db"
    if not chroma_dir.exists():
        return None
    try:
        client = chromadb.PersistentClient(path=str(chroma_dir))
        ef = embedding_functions.DefaultEmbeddingFunction()
        return client.get_collection(
            name=f"{safe_slug(course_name)}_concepts",
            embedding_function=ef,
        )
    except Exception:
        return None


def _find_related_topics_legacy(df: pd.DataFrame, top_k: int = 3) -> pd.DataFrame:
    """
    Legacy topic-level similarity used by the public API query functions.
    Kept so get_related_subtopics_for_topic/course still work without
    needing to re-run the full analysis.
    """
    all_rows = []
    total    = len(df)

    for i, (_, source_row) in enumerate(df.iterrows(), start=1):
        source_course = source_row["course_name"]
        source_topic  = source_row["topic_name"]
        source_text   = source_row["concept_text"]

        for course_dir in get_course_folders(COURSES_DIR):
            target_course = course_dir.name
            if target_course == source_course:
                continue

            collection = _get_concepts_collection(course_dir, target_course)
            if collection is None:
                continue

            try:
                results = collection.query(query_texts=[source_text], n_results=top_k)
            except Exception:
                continue

            docs      = results.get("documents",  [[]])[0]
            metas     = results.get("metadatas",   [[]])[0]
            distances = results.get("distances",   [[None]*len(metas)])[0]

            for meta, dist, doc in zip(metas, distances, docs):
                all_rows.append({
                    "source_course":   source_course,
                    "source_topic":    source_topic,
                    "target_course":   meta.get("course_name", ""),
                    "target_topic":    meta.get("topic_name",  ""),
                    "distance":        dist,
                    "matched_text":    (doc or "")[:500],
                })

    result_df = pd.DataFrame(all_rows)
    if not result_df.empty:
        result_df = result_df.sort_values(
            by=["source_course", "source_topic", "distance"],
            ascending=[True, True, True],
        )
    return result_df


# =========================================================
# MAIN ANALYSIS ENTRY POINT
# =========================================================

def run_related_subtopics_analysis(
    top_k:       int  = 3,
    save_result: bool = True,
) -> dict:
    """
    Build and optionally save related_subtopics.csv at SUBTOPIC granularity.

    This is the function that should be called to (re)generate the CSV
    used by knowledgegraph.py to inject semantic edges.

    CSV columns produced:
        source_course, source_topic, source_subtopic,
        target_course, target_topic, target_subtopic,
        distance

    knowledgegraph.py reads these columns and creates:
        Topic     ↔ Topic     (isRelatedTo)
        Subtopic  ↔ Subtopic  (isSemanticallySimilarTo)
    """
    total_start = time.time()

    subtopics_df = collect_all_subtopics()
    if subtopics_df.empty:
        total_end = time.time()
        if save_result and OUTPUT_FILE.exists():
            print("[ANALYSIS] No subtopic data found — existing CSV left unchanged.")
        return {
            "success": False,
            "message": "No subtopic data found. Ensure chapter_concepts.json files exist.",
            "source_count": 0,
            "result_count": 0,
            "saved_path": None,
            "runtime_seconds": round(total_end - total_start, 2),
            "results": [],
        }

    related_df = find_related_subtopics_semantic(subtopics_df, top_k=top_k)

    save_path: Optional[str] = None
    if save_result and not related_df.empty:
        related_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        save_path = str(OUTPUT_FILE)
        print(f"[ANALYSIS] Saved {len(related_df)} subtopic similarity pairs → {save_path}")
    elif save_result and related_df.empty:
        print("[ANALYSIS] No similarity pairs found — CSV not written.")

    total_end = time.time()

    return {
        "success":          True,
        "message":          "Subtopic semantic analysis completed.",
        "source_count":     len(subtopics_df),
        "result_count":     len(related_df),
        "saved_path":       save_path,
        "runtime_seconds":  round(total_end - total_start, 2),
        "results":          _df_to_records(related_df),
    }


# =========================================================
# PUBLIC QUERY API  (used by frontend / other modules)
# =========================================================

def _df_to_records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    records = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            if isinstance(v, float) and pd.isna(v):
                clean[k] = None
            else:
                clean[k] = v
        records.append(clean)
    return records


def get_available_courses() -> dict:
    return {
        "success": True,
        "courses": [p.name for p in get_course_folders(COURSES_DIR)],
    }


def get_topics_for_course(course_name: str) -> dict:
    df = collect_all_subtopics()
    if df.empty:
        return {"success": False, "message": "No concept data found.", "topics": []}

    filtered = df[df["course_name"].str.lower() == course_name.strip().lower()]
    if filtered.empty:
        return {"success": False,
                "message": f"No topics found for course='{course_name}'.",
                "topics": []}

    topics = sorted(filtered["topic_name"].dropna().unique().tolist())
    return {"success": True, "course_name": course_name, "topics": topics}


def get_related_subtopics_for_topic(
    course_name: str,
    topic_name:  str,
    top_k:       int = 3,
) -> dict:
    """
    Return subtopics from OTHER courses semantically similar to all subtopics
    inside the given topic.
    """
    df = collect_all_subtopics()
    if df.empty:
        return {"success": False, "message": "No concept data found.", "results": []}

    filtered = df[
        (df["course_name"].str.lower() == course_name.strip().lower()) &
        (df["topic_name"].str.lower()  == topic_name.strip().lower())
    ]
    if filtered.empty:
        return {"success": False,
                "message": f"No subtopics found for course='{course_name}' topic='{topic_name}'.",
                "results": []}

    related_df = find_related_subtopics_semantic(filtered, top_k=top_k)
    return {
        "success":       True,
        "message":       "Related subtopics fetched.",
        "source_count":  len(filtered),
        "result_count":  len(related_df),
        "results":       _df_to_records(related_df),
    }


def get_related_subtopics_for_course(
    course_name: str,
    top_k:       int = 3,
) -> dict:
    """Return subtopics from OTHER courses semantically similar to any
    subtopic inside the given course."""
    df = collect_all_subtopics()
    if df.empty:
        return {"success": False, "message": "No concept data found.", "results": []}

    filtered = df[df["course_name"].str.lower() == course_name.strip().lower()]
    if filtered.empty:
        return {"success": False,
                "message": f"No subtopics found for course='{course_name}'.",
                "results": []}

    related_df = find_related_subtopics_semantic(filtered, top_k=top_k)
    return {
        "success":      True,
        "message":      "Related subtopics fetched.",
        "source_count": len(filtered),
        "result_count": len(related_df),
        "results":      _df_to_records(related_df),
    }


def get_related_subtopics_for_subtopic(
    course_name:   str,
    topic_name:    str,
    subtopic_text: str,
    top_k:         int = 3,
) -> dict:
    """
    Return subtopics from OTHER courses semantically similar to ONE specific
    subtopic.  This is now a true subtopic-level query.
    """
    df = collect_all_subtopics()
    if df.empty:
        return {"success": False, "message": "No concept data found.", "results": []}

    filtered = df[
        (df["course_name"].str.lower()   == course_name.strip().lower()) &
        (df["topic_name"].str.lower()    == topic_name.strip().lower()) &
        (df["subtopic_name"].str.lower() == subtopic_text.strip().lower())
    ]
    if filtered.empty:
        return {
            "success": False,
            "message": (
                f"No matching subtopic: course='{course_name}' "
                f"topic='{topic_name}' subtopic='{subtopic_text}'."
            ),
            "results": [],
        }

    related_df = find_related_subtopics_semantic(filtered, top_k=top_k)
    return {
        "success":      True,
        "message":      "Related subtopics fetched.",
        "source_count": len(filtered),
        "result_count": len(related_df),
        "results":      _df_to_records(related_df),
    }


# =========================================================
# MAIN
# =========================================================

def main() -> None:
    print("=" * 60)
    print("Manara – Subtopic Semantic Similarity Analysis")
    print("=" * 60)
    print(f"Courses dir : {COURSES_DIR}")
    print(f"Output file : {OUTPUT_FILE}")
    print()

    result = run_related_subtopics_analysis(top_k=3, save_result=True)

    print()
    print("Analysis complete.")
    print(f"  Success          : {result.get('success', False)}")
    print(f"  Message          : {result.get('message', '')}")
    print(f"  Source subtopics : {result.get('source_count', 0)}")
    print(f"  Similarity pairs : {result.get('result_count', 0)}")
    print(f"  Runtime          : {result.get('runtime_seconds', 0)}s")
    if result.get("saved_path"):
        print(f"  Saved to         : {result['saved_path']}")

    if result["results"]:
        print("\nSample pairs (first 5):")
        for row in result["results"][:5]:
            print(
                f"  [{row['source_course']}] {row['source_subtopic']}"
                f"  ↔  [{row['target_course']}] {row['target_subtopic']}"
                f"  (d={row['distance']})"
            )


if __name__ == "__main__":
    main()
