from __future__ import annotations

import os
import io
import re
import json
import base64
import zipfile
from pathlib import Path
from collections import Counter

import fitz
import pandas as pd
import chromadb
from tqdm import tqdm
from openai import OpenAI
from pptx import Presentation
from chromadb.utils import embedding_functions
from pptx.enum.shapes import MSO_SHAPE_TYPE


# =========================================================
# CONFIG
# =========================================================

PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
COURSES_DIR = PROJECT_DIR / "courses"

MODEL_NAME = "gpt-5.4-nano"
VISION_MODEL_NAME = "gpt-5.4-mini"

MAX_OUTPUT_TOKENS = 900
MAX_VISION_OUTPUT_TOKENS = 700

RUN_SUMMARIZATION = True
RUN_CONCEPT_EXTRACTION = True
SAVE_TO_CHROMA = True

FORCE_REGENERATE = False
TEST_COURSE_NAME = None

# multimodal controls
RUN_VISION_EXTRACTION = True
VISION_ONLY_WHEN_NEEDED = True
MIN_TEXT_LENGTH_FOR_VISION_SKIP = 120
MAX_VISION_CHARS_PER_PAGE = 2000

SUPPORTED_DIRECT_FILE_EXTENSIONS = {
    ".pdf",
    ".pptx",
    ".cpp",
    ".h",
    ".c",
    ".hpp",
    ".py",
    ".java",
    ".js",
    ".ts",
    ".txt",
    ".md",
    ".ipynb",
}

SUPPORTED_ZIP_MEMBER_EXTENSIONS = SUPPORTED_DIRECT_FILE_EXTENSIONS

IGNORED_DIR_NAMES = {
    "outputs",
    "chroma_db",
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "__MACOSX",
}

CHUNKS_COLLECTION_SUFFIX = "_chunks"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in your environment.")

client = OpenAI(api_key=OPENAI_API_KEY)


# =========================================================
# COURSE METADATA MAP
# =========================================================

