"""Mindy's humour should be varied, on-request and inclusive, not tech-by-default."""
import re
from collections import Counter

from app.services import mindy_content as C
from app.services.mindy_service import generate_reply, ALL_JOKES, classify, new_state

KIND_OF = {j: k for k, j in ALL_JOKES}


def joke_kind(reply):
    return next((KIND_OF[j] for j in KIND_OF if j in reply), None)


def chat(*messages):
    state, replies = None, []
    for m in messages:
        reply, state = generate_reply(m, None, state)
        replies.append(reply)
    return replies, state


def test_collection_is_balanced():
    assert len(C.DEFAULT_JOKE_KINDS) >= 10
    for kind in C.DEFAULT_JOKE_KINDS:
        assert len(C.JOKES[kind]) >= 5, kind
    tech_share = len(C.JOKES['tech']) / len(ALL_JOKES)
    assert tech_share < 0.1
    assert 'tech' not in C.DEFAULT_JOKE_KINDS and 'dark' not in C.DEFAULT_JOKE_KINDS
    texts = [j for _, j in ALL_JOKES]
    assert len(texts) == len(set(texts)), "duplicate jokes across categories"


def test_general_requests_are_diverse_and_never_tech():
    kinds = Counter(joke_kind(generate_reply("tell me a joke", None, None)[0]) for _ in range(300))
    assert None not in kinds
    assert 'tech' not in kinds and 'dark' not in kinds
    assert len(kinds) >= 9
    assert max(kinds.values()) / 300 < 0.25  # no category dominates


def test_category_requests_and_informal_phrasing():
    cases = {
        "Tell me a food joke.": 'food', "Tell me a joke about animals.": 'animal', "Give me a school joke.": 'school',
        "got any office jokes?": 'work', "tell me a joke about my family": 'family', "a travel joke pls": 'travel',
        "tell me a dad joke": 'wordplay', "give me a pun": 'wordplay', "something silly, tell me a random joke": 'silly',
        "tell me a science joke": 'trivia', "tell me a programming joke": 'tech', "knock knock": 'knock',
        "tell me a joke about dogs": 'animal', "do you know any cooking jokes": 'food',
    }
    for message, expected in cases.items():
        reply, _ = generate_reply(message, None, None)
        assert joke_kind(reply) == expected, f"{message!r} -> {reply!r}"


def test_misspelled_request_still_gets_a_joke():
    for message in ["tell me a joek", "jokes pls", "tell me a jok"]:
        assert joke_kind(generate_reply(message, None, None)[0]), message


def test_unknown_topic_is_honest():
    reply, _ = generate_reply("tell me a joke about cricket", None, None)
    assert reply.startswith("I don't have a cricket joke yet") and joke_kind(reply)


def test_not_a_joke_request():
    for message in ["my life is a joke", "this is no joke", "that joke wasn't funny"]:
        intent, _ = classify(message, new_state())
        assert intent != 'joke', message


def test_dark_request_stays_mild_and_is_skipped_after_crisis():
    reply, _ = generate_reply("tell me a dark joke", None, None)
    assert joke_kind(reply) == 'dark' and 'lighter side' in reply.lower() or 'nobody gets hurt' in reply.lower()
    replies, _ = chat("I want to die", "tell me a dark joke")
    assert joke_kind(replies[1]) != 'dark'


def test_another_keeps_category_and_never_repeats():
    replies, _ = chat("tell me an animal joke", *["another"] * 5)
    kinds = [joke_kind(r) for r in replies]
    assert kinds == ['animal'] * 6
    jokes = [next(j for j in KIND_OF if j in r) for r in replies]
    assert len(set(jokes)) == 6


def test_no_repeats_across_many_general_jokes():
    replies, _ = chat("tell me a joke", *["another"] * 40)
    jokes = [next(j for j in KIND_OF if j in r) for r in replies]
    assert len(set(jokes)) == len(jokes)


def test_unfunny_feedback_switches_style():
    for _ in range(20):
        _, state = chat("tell me a joke")
        first = state['last_joke_kind']
        reply, state = generate_reply("that wasn't funny", None, state)
        assert joke_kind(reply) and joke_kind(reply) != first
        assert state['joke_likes'][first] == -1


def test_liked_category_is_favoured():
    import random
    random.seed(1234)  # the bias is probabilistic; fix the seed so the test is deterministic
    state = None
    reply, state = generate_reply("tell me a food joke", None, state)
    for _ in range(2):
        reply, state = generate_reply("haha good one", None, state)
        reply, state = generate_reply("tell me a food joke", None, state)
    assert state['joke_likes']['food'] >= 2
    kinds = Counter()
    for _ in range(12):
        reply, state = generate_reply("tell me a joke", None, state)
        kinds[joke_kind(reply)] += 1
    assert kinds['food'] >= 3  # roughly half of general requests lean toward what landed


def test_serious_mode_respected():
    replies, state = chat("no jokes please, be serious", "I'm bored", "I had a terrible day")
    assert state['serious']
    for r in replies:
        assert not re.search(r'[\U0001F300-\U0001FAFF]', r)
    replies, state = chat("be serious", "ok actually tell me a joke")
    assert joke_kind(replies[1]) and not state['serious']


def test_core_requests_from_brief():
    expectations = [
        ("Tell me a riddle.", lambda r, s: s['activity']['type'] == 'riddle'),
        ("Let's play a guessing game.", lambda r, s: s['activity']['type'] == 'guess'),
        ("Tell me something interesting.", lambda r, s: r.startswith('Fun fact:')),
        ("I'm bored.", lambda r, s: s['activity']['type'] == 'menu'),
        ("I had a terrible day.", lambda r, s: not joke_kind(r) and '?' in r),
        ("I just want to vent.", lambda r, s: s['no_advice'] and not joke_kind(r)),
        ("Why is the sky blue?", lambda r, s: 'scatter' in r),
        ("How many bones are in the human body?", lambda r, s: '206' in r),
        ("Change the subject please.", lambda r, s: s['activity']['type'] == 'menu'),
    ]
    for message, check in expectations:
        reply, state = generate_reply(message, None, None)
        assert check(reply, state), f"{message!r} -> {reply!r}"


def test_no_jokes_target_groups():
    banned = ['blonde', 'women are', 'men are', 'religion', 'immigrant', 'fat', 'ugly', 'stupid people', 'old people']
    for _, joke in ALL_JOKES:
        for word in banned:
            assert not re.search(r'\b' + re.escape(word) + r'\b', joke.lower()), joke
