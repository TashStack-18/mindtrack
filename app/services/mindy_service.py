import re
import hashlib
from dataclasses import dataclass
from typing import Optional, List, Dict, Set, Tuple
from datetime import datetime
import json
import logging
from app.models.journal import JournalEntry
from app.services.reflection_service import ABSOLUTE_WORDS
from app.services.theme_service import THEME_CATEGORIES
from app.services.sentiment_service import analyze_text
from app.services.encryption_service import decrypt_text
from flask import current_app

@dataclass
class MindyContext:
    themes: List[str]
    tags: List[str]
    mood_label: str
    sentiment_label: str
    sentiment_polarity: float
    age_days: int
    keywords: Set[str]

SAFETY_MESSAGE = "I'm hearing that you are going through a really difficult time right now. As a reflection companion, I can't provide the level of help you might need, and I'm not a therapist. Please reach out to someone you trust, or contact your local emergency number or a crisis helpline in your country. You don't have to carry this alone."

# Banned vocabulary explicitly checked in tests.
# "depress", "anxiety", "clinical", etc.

TEMPLATES = {
    'safety_concern': [
        SAFETY_MESSAGE,
    ],
    'greeting': [
        "Hey. What's on your mind today?",
        "Hey, I'm Mindy. How are you doing today?",
        "Hey. Take a breath. What's going on?",
        "Hi. Want to talk for a bit?",
        "Hey. How's your day been treating you?",
        "Hey, I'm here. What's been on your mind?"
    ],
    'thanks_goodbye': [
        "You're welcome. Take care of yourself today.",
        "Of course. Take a little breather now.",
        "Anytime. I'll be here if you want to chat later."
    ],
    'ask_reflection': [
        "What's been going on?",
        "What's on your mind today?",
        "What's one thing you're carrying with you today?",
        "Does it help to write that down?"
    ],
    'ask_perspective': [
        "What actually happened today?",
        "Are you worried about what might happen next?",
        "That sounds overwhelming. What part of this is bothering you the most?",
        "What part of this is bothering you the most right now?"
    ],
    'absolute_language': [
        "It can feel like '{word}' sometimes.",
        "That sounds heavy.",
        "I know it feels like '{word}' right now."
    ],
    'overwhelm': [
        "You sound completely done for today.",
        "That sounds like a lot to carry around.",
        "What's the most urgent thing right now?",
        "That's so much to handle at once."
    ],
    'academic_stress': [
        "Oh, exam day. How did it go?",
        "That is a frustrating feeling, especially when you put the work in.",
        "School can take up so much energy.",
        "I am sorry. Is it the subject itself or just the pressure?"
    ],
    'sleep_concern': [
        "Not being able to sleep is very hard.",
        "Your brain just won't turn off, huh?",
        "That sounds exhausting."
    ],
    'sleep_and_academic': [
        "Losing sleep over school is a terrible feeling.",
        "It is hard to rest when you are stressed about tomorrow.",
        "That sounds exhausting."
    ],
    'work_pressure': [
        "Work can be very draining.",
        "That sounds like a really frustrating shift.",
        "That's a lot of pressure to deal with."
    ],
    'social_situation': [
        "I can see why that would hurt.",
        "I can see why you are mad.",
        "That sounds really complicated to deal with.",
        "Friendship stuff is so draining."
    ],
    'family_situation': [
        "Family stuff is always so heavy.",
        "That sounds like a really hard situation at home.",
        "I am sorry you have to deal with that."
    ],
    'positive_experience': [
        "That is actually so good.",
        "That is wonderful.",
        "That's such a nice little win.",
        "You deserve to enjoy that one.",
        "That is exciting.",
        "Tell me more about it."
    ],
    'negative_experience': [
        "That sounds really hard.",
        "I am sorry. That sounds exhausting.",
        "That sounds like a lot to carry around.",
        "You don't have to make it sound better than it was. You can just tell me.",
        "That really got to you.",
        "One of those days?"
    ],
    'fallback': [
        "I am here. Tell me a little more.",
        "How are you feeling about it now?",
        "That makes sense.",
        "That sounds like a lot.",
        "I hear you."
    ],
    'end_conversation': [
        "I think that is a good place to leave it for now. Take care of yourself.",
        "We will leave it here for today. I am glad you got some of that out.",
        "Let's pause here for now. Be kind to yourself today.",
        "That is enough thinking for now. Take a little breather.",
        "We will leave this one here. I hope the rest of your day feels a little lighter."
    ]
}