COURSE_METADATA_MAP = {
    "introduction to data science": {
        "course_code": "14140",
        "official_title": "Introduction to Data Science",
        "credit_hours": 3,
        "prerequisites": ["11102"],
        "concurrent": [],
        "recommended_year": 1,
        "recommended_semester": 2,
        "description": (
            "Introduces students to the field of data science and its basic principles, "
            "tools, data collection and integration, exploratory data analysis, predictive "
            "and descriptive modeling, evaluation, and communication."
        ),
        "aliases": [],
    },
    "data engineering": {
        "course_code": "14260",
        "official_title": "Data Engineering",
        "credit_hours": 3,
        "prerequisites": ["14140"],
        "concurrent": [],
        "recommended_year": 2,
        "recommended_semester": 1,
        "description": (
            "Examines the modern data ecosystem and core ETL tasks, data types, staging, "
            "profiling, cleansing, migration, and basic data visualization."
        ),
        "aliases": [],
    },
    "data engineering lab": {
        "course_code": "14261",
        "official_title": "Data Engineering Lab",
        "credit_hours": 1,
        "prerequisites": [],
        "concurrent": ["14260"],
        "recommended_year": 2,
        "recommended_semester": 1,
        "description": (
            "Practical exercises using common data engineering tools and ETL tasks on "
            "different types of data."
        ),
        "aliases": [],
    },
    "high performance computing for big data": {
        "course_code": "14362",
        "official_title": "High Performance Computing for Big Data",
        "credit_hours": 3,
        "prerequisites": ["14260"],
        "concurrent": [],
        "recommended_year": 2,
        "recommended_semester": 2,
        "description": (
            "Introduces big data concepts, platform organization, tools such as Hadoop and "
            "Spark, and the workflow of big-data components."
        ),
        "aliases": [],
    },
    "data visualization": {
        "course_code": "14364",
        "official_title": "Data Visualization",
        "credit_hours": 3,
        "prerequisites": ["14362"],
        "concurrent": [],
        "recommended_year": 3,
        "recommended_semester": 2,
        "description": (
            "Covers designing and creating data visualizations, visual encoding, dashboard "
            "development, and identification of patterns and trends."
        ),
        "aliases": [],
    },
    "data mining": {
        "course_code": "14465",
        "official_title": "Data Mining",
        "credit_hours": 3,
        "prerequisites": ["14362"],
        "concurrent": [],
        "recommended_year": 3,
        "recommended_semester": 2,
        "description": (
            "Introduces data mining concepts and methods with focus on pattern discovery, "
            "clustering, classification, and anomaly detection."
        ),
        "aliases": [],
    },
    "business intelligence": {
        "course_code": "14466",
        "official_title": "Business Intelligence",
        "credit_hours": 3,
        "prerequisites": ["14364"],
        "concurrent": [],
        "recommended_year": 4,
        "recommended_semester": 1,
        "description": (
            "Introduces business intelligence concepts, analytics, enterprise data warehousing, "
            "decision support, and case studies in BI applications."
        ),
        "aliases": [],
    },
    "natural language processing": {
        "course_code": "14351",
        "official_title": "Natural Language Processing",
        "credit_hours": 3,
        "prerequisites": ["14330"],
        "concurrent": [],
        "recommended_year": 4,
        "recommended_semester": 1,
        "description": (
            "Covers core NLP concepts, linguistic and computational properties of natural "
            "language, and applications such as question answering, summarization, dialogue, "
            "and machine translation."
        ),
        "aliases": [],
    },
    "artificial intelligence": {
        "course_code": "14330",
        "official_title": "Artificial Intelligence",
        "credit_hours": 3,
        "prerequisites": ["11212"],
        "concurrent": [],
        "recommended_year": 3,
        "recommended_semester": 1,
        "description": (
            "Introduces AI concepts, knowledge representation, heuristic search, expert systems, "
            "natural language processing, machine learning, and AI applications."
        ),
        "aliases": [],
    },
    "database systems": {
        "course_code": "11323",
        "official_title": "Database Systems",
        "credit_hours": 3,
        "prerequisites": ["11212"],
        "concurrent": [],
        "recommended_year": 3,
        "recommended_semester": 1,
        "description": (
            "Covers basic database concepts, DBMS components, transaction management, "
            "data modeling, ER diagrams, relational algebra, queries, and normalization."
        ),
        "aliases": [],
    },
    "database systems lab": {
        "course_code": "11354",
        "official_title": "Database Systems Lab",
        "credit_hours": 1,
        "prerequisites": [],
        "concurrent": ["11323"],
        "recommended_year": 3,
        "recommended_semester": 1,
        "description": (
            "Practical training on designing and implementing a full database application using "
            "a relational DBMS."
        ),
        "aliases": [],
    },
    "data structures and introduction to algorithms": {
        "course_code": "11212",
        "official_title": "Data Structures and Introduction to Algorithms",
        "credit_hours": 3,
        "prerequisites": ["20134", "11206", "11253"],
        "concurrent": [],
        "recommended_year": 2,
        "recommended_semester": 2,
        "description": (
            "Introduces algorithm design and analysis basics, asymptotic complexity, searching, "
            "sorting, recursion, and core data structures."
        ),
        "aliases": [],
    },
    "algorithms design and analysis": {
        "course_code": "11313",
        "official_title": "Algorithms Design and Analysis",
        "credit_hours": 3,
        "prerequisites": ["11212"],
        "concurrent": [],
        "recommended_year": 3,
        "recommended_semester": 1,
        "description": (
            "Covers formal techniques for designing and analyzing algorithms including greedy, "
            "divide-and-conquer, backtracking, heuristics, and graph algorithms."
        ),
       "aliases": [],
    },
    "object oriented programming": {
        "course_code": "11206",
        "official_title": "Object Oriented Programming",
        "credit_hours": 3,
        "prerequisites": ["11103"],
        "concurrent": [],
        "recommended_year": 2,
        "recommended_semester": 1,
        "description": (
            "Introduces OOP concepts including abstraction, encapsulation, classes, inheritance, "
            "overloading, polymorphism, and templates."
        ),
        "aliases": [],
    },
    "structured programming": {
        "course_code": "11103",
        "official_title": "Structured Programming",
        "credit_hours": 3,
        "prerequisites": ["11102"],
        "concurrent": [],
        "recommended_year": 1,
        "recommended_semester": 2,
        "description": (
            "Introduces structured programming concepts, C++ syntax and semantics, control "
            "structures, recursion, functions, arrays, pointers, and basic file I/O."
        ),
        "aliases": [],
    },
    "introduction to computer science": {
        "course_code": "11102",
        "official_title": "Introduction to Computer Science",
        "credit_hours": 3,
        "prerequisites": [],
        "concurrent": [],
        "recommended_year": 1,
        "recommended_semester": 1,
        "description": (
            "Introduces core computer science concepts, data representation, number systems, "
            "problem solving, flowcharts, and basic programming."
        ),
        "aliases": [],
    },
        "calculus 1": {
        "course_code": "20132",
        "official_title": "Calculus (1)",
        "credit_hours": 3,
        "prerequisites": [],
        "concurrent": [],
        "recommended_year": 1,
        "recommended_semester": 1,
        "description": (
            "Functions, limits and continuity, derivatives, differentiation, inverse functions, "
            "trigonometric functions, logarithmic and exponential functions, hyperbolic functions, and integrals."
        ),
        "aliases": [],
    },
    "calculus 2": {
        "course_code": "20133",
        "official_title": "Calculus (2)",
        "credit_hours": 3,
        "prerequisites": ["20132"],
        "concurrent": [],
        "recommended_year": 1,
        "recommended_semester": 2,
        "description": (
            "Methods of integration, applications of integration, plane analytic geometry including "
            "polar coordinates, sequences and series, including power series."
        ),
        "aliases": [],
    },
    "linear algebra": {
        "course_code": "20234",
        "official_title": "Linear Algebra",
        "credit_hours": 3,
        "prerequisites": ["20133"],
        "concurrent": [],
        "recommended_year": 2,
        "recommended_semester": 1,
        "description": (
            "System of linear equations, row-echelon form, Gaussian elimination, Gauss-Jordan method, "
            "matrices, determinants, Euclidean n-space, linear transformations, vector spaces, "
            "orthogonality, least squares, QR decomposition, eigenvalues and eigenvectors."
        ),
        "aliases": [],
    },
    "operating systems": {
        "course_code": "11335",
        "official_title": "Operating Systems",
        "credit_hours": 3,
        "prerequisites": ["11212"],
        "concurrent": [],
        "recommended_year": 3,
        "recommended_semester": 1,
        "description": (
            "Introduction to operating systems, processes, threads, CPU scheduling, process synchronization, "
            "deadlocks, memory management, virtual memory, file systems, mass storage management, and UNIX case study."
        ),
       "aliases": [],
    },
    "operating systems lab": {
        "course_code": "11355",
        "official_title": "Operating Systems Lab",
        "credit_hours": 1,
        "prerequisites": [],
        "concurrent": ["11335"],
        "recommended_year": 3,
        "recommended_semester": 1,
        "description": (
            "Practical UNIX/Linux skills including installation, Vi editor, file and process management, "
            "shell programming, system administration, and implementation of some operating system concepts."
        ),
        "aliases": [],
    },
    "distributed systems": {
        "course_code": "11436",
        "official_title": "Distributed Systems",
        "credit_hours": 3,
        "prerequisites": ["11435"],
        "concurrent": [],
        "recommended_year": 4,
        "recommended_semester": 1,
        "description": (
            "Concepts of distributed systems, communication, client-server model, RPC, RMI, group communication, "
            "synchronization, election algorithms, atomic transactions, deadlocks, allocation, scheduling, "
            "fault tolerance, real-time systems, and distributed shared memory."
        ),
        "aliases": [],
    },
    "cloud computing": {
        "course_code": "14467",
        "official_title": "Cloud Computing",
        "credit_hours": 3,
        "prerequisites": ["11335"],
        "concurrent": [],
        "recommended_year": 4,
        "recommended_semester": 1,
        "description": (
            "Introduction to cloud computing, data centers, virtualization, cloud storage, programming models, "
            "service models, design and management of data centers, data distribution, durability, consistency, and redundancy."
        ),
        "aliases": [],
    },
    "computer architecture for machine learning": {
        "course_code": "14350",
        "official_title": "Computer Architecture for Machine Learning",
        "credit_hours": 3,
        "prerequisites": ["14330"],
        "concurrent": [],
        "recommended_year": 4,
        "recommended_semester": 1,
        "description": (
            "Foundations of machine learning, implementation of algorithms and applications, including supervised "
            "learning, unsupervised learning, deep learning, reinforcement learning, and computer architectures "
            "for efficient execution such as CPU, GPU, and TensorFlow basics."
        ),
        "aliases": [],
    },
    "computer vision": {
        "course_code": "14458",
        "official_title": "Computer Vision",
        "credit_hours": 3,
        "prerequisites": ["12446"],
        "concurrent": [],
        "recommended_year": 4,
        "recommended_semester": 2,
        "description": (
            "Fundamentals of image formation, camera imaging geometry, feature detection and matching, "
            "stereo algorithms, motion estimation and tracking, image classification with neural networks, "
            "and object detection and tracking."
        ),
       "aliases": [],
    },
    "information retrieval": {
        "course_code": "14457",
        "official_title": "Information Retrieval",
        "credit_hours": 3,
        "prerequisites": ["11323"],
        "concurrent": [],
        "recommended_year": 4,
        "recommended_semester": 2,
        "description": (
            "Introduces the principles and techniques of information retrieval systems, "
            "including text processing, indexing, query processing, ranking models, "
            "vector space model, probabilistic retrieval models, evaluation metrics, "
            "and applications such as search engines and document retrieval."
    ),
    "aliases": [],
    },
}


