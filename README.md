# Manara

Manara is an AI-powered academic guidance system designed for PSUT students.  
It helps students identify weaknesses and follow a personalized learning path.

---

## Project Overview

Manara helps students move from confusion to clarity by analyzing student performance and focusing only on weak areas.

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

### 5. Notifications System
- WhatsApp reminders: [whats.py](./whats.py)  
  → Sends automated WhatsApp reminders to students based on inactivity and progress using Twilio API and AI-generated messages.

---

### 6. Output & Export
- PDF generation: [pdf.py](./pdf.py)  
  → Generates downloadable learning path reports.

---

### 7. System Testing & Validation
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
6. Student practices using quizzes and tracking system  
7. Smart reminders are sent if the student becomes inactive  

---

## Tech Stack

- React  
- FastAPI  
- Python  
- Retrieval-Augmented Generation (RAG)  
- Twilio API (WhatsApp Integration)  

---

## Academic Context

Graduation Project — PSUT  

---

## Note

Manara is designed to support student learning, not replace course instruction.
