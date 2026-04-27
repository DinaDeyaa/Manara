from pathlib import Path
import random
import pandas as pd
from faker import Faker

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path("/Users/dinaal-memah/Desktop/graduation project 2")
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "students_accounts.csv"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# CONFIG
# =========================================================

START_YEAR = 2020
END_YEAR = 2024
STUDENTS_PER_YEAR = 1000
LIMIT_STUDENTS = None

random.seed(0)
Faker.seed(0)
fake = Faker("ar_SA")


# =========================================================
# ID GENERATION
# =========================================================

def generate_all_student_ids() -> list[str]:
    student_ids = []

    for year in range(START_YEAR, END_YEAR + 1):
        for i in range(1, STUDENTS_PER_YEAR + 1):
            sid = f"{year}{i:04d}"
            student_ids.append(sid)

    return student_ids


# =========================================================
# PASSWORD
# =========================================================

def generate_password(length: int = 8) -> str:
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(chars) for _ in range(length))


# =========================================================
# MAIN
# =========================================================

def main():
    student_ids = generate_all_student_ids()
    print(f"Generated total IDs: {len(student_ids)}")

    if LIMIT_STUDENTS is not None:
        student_ids = random.sample(student_ids, LIMIT_STUDENTS)
        print(f"Using subset: {len(student_ids)} students")

    rows = []

    for sid in student_ids:
        if sid in CUSTOM_STUDENTS:
            rows.append({
                "student_id": sid,
               "student_name": CUSTOM_STUDENTS[sid]["student_name"],
               "password": CUSTOM_STUDENTS[sid]["password"],
            })
        else:
            rows.append({
                "student_id": sid,
                "student_name": f"{fake.first_name()} {fake.last_name()}",
                "password": generate_password(),
            })

    df = pd.DataFrame(rows, columns=["student_id", "student_name", "password"])
    df["student_id"] = df["student_id"].astype(str)

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\n✅ Student accounts CSV created successfully")
    print("Saved to:", OUTPUT_FILE)
    print("\nSample:")
    print(df.head(10))

# =========================================================
# CUSTOM STUDENTS 
# =========================================================

CUSTOM_STUDENTS = {
    "20220110": {"student_name": "Dina Al-Mimeh", "password": "dina123"},
    "20220491": {"student_name": "Marah Al-Shrouf", "password": "marah123"},
    "20240162": {"student_name": "Leen Deya'a Almimeh", "password": "leen123"},
    "20220111": {"student_name": "Dr. Omar Alqawasmeh", "password": "omar123"},
}

if __name__ == "__main__":
    main()
