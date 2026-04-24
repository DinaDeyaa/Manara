from __future__ import annotations

from pathlib import Path
import json
import re
import time
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions


# =========================================================
# CONFIG
# =========================================================

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR = PROJECT_DIR / "courses"
OUTPUT_FILE = PROJECT_DIR / "related_subtopics.csv"


# =========================================================
# HELPERS
# =========================================================

def safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")


def get_course_folders(courses_dir: Path) -> list[Path]:
    return sorted([p for p in courses_dir.iterdir() if p.is_dir()])


def get_concepts_collection(course_dir: Path, course_name: str):
    chroma_dir = course_dir / "outputs" / "chroma_db"
    if not chroma_dir.exists():
        return None

    client = chromadb.PersistentClient(path=str(chroma_dir))
    embedding_function = embedding_functions.DefaultEmbeddingFunction()
    collection_name = f"{safe_slug(course_name)}_concepts"

    try:
        return client.get_collection(name=collection_name, embedding_function=embedding_function)
    except Exception:
        return None


# =========================================================
# BUILD TABLE OF CONCEPTS
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
            chapter = content.get("chapter", "")

            for idx, topic in enumerate(content.get("topics", [])):
                topic_name = topic.get("topic_name", "").strip()
                subtopics = topic.get("subtopics", [])
                keywords = topic.get("keywords", [])

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
                    "concept_text": concept_text
                })

    return pd.DataFrame(rows)

def df_to_records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    records = df.to_dict(orient="records")
    clean_records = []

    for row in records:
        clean_row = {}
        for key, value in row.items():
            if value is None:
                clean_row[key] = None
            elif isinstance(value, float) and pd.isna(value):
                clean_row[key] = None
            else:
                clean_row[key] = value
        clean_records.append(clean_row)

    return clean_records

# =========================================================
# RELATED SUBTOPICS
# =========================================================

def find_related_subtopics(df: pd.DataFrame, top_k: int = 3) -> pd.DataFrame:
    all_rows = []
    total_topics = len(df)
    search_start = time.time()

    for i, (_, source_row) in enumerate(df.iterrows(), start=1):
        if i == 1 or i % 10 == 0 or i == total_topics:
            elapsed = time.time() - search_start
            print(f"Processing topic {i}/{total_topics} | elapsed: {elapsed:.2f} sec")

        source_course = source_row["course_name"]
        source_topic = source_row["topic_name"]
        source_text = source_row["concept_text"]

        related_items = []

        # search across OTHER courses only
        for course_dir in get_course_folders(COURSES_DIR):
            target_course = course_dir.name
            if target_course == source_course:
                continue

            collection = get_concepts_collection(course_dir, target_course)
            if collection is None:
                continue

            results = collection.query(
                query_texts=[source_text],
                n_results=top_k
            )

            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])

            if distances and len(distances[0]) == len(metas):
                dist_list = distances[0]
            else:
                dist_list = [None] * len(metas)

            for meta, dist, doc in zip(metas, dist_list, docs):
                related_items.append({
                    "source_course": source_course,
                    "source_topic": source_topic,
                    "target_course": meta.get("course_name", ""),
                    "target_topic": meta.get("topic_name", ""),
                    "target_relative_path": meta.get("relative_path", ""),
                    "distance": dist,
                    "matched_text": (doc or "")[:500]
                })

        all_rows.extend(related_items)

    result_df = pd.DataFrame(all_rows)

    if not result_df.empty:
        result_df = result_df.sort_values(
            by=["source_course", "source_topic", "distance"],
            ascending=[True, True, True]
        )

    return result_df

def get_related_subtopics_for_topic(
    course_name: str,
    topic_name: str,
    top_k: int = 3,
) -> dict:
    concepts_df = collect_all_concepts()

    if concepts_df.empty:
        return {
            "success": False,
            "message": "No concept data found.",
            "results": [],
        }

    filtered_df = concepts_df[
        (concepts_df["course_name"].astype(str).str.strip().str.lower() == course_name.strip().lower()) &
        (concepts_df["topic_name"].astype(str).str.strip().str.lower() == topic_name.strip().lower())
    ]

    if filtered_df.empty:
        return {
            "success": False,
            "message": f"No topic found for course='{course_name}' and topic='{topic_name}'.",
            "results": [],
        }

    related_df = find_related_subtopics(filtered_df, top_k=top_k)

    return {
        "success": True,
        "message": "Related subtopics fetched successfully.",
        "source_count": len(filtered_df),
        "result_count": len(related_df),
        "results": df_to_records(related_df),
    }