# =========================================================
# HELPERS
# =========================================================

def safe_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).strip().lower()).strip("_")


def collect_course_folders(courses_root: Path) -> list[Path]:
    if not courses_root.exists():
        raise FileNotFoundError(f"Courses folder not found: {courses_root}")
    return sorted([p for p in courses_root.iterdir() if p.is_dir()])


def should_ignore_path(path: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def normalize_title(name: str) -> str:
    cleaned = re.sub(r"[_\-]+", " ", str(name).lower()).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def resolve_course_metadata(course_name: str) -> dict:
    normalized = normalize_title(course_name)

    if normalized in COURSE_METADATA_MAP:
        return COURSE_METADATA_MAP[normalized]

    for meta in COURSE_METADATA_MAP.values():
        aliases = [normalize_title(a) for a in meta.get("aliases", [])]
        if normalized in aliases:
            return meta

    return {
        "course_code": "",
        "official_title": course_name,
        "credit_hours": None,
        "prerequisites": [],
        "concurrent": [],
        "recommended_year": None,
        "recommended_semester": None,
        "description": "",
        "aliases": [],
    }


def collect_supported_sources(course_dir: Path) -> list[Path]:
    files = []

    for path in course_dir.rglob("*"):
        if should_ignore_path(path):
            continue
        if not path.is_file():
            continue
        if path.name.startswith("._"):
            continue

        suffix = path.suffix.lower()
        if suffix in SUPPORTED_DIRECT_FILE_EXTENSIONS or suffix == ".zip":
            files.append(path)

    return sorted(files)


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip()).lower()


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
                "content": "You are a precise academic assistant. Return clean structured output only.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
    )

    if hasattr(response, "usage") and response.usage:
        print("  Usage:", response.usage)

    return response.choices[0].message.content.strip()


def encode_image_bytes_to_data_url(image_bytes: bytes, mime_type: str = "image/png") -> str:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def should_run_vision_on_pdf_page(page, extracted_text: str) -> bool:
    if not RUN_VISION_EXTRACTION:
        return False

    if not VISION_ONLY_WHEN_NEEDED:
        return True

    text_len = len((extracted_text or "").strip())
    has_images = bool(page.get_images(full=True))

    return has_images or text_len < MIN_TEXT_LENGTH_FOR_VISION_SKIP


def should_run_vision_on_slide(slide_text: str, has_picture: bool) -> bool:
    if not RUN_VISION_EXTRACTION:
        return False

    if not VISION_ONLY_WHEN_NEEDED:
        return True

    text_len = len((slide_text or "").strip())
    return has_picture or text_len < MIN_TEXT_LENGTH_FOR_VISION_SKIP


def ask_vision_on_image_bytes(image_bytes: bytes, prompt: str) -> str:
    """
    Uses the Responses API with image input.
    """
    image_url = encode_image_bytes_to_data_url(image_bytes, mime_type="image/png")

    response = client.responses.create(
        model=VISION_MODEL_NAME,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": image_url,
                        "detail": "high",
                    },
                ],
            }
        ],
        max_output_tokens=MAX_VISION_OUTPUT_TOKENS,
    )

    text = getattr(response, "output_text", None)
    if text:
        return text.strip()

    try:
        parts = []
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for c in getattr(item, "content", []):
                    if getattr(c, "type", None) == "output_text":
                        parts.append(c.text)
        return "\n".join(parts).strip()
    except Exception:
        return ""


def build_visual_prompt(file_type: str, page_number: int) -> str:
    return f"""
You are analyzing a {file_type.upper()} course-material page/slide.

Extract only academically useful visual information that may be needed later for:
- retrieval
- question answering
- concept extraction
- related subtopic analysis

Include only useful visual content such as:
- diagrams and relationships
- charts, axes, legends, labels, trends, values if visible
- flowcharts and step order
- screenshots of code or pseudocode
- formulas shown inside images
- tables embedded as images
- figure captions and labels
- important visual examples

If code appears in an image, transcribe the visible code as accurately as possible and briefly say what it does.

Do NOT describe decorative backgrounds or irrelevant style details.
Return plain text only.
Be concise but specific.

This is page/slide number {page_number}.
""".strip()


def render_pdf_page_to_png_bytes(page, zoom: float = 2.0) -> bytes:
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return pix.tobytes("png")


def extract_picture_texts_from_slide(slide, run_vision: bool) -> tuple[list[str], bool]:
    """
    Extract text from images inside PowerPoint slides using vision.
    Returns (visual_text_blocks, has_picture_shape).
    """
    visual_blocks = []
    has_picture = False

    for shape in slide.shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            has_picture = True

            if not run_vision:
                continue

            try:
                image_bytes = shape.image.blob
                prompt = """
Analyze this image from a course PowerPoint slide.

Extract only academically useful information:
- diagrams
- charts
- code screenshots
- formulas
- flowcharts
- labels/captions
- important visual relationships

Return plain text only.
Do not include decorative details.
""".strip()

                visual_text = ask_vision_on_image_bytes(image_bytes, prompt)
                if visual_text:
                    visual_blocks.append(visual_text[:MAX_VISION_CHARS_PER_PAGE])
            except Exception as e:
                print(f"  Vision failed on slide image: {e}")

    return visual_blocks, has_picture


