"""
Create a demo account with a few journal entries in a SEPARATE database,
for trying the UI without touching your real data.

Usage (from the mindtrack folder):
    DATABASE_URL=sqlite:///C:/path/to/demo.db python scripts/seed_demo.py [--reset]

Demo login:  demo@mindtrack.test  /  demo-password-123
Refuses to run against the default instance/mindtrack.db.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEMO_EMAIL = 'demo@mindtrack.test'
DEMO_PASSWORD = 'demo-password-123'

if not os.environ.get('DATABASE_URL'):
    sys.exit("Set DATABASE_URL to a separate demo database first; refusing to seed your real database.")

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.journal import JournalEntry  # noqa: E402
from app.services.encryption_service import encrypt_text  # noqa: E402
from app.routes.journal import get_or_create_tags, apply_content_analysis  # noqa: E402

DEMO_ENTRIES = [
    # (days ago, hour, mood score, label, title, text, contexts)
    (0, 9, 4, 'Good', 'Morning walk', 'Went for a walk before class and felt clear-headed.', ['Health', 'Study']),
    (1, 21, 2, 'Low', 'Late night studying', 'Stayed up late studying for the exam and felt exhausted.', ['Study', 'Sleep']),
    (2, 19, 5, 'Great', 'Dinner with friends', 'Had dinner with friends and laughed a lot.', ['Friends']),
    (4, 18, 3, 'Okay', 'Ordinary day', 'Nothing special, classes and some reading at home.', ['Home', 'Study']),
    (5, 20, 4, 'Good', 'Movie night', 'Watched a movie with friends, felt like myself again.', ['Friends']),
    (6, 22, 2, 'Low', 'Could not sleep', 'Could not sleep, kept thinking about the assignment.', ['Sleep', 'Study']),
    (9, 17, 4, 'Good', 'Assignment done', 'Finished my assignment and felt relieved.', ['Study', 'Achievement']),
    (11, 13, 5, 'Great', 'Lunch with friends', 'Long lunch with friends after the test.', ['Friends']),
]

app = create_app()
with app.app_context():
    user = User.query.filter_by(email=DEMO_EMAIL).first()
    if not user:
        user = User(name='Demo User', email=DEMO_EMAIL)
        user.set_password(DEMO_PASSWORD)
        db.session.add(user)
        db.session.commit()
    if '--reset' in sys.argv:
        JournalEntry.query.filter_by(user_id=user.id).delete()
        db.session.commit()
    if JournalEntry.query.filter_by(user_id=user.id).count() == 0:
        now = datetime.utcnow()
        for days, hour, score, label, title, text, contexts in DEMO_ENTRIES:
            created = (now - timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
            entry = JournalEntry(user_id=user.id, title=title, encrypted_content=encrypt_text(text),
                                 mood_score=score, mood_label=label, created_at=created, updated_at=created)
            entry.tags = get_or_create_tags(contexts, user.id)
            apply_content_analysis(entry, text)
            db.session.add(entry)
        db.session.commit()
    print(f"Demo user ready: {DEMO_EMAIL}")
