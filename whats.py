from twilio.rest import Client
import schedule
import time
import pandas as pd
from datetime import datetime
from pathlib import Path

from openai import OpenAI
import os

import json
import re

# 📁 Paths
BASE_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
PROFILES_CSV = BASE_DIR / "student_profiles" / "student_profiles.csv"
PROGRESS_DIR = BASE_DIR / "progress_tracking_results"

# 🔑 Twilio Credentials
TWILIO_SID = "ACca49cd35417de2eb89217201c9baff68"
TWILIO_AUTH = "3c165dd545f6c4e08377fcd6947cd628"

client = Client(TWILIO_SID, TWILIO_AUTH)
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ================================
# 📞 FORMAT NUMBER
# ================================
def format_phone_number(to):
    number = str(to).strip()
    number = re.sub(r"[^\d+]", "", number)

    if number.startswith("+"):
        return number

    # if starts with 962 already
    if number.startswith("962"):
        return f"+{number}"

    # local Jordan number
    number = number.lstrip("0")
    return f"+962{number}"

# ================================
# 📩 SEND MESSAGE
# ================================
def send_whatsapp_message(to, message):
    try:
        formatted_number = format_phone_number(to)

        client.messages.create(
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{formatted_number}",
            body=message
        )

        print(f"✅ Sent to {formatted_number}")

    except Exception as e:
        print(f"❌ Error sending to {to}: {e}")

def generate_message(student, progress, inactive_days, tone):
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
- encourage small action

Tone: {tone}

Student name: {student.get("student_name")}
Progress: {progress}%
Inactive: {inactive_days}

Return ONLY the message.
"""

        response = client_ai.chat.completions.create(
            model="gpt-5.4-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_completion_tokens=100
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"AI error: {e}")

        return f"""Hi {student.get('student_name', 'Student')} 👋

    Keep going — you're closer than you think 📚
    Jump back in and continue your progress 🚀"""

# ================================
# 📄 LOAD STUDENTS
# ================================
def load_students():
    if not PROFILES_CSV.exists():
        print("❌ CSV not found")
        return []

    df = pd.read_csv(PROFILES_CSV).fillna("")
    return df.to_dict(orient="records")

# ================================
# 📊 GET PROGRESS
# ================================
def get_progress(student_id):
    if not PROGRESS_DIR.exists():
        return 0

    for file in PROGRESS_DIR.glob(f"progress_{student_id}_*.json"):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                return float(data.get("progress_percent", 0))
        except:
            return 0

    return 0

# ================================
# 🧠 INACTIVITY
# ================================
def get_inactive_days(last_active_at):
    if not last_active_at:
        return 999

    try:
        last_active = datetime.strptime(last_active_at, "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - last_active).days
    except:
        return 999

# ================================
# ⚠️ CONDITION (REAL LOGIC)
# ================================
def should_send_reminder(student):
    phone = str(student.get("phone_number", "")).strip()
    opt_in = str(student.get("whatsapp_opt_in", "")).lower() == "true"
    student_id = student.get("student_id", "")

    progress = get_progress(student_id)
    inactive_days = get_inactive_days(student.get("last_active_at", ""))

    print(f"DEBUG → {student_id} | progress={progress} | inactive={inactive_days}")

    return (
        phone != "" and
        opt_in and
        progress < 100 and
        inactive_days >= 2  
    )

# ================================
# 💬 MESSAGE
# ================================
def build_message(student):
    return f"""Hi {student.get('student_name', 'Student')} 👋

We noticed you haven’t been active recently 📚  
You still have unfinished progress — continue your learning journey 🚀"""

# ================================
# 🔁 MAIN JOB
# ================================
def run_reminders():
    print("🚀 Running reminders...")

    students = load_students()

    for student in students:
        if should_send_reminder(student):

            progress = get_progress(student["student_id"])
            inactive_days = get_inactive_days(student.get("last_active_at", ""))

            if inactive_days >= 100:
                inactive_days = "a while"

            if progress < 30:
                tone = "encourage start"
            elif progress < 80:
                tone = "keep going"
            else:
                tone = "almost done"

            message = generate_message(student, progress, inactive_days, tone)

            send_whatsapp_message(
                student["phone_number"],
                message
            )

        else:
            print(f"⏭️ Skipped {student.get('student_name')}")

# ================================
# ⏰ SCHEDULE
# ================================
schedule.every().day.at("23:15").do(run_reminders)

# ================================
# 🔄 RUN
# ================================
if __name__ == "__main__":
    print("⏳ Scheduler started...")

    while True:
        schedule.run_pending()
        time.sleep(60)