def combine_page_text(text: str, visual_text: str) -> str:
    text = (text or "").strip()
    visual_text = (visual_text or "").strip()

    if text and visual_text:
        return f"{text}\n\n[Visual content]\n{visual_text}".strip()
    if text:
        return text
    if visual_text:
        return f"[Visual content]\n{visual_text}".strip()
    return ""


# =========================================================
# FILE READING
# =========================================================

def build_doc_record(file_name: str, relative_path: str, file_type: str, pages: list[dict]) -> dict:
    return {
        "file_name": file_name,
        "relative_path": relative_path,
        "file_type": file_type,
        "num_pages": len(pages),
        "pages": pages,
        "full_text": "\n\n".join([p.get("combined_text", p.get("text", "")) for p in pages]).strip(),
    }


def extract_pdf_text_from_path(pdf_path: Path, relative_path: str) -> dict:
    doc = fitz.open(pdf_path)
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        visual_text = ""

        if should_run_vision_on_pdf_page(page, text):
            try:
                image_bytes = render_pdf_page_to_png_bytes(page)
                prompt = build_visual_prompt(file_type="pdf", page_number=i + 1)
                visual_text = ask_vision_on_image_bytes(image_bytes, prompt)
                visual_text = visual_text[:MAX_VISION_CHARS_PER_PAGE].strip()
            except Exception as e:
                print(f"  Vision failed on PDF page {i + 1} in {pdf_path.name}: {e}")

        combined_text = combine_page_text(text, visual_text)

        pages.append({
            "page": i + 1,
            "text": text,
            "visual_text": visual_text,
            "combined_text": combined_text,
        })

    doc.close()

    return build_doc_record(
        file_name=pdf_path.name,
        relative_path=relative_path,
        file_type="pdf",
        pages=pages,
    )


def extract_pdf_text_from_bytes(file_name: str, relative_path: str, file_bytes: bytes) -> dict:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        visual_text = ""

        if should_run_vision_on_pdf_page(page, text):
            try:
                image_bytes = render_pdf_page_to_png_bytes(page)
                prompt = build_visual_prompt(file_type="pdf", page_number=i + 1)
                visual_text = ask_vision_on_image_bytes(image_bytes, prompt)
                visual_text = visual_text[:MAX_VISION_CHARS_PER_PAGE].strip()
            except Exception as e:
                print(f"  Vision failed on PDF page {i + 1} in {file_name}: {e}")

        combined_text = combine_page_text(text, visual_text)

        pages.append({
            "page": i + 1,
            "text": text,
            "visual_text": visual_text,
            "combined_text": combined_text,
        })

    doc.close()

    return build_doc_record(
        file_name=file_name,
        relative_path=relative_path,
        file_type="pdf",
        pages=pages,
    )


def extract_pptx_text_from_path(pptx_path: Path, relative_path: str) -> dict:
    prs = Presentation(str(pptx_path))
    slides_data = []

    for i, slide in enumerate(prs.slides):
        slide_text_parts = []

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                slide_text_parts.append(shape.text)

        text = "\n".join(slide_text_parts).strip()

        has_picture = any(shape.shape_type == MSO_SHAPE_TYPE.PICTURE for shape in slide.shapes)
        run_vision = should_run_vision_on_slide(text, has_picture)

        visual_blocks, _ = extract_picture_texts_from_slide(slide, run_vision=run_vision)
        visual_text = "\n\n".join([b for b in visual_blocks if b.strip()]).strip()

        combined_text = combine_page_text(text, visual_text)

        slides_data.append({
            "page": i + 1,
            "text": text,
            "visual_text": visual_text,
            "combined_text": combined_text,
        })

    return build_doc_record(
        file_name=pptx_path.name,
        relative_path=relative_path,
        file_type="pptx",
        pages=slides_data,
    )


def extract_pptx_text_from_bytes(file_name: str, relative_path: str, file_bytes: bytes) -> dict:
    prs = Presentation(io.BytesIO(file_bytes))
    slides_data = []

    for i, slide in enumerate(prs.slides):
        slide_text_parts = []

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                slide_text_parts.append(shape.text)

        text = "\n".join(slide_text_parts).strip()

        has_picture = any(shape.shape_type == MSO_SHAPE_TYPE.PICTURE for shape in slide.shapes)
        run_vision = should_run_vision_on_slide(text, has_picture)

        visual_blocks, _ = extract_picture_texts_from_slide(slide, run_vision=run_vision)
        visual_text = "\n\n".join([b for b in visual_blocks if b.strip()]).strip()

        combined_text = combine_page_text(text, visual_text)

        slides_data.append({
            "page": i + 1,
            "text": text,
            "visual_text": visual_text,
            "combined_text": combined_text,
        })

    return build_doc_record(
        file_name=file_name,
        relative_path=relative_path,
        file_type="pptx",
        pages=slides_data,
    )


def extract_code_text_from_path(file_path: Path, relative_path: str) -> dict:
    text = file_path.read_text(encoding="utf-8", errors="ignore").strip()

    return build_doc_record(
        file_name=file_path.name,
        relative_path=relative_path,
        file_type=file_path.suffix.lower().lstrip("."),
        pages=[{
            "page": 1,
            "text": text,
            "visual_text": "",
            "combined_text": text,
        }],
    )


def extract_code_text_from_bytes(file_name: str, relative_path: str, file_type: str, file_bytes: bytes) -> dict:
    text = file_bytes.decode("utf-8", errors="ignore").strip()

    return build_doc_record(
        file_name=file_name,
        relative_path=relative_path,
        file_type=file_type,
        pages=[{
            "page": 1,
            "text": text,
            "visual_text": "",
            "combined_text": text,
        }],
    )


def extract_regular_file(file_path: Path, course_dir: Path) -> list[dict]:
    suffix = file_path.suffix.lower()
    relative_path = str(file_path.relative_to(course_dir))

    if suffix == ".pdf":
        return [extract_pdf_text_from_path(file_path, relative_path)]
    if suffix == ".pptx":
        return [extract_pptx_text_from_path(file_path, relative_path)]

    return [extract_code_text_from_path(file_path, relative_path)]


