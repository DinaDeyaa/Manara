from __future__ import annotations

from pathlib import Path
import json
import re
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime

print("studentprofile.py loaded")


# =========================================================
# PATHS
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "student_profiles"

PROFILES_CSV = OUTPUT_DIR / "student_profiles.csv"
PROFILES_JSON = OUTPUT_DIR / "student_profiles.json"

CHROMA_DIR = OUTPUT_DIR / "chroma_db"
STUDENT_COLLECTION = "student_profiles"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# FILE FINDER
# =========================================================

def find_existing_file(candidates: list[Path], label: str) -> Path:
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"{label} not found. Checked:\n" + "\n".join(str(p) for p in candidates)
    )


ACCOUNTS_FILE = find_existing_file(
    [
        DATA_DIR / "students_accounts.csv",
        SCRIPT_DIR / "students_accounts.csv",
        Path("/Users/dinaal-memah/Desktop/students_accounts.csv"),
    ],
    "Accounts file"
)

STUDY_PLAN_FILE = find_existing_file(
    [
        DATA_DIR / "study_plan.json",
        DATA_DIR / "studyplan.json",
        SCRIPT_DIR / "study_plan.json",
        SCRIPT_DIR / "studyplan.json",
        Path("/Users/dinaal-memah/Desktop/study_plan.json"),
        Path("/Users/dinaal-memah/Desktop/studyplan.json"),
    ],
    "Study plan file"
)


# =========================================================
# CUSTOM ERRORS
# =========================================================

class StudentProfileError(Exception):
    pass


class AuthenticationError(StudentProfileError):
    pass


class ValidationError(StudentProfileError):
    pass


# =========================================================
# LOAD HELPERS
# =========================================================

def load_accounts() -> pd.DataFrame:
    df = pd.read_csv(ACCOUNTS_FILE, dtype=str).fillna("")
    df.columns = [str(c).strip() for c in df.columns]

    required_cols = {"student_id", "student_name", "password"}
    if not required_cols.issubset(df.columns):
        raise ValueError(
            f"Accounts CSV must contain columns: {sorted(required_cols)}"
        )

    df["student_id"] = df["student_id"].astype(str).str.strip()
    df["student_name"] = df["student_name"].astype(str).str.strip()
    df["password"] = df["password"].astype(str).str.strip()

    return df


def load_study_plan() -> dict:
    with open(STUDY_PLAN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_existing_profiles() -> pd.DataFrame:
    expected_cols = [
        "student_id",
        "student_name",
        "courses_taken",
        "terms_accepted",
        "phone_number",
        "whatsapp_opt_in",
        "last_active_at",
    ]

    if PROFILES_CSV.exists():
        df = pd.read_csv(PROFILES_CSV, dtype=str).fillna("")
        df.columns = [str(c).strip() for c in df.columns]

        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""

        df["student_id"] = df["student_id"].astype(str).str.strip()
        return df[expected_cols]

    return pd.DataFrame(columns=expected_cols)


# =========================================================
# NORMALIZATION HELPERS
# =========================================================

def normalize_course_name(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def parse_saved_courses(courses_text: str) -> list[str]:
    if not str(courses_text).strip():
        return []

    parts = [c.strip() for c in str(courses_text).split("|")]
    return [c for c in parts if c]


def stringify_courses(courses: list[str]) -> str:
    return " | ".join(courses)


def to_bool_str(value: bool) -> str:
    return "true" if bool(value) else "false"


def str_to_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


# =========================================================
# JORDAN PHONE VALIDATION
# =========================================================

def normalize_jordan_phone(phone_number: str) -> str:
    phone = str(phone_number or "").strip()

    if not phone:
        return ""

    phone = phone.replace(" ", "").replace("-", "")

    if phone.startswith("+962"):
        phone = "0" + phone[4:]
    elif phone.startswith("962"):
        phone = "0" + phone[3:]

    return phone


def validate_jordan_phone(phone_number: str) -> tuple[bool, str]:
    normalized = normalize_jordan_phone(phone_number)

    if not normalized:
        return True, ""

    pattern = r"^07[789]\d{7}$"
    if not re.fullmatch(pattern, normalized):
        return False, ""

    return True, normalized


# =========================================================
# STUDY PLAN VALIDATION
# =========================================================

def build_course_lookup(study_plan: dict) -> dict:
    if "courses" not in study_plan:
        raise ValueError("study_plan.json must contain top-level key: 'courses'")

    lookup = {}

    for course_name, course_info in study_plan["courses"].items():
        lookup[normalize_course_name(course_name)] = {
            "official_name": course_name,
            "course_code": course_info.get("course_code", ""),
            "prerequisites": course_info.get("prerequisites", []),
        }

    return lookup


def validate_completed_courses(courses_taken: list[str], study_plan: dict) -> dict:
    lookup = build_course_lookup(study_plan)

    entered_normalized = [normalize_course_name(c) for c in courses_taken]
    entered_set = set(entered_normalized)

    unknown_courses = []
    violations = []
    valid_courses = []

    for original_course in courses_taken:
        norm_course = normalize_course_name(original_course)

        if norm_course not in lookup:
            unknown_courses.append(original_course)
            continue

        course_info = lookup[norm_course]
        missing_prereqs = []

        for prereq in course_info["prerequisites"]:
            prereq_norm = normalize_course_name(prereq)
            if prereq_norm not in entered_set:
                missing_prereqs.append(prereq)

        if missing_prereqs:
            violations.append({
                "course": course_info["official_name"],
                "missing_prerequisites": missing_prereqs,
            })
        else:
            valid_courses.append(course_info["official_name"])

    return {
        "valid_courses": valid_courses,
        "unknown_courses": unknown_courses,
        "violations": violations,
        "is_valid": len(violations) == 0 and len(unknown_courses) == 0,
    }


# =========================================================
# PROFILE HELPERS
# =========================================================

def merge_courses(old_courses: list[str], new_courses: list[str]) -> list[str]:
    merged = []
    seen = set()

    for course in old_courses + new_courses:
        key = normalize_course_name(course)
        if key and key not in seen:
            seen.add(key)
            merged.append(course.strip())

    return merged


def get_profile_row(student_id: str, profiles_df: pd.DataFrame):
    match = profiles_df[profiles_df["student_id"].astype(str).str.strip() == str(student_id).strip()]
    if match.empty:
        return None
    return match.iloc[0]


def row_to_profile_dict(row) -> dict:
    return {
        "student_id": str(row["student_id"]).strip(),
        "student_name": str(row["student_name"]).strip(),
        "courses_taken": parse_saved_courses(row.get("courses_taken", "")),
        "terms_accepted": str_to_bool(row.get("terms_accepted", "")),
        "phone_number": str(row.get("phone_number", "")).strip(),
        "whatsapp_opt_in": str_to_bool(row.get("whatsapp_opt_in", "")),
        "last_active_at": str(row.get("last_active_at", "")).strip(),  
    }

def update_last_active(student_id: str):
    profiles_df = load_existing_profiles()
    row = get_profile_row(student_id, profiles_df)

    if row is None:
        profile = {
            "student_id": student_id,
            "student_name": "",
            "courses_taken": [],
            "terms_accepted": False,
            "phone_number": "",
            "whatsapp_opt_in": False,
            "last_active_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        profile = row_to_profile_dict(row)

    save_student_profile(profile)


# =========================================================
# SAVE PROFILE
# =========================================================

def save_student_profile(student_profile: dict):
    row = {
        "student_id": str(student_profile["student_id"]).strip(),
        "student_name": str(student_profile["student_name"]).strip(),
        "courses_taken": stringify_courses(student_profile.get("courses_taken", [])),
        "terms_accepted": to_bool_str(student_profile.get("terms_accepted", False)),
        "phone_number": str(student_profile.get("phone_number", "")).strip(),
        "whatsapp_opt_in": to_bool_str(student_profile.get("whatsapp_opt_in", False)),
        "last_active_at": student_profile.get("last_active_at", ""), 
    }

    new_df = pd.DataFrame([row])

    if PROFILES_CSV.exists():
        old_df = pd.read_csv(PROFILES_CSV, dtype=str).fillna("")
        old_df.columns = [str(c).strip() for c in old_df.columns]

        for col in new_df.columns:
            if col not in old_df.columns:
                old_df[col] = ""

        old_df["student_id"] = old_df["student_id"].astype(str).str.strip()
        old_df = old_df[old_df["student_id"] != str(student_profile["student_id"]).strip()]
        final_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        final_df = new_df

    final_df.to_csv(PROFILES_CSV, index=False, encoding="utf-8-sig")

    records = final_df.to_dict(orient="records")
    with open(PROFILES_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def save_student_to_chroma(student_profile: dict):
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    embedding_function = embedding_functions.DefaultEmbeddingFunction()

    collection = chroma_client.get_or_create_collection(
        name=STUDENT_COLLECTION,
        embedding_function=embedding_function
    )

    student_id = str(student_profile["student_id"]).strip()
    student_name = str(student_profile["student_name"]).strip()
    courses_taken = student_profile.get("courses_taken", [])
    phone_number = str(student_profile.get("phone_number", "")).strip()

    profile_text = f"""
Student ID: {student_id}
Student Name: {student_name}
Courses Taken: {", ".join(courses_taken)}
Terms Accepted: {student_profile.get("terms_accepted", False)}
Phone Number: {phone_number}
WhatsApp Opt In: {student_profile.get("whatsapp_opt_in", False)}
""".strip()

    metadata = {
        "student_id": student_id,
        "student_name": student_name,
        "courses_taken_count": len(courses_taken),
        "terms_accepted": bool(student_profile.get("terms_accepted", False)),
        "has_phone_number": bool(phone_number),
        "whatsapp_opt_in": bool(student_profile.get("whatsapp_opt_in", False)),
    }

    collection.upsert(
        ids=[student_id],
        documents=[profile_text],
        metadatas=[metadata]
    )


# =========================================================
# FRONTEND-FRIENDLY SERVICE FUNCTIONS
# =========================================================

def authenticate_student(student_id: str, password: str) -> dict:
    accounts_df = load_accounts()
    profiles_df = load_existing_profiles()

    match = accounts_df[
        (accounts_df["student_id"].astype(str).str.strip() == str(student_id).strip()) &
        (accounts_df["password"].astype(str).str.strip() == str(password).strip())
    ]

    if match.empty:
        raise AuthenticationError("Invalid student ID or password.")

    student_row = match.iloc[0]
    existing_row = get_profile_row(student_row["student_id"], profiles_df)

    if existing_row is None:
        profile = {
            "student_id": str(student_row["student_id"]).strip(),
            "student_name": str(student_row["student_name"]).strip(),
            "courses_taken": [],
            "terms_accepted": False,
            "phone_number": "",
            "whatsapp_opt_in": False,
        }
    else:
        profile = row_to_profile_dict(existing_row)

    update_last_active(student_row["student_id"])  

    return {
        "student_id": str(student_row["student_id"]).strip(),
        "student_name": str(student_row["student_name"]).strip(),
        "terms_accepted": profile["terms_accepted"],
        "phone_number": profile["phone_number"],
        "whatsapp_opt_in": profile["whatsapp_opt_in"],
        "courses_taken": profile["courses_taken"],
    }


def get_student_profile(student_id: str) -> dict | None:
    profiles_df = load_existing_profiles()
    row = get_profile_row(student_id, profiles_df)

    if row is None:
        return None

    return row_to_profile_dict(row)


def accept_terms(student_id: str) -> dict:
    accounts_df = load_accounts()
    profiles_df = load_existing_profiles()

    student_match = accounts_df[accounts_df["student_id"].astype(str).str.strip() == str(student_id).strip()]
    if student_match.empty:
        raise ValidationError("Student not found.")

    student_row = student_match.iloc[0]
    existing_row = get_profile_row(student_id, profiles_df)

    profile = {
        "student_id": str(student_row["student_id"]).strip(),
        "student_name": str(student_row["student_name"]).strip(),
        "courses_taken": [],
        "terms_accepted": True,
        "phone_number": "",
        "whatsapp_opt_in": False,
    }

    if existing_row is not None:
        old_profile = row_to_profile_dict(existing_row)
        profile["courses_taken"] = old_profile["courses_taken"]
        profile["phone_number"] = old_profile["phone_number"]
        profile["whatsapp_opt_in"] = old_profile["whatsapp_opt_in"]

    save_student_profile(profile)
    save_student_to_chroma(profile)

    update_last_active(student_id)

    return profile


def update_phone_number(student_id: str, phone_number: str = "", whatsapp_opt_in: bool = False) -> dict:
    accounts_df = load_accounts()
    profiles_df = load_existing_profiles()

    student_match = accounts_df[accounts_df["student_id"].astype(str).str.strip() == str(student_id).strip()]
    if student_match.empty:
        raise ValidationError("Student not found.")

    is_valid, normalized_phone = validate_jordan_phone(phone_number)
    if not is_valid:
        raise ValidationError("Invalid Jordan phone number. Use format like 0791234567.")

    student_row = student_match.iloc[0]
    existing_row = get_profile_row(student_id, profiles_df)

    profile = {
        "student_id": str(student_row["student_id"]).strip(),
        "student_name": str(student_row["student_name"]).strip(),
        "courses_taken": [],
        "terms_accepted": False,
        "phone_number": normalized_phone,
        "whatsapp_opt_in": bool(whatsapp_opt_in) if normalized_phone else False,
    }

    if existing_row is not None:
        old_profile = row_to_profile_dict(existing_row)
        profile["courses_taken"] = old_profile["courses_taken"]
        profile["terms_accepted"] = old_profile["terms_accepted"]

    save_student_profile(profile)
    save_student_to_chroma(profile)

    update_last_active(student_id)

    return profile


def update_completed_courses(student_id: str, new_courses: list[str]) -> dict:
    accounts_df = load_accounts()
    study_plan = load_study_plan()
    profiles_df = load_existing_profiles()

    student_match = accounts_df[accounts_df["student_id"].astype(str).str.strip() == str(student_id).strip()]
    if student_match.empty:
        raise ValidationError("Student not found.")

    student_row = student_match.iloc[0]
    existing_row = get_profile_row(student_id, profiles_df)

    old_courses = []
    terms_accepted = False
    phone_number = ""
    whatsapp_opt_in = False

    if existing_row is not None:
        old_profile = row_to_profile_dict(existing_row)
        old_courses = old_profile["courses_taken"]
        terms_accepted = old_profile["terms_accepted"]
        phone_number = old_profile["phone_number"]
        whatsapp_opt_in = old_profile["whatsapp_opt_in"]

    cleaned_new_courses = [str(c).strip() for c in new_courses if str(c).strip()]
    all_courses = merge_courses(old_courses, cleaned_new_courses)

    validation_result = validate_completed_courses(all_courses, study_plan)

    if validation_result["unknown_courses"]:
        raise ValidationError(
            "Unknown courses: " + ", ".join(validation_result["unknown_courses"])
        )

    if validation_result["violations"]:
        messages = []
        for item in validation_result["violations"]:
            messages.append(
                f"{item['course']} is missing prerequisites: {', '.join(item['missing_prerequisites'])}"
            )
        raise ValidationError(" | ".join(messages))

    student_profile = {
        "student_id": str(student_row["student_id"]).strip(),
        "student_name": str(student_row["student_name"]).strip(),
        "courses_taken": all_courses,
        "terms_accepted": terms_accepted,
        "phone_number": phone_number,
        "whatsapp_opt_in": whatsapp_opt_in,
        "last_active_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    save_student_profile(student_profile)
    save_student_to_chroma(student_profile)

    update_last_active(student_id) 

    return student_profile


if __name__ == "__main__":
    print("This file is now frontend-friendly.")
    print("Use these functions from your backend/API:")
    print("- authenticate_student(student_id, password)")
    print("- get_student_profile(student_id)")
    print("- accept_terms(student_id)")
    print("- update_phone_number(student_id, phone_number, whatsapp_opt_in)")
    print("- update_completed_courses(student_id, new_courses)")
