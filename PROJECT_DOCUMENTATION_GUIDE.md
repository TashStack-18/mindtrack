# MindTrack — Project Documentation Guide

A study guide for writing the project report. It describes **what the code in this archive
actually does**. Planned or incomplete items are listed separately in
[section 15](#15-implemented-vs-planned) so they are not mistaken for finished features.
Where a number appears (e.g. "31 topics"), it was counted from the source code, not estimated.

The original planning documents are also included: `01_PRD.md` (requirements), `03_TECH_STACK.md`,
`04_ARCHITECTURE.md`, `05_DATABASE_SCHEMA.md`, `10_UI_UX_SPEC.md`. They describe the *intended*
design; where they differ from the code, this guide follows the code.

---

## 1. Project overview and problem statement

MindTrack is a privacy-focused mood journaling web application. Users record how they feel
(a 1–5 mood check-in), optionally write about their day, and later look back at patterns in
their own entries.

Problem it addresses (from `01_PRD.md`): many wellness apps offer either quick mood tracking,
journaling, generic exercises or a chatbot. MindTrack combines journaling and mood tracking with
**explainable, rule-based insights from the user's own data**, optional reflection prompts, and a
PDF summary the user can choose to share with a counselor, while keeping journal text encrypted.

MindTrack is explicitly **not** a diagnostic or crisis service. The app, the PDF report and Mindy
all state this.

## 2. Objectives and key features (implemented)

- Account registration, login, logout, and per-user data isolation.
- Daily mood check-in (5 levels: Very Low, Low, Okay, Good, Great) with an optional short note and optional context tags.
- Full journal entries: create, view, edit, delete; title, mood, up to 3 "feelings", context tags and custom tags.
- Encryption of journal text, reflection answers and Mindy chat messages (Fernet).
- Sentiment estimate (TextBlob polarity/subjectivity/label) stored per entry.
- Keyword-based theme detection (7 themes) stored per entry.
- Insights page: date range (7 days / 30 days / all time), mood chart, summary statistics, context breakdown, mood × context view, evidence-based observations and cautious suggestions.
- CBT-inspired reflection prompts and a page to write a private (encrypted) reflection on an entry.
- Dashboard with greeting, mood selection, mood chart, recent moments, weekly check-in dots and a daily-changing photo.
- PDF report generation (ReportLab) for a chosen date range, with journal text included only if the user ticks the option.
- **Mindy**, a rule-based conversational companion (no external AI service).
- Public landing page, responsive layouts, and production deployment configuration (not yet deployed).

## 3. Technology stack

| Technology | Version (requirements.txt) | What it does in MindTrack |
|---|---|---|
| Python | 3.13 used in development | Application language |
| Flask | 3.0.3 | Web framework: routing, sessions, Jinja2 templates, CLI (`flask init-db`) |
| Werkzeug | 3.0.1 | Password hashing (`generate_password_hash`/`check_password_hash`), dev server |
| Flask-SQLAlchemy / SQLAlchemy | 3.1.1 / 2.1.3 | ORM models and queries |
| SQLite | (built in) | Local development database (`instance/mindtrack.db`, not included in this archive) |
| PostgreSQL via psycopg | psycopg[binary] 3.2.13 | Intended production database (Cloud SQL); prepared, not yet deployed |
| Flask-WTF | 1.2.1 | CSRF protection for all forms and POST requests |
| python-dotenv | 1.0.1 | Loads `SECRET_KEY` and `MINTRACK_ENCRYPTION_KEY` from a local `.env` file |
| cryptography (Fernet) | 42.0.5 | Symmetric authenticated encryption of journal text, reflections and Mindy messages |
| TextBlob | 0.18.0.post0 | Sentiment polarity/subjectivity of journal text (rough text estimate, not clinical) |
| ReportLab | 4.1.0 | Builds the PDF report in memory |
| Chart.js | 4.4.1 (loaded from jsDelivr CDN) | Mood charts on the dashboard and Insights page |
| Gunicorn | 23.0.0 | Production WSGI server inside the Docker image |
| pytest | 8.1.1 | Automated tests |
| HTML / CSS / vanilla JavaScript, Jinja2 | — | Front end; no React or build step |
| Google Fonts (Inter, Caveat, Plus Jakarta Sans on the landing page) | — | Typography, loaded from Google Fonts |

## 4. Architecture and directory structure

A single Flask application using the **application factory** pattern (`create_app()` in
`app/__init__.py`) with **blueprints** for each area and a **service layer** holding the logic.

```
Browser (HTML/CSS/JS, Chart.js)
   │  HTTP
   ▼
Flask app (create_app) ── blueprints: auth, dashboard, journal, insights, reports, mindy
   │
   ▼
Services: encryption, sentiment, theme, insight, reflection, report, mindy, time, inspiration, copy
   │
   ▼
SQLAlchemy models ──► SQLite (local) / PostgreSQL (production, prepared)
```

```
MindTrack/
├── run.py                     # creates the app; `python run.py` = local debug server
├── requirements.txt
├── app/
│   ├── __init__.py            # create_app(), startup key check, /health, /tz, cache headers, flask init-db
│   ├── config.py              # env-based config, DB URL handling, production cookie settings
│   ├── extensions.py          # db (SQLAlchemy), csrf (CSRFProtect)
│   ├── models/                # user, journal, tag (+ journal_tags), theme, reflection, report, mindy
│   ├── routes/                # auth, dashboard, journal, insights, reports, mindy (blueprints)
│   ├── services/              # business logic (see sections 7–12)
│   ├── templates/             # Jinja2 pages, partials and macros
│   └── static/                # css/, js/, img/ (photos, Mindy SVGs)
├── scripts/                   # migrate_sqlite_to_postgres.py, seed_demo.py, encrypt_existing_data.py
├── tests/                     # pytest suite (240 tests)
├── Dockerfile, .dockerignore, .gcloudignore, firebase.json, firebase-public/   # deployment config
└── *.md                       # documentation
```

### Main pages and endpoints

| URL | Purpose |
|---|---|
| `/` | Landing page (logged out) or redirect to dashboard |
| `/register`, `/login`, `/logout`, `/profile` | Accounts |
| `/dashboard` | Personal dashboard |
| `/journal/` | Journal home: daily check-in, today's status, recent entries, reflection card |
| `/journal/checkin` (POST) | Save a quick mood check-in |
| `/journal/history` | All entries with filters (mood, tag, title search) |
| `/journal/create`, `/journal/<id>`, `/journal/<id>/edit`, `/journal/<id>/delete`, `/journal/<id>/reflect` | Full entries and reflections |
| `/insights/?range=7\|30\|all` | Personal analytics |
| `/reports/`, `/reports/generate` (POST), `/reports/mindy/<id>` | PDF reports and saved Mindy conversations |
| `/mindy/init`, `/mindy/message`, `/mindy/new`, `/mindy/history`, `/mindy/conversation/<id>` | Mindy chat JSON API |
| `/health` | Health check (`OK`) |
| `/tz` (POST) | Stores the browser's UTC offset in the session |

## 5. Database models and relationships

Defined in `app/models/`. Timestamps are stored as naive UTC (`datetime.utcnow`).

| Table | Key columns | Notes |
|---|---|---|
| `users` | id, name, email (unique), password_hash, created_at, updated_at, last_hero_idx, last_mot_idx | Password is a Werkzeug hash, never plaintext. The two `last_*_idx` columns are legacy (see section 15). |
| `journal_entries` | id, user_id → users, title, **encrypted_content**, mood_score (1–5), mood_label, feelings_raw (≤3 comma-separated), sentiment_polarity, sentiment_subjectivity, sentiment_label, created_at, updated_at | Text is encrypted; mood and sentiment numbers are not, so they can be charted. |
| `tags` | id, user_id → users, name | Unique per user (`uq_user_tag_name`). Used for context tags. |
| `journal_tags` | journal_id → journal_entries, tag_id → tags | Many-to-many link (composite primary key). |
| `detected_themes` | id, journal_id → journal_entries, theme_name | Automatic keyword themes. |
| `reflections` | id, journal_id → journal_entries, prompt, **response_encrypted**, created_at | The user's reflection answer is encrypted. |
| `reports` | id, user_id → users, start_date, end_date, includes_journal_text, created_at | A log of generated reports (the PDF itself is not stored). |
| `mindy_conversations` | id, user_id → users, title, status (active/completed), created_at, updated_at, completed_at | One active conversation per user at a time. |
| `mindy_messages` | id, conversation_id → mindy_conversations, sender (user/mindy), **encrypted_message**, created_at | All chat text is encrypted. |

```
users ─┬─< journal_entries ─┬─< journal_tags >── tags (also belong to users)
       │                    ├─< detected_themes
       │                    └─< reflections
       ├─< reports
       └─< mindy_conversations ──< mindy_messages
```

Deleting a journal entry also removes its tag links, detected themes and reflections (SQLAlchemy
cascades). The `User` model cascades to journal entries, tags and reports, but Mindy conversations are
not linked through a cascading relationship (there is no account-deletion feature yet; see section 15).
Tables are created with `db.create_all()` (automatically in development; via `flask init-db`
or the migration script in production). There is no Alembic migration history.

## 6. Authentication and user privacy

- **Passwords**: hashed with Werkzeug; login compares hashes (`app/models/user.py`, `app/routes/auth.py`).
- **Sessions**: Flask signed session cookie storing `user_id`; `HttpOnly`, `SameSite=Lax`. In production
  the cookie is `Secure` and named `__session` (required by Firebase Hosting) — see `app/config.py`.
- **Access control**: `login_required` decorator on every private page; every query filters by
  `g.user.id`, and records are fetched with `filter_by(id=..., user_id=g.user.id)`, so one user cannot
  open another user's entries, reports or Mindy conversations (covered by tests).
- **CSRF**: Flask-WTF protects every form and JSON POST (the chat sends the token in `X-CSRFToken`).
- **No secrets in code**: `SECRET_KEY` and `MINTRACK_ENCRYPTION_KEY` come from environment
  variables (`.env` locally, Secret Manager in production). `.env.example` contains placeholders only.
- **Caching**: page responses are sent with `Cache-Control: private, no-cache` so shared caches/CDNs don't store personal pages.
- **Logging**: error handlers log exception types, not message contents.

## 7. Journal encryption and key management

`app/services/encryption_service.py` wraps `cryptography.fernet.Fernet`:

- `encrypt_text(text)` → Fernet token string stored in the database; `decrypt_text(token)` reverses it.
  Empty strings are stored as empty strings.
- Encrypted fields: `journal_entries.encrypted_content`, `reflections.response_encrypted`,
  `mindy_messages.encrypted_message`. Mindy's short-term conversation memory is also encrypted
  before being placed in the session cookie.
- **Not encrypted**: entry titles, mood scores/labels, feelings, tags, themes, sentiment numbers, timestamps (needed for charts and filters).
- The key is read from `MINTRACK_ENCRYPTION_KEY`; the app refuses to start if it is missing or malformed
  (`_check_encryption_key` in `app/__init__.py`).
- **Key management rule**: the same key must be used for as long as the data exists. A new key cannot
  decrypt old data. `scripts/migrate_sqlite_to_postgres.py` verifies every encrypted value decrypts with the
  configured key and prints only a short SHA-256 fingerprint so two environments can be compared.
- The key is held by the server, so this is encryption **at rest**, not end-to-end encryption.
- Consequence: the database cannot search inside entry text, so journal search matches titles only.

## 8. Sentiment, themes, insights and reflection services

- **Sentiment** (`sentiment_service.py`): TextBlob polarity (−1…1) and subjectivity; label Positive /
  Neutral / Negative by thresholds. Computed when an entry is saved or its text is edited. It is a text
  estimate shown separately from the mood the user chose.
- **Themes** (`theme_service.py`): transparent keyword matching for 7 themes — Academics, Sleep, Social,
  Family, Work, Exercise, Finance — stored in `detected_themes`.
- **Context tags**: user-selected tags; the journal offers Study, Friends, Family, Home, Sleep, Health,
  Work, Achievement, Other (older tag names such as "Academics" are mapped onto these in analytics).
- **Insights** (`insight_service.py`):
  - `generate_insights()` — rule-based observations: recurring themes (≥3 entries), theme vs average mood
    (difference ≥0.5), frequently chosen feelings, mood trend and writing-tone trend (≥6 entries).
  - `build_insights_view()` — the Insights page: chart series per local day (or per week for long ranges;
    days without check-ins stay empty), summary statistics, previous-period comparison only when both periods
    have ≥3 check-ins, context counts and mood × context distribution, evidence lines for every observation,
    and "Little things worth keeping" suggestions only when a context has ≥3 entries with ≥60% good moods.
  - Wording is deliberately cautious (no diagnosis, no causal claims); tests check this.
- **Reflection prompts** (`reflection_service.py`): priority rules on the entry's decrypted text and
  sentiment — absolute language ("always", "never"…) → evidence question; strongly negative → self-compassion
  question; mildly negative → reframing question; theme-specific prompts; positive → "what helped?";
  otherwise a general prompt. The Journal page falls back to a date-rotated general prompt when there is no recent entry.
- **Local dates** (`time_service.py`): entries are stored in UTC and grouped by the user's local day using
  the browser's UTC offset (cookie `mt_tz`, or the session value set by `/tz`).

## 9. Mindy chatbot implementation

Mindy is a **local, rule-based** conversational engine (no external AI API, no model training). Files:
`app/services/mindy_service.py` (engine), `mindy_content.py` (jokes, games, replies, knowledge),
`mindy_topics.py` (everyday topics), `app/routes/mindy.py` (JSON API), `app/static/js/mindy.js` + `partials/mindy.html` (chat UI).

How a message is handled:
1. **Classification** (`classify`): ordered rules decide the intent — crisis language first, then
   conversation controls ("just listen", "stop asking questions", "change the subject", "no jokes"),
   explicit requests (joke, riddle, game, fact, advice, Mindy/MindTrack questions, knowledge, maths),
   follow-ups to the current activity ("another", riddle guesses), everyday topics, emotions, and finally general statements.
2. **Handlers**: one function per intent (47 intents) builds the reply.
3. **State**: a small JSON state remembers the current activity, the topic being discussed, used jokes/riddles
   (to avoid repeats), "listen only"/"no questions"/"serious" preferences, joke likes/dislikes and the user's
   writing style. It is stored server-side in the session, encrypted with the Fernet key, and rebuilt from
   stored messages if missing. The browser cannot read or modify it.
4. **Style mirroring**: replies are lowercased for users who text in lowercase; emoji are removed for formal writers.

Content counted from the code: 92 jokes in 14 categories (11 used for a general "tell me a joke"; tech, dark
and knock-knock only on request), 12 riddles, 10 "would you rather" questions, a number-guessing game, a
word-chain game, 14 fun facts, 38 short explanations of common questions, and 31 everyday topics (e.g.
periods, being unwell, exams, family comparison, a friend moving away, movies, food) each with specific
replies, follow-up questions and non-medical tips.

Safety: 19 crisis-language patterns trigger a fixed safety message pointing to trusted people, Tele-MANAS
(14416, India) and emergency number 112; idioms like "this joke is killing me" are excluded and tested.

Persistence: conversations and messages are stored encrypted; users can start a new chat, view, rename and
delete past conversations. Saved conversations also appear on the Reports page.

Limitation: being rule-based, Mindy understands only patterns it has rules for; messages outside its
topics get a caring but general reply.

## 10. Report generation and PDF export

`app/routes/reports.py` + `app/services/report_service.py`:
- The user chooses a range (7 days, 30 days, or all) and whether to include journal text.
- ReportLab builds the PDF **in memory** and sends it as a download (`mindtrack-reflection-report-<date>.pdf`).
- Sections: title and period, overview statistics, detected themes table, insights (from `generate_insights`),
  the user's text and reflections **only if explicitly selected**, and a privacy note stating it is not a diagnosis.
- A row is added to `reports` recording the range and whether text was included; the PDF is not stored.

## 11. Running the project locally

```bash
# from the MindTrack folder
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` (never commit it):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"   # MINTRACK_ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_hex(32))"                                    # SECRET_KEY
```

Then:

```bash
python run.py        # http://127.0.0.1:5000 — creates instance/mindtrack.db on first run
```

A fresh key means a fresh, empty database: data encrypted with another key cannot be read.
Optional demo data in a separate database: see the docstring in `scripts/seed_demo.py`.

## 12. Running tests

```bash
pytest -q
```

Tests use an in-memory SQLite database (`tests/conftest.py`) and need `SECRET_KEY` and
`MINTRACK_ENCRYPTION_KEY` set (any valid values, e.g. from `.env`). The suite has 240 tests covering
authentication, journal CRUD and check-ins, encryption, sentiment, themes, insights and the Insights page,
reflection prompts, reports, the dashboard, Mindy (intents, jokes, topics, safety, isolation between users),
production configuration and the migration script.

## 13. Deployment architecture (prepared, not deployed)

See `DEPLOYMENT.md` for the full procedure.

```
Browser → Firebase Hosting (rewrite "**") → Cloud Run service "mindtrack" (asia-south1, Gunicorn, Docker)
                                             → Cloud SQL PostgreSQL (Unix socket)
Secrets (SECRET_KEY, MINTRACK_ENCRYPTION_KEY, DB password) → Google Secret Manager
```

Prepared in code: production mode (`MINDTRACK_ENV=production` or Cloud Run), PostgreSQL URL handling,
`__session` secure cookie, no automatic table creation in production, `Dockerfile`, `firebase.json`,
ignore files that keep `.env` and databases out of uploads, and a read-only, verified SQLite → PostgreSQL
migration script. **Not yet done**: building the image, creating cloud resources, running the migration
against PostgreSQL, and testing Firebase → Cloud Run end to end.

## 14. Known limitations and future enhancements

Limitations (current code):
- Mindy is rule-based; it cannot understand arbitrary language.
- Journal search covers titles only (text is encrypted).
- No account deletion, data export (other than the PDF), or "clear history" feature yet.
- Charts load Chart.js from a CDN; the Insights chart falls back to a text list if it can't load.
- Timezone grouping depends on the browser reporting its offset; the very first page view may use UTC.
- No database migration framework (schema changes need manual handling).
- The mood face icons on the older journal create/detail/history pages render blank, because the SVG
  sprite they use (`partials/mood_symbols.html`) is never included.
- No password reset or email verification.

Possible future work (from `01_PRD.md` and this review): account deletion and data export; Alembic
migrations; password reset; richer NLP themes; optional AI-assisted Mindy (would require sending messages
to a provider); PWA/mobile support; counselor sharing with explicit consent.

## 15. Implemented vs planned

| Feature (from 01_PRD.md / specs) | Status |
|---|---|
| Register / login / logout, hashed passwords, sessions | Implemented |
| Journal create / read / edit / delete, mood 1–5, tags, custom tags | Implemented |
| Search / filter entries | Partial: filter by mood and tag; search by title only |
| Encryption of journal text and reflections | Implemented (plus Mindy messages) |
| TextBlob sentiment stored per entry | Implemented (shown on the entry page and used in insights) |
| Transparent keyword theme detection | Implemented (7 themes) |
| Rule-based, explainable insights with cautious wording | Implemented |
| Reflection prompts + private reflection | Implemented (no "dismiss prompt" action) |
| Mood trend chart, mood distribution, context vs mood | Implemented |
| Sentiment trend **chart** | Not implemented (sentiment trend appears only as a text observation) |
| PDF counselor report with user-selected text | Implemented (no in-app preview before download) |
| Delete account, export data, clear analytics/history | Not implemented |
| Settings / Privacy pages | Not implemented (profile page exists) |
| PostgreSQL + Cloud Run + Firebase Hosting | Configuration prepared; not deployed |

Unused or legacy files kept in the archive for completeness:
- `app/templates/orig_dashboard.html` — an earlier dashboard template, not rendered by any route.
- `app/templates/partials/mood_symbols.html` — SVG mood sprite, not currently included in any page.
- `app/services/copy_service.py` — rotating UI copy, available to templates via `copy()` but not used by current templates (it has its own tests).
- `app/static/img/daily/mot_*.jpg` and the `last_hero_idx` / `last_mot_idx` user columns — from an earlier
  random-image feature; the dashboard now uses the date-based images in `app/static/img/inspiration/`.
- `scripts/encrypt_existing_data.py` — one-off helper to encrypt legacy plaintext entries.
