"""Mindy should stay on the user's actual topic and talk the way they talk."""
import re

import pytest

from app.services import mindy_topics as T
from app.services.mindy_service import generate_reply, detect_topic, normalize, SAFETY_MESSAGE


def chat(*messages):
    state, replies = None, []
    for m in messages:
        reply, state = generate_reply(m, None, state)
        replies.append(reply)
    return replies, state


GENERIC_BAD = ["ha, fair", "kind of cool", "good days deserve", "what made you think of that", "tell me more!"]


def assert_not_generic(reply):
    low = reply.lower()
    for phrase in GENERIC_BAD:
        assert phrase not in low, reply


# --- The conversation from the bug report ---------------------------------------

def test_period_conversation_stays_on_topic():
    for _ in range(10):  # replies are randomised; check several runs
        replies, state = chat("im on my periods", "cramps are so bad today", "yeah and i have class too")
        assert state['topic']['id'] == 'period'
        assert re.search(r'period', replies[0].lower())
        assert re.search(r'cramp|hot water|heating|lie down', replies[1].lower())
        assert re.search(r'class|full day', replies[2].lower())
        for r in replies:
            assert_not_generic(r)
            assert 'must feel bad' not in r.lower()


@pytest.mark.parametrize('first, second, topic_id, second_pattern', [
    ("my mom keeps comparing me to my cousin", "it makes me feel like im not enough", 'family_compare', r'not enough|worth|your own person'),
    ("i have a fever since morning", "i couldnt go to college", 'sick', r'staying home|missing a day|rest'),
    ("my best friend is moving to another city", "we've been friends since 5th grade", 'friend_moving', r'friendship|history|since you were little'),
    ("omg i just watched the new spiderman movie", "it was sooo good", 'movie_show', r'best part|watch it again'),
    ("i cant stop eating junk food lately", "yeah", 'food', r'.'),
    ("my roommate and I argued yesterday", "she never cleans", 'roommate', r'clean|share'),
    ("i have exams tomorrow and havent studied", "i cant focus", 'exam', r'phone|focus|25'),
])
def test_topics_from_real_examples(first, second, topic_id, second_pattern):
    replies, state = chat(first, second)
    assert state['topic']['id'] == topic_id
    assert re.search(second_pattern, replies[1].lower()), replies
    for r in replies:
        assert_not_generic(r)


def test_sad_news_never_gets_cheerful_reply():
    for _ in range(10):
        r, _ = generate_reply("my best friend is moving to another city", None, None)
        assert 'yay' not in r.lower() and 'good days' not in r.lower()


def test_no_robotic_echo():
    for msg in ["i have a fever since morning", "omg i just watched the new spiderman movie", "I'll tell you about my day later"]:
        r, _ = generate_reply(msg, None, None)
        assert not r.lower().startswith("oh, you"), r
        assert "you have a fever since morning?" not in r.lower()


# --- Matching precision ------------------------------------------------------------

@pytest.mark.parametrize('message, expected', [
    ("im on my period", 'period'), ("my cramps are killing me", 'period'),
    ("my head hurts so bad", 'sick'), ("i caught a cold", 'sick'),
    ("i'm so sick of my roommate", 'roommate'),          # "sick of" is not illness
    ("I'll call you later", None),                         # "I'll" -> "ill" must not mean sick
    ("show me something", None),                           # "show" alone is not TV
    ("i cant stop eating junk food lately", 'food'),
    ("my dad yelled at me", 'family_fight'),
    ("we broke up yesterday", 'breakup'), ("im broke this month", 'money'),
])
def test_detect_topic_precision(message, expected):
    found = detect_topic(normalize(message))
    assert (found or {}).get('id') == expected


def test_lately_does_not_match_late():
    r, _ = generate_reply("i cant stop eating junk food lately", None, None)
    assert 'missing it' not in r.lower() and 'rushing' not in r.lower()


def test_every_topic_is_well_formed():
    ids = [t['id'] for t in T.TOPICS]
    assert len(ids) == len(set(ids)) and len(ids) >= 25
    for t in T.TOPICS:
        assert t['openers'] and t['followups'] and t['ref'] and t['valence'] in ('hard', 'good', 'mixed', 'neutral')
        for p in t['patterns']:
            re.compile(p)
            assert '\x08' not in p, t['id']  # a lost backslash would silently break matching
        for p, replies in t['details']:
            re.compile(p)
            assert '\x08' not in p and replies, t['id']
        for q in t['followups']:
            assert q.endswith('?')


# --- Behaviour around topics ----------------------------------------------------------

def test_advice_on_topic_uses_topic_tips():
    replies, _ = chat("im on my periods", "what should i do for cramps")
    assert 'hot water bottle' in replies[1] and 'doctor' in replies[1]


def test_offer_then_accept_tips():
    replies, state = chat("my mom yelled at me for no reason", "i didnt even do anything", "it really hurt")
    offered = [r for r in replies if 'want a couple of things' in r.lower()]
    if offered:
        reply, state = generate_reply("yes please", None, state)
        assert 'calm' in reply.lower()


def test_listen_mode_keeps_topic_without_tips():
    replies, state = chat("just listen, my best friend is moving away", "we've been friends forever", "i'll miss her so much")
    assert state['no_advice'] and state['topic']['id'] == 'friend_moving'
    for r in replies:
        assert 'want a couple of things' not in r.lower()
        assert 'goodbye day' not in r.lower()


def test_topic_switch_follows_user():
    replies, state = chat("i have exams tomorrow", "ok anyway i watched a movie yesterday", "it was boring tbh")
    assert state['topic']['id'] == 'movie_show'
    assert 'letdown' in replies[2].lower()


def test_game_input_is_not_a_topic():
    _, state = chat("let's play word chain")
    last = state['activity']['last']
    word = next(w for w in ['cake', 'pizza', 'rain', 'exam', 'movie'] if w[0] != last[-1])
    reply, state = generate_reply(word, None, state)
    assert state['activity'] and state['activity']['type'] == 'wordchain'
    assert f"'{last[-1]}'" in reply


def test_crisis_beats_topic():
    replies, state = chat("my head hurts so bad", "i want to die")
    assert replies[1] == SAFETY_MESSAGE


def test_good_news_remembers_topic():
    replies, state = chat("omg bestie i finally finished my assignment", "sooo relieved")
    assert state['topic']['id'] == 'assignment'
    assert 'tough' not in replies[1].lower() and 'sorry' not in replies[1].lower()


# --- Style mirroring --------------------------------------------------------------

def test_lowercase_texting_is_mirrored():
    replies, _ = chat("im on my periods", "cramps are so bad today", "yeah")
    assert replies[2] == replies[2].lower()


def test_formal_writer_gets_no_emoji_and_proper_case():
    replies, _ = chat("I am on my period and it is quite painful today.", "I also have a lecture at noon.")
    for r in replies:
        assert not re.search(r'[\U0001F300-\U0001FAFF]', r), r
        assert r[0].isupper()


def test_emoji_removal_keeps_sentences_apart():
    from app.services.mindy_service import strip_emoji
    assert strip_emoji("Sending you a virtual hot water bottle 🫶 How bad is it today?") == \
        "Sending you a virtual hot water bottle. How bad is it today?"
    assert strip_emoji("Oh no 😣 being sick is the worst") == "Oh no being sick is the worst"
    assert strip_emoji("That's amazing! 🎉 Tell me more") == "That's amazing! Tell me more"


def test_excited_capitalised_message_keeps_celebration_emoji():
    r, _ = generate_reply("I finally got selected for the club!", None, None)
    from app.services import mindy_content as C
    assert r in C.CELEBRATE
