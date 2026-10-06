import pytest
from app.models.journal import JournalEntry
from app.models.tag import Tag

def login(client, email='test@example.com', password='password123'):
    return client.post('/login', data={'email': email, 'password': password})

@pytest.fixture
def auth_client(client, app):
    client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123'
    })
    login(client)
    return client

def test_journal_create(auth_client, app):
    response = auth_client.post('/journal/create', data={
        'title': 'Test Entry',
        'content': 'This is a test journal entry.',
        'mood': '4',
        'tags': ['Academics', 'Sleep'],
        'custom_tags': 'Coding'
    })
    assert response.status_code == 302
    
    with app.app_context():
        entry = JournalEntry.query.first()
        assert entry is not None
        assert entry.title == 'Test Entry'
        assert entry.encrypted_content == 'This is a test journal entry.'
        assert entry.mood_score == 4
        assert entry.mood_label == 'Good'
        assert entry.tags.count() == 3
        tag_names = [t.name for t in entry.tags]
        assert 'Academics' in tag_names
        assert 'Coding' in tag_names

def test_journal_create_validation(auth_client, app):
    # Empty content
    response = auth_client.post('/journal/create', data={
        'title': 'Test Entry',
        'content': '',
        'mood': '4'
    })
    assert b'Journal content is required.' in response.data
    
    # Invalid mood
    response = auth_client.post('/journal/create', data={
        'title': 'Test Entry',
        'content': 'Test',
        'mood': '10'
    })
    assert b'Valid mood score is required.' in response.data

def test_journal_edit(auth_client, app):
    auth_client.post('/journal/create', data={
        'title': 'Old Title',
        'content': 'Old content',
        'mood': '3'
    })
    
    with app.app_context():
        entry_id = JournalEntry.query.first().id
        
    response = auth_client.post(f'/journal/{entry_id}/edit', data={
        'title': 'New Title',
        'content': 'New content',
        'mood': '5'
    })
    assert response.status_code == 302
    
    with app.app_context():
        entry = JournalEntry.query.get(entry_id)
        assert entry.title == 'New Title'
        assert entry.encrypted_content == 'New content'
        assert entry.mood_score == 5

def test_journal_delete(auth_client, app):
    auth_client.post('/journal/create', data={
        'title': 'To Delete',
        'content': 'content',
        'mood': '3'
    })
    
    with app.app_context():
        entry_id = JournalEntry.query.first().id
        
    response = auth_client.post(f'/journal/{entry_id}/delete')
    assert response.status_code == 302
    
    with app.app_context():
        entry = JournalEntry.query.get(entry_id)
        assert entry is None

def test_journal_unauthorized_access(client, auth_client, app):
    auth_client.post('/journal/create', data={
        'title': 'Secret',
        'content': 'Secret content',
        'mood': '3'
    })
    
    with app.app_context():
        entry_id = JournalEntry.query.first().id
        
    client.get('/logout')
    
    # Unauthenticated user
    response = client.get(f'/journal/{entry_id}')
    assert response.status_code == 302
    
    # Different user
    client.post('/register', data={
        'name': 'Other User',
        'email': 'other@example.com',
        'password': 'password123'
    })
    login(client, 'other@example.com', 'password123')
    
    response = client.get(f'/journal/{entry_id}')
    assert response.status_code == 404
