# Manara

Manara is an AI-powered academic guidance system designed for PSUT students.  
It helps students identify weaknesses and follow a personalized learning path.

---

## Project Overview

Manara helps students move from confusion to clarity by analyzing their understanding and focusing only on what they actually need to improve.

---

## Backend (Core System Logic)

### 1. Core System Entry Point
- Main FastAPI server: [api_server.py](./api_server.py)  
  → Central controller that connects all components and exposes API endpoints.

---

### 2. Student & Data Management
- Student data handling: [studentprofile.py](./studentprofile.py)  
  → Stores and manages student profiles, courses, and inputs.

- Data preprocessing: [datapreprocessing.py](./datapreprocessing.py)  
  → Cleans and prepares course material for system use.

- Knowledge graph: [knowledgegraph.py](./knowledgegraph.py)  
  → Builds relationships between courses, topics, and prerequisites.

---

### 3. Diagnostic & Learning Path Generation
- Diagnostic exam generation & grading: [exam1.py](./exam1.py)  
  → Generates exams and evaluates student performance.

- Weak area detection: [related_subtopic_analysis.py](./related_subtopic_analysis.py)  
  → Identifies weak subtopics based on results.

---

### 4. Learning Support Features
- Progress tracking & mini quizzes: [track.py](./track.py)  
  → Tracks progress and generates quizzes for improvement.

- Question bank generation: [qb.py](./qb.py)  
  → Generates practice questions by chapter.

- Chat-based course assistant: [askcourse.py](./askcourse.py)  
  → AI assistant answering questions using course material.

---

### 5. Output & Export
- PDF generation: [pdf.py](./pdf.py)  
  → Generates downloadable learning path reports.

---

### 6. System Testing & Validation
- RAG testing: [check_rag.py](./check_rag.py)  
  → Tests chatbot retrieval accuracy.

- Vector database checks: [check_student_chroma.py](./check_student_chroma.py)  
  → Validates stored embeddings and vector database.
---

## Frontend

- Main React application: [App.jsx](./App.jsx)  
  → User interface where students interact with the system.

---

## Utilities

- Generate student accounts: [generate_student_accounts.py](./generate_student_accounts.py)  
  → Creates sample student data for testing the system.

---

## Data Files

- Course structure: [studyplan.json](./studyplan.json)  
  → Contains course relationships, topics, and prerequisite structure.

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
- Retrieval-Augmented Generation (RAG)  

---

## Academic Context

Graduation project — PSUT  

---

## Note

Manara is designed to support student learning, not replace course instruction.
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
