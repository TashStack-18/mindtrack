"""
Mindy's conversation engine.

Mindy is a local, rule-based companion (no external AI service). Each turn:
  1. classify()   -> work out what the user is asking for (intent), using
                     the conversation state for follow-ups like "another".
  2. HANDLERS     -> one small function per intent builds the reply.
  3. state        -> remembers the current activity (joke, riddle, game),
                     the topic being discussed, listening preferences and
                     which content was already used, so replies don't repeat.

The state dict is plain JSON so the route can store it server-side.
"""
import ast
import logging
import operator
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

from app.models.journal import JournalEntry
from app.services import mindy_content as C
from app.services import mindy_topics as T
from app.services.mindy_content import TEMPLATES, SAFETY_MESSAGE  # re-exported for routes/tests

STATE_VERSION = 2
MAX_INPUT_CHARS = 1000


@dataclass
class MindyContext:
    """Read-only facts about the current user that Mindy may mention when asked.
    Built from mood check-ins only; journal text is never decrypted for chat."""
    mood_counts: Dict[str, int] = field(default_factory=dict)
    entry_count: int = 0
    days: int = 14
    average_score: Optional[float] = None
    trend: Optional[str] = None  # 'up', 'down', 'steady'
    themes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------
def new_state() -> dict:
    return {
        'v': STATE_VERSION,
        'turn': 0,
        'activity': None,      # current game/joke/riddle/menu, see handlers
        'offer': None,         # what Mindy just offered ("Want another one?")
        'topic': None,         # what the user is currently talking about
        'used': {},            # pool name -> indices already used
        'no_advice': False,    # user asked to just be listened to
        'no_questions': False, # user asked Mindy to stop asking questions
        'asked_pref': False,   # already asked "advice or listen?"
        'safety': 0,           # turns remaining in a safety check-in
        'last_intent': None,
        'joke_likes': {},      # joke category -> net thumbs up in this conversation
        'last_joke_kind': None,
        'serious': False,      # user asked for no jokes / a serious tone
        'style': {},           # how the user writes (lowercase, emoji, slang), last 3 messages
    }


def sanitize_state(state) -> dict:
    """Accept only a well-formed state of the current version."""
    base = new_state()
    if not isinstance(state, dict) or state.get('v') != STATE_VERSION:
        return base
    for key, default in base.items():
        value = state.get(key, default)
        if default is None:
            base[key] = value if isinstance(value, (dict, str)) or value is None else None
        elif isinstance(default, bool):
            base[key] = bool(value)
        elif isinstance(default, int):
            base[key] = value if isinstance(value, int) else default
        elif isinstance(default, dict):
            base[key] = value if isinstance(value, dict) else {}
    return base


def pick(state: dict, name: str, pool: List, rng=random):
    """Pick an item from a pool, avoiding ones already used this conversation."""
    used = [i for i in state['used'].get(name, []) if isinstance(i, int) and 0 <= i < len(pool)]
    available = [i for i in range(len(pool)) if i not in used]
    if not available:
        # Pool exhausted: start over, but never repeat the very last one.
        used = used[-1:] if len(pool) > 1 else []
        available = [i for i in range(len(pool)) if i not in used]
    idx = rng.choice(available)
    state['used'][name] = (used + [idx])[-40:]
    return idx, pool[idx]


