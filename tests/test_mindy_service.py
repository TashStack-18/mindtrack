import pytest
from app.services.mindy_service import generate_reply, build_context, MindyContext
from unittest.mock import patch, MagicMock

@pytest.fixture
def empty_context():
    return MindyContext(
        themes=[],
        tags=[],
        mood_label="",
        sentiment_label="",
        sentiment_polarity=0.0,
        age_days=10,
        keywords=set()
    )

def test_greeting(empty_context):
    reply, state = generate_reply("hi mindy", empty_context, None)
    from app.services.mindy_service import TEMPLATES
    assert reply in TEMPLATES['greeting']
    assert state['turn'] == 1
    assert state['last_intents'][0] == 'greeting'

def test_fallback_empty(empty_context):
    reply, state = generate_reply("x", empty_context, None) # too short
    from app.services.mindy_service import TEMPLATES
    assert reply in TEMPLATES['fallback']
    assert state['turn'] == 1
    assert state['last_intents'][0] == 'fallback'

def test_positive_input(empty_context):
    reply, state = generate_reply("I had a great time today with my friends.", empty_context, None)
    assert state['turn'] == 1
    assert state['last_intents'][0] in ['positive_experience', 'social_situation']

def test_work_overwhelm(empty_context):
    reply, state = generate_reply("i am so overwhelmed by work, there is too much to do", empty_context, None)
    assert state['last_intents'][0] in ['overwhelm', 'work_pressure']
    
def test_safety_concern(empty_context):
    from app.services.mindy_service import SAFETY_MESSAGE
    phrases = [
        "I want to kill myself",
        "I want to die",
        "I don't want to be here anymore",
        "I don't want to be alive",
        "I'm going to hurt myself",
        "I keep thinking about suicide"
    ]
    for phrase in phrases:
        reply, state = generate_reply(phrase, empty_context, None)
        assert state['last_intents'][0] == 'safety_concern'
        assert reply == SAFETY_MESSAGE

def test_determinism():
    reply1, state1 = generate_reply("I am sad", None, None)
    reply2, state2 = generate_reply("I am sad", None, None)
    assert reply1 == reply2
    
    reply3, state3 = generate_reply("I am sad", None, state1)
    assert reply3 != reply1

def test_state_sanitisation():
    malformed_state = {"turn": "not an int", "last_intents": "wrong"}
    reply, state = generate_reply("hi", None, malformed_state)
    assert state['turn'] == 1

def test_banned_vocabulary():
    from app.services.mindy_service import TEMPLATES
    
    banned_words = [
        "depress", "anxiety", "anxious disorder", "disorder", "diagnos", "clinical",
        "psychiatr", "psycholog", "mental illness", "mental health score", 
        "treatment", "treat you", "cure", "medication", "bipolar", "ptsd", "ocd",
        "you are depressed", "caused", "because of this you", 
        "that's why you feel", "your picture is forming", "AI therapist"
    ]
    
    for intent, templates in TEMPLATES.items():
        for template in templates:
            text = template.lower()
            if intent == 'safety_concern':
                pass
            for word in banned_words:
                assert word not in text, f"Banned word '{word}' found in intent '{intent}': {template}"
            if "therap" in text:
                assert "not a therapist" in text or "not a medical service" in text

def test_max_length():
    from app.services.mindy_service import TEMPLATES
    for intent, templates in TEMPLATES.items():
        for t in templates:
            assert len(t) < 400

def test_negation(empty_context):
    reply, state = generate_reply("I did not have a good day", empty_context, None)
    assert state['last_intents'][0] != 'positive_experience'

def test_context_integration(empty_context):
    reply, state = generate_reply("I am terrible", empty_context, None)
    assert state['last_intents'][0] == 'negative_experience'

def test_absolute_language(empty_context):
    reply, state = generate_reply("I always ruin everything and nobody likes me", empty_context, None)
    assert state['last_intents'][0] == 'absolute_language'

def test_template_tone_constraints():
    import re
    from app.services.mindy_service import TEMPLATES, CONTEXT_TEMPLATES
    
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
    all_caps_word = re.compile(r'\b[A-Z]{4,}\b')
    repeated_letters = re.compile(r'([a-zA-Z])\1{2,}')
    
    all_templates = []
    for t_list in TEMPLATES.values():
        all_templates.extend(t_list)
    for t_list in CONTEXT_TEMPLATES.values():
        all_templates.extend(t_list)
        
    for text in all_templates:
        assert not emoji_pattern.search(text), f"Emoji found in template: {text}"
        assert not all_caps_word.search(text), f"4+ letter all-caps word found in template: {text}"
        assert not repeated_letters.search(text), f"Repeated letter found in template: {text}"
