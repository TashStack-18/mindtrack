# MindTrack

Explainable, Privacy-First Mood Intelligence & Self-Reflection

## Project Overview
MindTrack is a privacy-first web application that allows users to privately record their moods and journal entries, analyze journal text using sentiment analysis, identify recurring themes and mood/context patterns, receive CBT-inspired reflection prompts, visualize mood trends, and optionally generate a counselor-friendly report.

## Tech Stack
- **Backend:** Python, Flask, SQLAlchemy
- **Database:** SQLite
- **NLP:** TextBlob
- **Encryption:** cryptography (Fernet)
- **Frontend:** HTML5, CSS3, JavaScript, Jinja
- **PDF Generation:** ReportLab
- **Testing:** pytest

## Installation
1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in the values
6. Run the application: `python run.py`

## Features
- Secure authentication
- Encrypted journal storage
- Sentiment analysis of journal entries
- Explainable insights based on mood patterns
- CBT-inspired reflection prompts
- Mood analytics and trend visualization
- Counselor report generation

## Disclaimer
MindTrack is a self-reflection and journaling application. It is NOT a medical diagnosis application and does not provide clinical emotional assessments or therapeutic treatment.