def extract_zip_contents(zip_path: Path, course_dir: Path) -> list[dict]:
    docs = []
    zip_relative = str(zip_path.relative_to(course_dir))

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member_name in zf.namelist():
            if member_name.endswith("/"):
                continue

            member_path = Path(member_name)

            if member_path.name.startswith("._"):
                continue
            if any(part in IGNORED_DIR_NAMES for part in member_path.parts):
                continue

            suffix = member_path.suffix.lower()
            if suffix not in SUPPORTED_ZIP_MEMBER_EXTENSIONS:
                continue

            file_bytes = zf.read(member_name)
            virtual_relative_path = f"{zip_relative}::{member_name}"

            try:
                if suffix == ".pdf":
                    docs.append(
                        extract_pdf_text_from_bytes(
                            file_name=member_path.name,
                            relative_path=virtual_relative_path,
                            file_bytes=file_bytes,
                        )
                    )
                elif suffix == ".pptx":
                    docs.append(
                        extract_pptx_text_from_bytes(
                            file_name=member_path.name,
                            relative_path=virtual_relative_path,
                            file_bytes=file_bytes,
                        )
                    )
                else:
                    docs.append(
                        extract_code_text_from_bytes(
                            file_name=member_path.name,
                            relative_path=virtual_relative_path,
                            file_type=suffix.lstrip("."),
                            file_bytes=file_bytes,
                        )
                    )
            except Exception as e:
                print(f"  Skipped zip member {virtual_relative_path}: {e}")

    return docs


def extract_source_docs(file_path: Path, course_dir: Path) -> list[dict]:
    suffix = file_path.suffix.lower()

    if suffix == ".zip":
        return extract_zip_contents(file_path, course_dir)

    return extract_regular_file(file_path, course_dir)


def load_all_docs(files: list[Path], course_dir: Path) -> list[dict]:
    docs = []

    for f in tqdm(files, desc="Reading files", leave=False):
        try:
            docs.extend(extract_source_docs(f, course_dir))
        except Exception as e:
            print(f"  Skipped {f.name}: {e}")

    return docs


# =========================================================
# METADATA JSON WRITING
# =========================================================

def build_materials_index(course_dir: Path, docs_df: pd.DataFrame) -> dict:
    materials = []

    for i, (_, row) in enumerate(docs_df.iterrows(), start=1):
        materials.append({
            "material_id": f"{safe_slug(course_dir.name)}_{i:03d}",
            "file_name": row["file_name"],
            "relative_path": row["relative_path"],
            "file_type": row["file_type"],
            "chapter": row["chapter"],
        })

    return {
        "course_folder": course_dir.name,
        "materials": materials,
    }


