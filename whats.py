from __future__ import annotations

import os
import re
import json
import time
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import schedule
from openai import OpenAI
from twilio.rest import Client

from studentprofile import (
    parse_activity_dates,
    update_last_reminder_sent,
    PROFILES_CSV,
)

# =========================================================
# CONFIG
# =========================================================

BASE_DIR     = Path("/Users/dinaal-memah/Desktop/graduation project 2")
PROGRESS_DIR = BASE_DIR / "progress_tracking_results"

# Twilio credentials — NEVER hardcode. Set these in your shell environment:
#   export TWILIO_SID="ACxxx..."
#   export TWILIO_AUTH="xxx..."
#   export TWILIO_FROM="whatsapp:+14155238886"
_TWILIO_SID  = os.getenv("TWILIO_SID", "")
_TWILIO_AUTH = os.getenv("TWILIO_AUTH", "")
_TWILIO_FROM = os.getenv("TWILIO_FROM", "whatsapp:+14155238886")

if not _TWILIO_SID or not _TWILIO_AUTH:
    raise EnvironmentError(
        "TWILIO_SID and TWILIO_AUTH must be set as environment variables. "
        "Do NOT hardcode credentials in source files."
    )

twilio_client = Client(_TWILIO_SID, _TWILIO_AUTH)
ai_client     = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL_NAME = "gpt-5.4-nano"


# =========================================================
# PHONE FORMATTING
# =========================================================

def format_phone_number(raw: str) -> str:
    number = re.sub(r"[^\d+]", "", str(raw).strip())

    if number.startswith("+"):
        return number
    if number.startswith("962"):
        return f"+{number}"

    number = number.lstrip("0")
    return f"+962{number}"


# =========================================================
# SEND
# =========================================================

def send_whatsapp_message(to: str, message: str) -> bool:
    """Send a WhatsApp message. Returns True on success."""
    try:
        formatted = format_phone_number(to)
        twilio_client.messages.create(
            from_=_TWILIO_FROM,
            to=f"whatsapp:{formatted}",
            body=message,
        )
        print(f"  ✅ Sent to {formatted}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to send to {to}: {e}")
        return False


# =========================================================
# AI MESSAGE GENERATION
# =========================================================

def generate_message(student: dict, progress: float, inactive_days: int | str) -> str:
    if progress < 30:
        tone = "encourage start"
    elif progress < 80:
        tone = "keep going"
    else:
        tone = "almost done"

    try:
        prompt = f"""
You are an academic assistant.

Write a SHORT WhatsApp motivational message for a university student.

Rules:
- max 2–3 lines
- friendly and natural
- avoid robotic wording
- do NOT mention exact large inactivity numbers
- if inactivity is high, say "you haven't been active for a while"
- encourage a small, specific action

Tone: {tone}
Student name: {student.get("student_name", "Student")}
Progress: {progress}%
Inactive: {inactive_days} days

Return ONLY the message text — no quotes, no labels.
""".strip()

        response = ai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=100,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"  AI generation error: {e}")
        name = student.get("student_name", "Student")
        return (
            f"Hi {name} 👋\n\n"
            "We miss you on Manara 📚\n"
            "Jump back in and continue your learning journey 🚀"
        )


# =========================================================
# LOAD STUDENTS
# =========================================================

def load_students() -> list[dict]:
    """
    Load all student profiles from CSV.
    Parses activity_dates from pipe-delimited string into a list.
    """
    if not PROFILES_CSV.exists():
        print("❌ student_profiles.csv not found")
        return []

    df = pd.read_csv(PROFILES_CSV, dtype=str).fillna("")
    students = df.to_dict(orient="records")

    for s in students:
        # Parse pipe-delimited activity_dates into a sorted list of YYYY-MM-DD strings
        s["activity_dates"] = parse_activity_dates(s.get("activity_dates", ""))

    return students


# =========================================================
# PROGRESS
# =========================================================

