import pytest
from app.services.reflection_service import generate_prompt
from app.models.theme import DetectedTheme

class MockJournalEntry:
    def __init__(self, text, polarity, themes):
        self.encrypted_content = text
        self.sentiment_polarity = polarity
        self.detected_themes = [DetectedTheme(theme_name=t) for t in themes]

def test_absolute_language_priority():
    # Even if strongly negative, absolute language takes priority 1
    entry = MockJournalEntry("I am never going to succeed.", -0.8, ["Academics"])
    prompt = generate_prompt(entry)
    assert "absolute statement" in prompt

def test_strongly_negative_priority():
    # Priority 2: negative sentiment bypasses theme if < -0.4
    entry = MockJournalEntry("I am very sad and things are bad.", -0.6, ["Social"])
    prompt = generate_prompt(entry)
    assert "friend described this same situation" in prompt
    
    # Mildly negative
    entry2 = MockJournalEntry("I am a bit disappointed.", -0.2, ["Social"])
    prompt2 = generate_prompt(entry2)
    assert "another possible way to interpret" in prompt2

def test_theme_aware_priority():
    # Priority 3: theme (polarity between -0.15 and 0.4)
    entry = MockJournalEntry("The office was busy today.", 0.1, ["Work"])
    prompt = generate_prompt(entry)
    assert "work situation" in prompt

def test_positive_reflection():
    # Priority 4: positive sentiment bypasses neutral
    entry = MockJournalEntry("The party was fun.", 0.6, [])
    prompt = generate_prompt(entry)
    assert "positive" in prompt

def test_neutral_reflection():
    entry = MockJournalEntry("I ate an apple.", 0.0, [])
    prompt = generate_prompt(entry)
    assert "What stands out most" in prompt

def test_empty_handling():
    entry = MockJournalEntry("", 0.0, [])
    prompt = generate_prompt(entry)
    assert "What stands out most" in prompt

def test_no_clinical_language():
    entry = MockJournalEntry("I feel very bad.", -0.9, [])
    prompt = generate_prompt(entry)
    prompt_lower = prompt.lower()
    assert "therapy" not in prompt_lower
    assert "depression" not in prompt_lower
    assert "symptom" not in prompt_lower
    assert "treatment" not in prompt_lower

def test_user_ownership(client, app):
    # Just asserting the route requires auth
    response = client.get('/journal/1/reflect')
    assert response.status_code == 302 # redirect to login