def ask(state: dict, question: str) -> str:
    """Append a follow-up question unless the user asked for no questions."""
    if not question or state.get('no_questions'):
        return ''
    return ' ' + question


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def normalize(text: str) -> str:
    text = text.lower().replace('’', "'").replace('‘', "'")
    text = text.replace("'", '')
    text = re.sub(r'[^\w\s?+\-*/.]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def words_of(t: str) -> List[str]:
    return re.findall(r'[a-z0-9]+', t)


def has(t: str, *phrases: str) -> bool:
    return any(re.search(r'\b' + re.escape(p) + r'\b', t) for p in phrases)


def has_prefix(t: str, *stems: str) -> bool:
    return any(re.search(r'\b' + re.escape(s), t) for s in stems)


def is_question(raw: str, t: str) -> bool:
    return raw.strip().endswith('?') or bool(re.match(
        r'^(what|whats|why|how|hows|when|where|who|whos|which|is|are|can|could|do|does|did|should|would|will|explain|tell me what|define)\b', t))


_REFLECT = {
    'i': 'you', 'me': 'you', 'my': 'your', 'mine': 'yours', 'myself': 'yourself',
    'am': 'are', 'im': 'youre', 'ive': 'youve', 'id': 'youd', 'ill': 'youll',
    'was': 'was', 'we': 'you', 'us': 'you', 'our': 'your',
}
_CONTRACTIONS = {'youre': "you're", 'youve': "you've", 'youd': "you'd", 'youll': "you'll",
                 'dont': "don't", 'cant': "can't", 'didnt': "didn't", 'wont': "won't", 'isnt': "isn't",
                 'havent': "haven't", 'wasnt': "wasn't", 'doesnt': "doesn't"}


def reflect(t: str) -> Optional[str]:
    """Turn 'i have a test tomorrow' into 'you have a test tomorrow'."""
    words = words_of(t)
    while words and words[0] in ('yeah', 'yes', 'yea', 'well', 'so', 'and', 'but', 'ok', 'okay', 'um', 'uh', 'like', 'no', 'honestly', 'basically'):
        words = words[1:]
    if not 3 <= len(words) <= 14 or 'you' in words or 'your' in words:
        return None
    out = [_REFLECT.get(w, w) for w in words]
    out = [_CONTRACTIONS.get(w, w) for w in out]
    return ' '.join(out)


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------
CRISIS_PATTERNS = [
    r'\bkill(ing)? myself\b', r'\bsuicid', r'\bend (my life|it all)\b', r'\btake my (own )?life\b',
    r'\bwant(ed)? to die\b(?! laughing)', r'\bwish i (was|were) dead\b', r'\bbetter off dead\b',
    r'\bbetter off without me\b', r'\b(dont|do not) want to (be alive|live|exist|be here anymore|wake up)\b',
    r'\b(hurt|harm|cut|cutting) myself\b', r'\bself ?harm', r'\bno reason to live\b', r'\bnot worth living\b',
    r'\boverdose\b', r'\bcant go on anymore\b', r'\bdisappear forever\b', r'\bfeel(ing)? like dying\b',
    r'\bwant to be dead\b', r'\bwant it all to end\b',
]

GREETING_WORDS = ('hi', 'hii', 'hiii', 'hey', 'heyy', 'heyyy', 'hello', 'helo', 'yo', 'hiya', 'heya', 'sup', 'wassup',
                  'good morning', 'good afternoon', 'good evening', 'hey there', 'hi there')

EMOTION_KEYWORDS = [
    # (kind, phrases) checked in order; first match wins
    ('left_out', ['nobody cares', 'no one cares', 'noone cares', 'dont care about me', 'doesnt care about me',
                  'left out', 'excluded', 'nobody likes me', 'no one likes me', 'actually cares about me', 'dont matter']),
    ('conflict', ['argued', 'argument', 'had a fight', 'got into a fight', 'fought', 'fell out', 'yelled at me', 'shouted at me']),
    ('overwhelmed', ['overwhelmed', 'too much', 'so much to do', 'drowning', 'cant keep up', 'cant cope']),
    ('lonely', ['lonely', 'alone', 'isolated', 'no friends']),
    ('angry', ['angry', 'mad', 'furious', 'pissed', 'annoyed', 'frustrated', 'irritated', 'fed up', 'so done']),
    ('stressed', ['stressed', 'stress', 'pressure', 'burnt out', 'burned out', 'burnout']),
    ('worried', ['worried', 'anxious', 'nervous', 'scared', 'afraid', 'panicking', 'overthinking']),
    ('tired', ['tired', 'exhausted', 'drained', 'sleepy', 'no energy']),
    ('weak', ['weak', 'empty', 'numb', 'hopeless', 'useless', 'worthless']),
    ('hurt', ['hurt', 'betrayed', 'heartbroken', 'broke up', 'rejected']),
    ('bad_day', ['bad day', 'terrible day', 'awful day', 'worst day', 'horrible day', 'rough day', 'went terribly',
                 'went badly', 'went horribly', 'went wrong', 'went bad', 'went awful', 'terrible', 'awful', 'horrible', 'the worst', 'rough']),
    ('sad', ['sad', 'upset', 'feeling down', 'feel down', 'so down', 'feeling low', 'feel low', 'crying', 'miserable', 'unhappy', 'depressed', 'bad',
             'not good', 'not okay', 'not ok', 'not great', 'not fine', 'meh', 'life is a joke', 'life sucks']),
]
GOOD_NEWS = ['got selected', 'got in', 'got into', 'got accepted', 'got the job', 'got an offer', 'got the internship',
             'got promoted', 'i passed', 'passed my', 'passed the', 'aced', 'i won', 'we won', 'got an a', 'topped',
             'got a scholarship', 'got the part', 'finally did it', 'i did it', 'nailed it', 'it worked', 'said yes', 'got first']
POSITIVE = ['good day', 'great day', 'amazing', 'happy', 'excited', 'great', 'awesome', 'wonderful', 'fantastic',
            'fun', 'good', 'nice', 'lovely', 'relieved', 'grateful', 'better', 'chill', 'calm', 'peaceful', 'best day']
NEGATIONS = ['not', 'dont', 'didnt', 'isnt', 'wasnt', 'never', 'no', 'cant', 'couldnt', 'wont', 'havent', 'hasnt', 'arent', 'werent']

FEATURE_KEYS = [
    ('privacy', ['encrypt', 'privacy', 'private', 'my data', 'secure', 'safe to write', 'who can see', 'who can read']),
    ('reports', ['report', 'pdf', 'counselor', 'counsellor']),
    ('insights', ['insight', 'pattern', 'trend', 'theme', 'chart']),
    ('sentiment', ['sentiment', 'textblob']),
    ('reflection', ['reflection prompt', 'reflect prompt', 'reflection', 'cbt prompt']),
    ('journal', ['journal', 'entry', 'entries', 'mood check', 'check in', 'checkin']),
    ('mindy', ['what can you do', 'what do you do', 'how do you work', 'how does mindy']),
]

NUMBER_WORDS = {w: i for i, w in enumerate(
    'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen '
    'seventeen eighteen nineteen twenty'.split())}

SHORT_ACTIVITIES = {'riddle': 8, 'guess': 6, 'wyr': 12, 'question': 40, 'wordchain': 4, 'menu': 8, 'advice_or_listen': 10}


def detect_crisis(t: str) -> bool:
    return any(re.search(p, t) for p in CRISIS_PATTERNS)


def emotion_kind(t: str) -> Optional[str]:
    for kind, phrases in EMOTION_KEYWORDS:
        if has(t, *phrases):
            return kind
    # "not happy", "dont feel good" etc.
    if has(t, *NEGATIONS) and has(t, 'happy', 'good', 'great', 'okay', 'ok', 'fine', 'well'):
        return 'sad'
    return None


def extract_subject(t: str) -> Optional[str]:
    patterns = [
        r'\bmy (roommate|flatmate|friend group|best friend|friends|friend|mom|mum|dad|parents|sister|brother|boss|manager|teacher|professor|partner|boyfriend|girlfriend|bf|gf|crush)\b',
        r'\bmy (\w+) (?:went|was|is|got|has been|did)\b',
        r'\b(?:at|in|from) (college|school|uni|university|class|work|the office|home|practice)\b',
        r'\b(exam|test|presentation|interview|assignment|project|quiz|match|game|date|meeting)\b',
    ]
    for p in patterns:
        m = re.search(p, t)
        if m and m.group(1) not in ('day', 'life', 'mind', 'head', 'week'):
            return m.group(1)
    return None


JOKE_WORD = re.compile(r'\b(jokes?|joke[sy]?|joek\w*|jok|jokw|puns?|punny|knock ?knock)\b')
NOT_A_JOKE_REQUEST = re.compile(r'\b(is|was|are|its|feels like|such|what) a joke\b|\bno joke\b|\bnot a joke\b|\bjoke of\b|\bjoke is on\b'
                                r'|\b(that|the|this|your|last) (joke|pun)\b(?! again)|\b(not|wasnt|isnt) (funny|that funny)\b')
JOKE_REQUEST_WORDS = ('tell', 'another', 'give', 'say', 'know', 'got', 'hear', 'want', 'share', 'one', 'more', 'need',
                      'any', 'some', 'gimme', 'pls', 'please', 'favourite', 'favorite', 'best', 'have')
JOKE_TOPIC_FILLER = {'a', 'an', 'another', 'good', 'funny', 'me', 'the', 'some', 'one', 'any', 'more', 'quick', 'new',
                     'short', 'best', 'your', 'favourite', 'favorite', 'bad', 'great', 'nice', 'tell', 'give', 'got',
                     'know', 'hear', 'us', 'pls', 'please', 'my', 'of', 'gimme', 'cute', 'little', 'fun', 'cool', 'real',
                     'really', 'actual', 'different', 'other', 'okay', 'ok', 'say', 'share', 'want', 'need', 'have', 'something'}


def _joke_kind_for(topic: str) -> Optional[str]:
    for kind, keywords in C.JOKE_KIND_KEYWORDS:
        if has(topic, *keywords):
            return kind
    return None


def detect_joke_request(t: str, words: List[str]) -> Optional[dict]:
    """Return {'kind': ..., 'topic': ...} if the message asks for a joke, else None."""
    if has(t, 'make me laugh', 'say something funny', 'something funny', 'tell me something funny', 'cheer me up with a joke'):
        return {'kind': None, 'topic': None}
    if not JOKE_WORD.search(t) or NOT_A_JOKE_REQUEST.search(t):
        return None
    if not (has(t, *JOKE_REQUEST_WORDS) or len(words) <= 5 or re.search(r'\bjokes? (about|on|with)\b', t)):
        return None
    # Whole-phrase categories first ("dad joke" is a pun, not a family joke).
    for kind in ('knock', 'wordplay'):
        if has(t, *dict(C.JOKE_KIND_KEYWORDS)[kind]):
            return {'kind': kind, 'topic': None}
    # Only look at the words describing the joke: "a FOOD joke", "a joke about ANIMALS".
    topic_parts = []
    m = re.search(r'\b(?:jokes?|puns?|joek\w*|jok)\s+(?:about|on|with|related to|involving|for)\s+((?:\w+\s?){1,3})', t)
    if m:
        topic_parts.append(m.group(1))
    m = re.search(r'((?:\w+\s){0,2})(?:jokes?|puns?|joek\w*|jok)\b', t)
    if m:
        topic_parts.append(m.group(1))
    topic_words = [w for part in topic_parts for w in words_of(part) if w not in JOKE_TOPIC_FILLER]
    topic = ' '.join(topic_words)
    kind = _joke_kind_for(topic) if topic else None
    unknown = topic if topic and not kind and len(topic) <= 25 else None
    return {'kind': kind, 'topic': unknown}


def classify(raw: str, state: dict) -> Tuple[str, dict]:
    t = normalize(raw[:MAX_INPUT_CHARS])
    words = words_of(t)
    activity = state.get('activity') or {}

    if not words and not re.search(r'[\U0001F600-\U0001F64F\U0001F923]', raw):
        return 'empty', {}
    if detect_crisis(t):
        return 'crisis', {}

    if state.get('safety', 0) > 0:
        if has(t, 'im safe', 'i am safe', 'yes', 'yeah', 'yep', 'im okay', 'im ok', 'im fine', 'i will be okay',
               'ill be okay', 'i wont', 'just kidding', 'i was joking', 'safe'):
            return 'safety_ok', {}
        if has(t, 'no', 'not safe', 'im not', 'nope'):
            return 'crisis', {}

    # A greeting followed by something else: answer the something else.
    for g in sorted(GREETING_WORDS, key=len, reverse=True):
        m = re.match(r'^' + g + r'\b\s*(mindy)?\s*', t)
        if m:
            rest = t[m.end():].strip()
            if len(words_of(rest)) <= 1 and rest not in ('bored',):
                return 'greeting', {}
            intent, data = classify(rest, state)
            data = dict(data, greeted=True)
            return intent, data

    # --- Conversation controls -------------------------------------------
    if has(t, 'stop asking', 'no more questions', 'dont ask me', 'stop with the questions', 'quit asking', 'enough questions'):
        return 'stop_questions', {}
    if has(t, 'dont want advice', 'dont want solutions', 'no advice', 'no solutions', 'just listen', 'just want to talk',
           'just need to talk', 'need to vent', 'can i vent', 'let me vent', 'want to vent', 'just want to vent',
           'dont fix', 'dont try to fix', 'not looking for advice', 'just hear me out'):
        return 'listen_mode', {}
    if has(t, 'change the subject', 'distract me', 'something else', 'dont want to think about', 'dont want to talk about',
           'new topic', 'change topic', 'take my mind off'):
        return 'distract', {}
    if activity and has(t, 'stop', 'quit', 'enough', 'im done', 'end game', 'stop playing', 'no more'):
        if activity.get('type') not in ('question',) or len(words) <= 4:
            return 'stop_activity', {}

    if has(t, 'no jokes', 'no more jokes', 'stop joking', 'stop with the jokes', 'be serious', 'serious please',
           'not in the mood for jokes', 'not in the mood for a joke', 'dont joke', 'stop being funny', 'enough jokes'):
        return 'serious_mode', {}

    # --- Explicit requests -------------------------------------------------
    joke_request = detect_joke_request(t, words)
    if joke_request is not None:
        return 'joke', joke_request
    if has_prefix(t, 'riddle'):
        return 'riddle', {}
    if has(t, 'would you rather', 'wyr'):
        return 'game', {'game': 'wyr'}
    if has(t, 'guess the number', 'guessing game', 'number game', 'guess a number'):
        return 'game', {'game': 'guess'}
    if has(t, 'word chain', 'word game', 'word association'):
        return 'game', {'game': 'wordchain'}
    if has(t, 'play a game', 'lets play', 'play something', 'play with me', 'wanna play', 'want to play') or t in ('game', 'a game', 'games'):
        return 'game', {'game': None}
    if has(t, 'hypothetical', 'ask me something', 'ask me a question', 'random question', 'ask me anything', 'question for me'):
        return 'question', {'kind': 'hypo' if 'hypothetical' in t else 'fun'}
    if has(t, 'fun fact', 'random fact', 'tell me a fact', 'interesting fact', 'tell me something interesting'):
        return 'fact', {}
    if has(t, 'motivate me', 'motivation', 'encourage me', 'hype me up', 'cheer me up', 'say something nice', 'wish me luck',
           'i need encouragement', 'pep talk', 'believe in me', 'i cant do this', 'i can not do this'):
        return 'encourage', {}
    if has(t, 'im bored', 'i am bored', 'so bored', 'bored', 'nothing to do', 'entertain me'):
        return 'bored', {}
    if has(t, 'how have i been', 'how ive been', 'my mood lately', 'my moods lately', 'my mood recently', 'mood trend',
           'my mood this week', 'how was my week', 'my recent moods', 'how am i doing lately'):
        return 'mood_summary', {}
    if re.search(r'\bare you (a |an )?(real|actual )?(human|person|bot|ai|robot|real)\b', t) or has(t, 'who are you', 'what are you', 'are you real', 'are you human', 'are you a bot', 'are you ai', 'are you an ai',
           'are you a robot', 'your name', 'tell me about yourself', 'are you a person', 'are you chatgpt'):
        return 'about', {}
    m = re.search(r'\b(?:whats|what is|what are|do you have a) your (?:favou?rite|fav|fave) (\w+(?: \w+)?)', t)
    if m:
        return 'opinion', {'kind': 'favourite', 'thing': m.group(1)}
    m = re.search(r'\b(?:do you (?:like|love|enjoy|play|watch|eat)) (\w+(?: \w+){0,2})', t)
    if m:
        return 'opinion', {'kind': 'like', 'thing': m.group(1)}
    m = re.search(r'\bhave you ever (\w+(?: \w+){0,4})', t)
    if m:
        return 'opinion', {'kind': 'ever', 'thing': m.group(1)}
    m = re.search(r'\bwhat should i (eat|watch|read|listen to|do tonight|do today|do this weekend|cook)\b', t)
    if m:
        return 'suggest', {'what': m.group(1).split()[0]}
    if has(t, 'how are you', 'how r u', 'how are u', 'hows it going', 'how you doing', 'how are you doing', 'wbu',
           'what about you', 'and you', 'how about you', 'how is your day', 'hows your day'):
        return 'how_are_you', {}

    # Mindy's own features ("is my data private?", "how do reports work?")
    if is_question(raw, t) or has(t, 'what can you do', 'explain', 'tell me about'):
        for key, kws in FEATURE_KEYS:
            if has_prefix(t, *kws) and (key != 'journal' or has(t, 'mindtrack', 'how do i', 'how does', 'how to', 'what is', 'where')):
                if key in ('insights',) and not has(t, 'mindtrack', 'insight', 'page', 'work', 'what'):
                    continue
                return 'feature', {'key': key}
        if has(t, 'mindtrack'):
            return 'feature', {'key': 'mindy' if has(t, 'you') else 'journal'}

    # General knowledge we can answer reliably
    wordset = set(words)
    if is_question(raw, t) or has(t, 'explain', 'difference', 'meaning of', 'define'):
        for keys, answer in C.KNOWLEDGE:
            if keys <= wordset:
                return 'knowledge', {'answer': answer}
    if re.fullmatch(r'(what is |whats |calculate |solve )?[\d\s+\-*/x().]+\??', t) and re.search(r'\d\s*[+\-*/x]\s*\d', t):
        return 'math', {'expr': t}

    advice_asked = has(t, 'what should i do', 'any advice', 'give me advice', 'need advice', 'your advice', 'advice',
                       'what do i do', 'what would you do', 'how do i deal', 'how do i handle', 'how can i deal', 'how do i stop',
                       'how do i get', 'how can i stop', 'how can i get', 'how do i talk', 'should i', 'any tips', 'tips',
                       'what can i do', 'help me think', 'think something through', 'honest take', 'your take',
                       'what do you think i should', 'how to deal', 'how to handle', 'how to stop')
    if advice_asked:
        return 'advice', {}

    # --- Follow-ups that depend on the current activity -------------------
    act_type = activity.get('type')
    if has(t, 'another', 'one more', 'again', 'next', 'more', 'another one', 'keep going', 'hit me', 'go on') and len(words) <= 5:
        target = act_type or state.get('offer')
        if target or t in ('another', 'another one', 'one more', 'again', 'more'):
            return 'another', {'target': target}
    if act_type == 'joke' or state.get('last_intent') == 'joke':
        if has(t, 'bad', 'lame', 'not funny', 'wasnt funny', 'isnt funny', 'not that funny', 'didnt laugh', 'try again', 'terrible', 'corny', 'cringe', 'boo', 'awful', 'dry', 'mid', 'worst', 'unfunny', 'meh'):
            return 'joke_bad', {}
        if has(t, 'lol', 'lmao', 'haha', 'hahaha', 'funny', 'good one', 'hilarious', 'lmfao', 'rofl', 'nice one') or '😂' in raw or '🤣' in raw:
            return 'joke_good', {}
        if has(t, 'dont get it', 'i dont understand', 'what does that mean', 'explain'):
            return 'joke_explain', {}
    if act_type in SHORT_ACTIVITIES and len(words) <= SHORT_ACTIVITIES[act_type]:
        return 'activity_input', {}
    if state.get('offer') and has(t, 'yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'go on', 'go ahead', 'please', 'yess', 'ya', 'yup', 'why not', 'of course') and len(words) <= 4:
        return 'accept_offer', {'target': state['offer']}
    if state.get('offer') and has(t, 'no', 'nope', 'nah', 'no thanks', 'not now', 'im good') and len(words) <= 4:
        return 'decline_offer', {}

    # --- Social basics -----------------------------------------------------
    if has(t, 'bye', 'goodbye', 'good night', 'goodnight', 'gn', 'gtg', 'got to go', 'gotta go', 'see you', 'see ya',
           'talk later', 'talk to you later', 'see you later', 'ttyl', 'cya', 'night night'):
        return 'farewell', {}
    if has(t, 'thanks', 'thank you', 'thank u', 'thx', 'ty', 'tysm', 'appreciate it') and len(words) <= 8:
        return 'thanks', {}
    if re.search(r'\b(youre|you are|ur) (so )?(funny|sweet|the best|nice|cute|amazing|awesome|kind|great|cool|lovely|helpful)\b', t) \
            or has(t, 'love you mindy', 'i love you', 'love u', 'you rock'):
        return 'compliment', {}
    if len(words) <= 8 and has(t, 'lol', 'lmao', 'haha', 'hahaha', 'lmfao'):
        return 'laugh', {}
    if re.fullmatch(r'((ha)+h?|(he)+h?|lol+|lmao+|lmfao|rofl|xd)( (ha)+h?| lol+| lmao+)*', t) or (not words and ('😂' in raw or '🤣' in raw)):
        return 'laugh', {}

    # --- Feelings and news -----------------------------------------------
    if has(t, *GOOD_NEWS) or (has(t, 'finally') and has(t, 'got', 'did', 'passed', 'selected', 'finished')):
        return 'good_news', {}
    if has(t, 'proud of myself', 'im proud', 'i am proud', 'feeling proud'):
        return 'proud', {}
    if has(t, 'not bad', 'not too bad', 'not that bad'):
        return 'positive', {}
    topic = detect_topic(t)
    if topic:
        return 'topic', topic
    kind = emotion_kind(t)
    if kind:
        return 'emotion', {'kind': kind, 'subject': extract_subject(t)}
    if has(t, *POSITIVE) and not has(t, *NEGATIONS):
        return 'positive', {}

    # --- Short replies that depend on the topic ---------------------------
    if t in ('yes', 'yeah', 'yep', 'yup', 'exactly', 'true', 'right', 'ikr', 'definitely', 'totally', 'same', 'for real',
             'fr', 'literally', 'yes exactly', 'exactly that', 'thats it', 'yess', 'ya', 'mhm', 'yeah exactly', 'right exactly'):
        return 'agree', {}
    if t in ('no', 'nope', 'nah', 'not really', 'no not really', 'not exactly', 'i dont think so', 'idk', 'i dont know', 'dunno'):
        return 'disagree', {}
    if t in ('why', 'why?', 'what do you mean', 'what', 'huh', 'how so', 'meaning', 'tell me more', 'continue', 'go on', 'and'):
        return 'clarify_followup', {}

    if is_question(raw, t):
        return 'unknown_question', {}
    return 'statement', {'subject': extract_subject(t)}


# ---------------------------------------------------------------------------
# Activities: jokes, riddles, games
# ---------------------------------------------------------------------------
ALL_JOKES = [(k, j) for k, js in C.JOKES.items() for j in js]
JOKE_INDEX = {j: i for i, (_, j) in enumerate(ALL_JOKES)}


def tell_joke(state, kind=None, prefix=None, avoid_kind=None, closer=None):
    """Tell a joke from `kind`, or a varied mix for a general request.

    General requests draw from everyday categories (not tech/dark/knock-knock),
    lean toward categories the user has enjoyed this conversation, and every
    joke told is remembered so nothing repeats until a category runs out.
    """
    if kind in C.JOKES:
        kinds = [kind]
    else:
        kinds = list(C.DEFAULT_JOKE_KINDS)
        likes = {k: v for k, v in (state.get('joke_likes') or {}).items() if v > 0 and k in C.JOKES}
        if likes and random.random() < 0.5:
            kinds = [max(likes, key=likes.get)]
        disliked = [k for k, v in (state.get('joke_likes') or {}).items() if v < 0]
        kinds = [k for k in kinds if k != avoid_kind and k not in disliked] or kinds

    seen = [i for i in state['used'].get('jokes', []) if isinstance(i, int)]
    candidates = [JOKE_INDEX[j] for k in kinds for j in C.JOKES[k] if JOKE_INDEX[j] not in seen]
    if not candidates:
        # Everything in these categories has been told: start them over, minus the latest joke.
        in_kinds = {JOKE_INDEX[j] for k in kinds for j in C.JOKES[k]}
        seen = [i for i in seen if i not in in_kinds or i == (seen[-1] if seen else None)]
        candidates = [i for i in in_kinds if i not in seen] or list(in_kinds)
    idx = random.choice(candidates)
    state['used']['jokes'] = (seen + [idx])[-80:]
    told_kind, joke = ALL_JOKES[idx]
    state['last_joke_kind'] = told_kind

    if prefix is None:
        _, prefix = pick(state, 'joke_opener', C.JOKE_OPENERS)
    if closer is None:
        _, closer = pick(state, 'joke_closer', C.JOKE_CLOSERS)
    state['activity'] = {'type': 'joke', 'kind': kind if kind in C.JOKES else None}
    state['offer'] = 'joke'
    return f"{prefix}{joke}{closer}".strip()


def start_riddle(state, prefix=''):
    idx, (question, _, _, _) = pick(state, 'riddle', C.RIDDLES)
    state['activity'] = {'type': 'riddle', 'idx': idx, 'tries': 0}
    state['offer'] = None
    return f"{prefix}Okay, riddle time 🤔 {question}"


def start_wyr(state, prefix=''):
    idx, (a, b) = pick(state, 'wyr', C.WOULD_YOU_RATHER)
    state['activity'] = {'type': 'wyr', 'idx': idx}
    state['offer'] = None
    return f"{prefix}Would you rather {a}, or {b}?"


def start_guess(state, prefix=''):
    state['activity'] = {'type': 'guess', 'n': random.randint(1, 20), 'tries': 0}
    state['offer'] = None
    return f"{prefix}Okay! I'm thinking of a number between 1 and 20. Take a guess 👀"


def start_wordchain(state, prefix=''):
    _, word = pick(state, 'wordchain', [w for ws in C.WORD_BANK.values() for w in ws])
    state['activity'] = {'type': 'wordchain', 'last': word, 'seen': [word], 'score': 0}
    state['offer'] = None
    return (f"{prefix}Word chain! I say a word, you reply with a word that starts with its last letter, and so on. "
            f"I'll start: **{word}**. Your word starts with '{word[-1]}'.").replace('**', '')


def start_question(state, kind='fun', prefix=''):
    pool = C.HYPOTHETICALS if kind == 'hypo' else C.FUN_QUESTIONS
    _, q = pick(state, 'q:' + kind, pool)
    state['activity'] = {'type': 'question', 'kind': kind}
    state['offer'] = None
    return f"{prefix}{q}"


def tell_fact(state, prefix=''):
    _, fact = pick(state, 'fact', C.FUN_FACTS)
    state['activity'] = {'type': 'fact'}
    state['offer'] = 'fact'
    return f"{prefix}Fun fact: {fact} Want another?"


GAME_MENU = "Ooh, yes. Pick one: would you rather, a number guessing game, or word chain?"


def start_activity(state, target, prefix=''):
    starters = {
        'joke': lambda: tell_joke(state, prefix=prefix or None),
        'riddle': lambda: start_riddle(state, prefix),
        'wyr': lambda: start_wyr(state, prefix),
        'guess': lambda: start_guess(state, prefix),
        'wordchain': lambda: start_wordchain(state, prefix),
        'question': lambda: start_question(state, 'fun', prefix),
        'hypo': lambda: start_question(state, 'hypo', prefix),
        'fact': lambda: tell_fact(state, prefix),
    }
    if target in starters:
        return starters[target]()
    state['activity'] = {'type': 'menu', 'options': ['wyr', 'guess', 'wordchain']}
    state['offer'] = None
    return prefix + GAME_MENU


MENU_CHOICES = [
    ('joke', ['joke', 'jokes', 'funny']),
    ('riddle', ['riddle', 'riddles']),
    ('wyr', ['would you rather', 'rather', 'wyr']),
    ('guess', ['guess', 'guessing', 'number']),
    ('wordchain', ['word chain', 'word', 'chain', 'words']),
    ('hypo', ['hypothetical', 'ridiculous', 'weird', 'scenario']),
    ('fact', ['fact', 'facts']),
    ('game', ['game', 'play', 'games']),
]


def handle_menu(state, t):
    options = state['activity'].get('options') or []
    choice = None
    for name, kws in MENU_CHOICES:
        if has(t, *kws):
            choice = name
            break
    if choice is None:
        m = re.search(r'\b(1|2|3|first|second|third|one|two|three|last)\b', t)
        if m and options:
            pos = {'1': 0, 'first': 0, 'one': 0, '2': 1, 'second': 1, 'two': 1, '3': 2, 'third': 2, 'three': 2, 'last': -1}[m.group(1)]
            if -len(options) <= pos < len(options):
                choice = options[pos]
    if choice is None:
        if has(t, 'you pick', 'you choose', 'surprise me', 'anything', 'whatever', 'idk', 'any'):
            choice = random.choice(options or ['joke'])
        else:
            labels = {'joke': 'a joke', 'riddle': 'a riddle', 'game': 'a game', 'wyr': 'would you rather',
                      'guess': 'the guessing game', 'wordchain': 'word chain', 'hypo': 'a hypothetical', 'fact': 'a fun fact'}
            return "Haha pick one! " + ', '.join(labels.get(o, o) for o in options) + '?'
    if choice == 'game':
        return start_activity(state, None)
    return start_activity(state, choice, prefix='Yay! ' if choice != 'joke' else '')


def handle_riddle_input(state, t):
    act = state['activity']
    question, answers, answer_text, hint = C.RIDDLES[act['idx']]
    if has(t, 'hint', 'clue', 'help'):
        return f"Hint: {hint}"
    if has(t, 'give up', 'i give up', 'tell me', 'answer', 'idk', 'i dont know', 'no idea', 'reveal', 'what is it', 'whats the answer', 'what is the answer'):
        state['activity'] = None
        state['offer'] = 'riddle'
        return f"It's {answer_text[0].lower()}{answer_text[1:]} Want another one?"
    if any(re.search(r'\b' + re.escape(a), t) for a in answers):
        state['activity'] = None
        state['offer'] = 'riddle'
        _, praise = pick(state, 'riddle_right', C.RIDDLE_RIGHT)
        return praise
    act['tries'] = act.get('tries', 0) + 1
    if act['tries'] >= 3:
        return f"Nope! Okay, here's a hint: {hint} Or say 'I give up' and I'll tell you."
    _, wrong = pick(state, 'riddle_wrong', C.RIDDLE_WRONG)
    return wrong


def parse_number(t):
    m = re.search(r'-?\d+', t)
    if m:
        return int(m.group())
    for w in words_of(t):
        if w in NUMBER_WORDS:
            return NUMBER_WORDS[w]
    return None


def handle_guess_input(state, t):
    act = state['activity']
    if has(t, 'give up', 'i give up', 'tell me', 'reveal'):
        state['activity'] = None
        state['offer'] = 'guess'
        return f"It was {act['n']}! Want to play again?"
    n = parse_number(t)
    if n is None:
        return "Just send me a number between 1 and 20! (Or say 'I give up'.)"
    act['tries'] = act.get('tries', 0) + 1
    if n == act['n']:
        tries = act['tries']
        state['activity'] = None
        state['offer'] = 'guess'
        return f"YES! It was {n}! You got it in {tries} {'try' if tries == 1 else 'tries'} 🎉 Play again?"
    if not 1 <= n <= 20:
        return "Ha, nice try, but it's between 1 and 20!"
    hint = 'Higher! ⬆️' if n < act['n'] else 'Lower! ⬇️'
    if act['tries'] >= 3 and abs(n - act['n']) <= 2:
        hint += " You're super close."
    return hint


def handle_wyr_input(state, t):
    a, b = C.WOULD_YOU_RATHER[state['activity']['idx']]
    key_a = [w for w in words_of(a) if len(w) > 3][:2]
    key_b = [w for w in words_of(b) if len(w) > 3][:2]
    if has(t, 'first', '1', 'the first', 'option a', 'a', 'former') or (key_a and has(t, *key_a) and not has(t, *key_b)):
        side = 'a'
    elif has(t, 'second', '2', 'the second', 'option b', 'b', 'latter') or (key_b and has(t, *key_b)):
        side = 'b'
    else:
        side = 'other'
    _, reaction = pick(state, 'wyr_react_' + side, C.WYR_REACTIONS[side])
    reaction = reaction.format(a=a[0].upper() + a[1:], b=b[0].upper() + b[1:])
    state['activity'] = None
    state['offer'] = 'wyr'
    return reaction + " Want another one?"


def handle_wordchain_input(state, t):
    act = state['activity']
    w = words_of(t)
    if not w:
        return f"Your word needs to start with '{act['last'][-1]}'!"
    word = w[0]
    if word[0] != act['last'][-1]:
        return f"Ooh, it has to start with '{act['last'][-1]}'! Try again 😄"
    if word in act.get('seen', []):
        return "Ha, that one's been used already! Try another."
    act.setdefault('seen', []).append(word)
    act['score'] = act.get('score', 0) + 1
    letter = word[-1]
    options = [x for x in C.WORD_BANK.get(letter, []) if x not in act['seen']]
    if not options:
        state['activity'] = None
        state['offer'] = 'wordchain'
        return f"Okay, you got me, I'm out of '{letter}' words! You win this round 🏆 ({act['score']} words). Again?"
    reply = random.choice(options)
    act['seen'].append(reply)
    act['seen'] = act['seen'][-30:]
    act['last'] = reply
    return f"{word[0].upper() + word[1:]}, nice! Mine: {reply}. Your turn, '{reply[-1]}'."


def handle_question_answer(state, raw, t):
    state['activity'] = None
    state['offer'] = 'question'
    _, reaction = pick(state, 'q_react', C.QUESTION_REACTIONS)
    return f"{reaction} Want another question?"


def handle_advice_or_listen(state, raw, t, ctx):
    state['activity'] = None
    if has(t, 'listen', 'vent', 'just talk', 'no advice', 'dont need advice', 'get it out'):
        return h_listen_mode(state, raw, t, {}, ctx)
    if has(t, 'advice', 'take', 'tell me', 'yes', 'yeah', 'sure', 'please', 'help', 'what should', 'honest'):
        return give_advice(state, (state.get('topic') or {}).get('text', '') + ' ' + t)
    return None  # not an answer; continue as a normal message


def h_activity_input(state, raw, t, data, ctx):
    act_type = state['activity']['type']
    if act_type == 'riddle':
        return handle_riddle_input(state, t)
    if act_type == 'guess':
        return handle_guess_input(state, t)
    if act_type == 'wyr':
        return handle_wyr_input(state, t)
    if act_type == 'wordchain':
        return handle_wordchain_input(state, t)
    if act_type == 'question':
        return handle_question_answer(state, raw, t)
    if act_type == 'menu':
        return handle_menu(state, t)
    if act_type == 'advice_or_listen':
        reply = handle_advice_or_listen(state, raw, t, ctx)
        if reply:
            return reply
        intent, data = classify(raw, state)
        return HANDLERS.get(intent, h_statement)(state, raw, t, data, ctx)
    return h_statement(state, raw, t, {}, ctx)


# ---------------------------------------------------------------------------
# Advice
# ---------------------------------------------------------------------------
def give_advice(state, text):
    t = normalize(text)
    mentioned = detect_topic(t)
    topic_id = (mentioned or {}).get('id') or (state.get('topic') or {}).get('id')
    if topic_id and T.TOPIC_BY_ID[topic_id].get('tips'):
        topic_def = T.TOPIC_BY_ID[topic_id]
        state['no_advice'] = False
        if (state.get('topic') or {}).get('id') != topic_id:
            state['topic'] = {'id': topic_id, 'kind': topic_def['valence'], 'subject': topic_def['ref'],
                              'text': text[:300], 'turns': 1, 'asked': []}
        return topic_def['tips'] + ask(state, _topic_question(state, topic_def))
    for keywords, advice, follow_up in C.ADVICE:
        if has_prefix(t, *keywords):
            break
    else:
        if len(words_of(t)) < 6 and not state.get('topic'):
            state['offer'] = None
            return "Of course, I'm in. What's the situation? Give me the details and I'll tell you what I honestly think."
        _, (advice, follow_up) = pick(state, 'general_advice', C.GENERAL_ADVICE)
    state['no_advice'] = False
    lead = "That sounds frustrating. " if has(t, 'ignor', 'annoy', 'frustrat', 'mad', 'angry', 'unfair') else ''
    return f"{lead}{advice}{ask(state, follow_up)}"


# ---------------------------------------------------------------------------
# Intent handlers. Signature: (state, raw, t, data, ctx) -> reply
# ---------------------------------------------------------------------------
def h_empty(state, raw, t, data, ctx):
    return "Hm, I didn't catch anything there. What's up?"


def h_crisis(state, raw, t, data, ctx):
    state['activity'] = None
    state['offer'] = None
    already = state.get('safety', 0) > 0
    state['safety'] = 4
    return C.SAFETY_FOLLOWUP if already and state.get('last_intent') == 'crisis' else SAFETY_MESSAGE


def h_safety_ok(state, raw, t, data, ctx):
    state['safety'] = 0
    _, reply = pick(state, 'safety_ok', C.SAFETY_RELIEVED)
    return reply


def h_greeting(state, raw, t, data, ctx):
    _, reply = pick(state, 'greeting', C.GREETING_REPLIES)
    return reply


def h_how_are_you(state, raw, t, data, ctx):
    _, reply = pick(state, 'how_are_you', C.HOW_ARE_YOU)
    return reply


def h_about(state, raw, t, data, ctx):
    if has(t, 'real', 'human', 'person', 'bot', 'ai', 'robot', 'chatgpt'):
        return ("Honest answer: I'm not a human. I'm Mindy, a little companion built into MindTrack. I run on simple "
                "built-in logic, not a big online AI, so I won't always get everything. But I'm a good listener and "
                "I know a lot of bad jokes 😄")
    return C.FEATURE_INFO['mindy']


def h_feature(state, raw, t, data, ctx):
    return C.FEATURE_INFO.get(data.get('key'), C.FEATURE_INFO['mindy'])


def h_knowledge(state, raw, t, data, ctx):
    return data['answer']


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError('unsupported')


def h_math(state, raw, t, data, ctx):
    expr = re.sub(r'^(what is|whats|calculate|solve)\s*', '', data['expr']).replace('x', '*').rstrip('?. ')
    if len(expr) > 60:
        return "That's a bit long for me to do in my head 😅"
    try:
        value = _safe_eval(ast.parse(expr, mode='eval'))
    except ZeroDivisionError:
        return "Dividing by zero? Not even I can do that 😄"
    except Exception:
        return "Hmm, I couldn't work that one out. Can you write it like 12 * 4?"
    if isinstance(value, float):
        value = round(value, 4)
        if value == int(value):
            value = int(value)
    return f"That's {value}."


def h_joke(state, raw, t, data, ctx):
    state['serious'] = False  # asking for a joke ends "serious mode"
    kind = data.get('kind')
    activity = state.get('activity') or {}
    if kind is None and has(t, 'another', 'one more', 'more') and activity.get('type') == 'joke':
        kind = activity.get('kind')  # "another joke" keeps the current category
    if kind == 'dark' and state.get('safety', 0) > 0:
        kind = None  # not after someone has just shared something heavy
    prefix = None
    if kind == 'dark':
        prefix = random.choice(["Okay, keeping it on the lighter side of dark: ", "Mildly dark, nobody gets hurt: "])
    elif data.get('topic'):
        # Be honest when there's no joke on that exact topic.
        prefix = f"I don't have a {data['topic']} joke yet, so here's something else: "
    return tell_joke(state, kind, prefix=prefix)


def h_riddle(state, raw, t, data, ctx):
    return start_riddle(state)


def h_game(state, raw, t, data, ctx):
    return start_activity(state, data.get('game'))


def h_question(state, raw, t, data, ctx):
    return start_question(state, data.get('kind', 'fun'))


def h_fact(state, raw, t, data, ctx):
    return tell_fact(state)


def h_another(state, raw, t, data, ctx):
    target = data.get('target')
    if target == 'joke':
        return tell_joke(state, (state.get('activity') or {}).get('kind'), prefix=random.choice(["Okay, another! ", "Here's one more: ", "Alright: ", ""]))
    if target in ('riddle', 'wyr', 'guess', 'wordchain', 'fact'):
        return start_activity(state, target)
    if target == 'question':
        return start_question(state, 'fun')
    return "Another what? A joke, a riddle, or a game? 😄"


def h_accept_offer(state, raw, t, data, ctx):
    return h_another(state, raw, t, data, ctx)


def h_decline_offer(state, raw, t, data, ctx):
    state['offer'] = None
    state['activity'] = None
    return random.choice(["No worries! What do you feel like doing instead?", "Okay! What's on your mind?", "Fair enough 😄 So, what's up?"])


def _rate_last_joke(state, delta):
    last = state.get('last_joke_kind')
    if last:
        likes = state.setdefault('joke_likes', {})
        likes[last] = max(-3, min(5, likes.get(last, 0) + delta))
    return last


def h_joke_bad(state, raw, t, data, ctx):
    # Try a different style: switch away from the category that didn't land.
    last = _rate_last_joke(state, -1)
    _, prefix = pick(state, 'joke_bad', C.JOKE_BAD_FEEDBACK)
    return tell_joke(state, None, prefix=prefix, avoid_kind=last, closer='')


def h_joke_good(state, raw, t, data, ctx):
    last = _rate_last_joke(state, +1)
    _, reply = pick(state, 'joke_good', C.JOKE_GOOD_FEEDBACK)
    if last and state['joke_likes'].get(last, 0) >= 2 and last in C.JOKE_KIND_NAMES:
        reply = f"Okay, you're clearly a fan of {C.JOKE_KIND_NAMES[last]} jokes. Noted 😄 Want another?"
    state['offer'] = 'joke'
    return reply


def h_serious_mode(state, raw, t, data, ctx):
    state['serious'] = True
    state['activity'] = None
    state['offer'] = None
    return "Got it, no jokes. I'm here, and we can keep it straightforward. What's on your mind?"


def h_joke_explain(state, raw, t, data, ctx):
    state['offer'] = 'joke'
    return "Haha, it's a pun, it's playing on a word with two meanings. Admittedly, explaining it makes it way less funny 😅 Want a different one?"


def h_stop_activity(state, raw, t, data, ctx):
    act = state.get('activity') or {}
    state['activity'] = None
    state['offer'] = None
    extra = f" (It was {act['n']}, by the way.)" if act.get('type') == 'guess' else ''
    return f"Okay, game over!{extra} That was fun. What do you want to talk about?"


def h_bored(state, raw, t, data, ctx):
    _, reply = pick(state, 'bored', C.BORED_REPLIES)
    state['activity'] = {'type': 'menu', 'options': ['joke', 'riddle', 'game']}
    state['offer'] = None
    return reply


def h_distract(state, raw, t, data, ctx):
    state['topic'] = None
    idx, reply = pick(state, 'distract', C.DISTRACT_REPLIES)
    options = [['hypo', 'guess'], ['riddle', 'hypo', 'fact'], ['joke', 'riddle', 'guess']][idx]
    state['activity'] = {'type': 'menu', 'options': options}
    state['offer'] = None
    return reply


def h_listen_mode(state, raw, t, data, ctx):
    state['no_advice'] = True
    state['asked_pref'] = True
    state['activity'] = None
    _, reply = pick(state, 'listen', C.LISTEN_MODE_REPLIES)
    # If they already started telling us something, respond to that too.
    rest = re.sub(r'.*(just listen|just want to talk|need to vent|let me vent|want to vent|no advice|no solutions|dont want advice|dont want solutions)\b', '', t).strip()
    if len(words_of(rest)) >= 3:
        lead = random.choice(["Of course, I'm listening.", "Totally, no fixing mode.", "I'm here, just listening."])
        topic = detect_topic(rest)
        if topic:
            return lead + ' ' + h_topic(state, raw, rest, topic, ctx)
        return lead + ' ' + h_statement(state, raw, rest, {'subject': extract_subject(rest)}, ctx)
    return reply


def h_stop_questions(state, raw, t, data, ctx):
    state['no_questions'] = True
    _, reply = pick(state, 'stop_q', C.STOP_QUESTIONS_REPLIES)
    return reply


def h_encourage(state, raw, t, data, ctx):
    _, reply = pick(state, 'encourage', C.ENCOURAGEMENT)
    return reply


def h_farewell(state, raw, t, data, ctx):
    state['activity'] = None
    state['offer'] = None
    _, reply = pick(state, 'farewell', C.FAREWELLS)
    return reply


def h_thanks(state, raw, t, data, ctx):
    _, reply = pick(state, 'thanks', C.THANKS_REPLIES)
    return reply


def h_compliment(state, raw, t, data, ctx):
    _, reply = pick(state, 'compliment', C.COMPLIMENT_REPLIES)
    return reply


def h_laugh(state, raw, t, data, ctx):
    _, reply = pick(state, 'laugh', C.LAUGH_REPLIES)
    return reply


def h_good_news(state, raw, t, data, ctx):
    state['topic'] = {'kind': 'good', 'subject': extract_subject(t), 'text': raw[:300], 'turns': 0, 'asked': []}
    topic = detect_topic(t)
    if topic:
        # Celebrate, but remember what it was about ("finished my assignment")
        # so the next messages stay on it.
        topic_def = T.TOPIC_BY_ID[topic['id']]
        state['topic'].update({'id': topic['id'], 'subject': topic_def['ref']})
    _, reply = pick(state, 'celebrate', C.CELEBRATE)
    return reply


def h_proud(state, raw, t, data, ctx):
    _, reply = pick(state, 'proud', C.PROUD_REPLIES)
    return reply


def h_positive(state, raw, t, data, ctx):
    state['topic'] = {'kind': 'good', 'subject': extract_subject(t), 'text': raw[:300], 'turns': 0, 'asked': []}
    _, reply = pick(state, 'positive', C.POSITIVE_REPLIES)
    return reply


EVENT_BAD = [
    "Oh no :( What happened? Did something go wrong during the {s}, or does it just feel like it didn't go as well as you hoped?",
    "Ugh, I'm sorry. What happened with the {s}?",
]


def h_emotion(state, raw, t, data, ctx):
    kind = data.get('kind') or 'sad'
    subject = data.get('subject')
    topic = state.get('topic')
    continuing = bool(topic and topic.get('kind') not in ('good',) and topic.get('turns', 0) < 6)
    if continuing:
        if subject and not topic.get('subject'):
            topic['subject'] = subject
        return h_statement(state, raw, t, {'subject': subject}, ctx, from_emotion=kind)

    state['topic'] = {'kind': kind, 'subject': subject, 'text': raw[:300], 'turns': 0, 'asked': []}
    if state.get('safety', 0) > 0:
        return "That sounds really heavy, and I'm here. Please also reach out to someone you trust today, you deserve real support with this."
    if kind == 'bad_day' and subject and subject not in ('college', 'school', 'uni', 'university', 'class', 'work', 'the office', 'home'):
        _, reply = pick(state, 'event_bad', EVENT_BAD)
        reply = reply.format(s=subject)
    elif kind == 'left_out':
        reply = ("Ouch, that can really hurt, especially when it's people you want to feel close to."
                 + ask(state, "Did something happen today that made you feel this way?"))
    elif kind == 'conflict':
        reply = random.choice(["Oh no, what happened?", "Ugh, fights are the worst. What was it about?", "Oof. What happened?"])
        if subject in ('roommate', 'flatmate', 'mom', 'mum', 'dad', 'parents', 'sister', 'brother', 'best friend', 'friend', 'partner', 'boyfriend', 'girlfriend'):
            reply = random.choice([f"Oh no, with your {subject}? What happened?", "Oh no, what happened?"])
    else:
        _, reply = pick(state, 'emo:' + kind, C.EMOTION_REPLIES.get(kind, C.EMOTION_REPLIES['sad']))
    if state.get('no_questions'):
        reply = strip_questions(reply) or random.choice(C.LISTENING)
    return reply


def strip_questions(text: str) -> str:
    parts = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(p for p in parts if not p.rstrip().endswith('?')).strip()


TOPIC_QUESTIONS = [
    "How are you feeling about it now?",
    "Has this happened before, or is it new?",
    "What's bugging you most about it?",
    "Do you think there's something else underneath it?",
    "Did anything help, even a little?",
]


def next_topic_question(state):
    topic = state.get('topic') or {}
    asked = topic.setdefault('asked', [])
    remaining = [i for i in range(len(TOPIC_QUESTIONS)) if i not in asked]
    if not remaining:
        return ''
    i = remaining[0]
    asked.append(i)
    return TOPIC_QUESTIONS[i]


def h_statement(state, raw, t, data, ctx, from_emotion=None):
    topic = state.get('topic')
    in_topic = bool(topic and topic.get('turns', 0) < 8)

    if state.get('safety', 0) > 0:
        return "I hear you. " + C.SAFETY_FOLLOWUP

    # Specific reactions to details people share ("I forgot half my speech").
    for keywords, reactions, follow_ups in C.DETAIL_REACTIONS:
        if has(t, *keywords):  # whole words: "lately" must not match "late"
            if not topic:
                state['topic'] = topic = {'kind': from_emotion or 'event', 'subject': data.get('subject'), 'text': '', 'turns': 0, 'asked': []}
            topic['text'] = (topic.get('text', '') + ' ' + raw)[-300:]
            topic['turns'] = topic.get('turns', 0) + 1
            return random.choice(reactions) + maybe_offer_help(state) if (topic['turns'] >= 2 and not state['asked_pref']) \
                else random.choice(reactions) + ask(state, random.choice(follow_ups))

    if in_topic:
        topic['text'] = (topic.get('text', '') + ' ' + raw)[-300:]
        topic['turns'] = topic.get('turns', 0) + 1
        if topic.get('kind') == 'good':
            return random.choice(["Ahh, I love that!", "That's so good.", "Okay, that's honestly great."]) + ask(state, random.choice(["What happens next?", "How did that feel?", "Tell me more!"]))
        if topic.get('kind') == 'neutral':
            _, casual = pick(state, 'casual', CASUAL)
            return casual + ask(state, random.choice(["And then what?", "How do you feel about it?", "What happened next?", ""]))
        lead = ''
        if topic.get('kind') in ('neutral', 'good') and message_valence(raw, t) == 'neg':
            topic['kind'] = 'sad'  # the conversation turned heavier
        _, listening = pick(state, 'listening', C.LISTENING)
        if topic['turns'] >= 2 and not state['asked_pref'] and not state['no_advice']:
            return lead + listening + maybe_offer_help(state)
        if state['no_advice']:
            return lead + listening + ask(state, next_topic_question(state) if random.random() < 0.5 else '')
        return lead + listening + ask(state, next_topic_question(state))

    # In "just listen" mode, treat whatever they share as the thing they're venting about.
    if state.get('no_advice'):
        state['topic'] = {'kind': 'vent', 'subject': data.get('subject'), 'text': raw[:300], 'turns': 1, 'asked': []}
        _, listening = pick(state, 'listening', C.LISTENING)
        return listening

    # Not part of an ongoing topic: respond to how the message feels.
    valence = message_valence(raw, t)
    if valence == 'neg':
        state['topic'] = {'kind': 'sad', 'subject': data.get('subject'), 'text': raw[:300], 'turns': 0, 'asked': []}
        _, reply = pick(state, 'neg_open', NEG_OPENERS)
        return reply if not state.get('no_questions') else (strip_questions(reply) or "I'm here.")
    if valence == 'pos':
        _, reply = pick(state, 'positive', C.POSITIVE_REPLIES)
        return reply
    if len(words_of(t)) >= 4:
        state['topic'] = {'kind': 'neutral', 'subject': data.get('subject'), 'text': raw[:300], 'turns': 0, 'asked': []}
        _, reply = pick(state, 'curious', CURIOUS)
        return reply if not state.get('no_questions') else "Mm, I'm listening."
    _, ack = pick(state, 'ack', C.GENERIC_ACK)
    _, prompt = pick(state, 'prompt', C.GENERIC_PROMPTS)
    return ack + ask(state, prompt)


def maybe_offer_help(state):
    state['asked_pref'] = True
    if state.get('no_questions'):
        return ''
    state['activity'] = {'type': 'advice_or_listen'}
    _, q = pick(state, 'advice_or_listen', C.ADVICE_OR_LISTEN)
    return q


CASUAL = ["Oh, interesting!", "Mm, I get that.", "Ooh, okay.", "Got it.", "Oh really?"]
CURIOUS = ["Oh? Tell me more.", "Ooh, what's the story there?", "Hmm, how come?", "Oh really? How did that happen?",
           "Okay, I'm listening. What's going on with that?"]
NEG_OPENERS = ["That sounds hard. Do you want to tell me a bit more about what's going on?",
               "Ugh, I'm sorry. What's been going on?",
               "Mm, that sounds like a lot. I'm listening, tell me more?",
               "Oh no. What happened?"]

OPINION = {
    'favourite': ["Ooh, tough one. I don't really have a favourite {x}, perks of living inside an app 😅 What's yours?",
                  "Honestly, I can't pick a favourite {x} myself, I just live in this chat box! But tell me yours, I want to know."],
    'like': ["I can't really try {x} myself (app life 😅), but I'm curious. What do you like about it?",
             "Ha, I don't get to experience {x} myself, but I love hearing about it. Are you a fan?"],
    'ever': ["Nope, can't say I have, I mostly hang out in this chat box 😄 Have you?",
             "Ha, not me, I'm a homebody app. Have you ever {x}?"],
}
SUGGESTIONS = {
    'eat': ["Something warm and comforting? Noodles, a good sandwich, or whatever you've been craving all week. What are you in the mood for: sweet or savoury?",
            "Honestly? The thing you'd be happiest eating, not the 'sensible' one 😄 Something cheesy, something spicy, or something sweet?"],
    'watch': ["Depends on your mood! A comfort rewatch if you're tired, a comedy if you need a laugh, or a mystery if you want to switch your brain on. Which vibe?",
              "If you want zero effort, a comfort show you've already seen is unbeatable. Want something funny, cosy, or gripping?"],
    'read': ["Short stories are great when your focus is low. Or reread something you loved, it's like visiting an old friend. Fiction or non-fiction?"],
    'listen': ["A 'main character walking in the rain' playlist never fails 😌 Or something upbeat if you need energy. What's the mood?"],
    'do': ["A few ideas: a short walk with music, a cosy movie, calling a friend, or finally doing that tiny thing you keep postponing. Low-key or social?",
           "How about something small that feels nice: a snack, a show, a walk, or a long shower with a good playlist? Which sounds good?"],
    'cook': ["Something simple and cosy: pasta with whatever's in the fridge, or eggs on toast, the fancy way 😄 What ingredients do you have?"],
}


def h_opinion(state, raw, t, data, ctx):
    _, reply = pick(state, 'opinion:' + data['kind'], OPINION[data['kind']])
    reply = reply.format(x=data.get('thing', 'that'))
    return reply if not state.get('no_questions') else strip_questions(reply)


def h_suggest(state, raw, t, data, ctx):
    _, reply = pick(state, 'suggest:' + data['what'], SUGGESTIONS.get(data['what'], SUGGESTIONS['do']))
    return reply


def h_agree(state, raw, t, data, ctx):
    topic = state.get('topic')
    if topic and topic.get('turns', 0) < 8:
        topic['turns'] = topic.get('turns', 0) + 1
        _, prefix = pick(state, 'agree', C.AGREEMENT_PREFIX)
        subject = topic.get('subject')
        if topic.get('kind') == 'conflict' and 1 not in topic.get('asked', []):
            topic.setdefault('asked', []).append(1)
            q = "Do you think you two just see the situation differently, or was there something else underneath it?"
        else:
            q = next_topic_question(state)
        if subject and not q:
            return f"{prefix} It sounds like the {subject} thing really got to you."
        return prefix + ask(state, q) if ask(state, q) else prefix + " I'm here."
    return random.choice(["Okay! Tell me more 😄", "Yes! So what's going on?", "Love that. What's up?"])


def h_disagree(state, raw, t, data, ctx):
    if state.get('topic'):
        return "Okay, fair. I might have read that wrong." + ask(state, "How would you put it?")
    return random.choice(["Fair enough! What's on your mind, then?", "Okay, no worries. What's up?"])


def h_clarify_followup(state, raw, t, data, ctx):
    topic = state.get('topic')
    if topic and topic.get('subject'):
        return f"I just mean it sounds like the {topic['subject']} thing really affected you, and I'm curious how you're doing with it."
    if state.get('last_intent') == 'knowledge':
        return "That's the gist of it! If a part didn't make sense, tell me which bit and I'll try to put it differently."
    _, reply = pick(state, 'clarify', C.CLARIFY)
    return reply


def h_unknown_question(state, raw, t, data, ctx):
    _, reply = pick(state, 'unknown_q', C.UNKNOWN_QUESTION)
    return reply


def h_advice(state, raw, t, data, ctx):
    topic = state.get('topic') or {}
    if state.get('no_advice'):
        state['no_advice'] = False
        prefix = "Okay, switching to advice mode for a sec. "
    else:
        prefix = ''
    topic_text = topic.get('text', '') if topic.get('kind') != 'good' else ''
    return prefix + give_advice(state, raw + ' ' + topic_text)


def h_mood_summary(state, raw, t, data, ctx):
    if not ctx or not ctx.entry_count:
        return ("I don't see any mood check-ins from the last couple of weeks, so I honestly can't say. "
                "If you log a few in your journal, I can tell you what they show!")
    counts = sorted(ctx.mood_counts.items(), key=lambda kv: -kv[1])
    top_label, top_n = counts[0]
    plural = 'check-in' if ctx.entry_count == 1 else 'check-ins'
    parts = [f"Based on the {ctx.entry_count} mood {plural} you logged in the last {ctx.days} days, you picked '{top_label}' most often ({top_n}×)."]
    if ctx.trend == 'up':
        parts.append("Your more recent check-ins have been a bit higher than earlier ones.")
    elif ctx.trend == 'down':
        parts.append("Your more recent check-ins have been a bit lower than earlier ones.")
    elif ctx.trend == 'steady':
        parts.append("Things look fairly steady across that time.")
    parts.append("That's just the moods you chose, not a diagnosis, and the Insights page has the fuller picture.")
    parts.append(ask(state, "Does that match how it's felt to you?").strip())
    return ' '.join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Topics: talk about what the user is actually talking about
# ---------------------------------------------------------------------------
_COMPILED_TOPICS = [(tp, [re.compile(p) for p in tp['patterns']]) for tp in T.TOPICS]
_THING_STOPWORDS = {'it', 'this', 'that', 'something', 'a', 'an', 'the', 'movie', 'film', 'tv', 'one', 'some', 'stuff'}


def detect_topic(t: str) -> Optional[dict]:
    """First matching everyday topic (list order = priority) and any captured detail."""
    for topic, patterns in _COMPILED_TOPICS:
        for rx in patterns:
            m = rx.search(t)
            if m:
                thing = (m.groupdict().get('thing') or '').strip()
                thing = re.sub(r'^(the|a|an)\s+', '', thing)
                if not thing or thing in _THING_STOPWORDS or len(thing.split()) > 6:
                    thing = None
                return {'id': topic['id'], 'thing': thing}
    return None


NEG_HINTS = ('hurt', 'hurts', 'pain', 'painful', 'sad', 'cry', 'cried', 'crying', 'bad', 'worst', 'hate', 'hated', 'annoying',
             'annoyed', 'unfair', 'tired', 'exhausted', 'scared', 'worried', 'anxious', 'stressed', 'lonely', 'alone', 'sick',
             'ugh', 'not enough', 'cant', 'couldnt', 'failed', 'lost', 'miss', 'missing', 'nobody', 'no one', 'angry', 'mad',
             'upset', 'terrible', 'awful', 'horrible', 'rough', 'hard', 'difficult', 'struggling', 'stuck', 'overwhelmed',
             'depressed', 'down', 'weak', 'useless', 'worthless', 'embarrassed', 'ashamed', 'guilty', 'jealous', 'broke')
POS_HINTS = ('love', 'loved', 'great', 'amazing', 'awesome', 'happy', 'excited', 'fun', 'good', 'best', 'yay', 'finally',
             'proud', 'glad', 'nice', 'cute', 'beautiful', 'won', 'perfect', 'enjoyed', 'lit', 'fire', 'cool',
             'relieved', 'relief', 'phew', 'done', 'finished', 'submitted', 'passed', 'better', 'grateful', 'thankful')


def message_valence(raw: str, t: str) -> str:
    """'neg', 'pos' or 'neutral' from a small lexicon, with TextBlob as a tiebreaker."""
    if has(t, 'not bad', 'not too bad'):
        return 'pos'
    neg = sum(1 for w in NEG_HINTS if has(t, w))
    pos = sum(1 for w in POS_HINTS if has(t, w)) if not has(t, *NEGATIONS) else 0
    if neg > pos:
        return 'neg'
    if pos > neg:
        return 'pos'
    try:
        from textblob import TextBlob
        polarity = TextBlob(raw).sentiment.polarity
    except Exception:
        polarity = 0.0
    return 'neg' if polarity <= -0.25 else 'pos' if polarity >= 0.35 else 'neutral'


def _topic_detail(state, topic_def, t):
    """A reply for a specific detail the user mentioned within the topic, avoiding repeats."""
    for i, (pattern, replies) in enumerate(topic_def['details']):
        if re.search(pattern, t):
            used = state['topic'].setdefault('details_used', [])
            options = [r for j, r in enumerate(replies) if f"{i}:{j}" not in used] or replies
            reply = random.choice(options)
            used.append(f"{i}:{replies.index(reply)}")
            return reply
    return None


def _topic_question(state, topic_def):
    topic = state['topic']
    asked = topic.setdefault('asked', [])
    remaining = [q for q in topic_def['followups'] if q not in asked]
    if not remaining:
        return ''
    q = remaining[0]
    asked.append(q)
    return q


def h_topic(state, raw, t, data, ctx):
    """A message that brings up an everyday topic (periods, fever, exams, a movie...)."""
    topic_def = T.TOPIC_BY_ID[data['id']]
    current = state.get('topic') or {}
    if current.get('id') == topic_def['id']:
        return h_topic_followup(state, raw, t, data, ctx)

    state['topic'] = {'id': topic_def['id'], 'kind': topic_def['valence'], 'subject': topic_def['ref'],
                      'text': raw[:300], 'turns': 0, 'asked': [], 'thing': data.get('thing')}
    if state.get('safety', 0) > 0 and topic_def['valence'] == 'hard':
        return "That sounds really heavy, and I'm here. Please also reach out to someone you trust today, you deserve real support with this."

    # Mention-specific reply first when the message already has details
    # ("cramps are so bad today"), except for emotional topics, which get acknowledged first.
    reply = None
    if not topic_def.get('opener_first') and len(words_of(t)) >= 4:
        reply = _topic_detail(state, topic_def, t)
        if reply and '?' not in reply:
            reply += ask(state, _topic_question(state, topic_def))
    if not reply:
        openers = [o for o in topic_def['openers'] if '{thing}' not in o or data.get('thing')]
        _, reply = pick(state, 'topic_open:' + topic_def['id'], openers)
        reply = reply.format(thing=data.get('thing') or '')
    if state.get('no_questions'):
        reply = strip_questions(reply) or random.choice(C.LISTENING)
    return reply


def h_topic_followup(state, raw, t, data, ctx):
    """Continue the current topic, reacting to what was just said."""
    topic = state['topic']
    topic_def = T.TOPIC_BY_ID[topic['id']]
    topic['turns'] = topic.get('turns', 0) + 1
    topic['text'] = (topic.get('text', '') + ' ' + raw)[-300:]
    if state.get('safety', 0) > 0:
        return "I hear you. " + C.SAFETY_FOLLOWUP

    reply = _topic_detail(state, topic_def, t)
    if not reply:
        for keywords, reactions, follow_ups in C.DETAIL_REACTIONS:
            if has(t, *keywords):
                reply = random.choice(reactions)
                break
    if not reply:
        valence = message_valence(raw, t)
        # The conversation's mood (e.g. 'good' after "I finally finished it!") wins
        # over the topic's usual tone.
        mood = topic.get('kind') or topic_def['valence']
        if valence == 'neg' or (valence == 'neutral' and mood == 'hard'):
            pool = T.CONTINUE_HARD
        elif valence == 'pos' or mood == 'good':
            pool = T.CONTINUE_GOOD
        else:
            pool = T.CONTINUE_NEUTRAL
        _, reply = pick(state, 'continue:' + topic['id'], pool)
        reply = reply.format(ref=topic_def['ref'])

    if '?' in reply:
        return reply if not state.get('no_questions') else (strip_questions(reply) or "I'm here.")
    # Offer practical ideas once on hard topics (unless they only want to vent).
    if (topic_def.get('tips') and topic_def['valence'] in ('hard', 'mixed') and topic['turns'] >= 2
            and not state['asked_pref'] and not state['no_advice'] and not state.get('no_questions')):
        state['asked_pref'] = True
        state['activity'] = {'type': 'advice_or_listen'}
        return reply + f" Want a couple of things that might help with {topic_def['ref']}, or would you rather just talk?"
    if state['no_advice'] and random.random() < 0.5:
        return reply
    return reply + ask(state, _topic_question(state, topic_def))


# ---------------------------------------------------------------------------
# Style mirroring: reply the way the user writes
# ---------------------------------------------------------------------------
SLANG = ('omg', 'lol', 'lmao', 'bro', 'fr', 'ngl', 'idk', 'tbh', 'ya', 'yaa', 'yaar', 'pls', 'plz', 'rn', 'u', 'ur',
         'bestie', 'sis', 'dude', 'bruh', 'lowkey', 'highkey', 'istg', 'imo', 'btw', 'kinda', 'gonna', 'wanna')
STYLED_INTENTS = {'topic', 'topic_followup', 'statement', 'emotion', 'agree', 'disagree', 'greeting', 'how_are_you',
                  'positive', 'good_news', 'proud', 'thanks', 'farewell', 'laugh', 'compliment', 'encourage',
                  'listen_mode', 'clarify_followup', 'decline_offer', 'advice'}


def strip_emoji(text: str) -> str:
    """Remove emoji without gluing sentences together ("bottle 🫶 How" -> "bottle. How")."""
    text = re.sub(r'([^\s.!?])\s*(?:' + EMOJI_RE.pattern + r')+\s+(?=[A-Z])', r'\1. ', text)
    text = EMOJI_RE.sub('', text)
    return re.sub(r'\s{2,}', ' ', re.sub(r'\s+([.!?,])', r'\1', text)).strip()


def update_style(state, raw):
    letters = re.sub(r'[^A-Za-z]', '', raw)
    sample = {
        'lower': int(bool(letters) and letters == letters.lower()),
        'emoji': int(bool(EMOJI_RE.search(raw))),
        'casual': int(has(normalize(raw), *SLANG) or bool(re.search(r'([a-z])\1{2,}', raw.lower()))),
    }
    style = state.setdefault('style', {})
    for k, v in sample.items():
        style[k] = ([x for x in style.get(k, []) if isinstance(x, int)] + [v])[-3:]


def apply_style(state, reply, intent, raw):
    style = state.get('style') or {}
    lower, emoji, casual = (style.get(k, []) for k in ('lower', 'emoji', 'casual'))
    if not lower:
        return reply
    texting = sum(lower) >= 2 and lower[-1]
    uses_emoji = any(emoji)
    is_casual = any(casual)
    # Formal = capitalised, no exclamation, no slang or emoji ("I am on my period and it is painful.").
    formal = bool(re.match(r'\s*[A-Z]', raw)) and '!' not in raw and not is_casual and not uses_emoji
    if formal:
        reply = strip_emoji(reply)  # writes formally: keep replies plain
    if is_casual and casual[-1] and intent in ('topic', 'topic_followup', 'emotion', 'good_news', 'positive'):
        valence = (state.get('topic') or {}).get('kind')
        start = reply.lower()[:6]
        if not re.match(r'(oh|ugh|aw|omg|wait|yay|ahh|ooh|nooo|okay|haha|yes|mm|yeah|right|honestly|totally|of course|i hear)', start):
            if valence == 'hard' and random.random() < 0.6:
                reply = random.choice(['Ugh, ', 'Nooo, ', 'Aw, ']) + reply[0].lower() + reply[1:]
            elif valence == 'good' and random.random() < 0.6:
                reply = random.choice(['Omg, ', 'Ahh, ']) + reply[0].lower() + reply[1:]
    if texting:
        reply = reply.lower()  # mirror lowercase texting
    return reply


HANDLERS: Dict[str, Callable] = {
    'empty': h_empty, 'crisis': h_crisis, 'safety_ok': h_safety_ok, 'greeting': h_greeting,
    'how_are_you': h_how_are_you, 'about': h_about, 'feature': h_feature, 'knowledge': h_knowledge, 'math': h_math,
    'joke': h_joke, 'riddle': h_riddle, 'game': h_game, 'question': h_question, 'fact': h_fact,
    'another': h_another, 'accept_offer': h_accept_offer, 'decline_offer': h_decline_offer,
    'joke_bad': h_joke_bad, 'joke_good': h_joke_good, 'joke_explain': h_joke_explain,
    'activity_input': h_activity_input, 'stop_activity': h_stop_activity, 'bored': h_bored, 'distract': h_distract,
    'listen_mode': h_listen_mode, 'stop_questions': h_stop_questions, 'encourage': h_encourage,
    'farewell': h_farewell, 'thanks': h_thanks, 'compliment': h_compliment, 'laugh': h_laugh,
    'good_news': h_good_news, 'proud': h_proud, 'positive': h_positive, 'emotion': h_emotion,
    'agree': h_agree, 'disagree': h_disagree, 'clarify_followup': h_clarify_followup,
    'unknown_question': h_unknown_question, 'advice': h_advice, 'mood_summary': h_mood_summary,
    'statement': h_statement, 'opinion': h_opinion, 'suggest': h_suggest, 'serious_mode': h_serious_mode,
    'topic': h_topic, 'topic_followup': h_topic_followup,
}

# Short replies that continue whatever topic is being discussed.
_CONTINUES_TOPIC = {'statement', 'emotion', 'agree', 'disagree', 'positive', 'clarify_followup'}

# Intents that end whatever game/joke run was going on.
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿⬆⬇️]")

_KEEPS_ACTIVITY = {'activity_input', 'another', 'accept_offer', 'joke', 'joke_bad', 'joke_good', 'joke_explain',
                   'riddle', 'game', 'question', 'fact', 'bored', 'distract', 'laugh', 'thanks'}


def generate_reply(user_message: str, context: Optional[MindyContext], state: Optional[dict]) -> Tuple[str, dict]:
    """Produce Mindy's reply and the updated conversation state."""
    state = sanitize_state(state)
    state['turn'] += 1
    raw = (user_message or '')[:MAX_INPUT_CHARS]
    try:
        update_style(state, raw)
        intent, data = classify(raw, state)
        t = normalize(raw)
        topic = state.get('topic') or {}
        if intent in _CONTINUES_TOPIC and topic.get('id') and topic.get('turns', 0) < 10:
            intent = 'topic_followup'
        if intent not in _KEEPS_ACTIVITY:
            state['activity'] = None
        if intent not in ('another', 'accept_offer', 'decline_offer', 'joke_good', 'activity_input', 'joke_explain') and intent not in _KEEPS_ACTIVITY:
            state['offer'] = None
        reply = HANDLERS.get(intent, h_statement)(state, raw, t, data, context)
        if data.get('greeted') and intent not in ('crisis',):
            reply = random.choice(["Hey! ", "Hi! ", "Heyy. "]) + reply
        if intent in STYLED_INTENTS:
            reply = apply_style(state, reply, intent, raw)
        if state.get('serious') and intent not in ('crisis', 'safety_ok'):
            reply = strip_emoji(reply)  # keep the tone plain when asked
        if state.get('safety', 0) > 0 and intent != 'crisis':
            state['safety'] -= 1
        state['last_intent'] = intent
        return reply.strip(), state
    except Exception as e:  # never let one odd message break the chat
        logging.error(f"Mindy engine error: {type(e).__name__}")
        state['activity'] = None
        state['last_intent'] = 'error'
        return "Sorry, I got a bit tangled up there 😅 Can you say that another way?", state


def suggestions_for(state: dict) -> List[str]:
    """Quick replies that make sense for the current moment."""
    act = (state or {}).get('activity') or {}
    t = act.get('type')
    if (state or {}).get('safety', 0) > 0:
        return []
    if t == 'riddle':
        return ["Give me a hint", "I give up"]
    if t == 'guess':
        return ["I give up"]
    if t == 'wyr':
        return ["The first one", "The second one"]
    if t == 'menu':
        labels = {'joke': 'A joke 😂', 'riddle': 'A riddle', 'game': 'A game', 'wyr': 'Would you rather',
                  'guess': 'Guessing game', 'wordchain': 'Word chain', 'hypo': 'A hypothetical', 'fact': 'A fun fact'}
        return [labels[o] for o in act.get('options', []) if o in labels]
    if t == 'advice_or_listen':
        return ["Give me advice", "Just listen"]
    if t == 'joke':
        return ["Another one 😂", "That was bad 😭"]
    offer = (state or {}).get('offer')
    if offer in ('riddle', 'wyr', 'guess', 'question', 'fact', 'wordchain'):
        return ["Yes, another!", "Let's talk instead"]
    return []


def recover_state(user_messages: List[str], mindy_messages: List[str]) -> dict:
    """Rebuild state from stored messages when the session state is missing
    (for example after logging in again): restores used jokes/riddles, the
    listening preference and an in-progress joke or riddle."""
    state = new_state()
    for i, (_, joke) in enumerate(ALL_JOKES):
        if any(joke in m for m in mindy_messages):
            state['used'].setdefault('jokes', []).append(i)
    for i, riddle in enumerate(C.RIDDLES):
        if any(riddle[0] in m for m in mindy_messages):
            state['used'].setdefault('riddle', []).append(i)
    for msg in user_messages:
        intent, _ = classify(msg, new_state())
        if intent == 'listen_mode':
            state['no_advice'] = True
            state['asked_pref'] = True
        elif intent == 'stop_questions':
            state['no_questions'] = True
        elif intent == 'advice':
            state['no_advice'] = False
        elif intent == 'serious_mode':
            state['serious'] = True
        elif intent == 'joke':
            state['serious'] = False
    if mindy_messages:
        last = mindy_messages[-1]
        for i, riddle in enumerate(C.RIDDLES):
            if riddle[0] in last:
                state['activity'] = {'type': 'riddle', 'idx': i, 'tries': 0}
        if any(j in last for js in C.JOKES.values() for j in js):
            state['activity'] = {'type': 'joke', 'kind': None}
            state['offer'] = 'joke'
    state['turn'] = len(user_messages)
    return state


def build_context(user_id: int, days: int = 14) -> Optional[MindyContext]:
    """Summarise the user's own recent mood check-ins (scores and labels only)."""
    try:
        since = datetime.utcnow() - timedelta(days=days)
        entries = (JournalEntry.query.filter(JournalEntry.user_id == user_id, JournalEntry.created_at >= since)
                   .order_by(JournalEntry.created_at.asc()).all())
        ctx = MindyContext(days=days)
        if not entries:
            return ctx
        ctx.entry_count = len(entries)
        for e in entries:
            ctx.mood_counts[e.mood_label] = ctx.mood_counts.get(e.mood_label, 0) + 1
        scores = [e.mood_score for e in entries if e.mood_score]
        if scores:
            ctx.average_score = sum(scores) / len(scores)
        if len(scores) >= 4:
            half = len(scores) // 2
            first, second = sum(scores[:half]) / half, sum(scores[half:]) / (len(scores) - half)
            ctx.trend = 'up' if second - first >= 0.5 else 'down' if first - second >= 0.5 else 'steady'
        return ctx
    except Exception as e:
        logging.error(f"Failed to build mindy context: {type(e).__name__}")
        return None