def get_progress(student_id: str) -> float:
    """Return the student's latest learning path progress percentage (0–100)."""
    if not PROGRESS_DIR.exists():
        return 0.0

    for file in PROGRESS_DIR.glob(f"progress_{student_id}_*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return float(data.get("progress_percent", 0))
        except Exception:
            return 0.0

    return 0.0


# =========================================================
# INACTIVITY — uses activity_dates as primary source
# =========================================================

def get_last_active_date(student: dict) -> date | None:
    """
    Return the most recent calendar date the student performed a learning action.

    Priority:
    1. Newest date in activity_dates  (real learning events: exam submit,
       quiz submit, exercises generated, chatbot used)
    2. Date portion of last_active_at (login timestamp — fallback only)
    3. None if neither exists
    """
    # Primary: activity_dates list (already parsed by load_students)
    dates: list[str] = student.get("activity_dates") or []
    if dates:
        try:
            return datetime.strptime(dates[0], "%Y-%m-%d").date()
        except ValueError:
            pass

    # Fallback: last_active_at timestamp
    raw = str(student.get("last_active_at", "")).strip()
    if raw:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue

    return None


def get_inactive_days(student: dict) -> int:
    """
    Return how many calendar days have elapsed since the student's last
    learning activity.  Returns 999 if no activity record exists.
    """
    last = get_last_active_date(student)
    if last is None:
        return 999
    return (date.today() - last).days


# =========================================================
# DUPLICATE-SEND GUARD
# =========================================================

def was_reminded_today(student: dict) -> bool:
    """
    Return True if a reminder was already sent to this student today.
    Reads last_reminder_sent_at from the CSV row (YYYY-MM-DD).
    """
    raw = str(student.get("last_reminder_sent_at", "")).strip()
    if not raw:
        return False
    try:
        sent_date = datetime.strptime(raw, "%Y-%m-%d").date()
        return sent_date == date.today()
    except ValueError:
        return False


# =========================================================
# REMINDER CONDITION
# =========================================================

def should_send_reminder(student: dict) -> tuple[bool, float, int]:
    """
    Returns (should_send, progress_pct, inactive_days).

    A reminder is sent when ALL of the following are true:
    - Student has a valid phone number
    - Student opted in to WhatsApp reminders
    - Student has not completed all learning steps (progress < 100%)
    - Student has been inactive for at least 2 full calendar days
      (active today = 0 days, active yesterday = 1 day → both skipped)
    - Student has NOT already received a reminder today
    """
    phone   = str(student.get("phone_number", "")).strip()
    opt_in  = str(student.get("whatsapp_opt_in", "")).lower() == "true"
    sid     = student.get("student_id", "")

    if not phone or not opt_in:
        return False, 0.0, 0

    progress     = get_progress(sid)
    inactive     = get_inactive_days(student)

    print(
        f"  [{sid}] progress={progress:.0f}%  "
        f"inactive={inactive}d  "
        f"reminded_today={was_reminded_today(student)}"
    )

    if progress >= 100:
        return False, progress, inactive
    if inactive < 2:          # active today (0) or yesterday (1) → no reminder
        return False, progress, inactive
    if was_reminded_today(student):
        return False, progress, inactive

    return True, progress, inactive


# =========================================================
# MAIN JOB
# =========================================================

def run_reminders() -> None:
    print(f"\n🚀 Running reminders — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    students = load_students()
    sent = 0
    skipped = 0

    for student in students:
        name = student.get("student_name", student.get("student_id", "?"))
        should, progress, inactive = should_send_reminder(student)

        if not should:
            print(f"  ⏭️  Skipped {name}")
            skipped += 1
            continue

        # Humanise large inactivity numbers in the AI prompt
        inactive_label: int | str = inactive if inactive < 100 else "a while"

        message = generate_message(student, progress, inactive_label)
        success = send_whatsapp_message(student["phone_number"], message)

        if success:
            # Persist the send date so we don't double-send today
            update_last_reminder_sent(student["student_id"])
            sent += 1
        else:
            skipped += 1

    print(f"\n📊 Done — {sent} sent, {skipped} skipped\n")


# =========================================================
# SCHEDULER
# =========================================================

schedule.every().day.at("23:15").do(run_reminders)

if __name__ == "__main__":
    print("⏳ WhatsApp reminder scheduler started (runs daily at 23:15)...")
    while True:
        schedule.run_pending()
        time.sleep(60)