def write_metadata_files(course_dir: Path, docs_df: pd.DataFrame):
    metadata_dir = course_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    course_meta = resolve_course_metadata(course_dir.name)

    course_info = {
        "course_code": course_meta["course_code"],
        "course_title": course_meta["official_title"],
        "course_folder_name": course_dir.name,
        "credit_hours": course_meta["credit_hours"],
        "prerequisites": course_meta["prerequisites"],
        "concurrent": course_meta["concurrent"],
        "recommended_year": course_meta["recommended_year"],
        "recommended_semester": course_meta["recommended_semester"],
        "description": course_meta["description"],
    }

    prerequisites = {
        "course_code": course_meta["course_code"],
        "course_title": course_meta["official_title"],
        "prerequisites": course_meta["prerequisites"],
        "concurrent": course_meta["concurrent"],
    }

    materials_index = build_materials_index(course_dir, docs_df)

    topic_schema = {
        "schema_name": "topic_object_v2",
        "fields": [
            "topic_name",
            "subtopics",
            "file_source",
            "relative_path",
            "chapter",
            "summary",
            "keywords",
        ],
    }

    files = {
        "course_info.json": course_info,
        "prerequisites.json": prerequisites,
        "materials_index.json": materials_index,
        "topic_schema.json": topic_schema,
    }

    for filename, content in files.items():
        with open(metadata_dir / filename, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

    return {
        "course_info": course_info,
        "prerequisites": prerequisites,
        "materials_index": materials_index,
        "topic_schema": topic_schema,
    }


# =========================================================
# CLEANING
# =========================================================

bad_patterns = [
    "copyright",
    "references",
    "reference",
    "lecture notes",
    "course instructor",
    "any question",
    "thank you",
    "princess sumaya university for technology",
    "king hussein school",
    "data science department",
    "amman",
    "p.o.box",
    "al-jubaiha",
    "www.psut.edu.jo",
    "info@psut.edu.jo",
    "www",
    "email",
    "call",
    "fax",
    "info",
    "962",
    "jo",
    "edu",
    "psut",
    "dr.",
    "doctor",
    "prof.",
    "ibrahim abu alhaol",
    "bushra alhijawi",
    "ahmad alzghoul",
    "mohammad azzeh",
    "ibrahim",
    "bushra",
    "alhijawi",
    "alzghoul",
    "abu",
]


def remove_repeated_page_lines(docs: list[dict], min_repeat_ratio: float = 0.35):
    all_lines = []
    page_count = 0

    for doc in docs:
        if doc["file_type"] not in {"pdf", "pptx"}:
            continue

        for page in doc["pages"]:
            page_count += 1
            lines = [normalize_line(l) for l in page.get("text", "").splitlines() if l.strip()]
            unique_lines = set(lines)
            all_lines.extend(unique_lines)

    line_counts = Counter(all_lines)

    repeated_lines = {
        line for line, count in line_counts.items()
        if page_count > 0 and count >= page_count * min_repeat_ratio
    }

    cleaned_docs = []

    for doc in docs:
        cleaned_pages = []

        for page in doc["pages"]:
            original_lines = page.get("text", "").splitlines()
            kept_lines = []

            for line in original_lines:
                norm = normalize_line(line)

                if not norm:
                    continue

                if doc["file_type"] in {"pdf", "pptx"} and norm in repeated_lines:
                    continue

                if doc["file_type"] in {"pdf", "pptx"} and any(p in norm for p in bad_patterns):
                    continue

                if doc["file_type"] in {"pdf", "pptx"} and re.fullmatch(r"\d{1,4}", norm):
                    continue

                if len(norm) <= 2:
                    continue

                if norm.isdigit():
                    continue

                kept_lines.append(line)

            cleaned_text = "\n".join(kept_lines).strip()
            visual_text = page.get("visual_text", "").strip()
            combined_text = combine_page_text(cleaned_text, visual_text)

            cleaned_pages.append({
                "page": page["page"],
                "text": cleaned_text,
                "visual_text": visual_text,
                "combined_text": combined_text,
            })

        cleaned_docs.append({
            "file_name": doc["file_name"],
            "relative_path": doc["relative_path"],
            "file_type": doc["file_type"],
            "num_pages": doc["num_pages"],
            "pages": cleaned_pages,
            "full_text": "\n\n".join([p.get("combined_text", "") for p in cleaned_pages]).strip(),
        })

    return cleaned_docs, repeated_lines


# =========================================================
# DATAFRAMES + CHUNKING
# =========================================================

def build_docs_df(docs: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(docs)
    df["chapter"] = df["file_name"].str.extract(r"(CH\d+|ch\d+)", expand=False)
    df["chapter"] = df["chapter"].fillna("").str.upper()
    return df


def chunk_text(text: str, chunk_size: int = 450, overlap: int = 80) -> list[str]:
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        if end == len(words):
            break

        start = end - overlap

    return chunks


def build_chunks_df(course_name: str, docs_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in docs_df.iterrows():
        chunks = chunk_text(row["full_text"])

        for idx, chunk in enumerate(chunks):
            rows.append({
                "course_name": course_name,
                "file_name": row["file_name"],
                "relative_path": row["relative_path"],
                "file_type": row["file_type"],
                "chapter": row["chapter"],
                "chunk_id": idx,
                "chunk_text": chunk,
            })

    return pd.DataFrame(rows)


# =========================================================
# SUMMARIZATION + CONCEPT EXTRACTION
# =========================================================

def run_summarization(course_name: str, docs_df: pd.DataFrame) -> dict:
    summaries = {}

    for _, row in tqdm(
        docs_df.iterrows(),
        total=len(docs_df),
        desc=f"Summarizing {course_name}",
        leave=False,
    ):
        prompt = f"""
Write a detailed academic summary of this course file.

Requirements:
- 2 to 4 medium-length paragraphs
- not bullet points
- mention main concepts, important methods, and what the file teaches
- keep it clear and study-oriented
- do not add information not found in the content

Course: {course_name}
File: {row['relative_path']}

Content:
{row['full_text'][:4000]}
"""
        summaries[row["relative_path"]] = ask_llm(prompt)

    return summaries


def run_concept_extraction(course_name: str, docs_df: pd.DataFrame) -> dict:
    concepts = {}

    for _, row in tqdm(
        docs_df.iterrows(),
        total=len(docs_df),
        desc=f"Concept extraction {course_name}",
        leave=False,
    ):
        prompt = f"""
You are extracting academic concepts from course content.

Course: {course_name}
File: {row['relative_path']}

Return ONLY valid JSON in this exact format:
{{
  "chapter": "{row['chapter']}",
  "topics": [
    {{
      "topic_name": "...",
      "subtopics": ["...", "..."],
      "keywords": ["...", "..."]
    }}
  ]
}}

Rules:
- Return valid JSON only.
- Do not add explanations before or after the JSON.
- Extract only concepts actually present in the content.
- Keep topic names concise and academic.
- Keep subtopics specific.
- Keep keywords short.

Content:
{row['full_text'][:2500]}
"""
        raw = ask_llm(prompt)
        parsed = extract_json_block(raw)

        if parsed and isinstance(parsed, dict) and "topics" in parsed:
            concepts[row["relative_path"]] = parsed
        else:
            concepts[row["relative_path"]] = {
                "chapter": row["chapter"],
                "topics": [],
            }

    return concepts


# =========================================================
# DATA PREP FOR SUMMARY / CONCEPT / METADATA VECTORIZATION
# =========================================================

def build_summaries_df(course_name: str, summaries: dict) -> pd.DataFrame:
    rows = []

    for relative_path, summary_text in summaries.items():
        rows.append({
            "course_name": course_name,
            "relative_path": relative_path,
            "summary_text": summary_text,
        })

    return pd.DataFrame(rows)


def flatten_concepts_for_chroma(course_name: str, concepts: dict) -> pd.DataFrame:
    rows = []

    for relative_path, content in concepts.items():
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
            ).strip()

            rows.append({
                "course_name": course_name,
                "relative_path": relative_path,
                "chapter": chapter,
                "topic_index": idx,
                "topic_name": topic_name,
                "concept_text": concept_text,
            })

    return pd.DataFrame(rows)


def build_metadata_documents(course_name: str, metadata_objects: dict) -> pd.DataFrame:
    rows = []

    for doc_type, content in metadata_objects.items():
        rows.append({
            "course_name": course_name,
            "doc_type": doc_type,
            "document_text": json.dumps(content, ensure_ascii=False, indent=2),
        })

    return pd.DataFrame(rows)


# =========================================================
# CHROMADB / VECTORIZATION
# =========================================================

def get_chroma_client(chroma_dir: Path):
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_dir))


def get_embedding_function():
    return embedding_functions.DefaultEmbeddingFunction()


def recreate_collection(chroma_client, collection_name: str, embedding_function):
    try:
        chroma_client.delete_collection(name=collection_name)
    except Exception:
        pass

    return chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
    )


def save_chunks_to_chroma(course_name: str, chunks_df: pd.DataFrame, chroma_dir: Path):
    chroma_client = get_chroma_client(chroma_dir)
    embedding_function = get_embedding_function()

    collection_name = f"{safe_slug(course_name)}{CHUNKS_COLLECTION_SUFFIX}"
    collection = recreate_collection(chroma_client, collection_name, embedding_function)

    ids = []
    documents = []
    metadatas = []

    for _, row in chunks_df.iterrows():
        ids.append(f"{safe_slug(course_name)}_{safe_slug(row['relative_path'])}_{row['chunk_id']}")
        documents.append(row["chunk_text"])
        metadatas.append({
            "doc_type": "chunk",
            "course_name": str(row["course_name"]),
            "file_name": str(row["file_name"]),
            "relative_path": str(row["relative_path"]),
            "file_type": str(row["file_type"]),
            "chapter": str(row["chapter"]),
            "chunk_id": int(row["chunk_id"]),
        })

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"  Chunks vectorized and saved: {collection.count()}")


def save_summaries_to_chroma(course_name: str, summaries_df: pd.DataFrame, chroma_dir: Path):
    chroma_client = get_chroma_client(chroma_dir)
    embedding_function = get_embedding_function()

    collection_name = f"{safe_slug(course_name)}_summaries"
    collection = recreate_collection(chroma_client, collection_name, embedding_function)

    ids = []
    documents = []
    metadatas = []

    for idx, row in summaries_df.iterrows():
        ids.append(f"{safe_slug(course_name)}_summary_{idx}")
        documents.append(row["summary_text"])
        metadatas.append({
            "doc_type": "summary",
            "course_name": str(row["course_name"]),
            "relative_path": str(row["relative_path"]),
        })

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    print(f"  Summaries vectorized and saved: {collection.count()}")


