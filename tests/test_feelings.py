import pytest
from app.models.journal import JournalEntry
from app import create_app
from app.extensions import db
from app.models.user import User

@pytest.fixture
def user(app):
    user = User(email='test@example.com', name='Test User')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user

def test_feelings_whitelist_and_cap(app, user):
    entry = JournalEntry(
        user_id=user.id,
        title='Test Entry',
        encrypted_content='encrypted',
        mood_score=4,
        mood_label='Good'
    )
    
    # Test valid feelings
    entry.feelings = ['calm', 'excited', 'loved']
    assert len(entry.feelings) == 3
    assert 'calm' in entry.feelings
    
    # Test cap (max 3)
    entry.feelings = ['calm', 'excited', 'loved', 'proud']
    assert len(entry.feelings) == 3
    assert 'proud' not in entry.feelings
    
    # Test unknown ignored
    entry.feelings = ['calm', 'unknown_feeling', 'loved']
    assert len(entry.feelings) == 2
    assert 'unknown_feeling' not in entry.feelings
    
    # Test old entries unaffected (None)
    entry.feelings_raw = None
    assert entry.feelings == []
    
    # Test isolation
    entry2 = JournalEntry(
        user_id=user.id,
        title='Test Entry 2',
        encrypted_content='encrypted',
        mood_score=2,
        mood_label='Low'
    )
    entry2.feelings = ['tired', 'sad']
    assert entry.feelings == []
    assert len(entry2.feelings) == 2
