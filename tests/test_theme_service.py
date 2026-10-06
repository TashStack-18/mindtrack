import pytest
from app.services.theme_service import detect_themes, get_theme_explanation
from app.models.journal import JournalEntry
from app.models.theme import DetectedTheme

def test_detect_academics():
    themes = detect_themes("I am studying for my exams and have an assignment due.")
    assert "Academics" in themes
    assert len(themes) == 1

def test_detect_sleep():
    themes = detect_themes("I am very tired and did not sleep well due to insomnia.")
    assert "Sleep" in themes
    
    themes2 = detect_themes("I couldn't sleep last night.")
    assert "Sleep" in themes2

    themes3 = detect_themes("I stayed awake until 3 AM.")
    assert "Sleep" in themes3

def test_detect_social():
    themes = detect_themes("My friends invited me to a party.")
    assert "Social" in themes

def test_detect_family():
    themes = detect_themes("My mom and dad visited home.")
    assert "Family" in themes

def test_detect_work():
    themes = detect_themes("I had a meeting with my manager at the office.")
    assert "Work" in themes

def test_detect_exercise():
    themes = detect_themes("I went to the gym for a workout and walking.")
    assert "Exercise" in themes

def test_detect_finance():
    themes = detect_themes("I need to budget my money for rent expenses.")
    assert "Finance" in themes

def test_multiple_themes():
    themes = detect_themes("I stayed up late studying for my exam and then went to the gym.")
    assert "Academics" in themes
    assert "Sleep" in themes 
    assert "Exercise" in themes
    
    themes2 = detect_themes("I slept badly because of my exam and friends.")
    assert "Sleep" in themes2
    assert "Academics" in themes2
    assert "Social" in themes2

def test_case_insensitive_and_punctuation():
    themes = detect_themes("EXAMS!!! ARE Terrible... sleeping badly.")
    assert "Academics" in themes
    assert "Sleep" in themes

def test_partial_word_false_positives():
    themes = detect_themes("I bought a new classical music album.")
    # "class" is in Academics, but "classical" should not trigger it.
    assert "Academics" not in themes

def test_empty_input():
    assert detect_themes("") == []
    assert detect_themes("   ") == []

def test_journal_detects_themes_on_creation(client, app):
    client.post('/register', data={'name': 'Test', 'email': 't3@example.com', 'password': 'password123'})
    client.post('/login', data={'email': 't3@example.com', 'password': 'password123'})
    
    client.post('/journal/create', data={
        'title': 'Test',
        'content': 'Studying for my exams with friends.',
        'mood': '3'
    })
    
    with app.app_context():
        entry = JournalEntry.query.order_by(JournalEntry.id.desc()).first()
        themes = [t.theme_name for t in entry.detected_themes]
        assert 'Academics' in themes
        assert 'Social' in themes
        
def test_journal_editing_redetects_themes(client, app):
    client.post('/register', data={'name': 'Test', 'email': 't4@example.com', 'password': 'password123'})
    client.post('/login', data={'email': 't4@example.com', 'password': 'password123'})
    
    client.post('/journal/create', data={
        'title': 'Test',
        'content': 'Gym workout.',
        'mood': '3'
    })
    
    with app.app_context():
        entry = JournalEntry.query.order_by(JournalEntry.id.desc()).first()
        entry_id = entry.id
        themes = [t.theme_name for t in entry.detected_themes]
        assert 'Exercise' in themes
        
    client.post(f'/journal/{entry_id}/edit', data={
        'title': 'Test',
        'content': 'Sleeping in my bed.',
        'mood': '3'
    })
    
    with app.app_context():
        entry = JournalEntry.query.get(entry_id)
        themes = [t.theme_name for t in entry.detected_themes]
        assert 'Exercise' not in themes
        assert 'Sleep' in themes
