from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import csv

from pdf import router as pdf_router

# ---------------------------------------------------------
# make sure Python can import your backend files
# ---------------------------------------------------------
PROJECT_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
if str(PROJECT_DIR) not in sys.path:
    sys.path.append(str(PROJECT_DIR))

STUDENT_ACCOUNTS_CSV = PROJECT_DIR / "data" / "students_accounts.csv"

# ---------------------------------------------------------
# import your backend functions
# ---------------------------------------------------------
# adjust these imports if your function names are different
from askcourse import ask_course_question

from exam1 import get_all_progress_for_student

from exam1 import (
    get_exam1_available_courses,
    generate_diagnostic_exam,
    submit_diagnostic_exam,
    generate_learning_path_from_graded_result,
    generate_learning_path_exercises,
    get_progress_for_student,
    get_available_courses,
)

from studentprofile import (
    authenticate_student,
    accept_terms,
    update_phone_number,
    update_completed_courses,
    get_student_profile,
)

from qb import (
    get_chapters_for_course,
    generate_question_bank_for_student,
)


from track import (
    create_tracking_progress_from_learning_path,
    load_progress_for_student_and_course,
    generate_quiz_for_current_subtopic,
    submit_quiz_for_current_subtopic,
)

from track import delete_tracking_for_student_and_course

# later you can import from these too:
# from studentprofile import ...
# from generate_student_account import ...
# from track import ...


# ---------------------------------------------------------
# app
# ---------------------------------------------------------
app = FastAPI(title="Manara API")


# allow React frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite
        "http://127.0.0.1:5173",
        "http://localhost:3000",   # React CRA if needed
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_router, prefix="/api")


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
# helper
# ---------------------------------------------------------

def build_exam1_profile(student_id: str) -> dict[str, Any]:
    student = get_student_profile(student_id)

    if not student:
        student = get_student(student_id)

    if not student:
        raise ValueError(f"Student {student_id} not found.")

    return {
        "student_id": student["student_id"],
        "student_name": student["student_name"],
        "courses_taken": student.get("courses_taken", []),
    }

