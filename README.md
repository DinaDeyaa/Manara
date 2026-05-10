# Manara

Manara is an AI-powered academic guidance system designed for PSUT students.  
It helps students identify weaknesses, generate prerequisite diagnostics, and follow a personalized learning path grounded in course material.

---

## Project Overview

Manara helps students move from confusion to clarity by analyzing prerequisite readiness and focusing only on weak areas.

The system uses:

- Course slides and uploaded materials
- Semantic knowledge graph relationships
- ChromaDB vector retrieval
- OpenAI-powered diagnostic generation
- Personalized learning paths
- Practice exercises and mini quizzes
- Progress tracking
- WhatsApp reminders

---

## Backend (Core System Logic)

### 1. Core System Entry Point

- Main FastAPI server: [api_server.py](./api_server.py)  
  Central controller that connects all backend components and exposes API endpoints.

---

### 2. Student & Data Management

- Student data handling: [studentprofile.py](./studentprofile.py)  
  Stores and manages student profiles, completed courses, validation, and course-selection logic.

- Data preprocessing: [datapreprocessing.py](./datapreprocessing.py)  
  Extracts and prepares PDFs, PPTX files, notebooks, code files, ZIPs, OCR/vision content, summaries, concepts, and ChromaDB embeddings.

- Knowledge graph: [knowledgegraph.py](./knowledgegraph.py)  
  Builds relationships between courses, topics, prerequisites, foundational concepts, and related subtopics.

- Related subtopic analysis: [related_subtopic_analysis.py](./related_subtopic_analysis.py)  
  Analyzes semantic similarity between subtopics and exports relationship data.

---

### 3. Diagnostic & Learning Path Generation

- Diagnostic exam generation & grading: [exam1.py](./exam1.py)  
  Generates prerequisite-readiness diagnostic exams using semantic graph expansion, cross-course retrieval, validation, grading, and weak-subtopic detection.

- Learning path generation: [api_server.py](./api_server.py) and [exam1.py](./exam1.py)  
  Converts diagnostic results into personalized learning paths focused on weak prerequisite areas.

---

### 4. Learning Support Features

- AI-generated exercises: [generate_exercises.py](./generate_exercises.py)  
  Generates practice exercises for weak subtopics using retrieved course material, exact question counts, difficulty selection, answers, and explanations.

- Progress tracking & mini quizzes: [track.py](./track.py)  
  Tracks student progress and generates mini quizzes.

- Question bank generation: [qb.py](./qb.py)  
  Generates chapter-based practice questions.

- Chat-based course assistant: [askcourse.py](./askcourse.py)  
  RAG-based assistant that answers student questions using course-specific materials.

---

### 5. Notifications System

- WhatsApp reminders: [whats.py](./whats.py)  
  Sends automated WhatsApp reminders to students based on inactivity and progress using Twilio API and AI-generated messages.

---

### 6. Output & Export

- PDF generation: [pdf.py](./pdf.py)  
  Generates downloadable learning path reports.

---

### 7. Utilities

- Generate student accounts: [generate_student_accounts.py](./generate_student_accounts.py)  
  Creates sample student data for testing.

---

## Frontend

- Main React application: [App.jsx](./App.jsx)  
  User interface where students log in, select courses, generate diagnostics, view learning paths, create exercises, track progress, use the knowledge graph, and ask course questions.

If the frontend is stored separately, it may be located in:

```bash
~/Desktop/manara-ui
