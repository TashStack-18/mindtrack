import pytest
from app.services.insight_service import generate_insights
from app.models.theme import DetectedTheme

class MockJournalEntry:
    def __init__(self, mood, sentiment_polarity, themes):
        self.mood_score = mood
        self.sentiment_polarity = sentiment_polarity
        self.detected_themes = [DetectedTheme(theme_name=t) for t in themes]
        self.feelings = []
        # Just mock created_at as an int for simple sorting testing
        self.created_at = 1

def test_no_insights_insufficient_data():
    entries = [MockJournalEntry(3, 0.0, ['Academics'])]
    insights = generate_insights(entries)
    assert len(insights) == 0

def test_recurring_theme_and_mood_association():
    entries = [
        MockJournalEntry(2, 0.0, ['Academics']),
        MockJournalEntry(3, 0.0, ['Academics']),
        MockJournalEntry(3, 0.0, ['Academics']),
        MockJournalEntry(4, 0.0, ['Friends']),
        MockJournalEntry(5, 0.0, ['Friends'])
    ]
    
    insights = generate_insights(entries)
    
    # overall avg mood = 17 / 5 = 3.4
    # Academics avg = 8 / 3 = 2.67. Diff = 2.67 - 3.4 = -0.73
    # Friends avg = 9 / 2 = 4.5. (Only 2, so won't trigger recurring or association)
    
    assert len(insights) == 2
    
    recurring = [i for i in insights if i['type'] == 'recurring_theme']
    assert len(recurring) == 1
    assert "Academics appeared frequently" in recurring[0]['title']
    
    association = [i for i in insights if i['type'] == 'mood_association']
    assert len(association) == 1
    assert "lower recorded mood" in association[0]['title']
    assert "Academics" in association[0]['title']

def test_no_causal_language():
    entries = [
        MockJournalEntry(2, 0.0, ['Academics']),
        MockJournalEntry(3, 0.0, ['Academics']),
        MockJournalEntry(3, 0.0, ['Academics']),
        MockJournalEntry(5, 0.0, ['Work'])
    ]
    insights = generate_insights(entries)
    for insight in insights:
        text = (insight['title'] + " " + insight['description']).lower()
        assert "caused" not in text
        assert "making you" not in text
        assert "depression" not in text

def test_trends():
    entries = [
        # Prev half
        MockJournalEntry(2, -0.5, []),
        MockJournalEntry(2, -0.5, []),
        MockJournalEntry(3, 0.0, []),
        # Recent half
        MockJournalEntry(4, 0.5, []),
        MockJournalEntry(5, 0.5, []),
        MockJournalEntry(5, 0.5, [])
    ]
    
    # Need to set created_at for sorting
    for i, e in enumerate(entries):
        e.created_at = i
        
    insights = generate_insights(entries)
    
    mood_trends = [i for i in insights if i['type'] == 'mood_trend']
    assert len(mood_trends) == 1
    assert "increased" in mood_trends[0]['title']
    
    sentiment_trends = [i for i in insights if i['type'] == 'sentiment_trend']
    assert len(sentiment_trends) == 1
    assert "positive" in sentiment_trends[0]['title']

def test_user_isolation(client, app):
    # This ensures routes return 401 unauthenticated
    response = client.get('/insights/')
    assert response.status_code == 302