def load_students_from_csv() -> dict[str, dict[str, Any]]:
    students: dict[str, dict[str, Any]] = {}

    if not STUDENT_ACCOUNTS_CSV.exists():
        return students

    with open(STUDENT_ACCOUNTS_CSV, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            student_id = str(row.get("student_id", "")).strip()
            if not student_id:
                continue

            students[student_id] = {
                "student_id": student_id,
                "student_name": str(row.get("student_name", "")).strip(),
                "password": str(row.get("password", "")).strip(),
                "terms_accepted": str(row.get("terms_accepted", "False")).strip().lower() == "true",
                "phone_number": str(row.get("phone_number", "")).strip(),
                "courses_taken": [
                    c.strip()
                    for c in str(row.get("courses_taken", "")).split("|")
                    if c.strip()
                ],
            }

    return students


def save_students_to_csv(students: dict[str, dict[str, Any]]) -> None:
    fieldnames = [
        "student_id",
        "student_name",
        "password",
        "terms_accepted",
        "phone_number",
        "courses_taken",
    ]

    with open(STUDENT_ACCOUNTS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for student_id, student in students.items():
            writer.writerow({
                "student_id": student.get("student_id", ""),
                "student_name": student.get("student_name", ""),
                "password": student.get("password", ""),
                "terms_accepted": str(student.get("terms_accepted", False)),
                "phone_number": student.get("phone_number", ""),
                "courses_taken": "|".join(student.get("courses_taken", [])),
            })


def get_student(student_id: str) -> dict[str, Any] | None:
    students = load_students_from_csv()
    return students.get(student_id)


def update_student(student_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    students = load_students_from_csv()
    student = students.get(student_id)

    if not student:
        return None

    student.update(updates)
    students[student_id] = student
    save_students_to_csv(students)
    return student

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
            exam1_profile = build_exam1_profile(payload.student_id)
            available_result = get_exam1_available_courses(exam1_profile)
            available_target_courses = available_result.get("available_target_courses", [])
        except Exception:
            pass

        return {
            "success": True,
            "message": "Login successful.",
            "student": {
                "student_id": student["student_id"],
                "student_name": student["student_name"],
                "terms_accepted": student.get("terms_accepted", False),
                "phone_number": student.get("phone_number", ""),
                "courses_taken": student.get("courses_taken", []),
            },
            "available_target_courses": available_target_courses,
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@app.post("/api/student/terms")
def api_save_terms(payload: TermsRequest):
    try:
        student = accept_terms(payload.student_id)

        return {
            "success": True,
            "message": "Terms updated successfully.",
            "terms_accepted": student["terms_accepted"],
            "student": student,
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@app.post("/api/student/phone")
def api_save_phone(payload: PhoneRequest):
    try:
        student = update_phone_number(
            student_id=payload.student_id,
            phone_number=payload.phone_number,
            whatsapp_opt_in=bool(payload.phone_number.strip()),
        )

        return {
            "success": True,
            "message": "Phone number saved successfully.",
            "phone_number": student["phone_number"],
            "student": student,
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@app.post("/api/student/profile-setup")
def api_profile_setup(payload: ProfileSetupRequest):
    try:
        update_phone_number(
            student_id=payload.student_id,
            phone_number=payload.phone_number,
            whatsapp_opt_in=bool(payload.phone_number.strip()),
        )

        student = update_completed_courses(
            student_id=payload.student_id,
            new_courses=payload.courses_taken,
        )

        available_result = get_exam1_available_courses(build_exam1_profile(payload.student_id))

        return {
            "success": True,
            "message": "Profile setup saved successfully.",
            "student": {
                "student_id": student["student_id"],
                "student_name": student["student_name"],
                "terms_accepted": student["terms_accepted"],
                "phone_number": student["phone_number"],
                "courses_taken": student["courses_taken"],
            },
            "available_target_courses": available_result.get("available_target_courses", []),
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@app.get("/api/exam1/available-courses/{student_id}")
def api_exam1_available_courses(student_id: str):
    profile = build_exam1_profile(student_id)
    return get_exam1_available_courses(profile)


@app.post("/api/exam1/generate")
def api_exam1_generate(payload: Exam1GenerateRequest):
    profile = build_exam1_profile(payload.student_id)
    return generate_diagnostic_exam(
        student_profile=profile,
        target_course=payload.target_course,
        save_result=True,
    )


@app.post("/api/exam1/submit")
def api_exam1_submit(payload: Exam1SubmitRequest):
    profile = build_exam1_profile(payload.student_id)

    submitted_answers = [
        {
            "question_id": item.question_id,
            "student_answer": item.student_answer,
        }
        for item in payload.submitted_answers
    ]

    return submit_diagnostic_exam(
        student_profile=profile,
        target_course=payload.target_course,
        submitted_answers=submitted_answers,
    )


@app.post("/api/exam1/learning-path")
def api_exam1_learning_path(payload: LearningPathRequest):
    profile = build_exam1_profile(payload.student_id)

    result = generate_learning_path_from_graded_result(
        student_profile=profile,
        graded_result_payload=payload.graded_result_payload,
        save_result=True,
    )

    delete_tracking_for_student_and_course(
        payload.student_id,
        result.get("target_course", "")
    )

    return result


@app.post("/api/exam1/exercises")
def api_exam1_exercises(payload: Exam1ExercisesRequest):
    profile = build_exam1_profile(payload.student_id)

    subtopic_requests = [
        {
            "topic_name": item.topic_name,
            "subtopic_name": item.subtopic_name,
            "num_exercises": item.num_exercises,
        }
        for item in payload.subtopic_requests
    ]

    return generate_learning_path_exercises(
        student_profile=profile,
        target_course=payload.target_course,
        subtopic_requests=subtopic_requests,
        save_result=True,
    )


@app.get("/api/progress/student/{student_id}")
def progress_for_student(student_id: str):
    try:
        profile = build_exam1_profile(student_id)
        raw = get_all_progress_for_student(profile)

        progress_list = raw.get("progress", [])
        fixed = []

        for item in progress_list:
            target_course = item.get("target_course", "")
            tracking = load_progress_for_student_and_course(profile, target_course) 

            if tracking.get("success"):
                item["learning_path_steps"] = len(tracking.get("subtopic_progress", []))
                item["completed_steps"] = tracking.get("completed_count", 0)
            else:
                item["learning_path_steps"] = item.get("weak_subtopics_count", 0)
                item["completed_steps"] = 0

            fixed.append(item)

        return {
            "success": True,
            "progress": fixed,
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "progress": [],
        }

@app.post("/api/ask-course")
def api_ask_course(payload: AskCourseRequest):
    return ask_course_question(payload.course_name, payload.question)

@app.get("/api/qb/chapters/{course_name}")
def api_qb_chapters(course_name: str):
    try:
        result = get_chapters_for_course(course_name)
        return {
            "success": True,
            "course_name": result["course_name"],
            "chapters": result["materials"],
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "chapters": [],
        }


@app.post("/api/qb/generate")
def api_qb_generate(payload: QuestionBankGenerateRequest):
    try:
        result = generate_question_bank_for_student(
            student_profile=None,
            target_course=payload.course_name,
            chapter_name=payload.chapter_name,
            save_result=True,
        )
        return {
            "success": True,
            "message": "Question bank generated successfully.",
            "target_course": result["target_course"],
            "chapter": result["chapter"],
            "total_questions": result["total_questions"],
            "questions": result["questions"],
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "questions": [],
        }

@app.post("/api/track/start")
def api_track_start(payload: TrackStartRequest):
    try:
        profile = build_exam1_profile(payload.student_id)

        delete_tracking_for_student_and_course(
            payload.student_id,
            payload.learning_path_payload.get("target_course", "")
        )

        return create_tracking_progress_from_learning_path(
            student_profile=profile,
            learning_path_payload=payload.learning_path_payload,
        )
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@app.get("/api/track/{student_id}/{target_course}")
def api_track_load(student_id: str, target_course: str):
    try:
        profile = build_exam1_profile(student_id)
        return load_progress_for_student_and_course(profile, target_course)
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@app.post("/api/track/quiz/{student_id}/{target_course}")
def api_track_generate_quiz(student_id: str, target_course: str):
    try:
        profile = build_exam1_profile(student_id)
        return generate_quiz_for_current_subtopic(profile, target_course)
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@app.post("/api/track/submit")
def api_track_submit(payload: TrackSubmitRequest):
    try:
        profile = build_exam1_profile(payload.student_id)
        submitted_answers = [
            {
                "question_id": item.question_id,
                "student_answer": item.student_answer,
            }
            for item in payload.submitted_answers
        ]
        return submit_quiz_for_current_subtopic(
            profile,
            payload.target_course,
            submitted_answers,
        )
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }

