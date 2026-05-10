from __future__ import annotations

from pathlib import Path
import json
import re
import difflib
import pandas as pd
from datetime import datetime

print("studentprofile.py loaded")


# =========================================================
# PATHS
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "student_profiles"
COURSES_DIR = BASE_DIR / "courses"

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
        "activity_dates",        # pipe-delimited YYYY-MM-DD dates, newest first, max 90
        "last_reminder_sent_at", # YYYY-MM-DD — date the last WhatsApp reminder was sent
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
    text = str(name or "")
    # Normalize common invisible/pasted characters that break exact matching.
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", text)
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text.strip().lower())
    return text


def resolve_course_name(course_name: str, lookup: dict) -> str | None:
    """
    Resolve an incoming frontend label to the canonical course name accepted by
    Manara. Exact normalized match wins; close aliases are accepted so profile
    setup does not reject valid folder-backed courses due to spelling/casing or
    spacing drift.
    """
    norm = normalize_course_name(course_name)
    if not norm:
        return None

    if norm in lookup:
        return lookup[norm]["official_name"]

    # Substring aliases cover labels like "Discrete Mathematics (MATH-...)".
    for valid_norm, info in lookup.items():
        if norm == valid_norm or norm in valid_norm or valid_norm in norm:
            return info["official_name"]

    # Conservative fuzzy match for small naming drift.
    matches = difflib.get_close_matches(norm, list(lookup.keys()), n=1, cutoff=0.88)
    if matches:
        return lookup[matches[0]]["official_name"]

    return None


def is_lab_course(course_name: str) -> bool:
    return normalize_course_name(course_name).endswith(" lab")


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
            "concurrent": course_info.get("concurrent", [])  
        }

    # Keep profile setup aligned with the actual Manara knowledge base. Some
    # processed course folders are not present in studyplan.json yet; they
    # should still be selectable and storable as completed courses.
    if COURSES_DIR.exists():
        for course_dir in COURSES_DIR.iterdir():
            if not course_dir.is_dir():
                continue
            course_name = course_dir.name.strip()
            norm = normalize_course_name(course_name)
            if course_name and norm not in lookup:
                lookup[norm] = {
                    "official_name": course_name,
                    "course_code": "",
                    "prerequisites": [],
                    "concurrent": [],
                }

    return lookup


def validate_completed_courses(courses_taken: list[str], study_plan: dict) -> dict:
    lookup = build_course_lookup(study_plan)

    resolved_incoming = []
    for course in courses_taken:
        official = resolve_course_name(course, lookup)
        resolved_incoming.append(official or str(course).strip())

    entered_normalized = [normalize_course_name(c) for c in resolved_incoming]
    entered_set = set(entered_normalized)

    unknown_courses = []
    violations = []
    valid_courses = []

    print("[COURSE VALIDATION]")
    print("incoming:", courses_taken)
    print("resolved:", resolved_incoming)
    print("valid:", sorted(info["official_name"] for info in lookup.values()))

    for original_course, resolved_course in zip(courses_taken, resolved_incoming):
        norm_course = normalize_course_name(resolved_course)

        if norm_course not in lookup:
            unknown_courses.append(original_course)
            continue

        course_info = lookup[norm_course]
        missing_prereqs = []

        # ✅ 1. STRICT PREREQUISITES (no bypass with concurrent)
        for prereq in course_info["prerequisites"]:
            prereq_norm = normalize_course_name(prereq)

            if prereq_norm not in entered_set:
                missing_prereqs.append(prereq)

        # 2. LAB/COREQUISITE RULE
        # Direction matters: labs depend on their lecture course, but lecture
        # courses do not require the lab. A lecture-only selection is valid.
        if is_lab_course(course_info["official_name"]):
            for concurrent_course in course_info.get("concurrent", []):
                concurrent_norm = normalize_course_name(concurrent_course)

                if concurrent_norm not in entered_set and concurrent_norm in lookup:
                    missing_prereqs.append(concurrent_course)

        # ✅ 3. FINAL DECISION (after all checks)
        if missing_prereqs:
            violations.append({
                "course": course_info["official_name"],
                "missing_prerequisites": list(set(missing_prereqs)),
            })
        else:
            valid_courses.append(course_info["official_name"])

    print("missing:", unknown_courses)

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


def parse_activity_dates(raw: str) -> list[str]:
    """Parse pipe-delimited YYYY-MM-DD activity dates, deduplicate, sort newest first."""
    parts = [p.strip() for p in str(raw or "").split("|") if p.strip()]
    # keep only valid date strings
    valid = []
    for p in parts:
        try:
            datetime.strptime(p, "%Y-%m-%d")
            valid.append(p)
        except ValueError:
            pass
    # deduplicate, sort newest first
    return sorted(set(valid), reverse=True)


def stringify_activity_dates(dates: list[str]) -> str:
    return "|".join(dates)


def row_to_profile_dict(row) -> dict:
    return {
        "student_id":            str(row["student_id"]).strip(),
        "student_name":          str(row["student_name"]).strip(),
        "courses_taken":         parse_saved_courses(row.get("courses_taken", "")),
        "terms_accepted":        str_to_bool(row.get("terms_accepted", "")),
        "phone_number":          str(row.get("phone_number", "")).strip(),
        "whatsapp_opt_in":       str_to_bool(row.get("whatsapp_opt_in", "")),
        "last_active_at":        str(row.get("last_active_at", "")).strip(),
        "activity_dates":        parse_activity_dates(row.get("activity_dates", "")),
        "last_reminder_sent_at": str(row.get("last_reminder_sent_at", "")).strip(),
    }

def update_last_active(student_id: str):
    """
    Record a learning activity event for the student:
    - Updates last_active_at to the current timestamp
    - Appends today's date (YYYY-MM-DD) to activity_dates
    - Keeps only the most recent 90 unique dates (≈ 3 months of data)
    Called on login and every meaningful learning action.
    """
    profiles_df = load_existing_profiles()
    row = get_profile_row(student_id, profiles_df)
    today = datetime.now().strftime("%Y-%m-%d")

    if row is None:
        profile = {
            "student_id":     student_id,
            "student_name":   "",
            "courses_taken":  [],
            "terms_accepted": False,
            "phone_number":   "",
            "whatsapp_opt_in": False,
            "last_active_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "activity_dates": [today],
        }
    else:
        profile = row_to_profile_dict(row)
        profile["last_active_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Prepend today, deduplicate, keep newest 90
        existing = profile.get("activity_dates", [])
        merged = sorted(set(existing + [today]), reverse=True)[:90]
        profile["activity_dates"] = merged

    save_student_profile(profile)


def update_last_reminder_sent(student_id: str) -> None:
    """
    Record that a WhatsApp reminder was sent to this student today.
    Writes today's date (YYYY-MM-DD) to last_reminder_sent_at so the
    reminder system can prevent duplicate sends on the same calendar day.
    """
    profiles_df = load_existing_profiles()
    row = get_profile_row(student_id, profiles_df)

    if row is None:
        return   # no profile to update — nothing to do

    profile = row_to_profile_dict(row)
    profile["last_reminder_sent_at"] = datetime.now().strftime("%Y-%m-%d")
    save_student_profile(profile)


# =========================================================
# SAVE PROFILE
# =========================================================

def save_student_profile(student_profile: dict):
    row = {
        "student_id":            str(student_profile["student_id"]).strip(),
        "student_name":          str(student_profile["student_name"]).strip(),
        "courses_taken":         stringify_courses(student_profile.get("courses_taken", [])),
        "terms_accepted":        to_bool_str(student_profile.get("terms_accepted", False)),
        "phone_number":          str(student_profile.get("phone_number", "")).strip(),
        "whatsapp_opt_in":       to_bool_str(student_profile.get("whatsapp_opt_in", False)),
        "last_active_at":        student_profile.get("last_active_at", ""),
        "activity_dates":        stringify_activity_dates(student_profile.get("activity_dates", [])),
        "last_reminder_sent_at": str(student_profile.get("last_reminder_sent_at", "")).strip(),
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
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except Exception as exc:
        print(f"[STUDENT CHROMA] Skipping profile vector save; Chroma import failed: {exc}")
        return

    try:
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
    except Exception as exc:
        print(f"[STUDENT CHROMA] Skipping profile vector save; Chroma write failed: {exc}")


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

    # Update last_active_at and activity_dates, then reload so return value is fresh
    update_last_active(student_row["student_id"])
    fresh_row = get_profile_row(student_row["student_id"], load_existing_profiles())
    fresh_profile = row_to_profile_dict(fresh_row) if fresh_row is not None else profile

    return {
        "student_id":     str(student_row["student_id"]).strip(),
        "student_name":   str(student_row["student_name"]).strip(),
        "terms_accepted": fresh_profile["terms_accepted"],
        "phone_number":   fresh_profile["phone_number"],
        "whatsapp_opt_in": fresh_profile["whatsapp_opt_in"],
        "courses_taken":  fresh_profile["courses_taken"],
        "activity_dates": fresh_profile.get("activity_dates", []),
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

    student_match = accounts_df[
        accounts_df["student_id"].astype(str).str.strip() == str(student_id).strip()
    ]

    if student_match.empty:
        raise ValidationError("Student not found.")

    student_row = student_match.iloc[0]
    existing_row = get_profile_row(student_id, profiles_df)

    terms_accepted = False
    phone_number = ""
    whatsapp_opt_in = False

    if existing_row is not None:
        old_profile = row_to_profile_dict(existing_row)
        terms_accepted = old_profile["terms_accepted"]
        phone_number = old_profile["phone_number"]
        whatsapp_opt_in = old_profile["whatsapp_opt_in"]

    # ✅ IMPORTANT: replace courses, do NOT merge with old courses
    cleaned_new_courses = []
    seen = set()

    for course in new_courses:
        course = str(course).strip()
        key = normalize_course_name(course)

        if course and key not in seen:
            seen.add(key)
            cleaned_new_courses.append(course)

    validation_result = validate_completed_courses(cleaned_new_courses, study_plan)

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
        "courses_taken": validation_result["valid_courses"],
        "terms_accepted": terms_accepted,
        "phone_number": phone_number,
        "whatsapp_opt_in": whatsapp_opt_in,
        "last_active_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    save_student_profile(student_profile)
    save_student_to_chroma(student_profile)

    return student_profile


if __name__ == "__main__":
    print("This file is now frontend-friendly.")
    print("Use these functions from your backend/API:")
    print("- authenticate_student(student_id, password)")
    print("- get_student_profile(student_id)")
    print("- accept_terms(student_id)")
    print("- update_phone_number(student_id, phone_number, whatsapp_opt_in)")
    print("- update_completed_courses(student_id, new_courses)")