def save_concepts_to_chroma(course_name: str, concepts_df: pd.DataFrame, chroma_dir: Path):
    chroma_client = get_chroma_client(chroma_dir)
    embedding_function = get_embedding_function()

    collection_name = f"{safe_slug(course_name)}_concepts"
    collection = recreate_collection(chroma_client, collection_name, embedding_function)

    ids = []
    documents = []
    metadatas = []

    for idx, row in concepts_df.iterrows():
        ids.append(f"{safe_slug(course_name)}_concept_{idx}")
        documents.append(row["concept_text"])
        metadatas.append({
            "doc_type": "concept",
            "course_name": str(row["course_name"]),
            "relative_path": str(row["relative_path"]),
            "chapter": str(row["chapter"]),
            "topic_name": str(row["topic_name"]),
            "topic_index": int(row["topic_index"]),
        })

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    print(f"  Concepts vectorized and saved: {collection.count()}")


def save_metadata_to_chroma(course_name: str, metadata_df: pd.DataFrame, chroma_dir: Path):
    chroma_client = get_chroma_client(chroma_dir)
    embedding_function = get_embedding_function()

    collection_name = f"{safe_slug(course_name)}_metadata"
    collection = recreate_collection(chroma_client, collection_name, embedding_function)

    ids = []
    documents = []
    metadatas = []

    for idx, row in metadata_df.iterrows():
        ids.append(f"{safe_slug(course_name)}_metadata_{idx}")
        documents.append(row["document_text"])
        metadatas.append({
            "doc_type": "metadata",
            "course_name": str(row["course_name"]),
            "metadata_type": str(row["doc_type"]),
        })

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    print(f"  Metadata vectorized and saved: {collection.count()}")


def vectorize_and_save_course_outputs(
    course_name: str,
    chunks_df: pd.DataFrame,
    summaries: dict | None,
    concepts: dict | None,
    metadata_objects: dict,
    chroma_dir: Path,
):
    print("  Starting vectorization and ChromaDB saving...")

    save_chunks_to_chroma(course_name, chunks_df, chroma_dir)

    if summaries:
        summaries_df = build_summaries_df(course_name, summaries)
        save_summaries_to_chroma(course_name, summaries_df, chroma_dir)

    if concepts:
        concepts_df = flatten_concepts_for_chroma(course_name, concepts)
        save_concepts_to_chroma(course_name, concepts_df, chroma_dir)

    metadata_df = build_metadata_documents(course_name, metadata_objects)
    save_metadata_to_chroma(course_name, metadata_df, chroma_dir)

    print("  Vectorization and ChromaDB saving completed.")


# =========================================================
# CHAPTER SUBTOPIC GROUPING + CLUSTERING
# =========================================================

