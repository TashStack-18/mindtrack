# MindTrack — Technical Stack

## Architecture choice
Use a simple monolithic Flask application for the mini-project.

```text
Browser
  ↓
HTML / CSS / JavaScript
  ↓
Flask routes
  ↓
Service layer
  ├── Authentication
  ├── Journal
  ├── Sentiment
  ├── Insights
  ├── Reflection
  ├── Analytics
  ├── Encryption
  └── Reports
  ↓
SQLAlchemy
  ↓
SQLite
```

## Frontend
### HTML5
Semantic page structure.

### CSS3
Responsive layout, design tokens, components.

### JavaScript
Form handling, API requests, Chart.js rendering, UI interactions.

### Chart.js
Use for:
- line charts
- doughnut charts
- mood trend
- sentiment trend

## Backend
### Python
Main application language.

### Flask
HTTP server, routing, sessions and templating.

### SQLAlchemy
Database abstraction and ORM.

### SQLite
Recommended for the academic MVP.

## NLP
### TextBlob
Use:
- `polarity`
- `subjectivity`

Do not claim TextBlob provides clinical emotional diagnosis.

## Encryption
### cryptography
Use Fernet authenticated symmetric encryption for journal content.

Important:
- secret key must be stored in environment configuration
- never commit the key
- never expose it through an API
- never log decrypted journal content

## PDF
### ReportLab
Generate counselor reports.

## Security
Recommended:
- Werkzeug password hashing or equivalent secure password hashing
- Flask sessions
- CSRF protection for forms
- environment variables
- secure cookies in production
- server-side authorization checks

## Development
- Python virtual environment
- Git
- `.env` for local secrets
- pytest
- Black/formatter optional
- Ruff/flake8 optional

## requirements.txt baseline

Use compatible current releases rather than hardcoding unnecessary versions:

```text
Flask
Flask-SQLAlchemy
Flask-WTF
python-dotenv
cryptography
textblob
reportlab
pytest
Werkzeug
```

Frontend Chart.js can be loaded through a pinned local/static dependency or a trusted CDN during development. For a fully offline submission, store the library in `static/`.

## Why not React?
For this mini-project, React adds complexity without improving the core Python evaluation. Flask + Jinja + JavaScript is easier to explain and maintain.

## Why not Django?
Django is excellent, but Flask keeps the project architecture transparent and easier to demonstrate in a Python mini-project viva.

## Why SQLite?
It is sufficient for a local academic project and requires no separate database server. PostgreSQL can be introduced later if deployment needs it.