# Add contextual templates where context can be injected.
# We append these to normal intents, but these are handled slightly differently.
CONTEXT_TEMPLATES = {
    'ask_reflection': [
        "You've been writing about {theme} lately. Is that still on your mind?",
        "Last time you checked in, you were feeling {mood}. Has anything shifted since then?",
        "Your last entry seemed a bit {sentiment}. Does that still reflect how you feel?"
    ]
}

def clean_text(text: str) -> str:
    # strip punctuation and lowercase
    return re.sub(r'[^\w\s]', '', text).lower().strip()

def detect_intent(text: str, text_clean: str) -> Tuple[str, Optional[str]]:
    # 1. Safety concern
    safety_words = ["die", "suicide", "end it all", "kill myself", "hurt myself", "dont want to be here", "dont want to be alive"]
    if any(re.search(rf'\b{w}\b', text_clean) for w in safety_words):
        return 'safety_concern', None

    # 2. Empty/fallback
    if not text_clean or len(text_clean) < 2:
        return 'fallback', None

    # Negation handling
    negations = ["not", "isnt", "wasnt", "arent", "werent", "dont", "doesnt", "didnt", "cant", "couldnt", "wont", "wouldnt"]
    has_negation = any(re.search(rf'\b{n}\b', text_clean) for n in negations)

    # 3. Greeting
    greetings = ["hi", "hello", "hey", "good morning", "good evening", "hi mindy"]
    if text_clean in greetings:
        return 'greeting', None

    # 4. Thanks/goodbye
    closing = ["thanks", "thank you", "bye", "goodbye", "goodnight"]
    if any(re.search(rf'\b{w}\b', text_clean) for w in closing) and len(text_clean.split()) < 5:
        return 'thanks_goodbye', None

    # 5. Ask reflection
    if any(re.search(rf'\b{w}\b', text_clean) for w in ["reflect", "what should i write", "dont know what to write", "give me a prompt", "help me reflect"]):
        return 'ask_reflection', None

    # 6. Ask perspective
    if any(re.search(rf'\b{w}\b', text_clean) for w in ["what do you think", "is it my fault", "am i wrong", "how should i see this", "another way to look", "am i overthinking"]):
        return 'ask_perspective', None

    # 7. Absolute language
    for word in ABSOLUTE_WORDS:
        if re.search(rf'\b{word}\b', text_clean):
            return 'absolute_language', word

    # 8. Overwhelm
    overwhelm_phrases = ["so much", "too much", "overwhelmed", "dont know where to start", "cant keep up", "drowning in"]
    if any(re.search(rf'\b{w}\b', text_clean) for w in overwhelm_phrases):
        return 'overwhelm', None

    # 9. Topic intents
    topics = {}
    for cat, kws in THEME_CATEGORIES.items():
        topics[cat.lower()] = False
        for kw in kws:
            if re.search(rf'\b{kw}\b', text_clean):
                topics[cat.lower()] = True
                break
    
    # Custom specific combinations
    is_sleep = topics.get('sleep', False)
    is_academic = topics.get('academics', False)
    if is_sleep and is_academic:
        return 'sleep_and_academic', None
    
    if is_academic: return 'academic_stress', None
    if topics.get('work', False): return 'work_pressure', None
    if topics.get('social', False): return 'social_situation', None
    if topics.get('family', False): return 'family_situation', None
    if is_sleep: return 'sleep_concern', None

    # 10. Positive/Negative Experience
    pos_words = ["good", "great", "happy", "excited", "proud", "grateful", "relieved", "well", "loved"]
    neg_words = ["sad", "upset", "angry", "frustrated", "bad", "rough", "hurt", "annoyed", "disappointed", "stressed", "worried", "scared", "awful", "terrible"]
    
    has_pos = any(re.search(rf'\b{w}\b', text_clean) for w in pos_words)
    has_neg = any(re.search(rf'\b{w}\b', text_clean) for w in neg_words)

    # Simple textblob tie breaker if we really needed, but let's just use negation
    if has_negation and has_pos:
        return 'negative_experience', None
    elif has_pos:
        return 'positive_experience', None
    elif has_neg:
        return 'negative_experience', None

    return 'fallback', None