def normalize_subtopic(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def build_chapter_subtopics_grouped(course_name: str, concepts: dict) -> dict:
    grouped = {
        "course_name": course_name,
        "chapters": []
    }

    chapter_map = {}

    for relative_path, content in concepts.items():
        chapter = str(content.get("chapter", "")).strip() or "NO_CHAPTER"

        if chapter not in chapter_map:
            chapter_map[chapter] = {
                "chapter": chapter,
                "topics": []
            }

        for topic in content.get("topics", []):
            topic_name = str(topic.get("topic_name", "")).strip()
            subtopics = [str(s).strip() for s in topic.get("subtopics", []) if str(s).strip()]
            keywords = [str(k).strip() for k in topic.get("keywords", []) if str(k).strip()]

            if not topic_name and not subtopics:
                continue

            chapter_map[chapter]["topics"].append({
                "topic_name": topic_name,
                "subtopics": subtopics,
                "keywords": keywords,
                "relative_path": relative_path,
            })

    grouped["chapters"] = sorted(
        chapter_map.values(),
        key=lambda x: x["chapter"]
    )

    return grouped


def build_subtopic_clusters(course_name: str, concepts: dict) -> dict:
    """
    Lightweight clustering:
    groups nearly identical / strongly overlapping subtopics inside the same chapter.
    This is a rule-based first version, simple and safe for your project.
    """
    clusters_output = {
        "course_name": course_name,
        "chapters": []
    }

    chapter_buckets = {}

    for relative_path, content in concepts.items():
        chapter = str(content.get("chapter", "")).strip() or "NO_CHAPTER"

        if chapter not in chapter_buckets:
            chapter_buckets[chapter] = []

        for topic in content.get("topics", []):
            topic_name = str(topic.get("topic_name", "")).strip()
            keywords = [str(k).strip() for k in topic.get("keywords", []) if str(k).strip()]

            for subtopic in topic.get("subtopics", []):
                subtopic = str(subtopic).strip()
                if not subtopic:
                    continue

                chapter_buckets[chapter].append({
                    "topic_name": topic_name,
                    "subtopic_name": subtopic,
                    "normalized_subtopic": normalize_subtopic(subtopic),
                    "keywords": keywords,
                    "relative_path": relative_path,
                })

    for chapter, items in sorted(chapter_buckets.items(), key=lambda x: x[0]):
        used = set()
        chapter_clusters = []

        for i, item in enumerate(items):
            if i in used:
                continue

            current_cluster = [item]
            used.add(i)

            item_words = set(item["normalized_subtopic"].split())

            for j, other in enumerate(items):
                if j in used:
                    continue

                other_words = set(other["normalized_subtopic"].split())

                if not item_words or not other_words:
                    continue

                overlap = len(item_words & other_words)
                min_len = min(len(item_words), len(other_words))

                # simple clustering rule:
                # same normalized text OR strong word overlap
                if (
                    item["normalized_subtopic"] == other["normalized_subtopic"]
                    or (min_len > 0 and overlap / min_len >= 0.6)
                ):
                    current_cluster.append(other)
                    used.add(j)

            representative = current_cluster[0]["subtopic_name"]

            chapter_clusters.append({
                "cluster_id": f"{safe_slug(course_name)}_{safe_slug(chapter)}_{len(chapter_clusters)+1}",
                "chapter": chapter,
                "representative_subtopic": representative,
                "members": [
                    {
                        "topic_name": x["topic_name"],
                        "subtopic_name": x["subtopic_name"],
                        "relative_path": x["relative_path"],
                    }
                    for x in current_cluster
                ],
                "cluster_size": len(current_cluster),
            })

        clusters_output["chapters"].append({
            "chapter": chapter,
            "clusters": chapter_clusters
        })

    return clusters_output

# =========================================================
# MAIN COURSE PIPELINE
# =========================================================

def load_json_file(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_course_already_processed(course_dir: Path) -> bool:
    outputs_dir = course_dir / "outputs"
    metadata_dir = course_dir / "metadata"
    chroma_dir = outputs_dir / "chroma_db"

    required_files = [
        outputs_dir / "raw_docs.json",
        outputs_dir / "chapters.csv",
        outputs_dir / "chunks.csv",
        metadata_dir / "course_info.json",
        metadata_dir / "prerequisites.json",
        metadata_dir / "materials_index.json",
        metadata_dir / "topic_schema.json",
    ]

    if RUN_SUMMARIZATION:
        required_files.append(outputs_dir / "chapter_summaries.json")

    if RUN_CONCEPT_EXTRACTION:
        required_files.append(outputs_dir / "chapter_concepts.json")
        required_files.append(outputs_dir / "chapter_subtopics_grouped.json")
        required_files.append(outputs_dir / "subtopic_clusters.json")

    files_exist = all(path.exists() for path in required_files)

    if SAVE_TO_CHROMA:
        chroma_exists = chroma_dir.exists()
        return files_exist and chroma_exists

    return files_exist

def process_course(course_dir: Path):
    course_name = course_dir.name
    outputs_dir = course_dir / "outputs"
    chroma_dir = outputs_dir / "chroma_db"

    outputs_dir.mkdir(parents=True, exist_ok=True)

    chapter_grouped_file = outputs_dir / "chapter_subtopics_grouped.json"
    subtopic_clusters_file = outputs_dir / "subtopic_clusters.json"
    concepts_file = outputs_dir / "chapter_concepts.json"

    # Partial processing: only create missing clustering files
    if not FORCE_REGENERATE:
        if concepts_file.exists() and (
            not chapter_grouped_file.exists() or not subtopic_clusters_file.exists()
        ):
            print(f"\nPartial processing (only clustering) for: {course_name}")

            concepts = load_json_file(concepts_file)

            chapter_grouped = build_chapter_subtopics_grouped(course_name, concepts)
            with open(chapter_grouped_file, "w", encoding="utf-8") as f:
                json.dump(chapter_grouped, f, indent=2, ensure_ascii=False)

            subtopic_clusters = build_subtopic_clusters(course_name, concepts)
            with open(subtopic_clusters_file, "w", encoding="utf-8") as f:
                json.dump(subtopic_clusters, f, indent=2, ensure_ascii=False)

            print("  Clustering done ✅ (no reprocessing)")
            return

    if not FORCE_REGENERATE and is_course_already_processed(course_dir):
        print(f"\nSkipping already processed course: {course_name} (outputs already exist)")
        return

    print(f"\nProcessing course: {course_name}")

    files = collect_supported_sources(course_dir)

    if not files:
        print("  No supported files found. Skipping.")
        return

    print(f"  Sources found: {len(files)}")

    docs = load_all_docs(files, course_dir)

    if not docs:
        print("  No readable documents extracted. Skipping.")
        return

    docs, removed_lines = remove_repeated_page_lines(docs)

    with open(outputs_dir / "raw_docs.json", "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

    with open(outputs_dir / "removed_repeated_lines.json", "w", encoding="utf-8") as f:
        json.dump(sorted(list(removed_lines)), f, indent=2, ensure_ascii=False)

    docs_df = build_docs_df(docs)
    docs_df.to_csv(outputs_dir / "chapters.csv", index=False)

    metadata_objects = write_metadata_files(course_dir, docs_df)

    chunks_df = build_chunks_df(course_name, docs_df)
    chunks_df.to_csv(outputs_dir / "chunks.csv", index=False)

    print(f"  Chunks created: {len(chunks_df)}")

    summaries = None
    concepts = None

    summaries_file = outputs_dir / "chapter_summaries.json"

    if RUN_SUMMARIZATION:
        if summaries_file.exists() and not FORCE_REGENERATE:
            summaries = load_json_file(summaries_file)
            print("  Summaries already exist, skipping LLM summarization")
        else:
            summaries = run_summarization(course_name, docs_df)
            with open(summaries_file, "w", encoding="utf-8") as f:
                json.dump(summaries, f, indent=2, ensure_ascii=False)
            print("  Summaries saved")

    if RUN_CONCEPT_EXTRACTION:
        if concepts_file.exists() and not FORCE_REGENERATE:
            concepts = load_json_file(concepts_file)
            print("  Concepts already exist, skipping LLM concept extraction")
        else:
            concepts = run_concept_extraction(course_name, docs_df)
            with open(concepts_file, "w", encoding="utf-8") as f:
                json.dump(concepts, f, indent=2, ensure_ascii=False)
            print("  Concepts saved")

        chapter_grouped = build_chapter_subtopics_grouped(course_name, concepts)
        with open(chapter_grouped_file, "w", encoding="utf-8") as f:
            json.dump(chapter_grouped, f, indent=2, ensure_ascii=False)
        print("  Chapter-grouped subtopics saved")

        subtopic_clusters = build_subtopic_clusters(course_name, concepts)
        with open(subtopic_clusters_file, "w", encoding="utf-8") as f:
            json.dump(subtopic_clusters, f, indent=2, ensure_ascii=False)
        print("  Subtopic clusters saved")

    if SAVE_TO_CHROMA:
        vectorize_and_save_course_outputs(
            course_name=course_name,
            chunks_df=chunks_df,
            summaries=summaries,
            concepts=concepts,
            metadata_objects=metadata_objects,
            chroma_dir=chroma_dir,
        )

    print("  Metadata written:", list(metadata_objects.keys()))
    print("  Done")

def process_all_courses(courses_root: Path):
    course_folders = collect_course_folders(courses_root)

    if not course_folders:
        print("No course folders found.")
        return

    print(f"Found {len(course_folders)} course folders.\n")

    if TEST_COURSE_NAME:
        test_course = courses_root / TEST_COURSE_NAME
        if not test_course.exists():
            raise FileNotFoundError(f"Test course folder not found: {test_course}")
        process_course(test_course)
        print("\nTest course processed successfully.")
        return

    for course_dir in course_folders:
        process_course(course_dir)

    print("\nAll courses processed successfully.")


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    process_all_courses(COURSES_DIR)