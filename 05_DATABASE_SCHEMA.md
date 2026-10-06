# MindTrack — Database Schema

## Database
SQLite + SQLAlchemy.

## Entity relationship

```text
User
 │
 ├────< JournalEntry
 │          │
 │          ├────< JournalTag >──── Tag
 │          │
 │          ├──── Sentiment
 │          └────< Reflection
 │
 └────< Report
```

## users

| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| name | String | Display name |
| email | String | Unique |
| password_hash | String | Never plaintext |
| created_at | DateTime | Account creation |
| updated_at | DateTime | Last update |

## journal_entries

| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| user_id | FK | Owner |
| title | String | Optional |
| encrypted_content | Text | Encrypted journal text |
| mood_score | Integer | 1–5 |
| mood_label | String | Optional |
| created_at | DateTime | Entry time |
| updated_at | DateTime | Last edit |
| sentiment_polarity | Float | TextBlob result |
| sentiment_subjectivity | Float | TextBlob result |
| sentiment_label | String | Positive/Neutral/Negative |

## tags

| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| user_id | FK | Owner |
| name | String | User-defined/context tag |

## journal_tags

| Field | Type | Notes |
|---|---|---|
| journal_id | FK | Journal entry |
| tag_id | FK | Tag |

Composite primary key:
`journal_id + tag_id`

## reflections

| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| journal_id | FK | Related entry |
| prompt | Text | Prompt shown |
| response_encrypted | Text | User reflection |
| created_at | DateTime | Creation |

## reports

| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| user_id | FK | Owner |
| start_date | Date | Report period |
| end_date | Date | Report period |
| includes_journal_text | Boolean | Explicit consent |
| created_at | DateTime | Generation time |

## Design rules
- Every private record belongs to a user.
- Every query must be scoped to the authenticated user's ID.
- Do not trust user-supplied `user_id`.
- Do not store plaintext passwords.
- Journal content and reflection responses should be encrypted.
- Sentiment metadata may remain queryable for analytics because it does not contain the original text.

## Example SQLAlchemy relationships

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    journal_entries = db.relationship(
        "JournalEntry",
        back_populates="user",
        cascade="all, delete-orphan"
    )
```

Use migrations once the schema stabilizes.
