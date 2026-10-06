# MindTrack — System Architecture

## High-level architecture

```text
┌──────────────────────────────┐
│          Browser             │
│ HTML / CSS / JavaScript      │
└──────────────┬───────────────┘
               │ HTTP/HTTPS
               ↓
┌──────────────────────────────┐
│          Flask App           │
├──────────────────────────────┤
│ Routes / Controllers         │
│ Authentication               │
│ Authorization                │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│        Service Layer         │
├──────────────────────────────┤
│ Journal Service              │
│ Sentiment Service            │
│ Theme Service                │
│ Insight Service              │
│ Reflection Service           │
│ Analytics Service            │
│ Report Service               │
│ Encryption Service           │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│       Data Access Layer      │
│          SQLAlchemy          │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│            SQLite            │
└──────────────────────────────┘
```

## Suggested directory structure

```text
mindtrack/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models/
│   │   ├── user.py
│   │   ├── journal.py
│   │   ├── tag.py
│   │   └── reflection.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── journal.py
│   │   ├── analytics.py
│   │   ├── reflection.py
│   │   └── reports.py
│   ├── services/
│   │   ├── sentiment_service.py
│   │   ├── theme_service.py
│   │   ├── insight_service.py
│   │   ├── reflection_service.py
│   │   ├── encryption_service.py
│   │   ├── analytics_service.py
│   │   └── report_service.py
│   ├── templates/
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
├── tests/
├── instance/
├── migrations/
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

## Request flow: create journal entry

```text
User
 ↓
Journal form
 ↓
POST /journal
 ↓
Validate input
 ↓
Check authenticated user
 ↓
Analyze sentiment
 ↓
Detect themes
 ↓
Generate insight metadata
 ↓
Encrypt journal content
 ↓
Save database record
 ↓
Return confirmation
```

## Important separation
Keep business logic out of Flask route functions.

Bad:
```python
@app.post("/journal")
def create():
    # 100 lines of encryption, NLP, database and report logic
```

Good:
```python
@app.post("/journal")
def create():
    entry = journal_service.create_entry(...)
    return ...
```

## Error handling
Use friendly UI messages while logging only technical details.

Never log:
- passwords
- encryption keys
- full journal entries
- decrypted journal content