def get_related_subtopics_for_course(
    course_name: str,
    top_k: int = 3,
) -> dict:
    concepts_df = collect_all_concepts()

    if concepts_df.empty:
        return {
            "success": False,
            "message": "No concept data found.",
            "results": [],
        }

    filtered_df = concepts_df[
        concepts_df["course_name"].astype(str).str.strip().str.lower() == course_name.strip().lower()
    ]

    if filtered_df.empty:
        return {
            "success": False,
            "message": f"No topics found for course='{course_name}'.",
            "results": [],
        }

    related_df = find_related_subtopics(filtered_df, top_k=top_k)

    return {
        "success": True,
        "message": "Related subtopics fetched successfully.",
        "source_count": len(filtered_df),
        "result_count": len(related_df),
        "results": df_to_records(related_df),
    }


def get_related_subtopics_for_subtopic(
    course_name: str,
    topic_name: str,
    subtopic_text: str,
    top_k: int = 3,
) -> dict:
    concepts_df = collect_all_concepts()

    if concepts_df.empty:
        return {
            "success": False,
            "message": "No concept data found.",
            "results": [],
        }

    mask_course = concepts_df["course_name"].astype(str).str.strip().str.lower() == course_name.strip().lower()
    mask_topic = concepts_df["topic_name"].astype(str).str.strip().str.lower() == topic_name.strip().lower()

    mask_subtopic = concepts_df["subtopics"].apply(
        lambda subs: any(str(x).strip().lower() == subtopic_text.strip().lower() for x in (subs or []))
    )

    filtered_df = concepts_df[mask_course & mask_topic & mask_subtopic]

    if filtered_df.empty:
        return {
            "success": False,
            "message": (
                f"No matching subtopic found for course='{course_name}', "
                f"topic='{topic_name}', subtopic='{subtopic_text}'."
            ),
            "results": [],
        }

    related_df = find_related_subtopics(filtered_df, top_k=top_k)

    return {
        "success": True,
        "message": "Related subtopics fetched successfully.",
        "source_count": len(filtered_df),
        "result_count": len(related_df),
        "results": df_to_records(related_df),
    }


def run_related_subtopics_analysis(
    top_k: int = 3,
    save_result: bool = True,
) -> dict:
    total_start = time.time()

    concepts_df = collect_all_concepts()
    if concepts_df.empty:
        return {
            "success": False,
            "message": "No concept data found.",
            "results": [],
        }

    related_df = find_related_subtopics(concepts_df, top_k=top_k)

    save_path = None
    if save_result:
        related_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        save_path = str(OUTPUT_FILE)

    total_end = time.time()

    return {
        "success": True,
        "message": "Related subtopic analysis completed successfully.",
        "source_count": len(concepts_df),
        "result_count": len(related_df),
        "saved_path": save_path,
        "runtime_seconds": round(total_end - total_start, 2),
        "results": df_to_records(related_df),
    }

# =========================================================
# FRONTEND-FRIENDLY PUBLIC API
# =========================================================

def get_available_courses() -> dict:
    course_folders = get_course_folders(COURSES_DIR)

    return {
        "success": True,
        "courses": [p.name for p in course_folders]
    }


def get_topics_for_course(course_name: str) -> dict:
    concepts_df = collect_all_concepts()

    if concepts_df.empty:
        return {
            "success": False,
            "message": "No concept data found.",
            "topics": [],
        }

    filtered_df = concepts_df[
        concepts_df["course_name"].astype(str).str.strip().str.lower() == course_name.strip().lower()
    ]

    if filtered_df.empty:
        return {
            "success": False,
            "message": f"No topics found for course='{course_name}'.",
            "topics": [],
        }

    topics = sorted(filtered_df["topic_name"].dropna().astype(str).unique().tolist())

    return {
        "success": True,
        "course_name": course_name,
        "topics": topics,
    }

# =========================================================
# MAIN
# =========================================================

def main():
    print("Testing frontend-friendly related subtopics API...\n")

    result = get_available_courses()
    print("Available courses:")
    print(result["courses"][:10])

    # Example test:
    course_name = input("\nEnter course name: ").strip()
    if not course_name:
        print("No course entered.")
        return

    topics_result = get_topics_for_course(course_name)
    if not topics_result["success"]:
        print(topics_result["message"])
        return

    print("\nAvailable topics:")
    for t in topics_result["topics"][:20]:
        print("-", t)

    topic_name = input("\nEnter topic name: ").strip()
    if not topic_name:
        print("No topic entered.")
        return

    result = get_related_subtopics_for_topic(course_name, topic_name, top_k=3)
    print("\nResult status:", result["success"])
    print("Message:", result["message"])
    print("Result count:", result.get("result_count", 0))

    for row in result["results"][:5]:
        print("\n---")
        print("Source course :", row.get("source_course"))
        print("Source topic  :", row.get("source_topic"))
        print("Target course :", row.get("target_course"))
        print("Target topic  :", row.get("target_topic"))
        print("Distance      :", row.get("distance"))

if __name__ == "__main__":
    main()