def generate_reply(user_message: str, context: Optional[MindyContext], state: Optional[dict]) -> Tuple[str, dict]:
    try:
        if state is None:
            state = {"turn": 0, "last_intents": [], "last_templates": [], "context_used_turn": -99}
        
        # Validations on state
        if not isinstance(state.get('turn'), int): state['turn'] = 0
        if not isinstance(state.get('last_intents'), list): state['last_intents'] = []
        if not isinstance(state.get('last_templates'), list): state['last_templates'] = []
        if not isinstance(state.get('context_used_turn'), int): state['context_used_turn'] = -99
        
        state['turn'] += 1
        
        text_clean = clean_text(user_message)
        intent, extracted_word = detect_intent(user_message, text_clean)
        
        # Contextual override
        use_context = False
        reply_template = None
        
        # We only use context if age_days < 7 and we haven't used it in the last 2 turns
        if context and context.age_days < 7 and (state['turn'] - state['context_used_turn'] > 2):
            if intent in ['greeting', 'ask_reflection', 'ask_perspective', 'fallback']:
                # Maybe use context
                if context.themes:
                    reply_template = CONTEXT_TEMPLATES['ask_reflection'][0].format(theme=context.themes[0])
                    use_context = True
                elif context.mood_label:
                    reply_template = CONTEXT_TEMPLATES['ask_reflection'][1].format(mood=context.mood_label)
                    use_context = True
                elif context.sentiment_label:
                    reply_template = CONTEXT_TEMPLATES['ask_reflection'][2].format(sentiment=context.sentiment_label)
                    use_context = True

        if use_context and reply_template:
            state['context_used_turn'] = state['turn']
            reply = reply_template
            template_idx = -1
        else:
            templates = TEMPLATES.get(intent, TEMPLATES['fallback'])
            
            # Deterministic selection
            # hash based on user message and turn
            h = int(hashlib.sha256(f"{text_clean}_{state['turn']}".encode()).hexdigest(), 16)
            
            # Avoid last used templates for this intent if possible
            available_indices = [i for i in range(len(templates)) if i not in state['last_templates']]
            if not available_indices:
                available_indices = list(range(len(templates))) # reset if exhausted
                
            template_idx = available_indices[h % len(available_indices)]
            reply_template = templates[template_idx]
            
            if intent == 'absolute_language' and extracted_word:
                reply = reply_template.format(word=extracted_word)
            else:
                reply = reply_template
        
        # Update state
        state['last_intents'].insert(0, intent)
        state['last_templates'].insert(0, template_idx)
        state['last_intents'] = state['last_intents'][:2]
        state['last_templates'] = state['last_templates'][:2]

        return reply, state
    except Exception as e:
        logging.error(f"Mindy engine error: {type(e)}")
        # Safe fallback
        if state is None or not isinstance(state, dict):
            state = {"turn": 1, "last_intents": [], "last_templates": [], "context_used_turn": -99}
        return "Tell me a little more about what's on your mind.", state

def build_context(user_id: int) -> Optional[MindyContext]:
    try:
        # Load the latest journal entry for the user
        entry = JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.created_at.desc()).first()
        if not entry:
            return None
        
        age_days = (datetime.utcnow() - entry.created_at).days
        
        # Extract themes
        themes = [t.theme_name for t in entry.detected_themes] if entry.detected_themes else []
        tags = [t.name for t in entry.tags] if entry.tags else []
        
        keywords = set()
        if age_days < 7:
            # Only decrypt and extract keywords if recent
            try:
                decrypted = decrypt_text(entry.encrypted_content)
                text_clean = clean_text(decrypted)
                for cat, kws in THEME_CATEGORIES.items():
                    for kw in kws:
                        if re.search(rf'\b{kw}\b', text_clean):
                            keywords.add(kw)
            except Exception:
                pass # Swallow decryption errors safely
            
        return MindyContext(
            themes=themes,
            tags=tags,
            mood_label=entry.mood_label,
            sentiment_label=entry.sentiment_label or "Neutral",
            sentiment_polarity=entry.sentiment_polarity or 0.0,
            age_days=age_days,
            keywords=keywords
        )
    except Exception as e:
        logging.error(f"Failed to build mindy context: {type(e)}")
        return None
