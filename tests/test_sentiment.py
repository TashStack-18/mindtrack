import pytest
from app.services.sentiment_service import analyze_text, classify_sentiment
from app.models.journal import JournalEntry

def test_classify_sentiment():
    assert classify_sentiment(0.2) == "Positive"
    assert classify_sentiment(1.0) == "Positive"
    
    assert classify_sentiment(-0.2) == "Negative"
    assert classify_sentiment(-1.0) == "Negative"
    
    assert classify_sentiment(0.1) == "Neutral"
    assert classify_sentiment(0.0) == "Neutral"
    assert classify_sentiment(-0.1) == "Neutral"

def test_analyze_positive_text():
    result = analyze_text("I had an amazing and wonderful day.")
    assert result['polarity'] > 0.15
    assert result['label'] == "Positive"
    assert 0 <= result['subjectivity'] <= 1

def test_analyze_negative_text():
    result = analyze_text("Everything went badly and I feel frustrated.")
    assert result['polarity'] < -0.15
    assert result['label'] == "Negative"
    assert 0 <= result['subjectivity'] <= 1

def test_analyze_neutral_text():
    result = analyze_text("The class started at ten in the morning.")
    assert -0.15 <= result['polarity'] <= 0.15
    assert result['label'] == "Neutral"

def test_analyze_empty_text():
    result = analyze_text("")
    assert result['polarity'] == 0.0
    assert result['subjectivity'] == 0.0
    assert result['label'] == "Neutral"
    
    result2 = analyze_text("   \n  ")
    assert result2['polarity'] == 0.0
    assert result2['label'] == "Neutral"

def test_journal_creation_stores_sentiment(client, app):
    # Register and login
    client.post('/register', data={'name': 'Test', 'email': 'test@example.com', 'password': 'password123'})
    client.post('/login', data={'email': 'test@example.com', 'password': 'password123'})
    
    # Create journal
    client.post('/journal/create', data={
        'title': 'Good Day',
        'content': 'I had an amazing and wonderful day.',
        'mood': '5'
    })
    
    with app.app_context():
        entry = JournalEntry.query.first()
        assert entry.sentiment_label == 'Positive'
        assert entry.sentiment_polarity > 0.15

def test_journal_editing_recalculates_sentiment(client, app):
    # Register and login
    client.post('/register', data={'name': 'Test', 'email': 'test2@example.com', 'password': 'password123'})
    client.post('/login', data={'email': 'test2@example.com', 'password': 'password123'})
    
    # Create journal (Negative initially)
    client.post('/journal/create', data={
        'title': 'Bad Day',
        'content': 'Everything went badly and I feel frustrated.',
        'mood': '1'
    })
    
    with app.app_context():
        entry = JournalEntry.query.first()
        entry_id = entry.id
        assert entry.sentiment_label == 'Negative'
        
    # Edit journal to Positive
    client.post(f'/journal/{entry_id}/edit', data={
        'title': 'Good Day Now',
        'content': 'I had an amazing and wonderful day.',
        'mood': '5'
    })
    
    with app.app_context():
        entry = JournalEntry.query.get(entry_id)
        assert entry.sentiment_label == 'Positive'
        assert entry.sentiment_polarity > 0.15
