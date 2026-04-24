# Manara

Manara is an AI-powered academic guidance system designed for PSUT students.  
It helps students identify weaknesses and follow a personalized learning path.

---

## Project Overview

Manara helps students move from confusion to clarity by analyzing their understanding and focusing only on what they actually need to improve.

---

## Backend (Core System Logic)

- Main FastAPI server: api_server.py  
- Diagnostic exam generation & grading: exam1.py  
- Progress tracking & mini quizzes: track.py  
- Question bank generation: qb.py  
- Chat-based course assistant: askcourse.py  
- Weak area detection: related_subtopic_analysis.py  
- Student data handling: studentprofile.py  
- Data preprocessing: datapreprocessing.py  
- Knowledge graph: knowledgegraph.py  
- RAG testing: check_rag.py  
- Vector database checks: check_student_chroma.py  
- PDF generation: pdf.py  

---

## Frontend

- Main React application: App.jsx  

---

## Utilities

- Generate student accounts: generate_student_accounts.py  

---

## Data Files

- Course structure: studyplan.json  

---

## How the System Works

1. Student selects a target course  
2. Diagnostic exam is generated  
3. Answers are analyzed  
4. Weak areas are identified  
5. Personalized learning path is created  
6. Student practices and tracks progress  

---

## Tech Stack

- React  
- FastAPI  
- Python  
- RAG  

---

## Academic Context

Graduation project — PSUT  

---

## Note

Manara is designed to support student learning, not replace course instruction.
