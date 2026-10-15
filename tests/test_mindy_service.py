import re

from app.services import mindy_content as C
from app.services.mindy_service import (
    generate_reply, classify, new_state, sanitize_state, suggestions_for, recover_state,
    MindyContext, SAFETY_MESSAGE, TEMPLATES,
)

ALL_JOKES = [j for js in C.JOKES.values() for j in js]


def chat(*messages, context=None):
    """Run a conversation and return the list of replies plus final state."""
    state, replies = None, []
    for m in messages:
        reply, state = generate_reply(m, context, state)
        replies.append(reply)
    return replies, state


def joke_in(reply):
    return next((j for j in ALL_JOKES if j in reply), None)


# --- Jokes and follow-ups ----------------------------------------------------

def test_joke_request_tells_a_joke():
    for msg in ["Tell me a joke", "tell me a joke pls", "joke", "Do you know any jokes?", "make me laugh"]:
        replies, state = chat(msg)
        assert joke_in(replies[0]), f"No joke for {msg!r}: {replies[0]}"
        for redirect in ('cbt', 'breath', 'exercise', 'reflection prompt', "i'm sorry you're feeling"):
            assert redirect not in replies[0].lower()


def test_another_gives_a_different_joke():
    replies, _ = chat("Tell me a joke", "another", "one more", "another one")
    jokes = [joke_in(r) for r in replies]
    assert all(jokes), replies
    assert len(set(jokes)) == len(jokes)


def test_bad_joke_feedback_gets_a_new_joke():
    replies, _ = chat("tell me a joke", "that was bad")
    assert joke_in(replies[1]) and joke_in(replies[1]) != joke_in(replies[0])


def test_specific_joke_kind():
    replies, _ = chat("tell me a programming joke")
    assert joke_in(replies[0]) in C.JOKES['tech']
    replies, _ = chat("knock knock")
    assert joke_in(replies[0]) in C.JOKES['knock']


def test_jokes_do_not_repeat_within_a_conversation():
    replies, _ = chat("tell me a joke", *["another"] * 15)
    jokes = [joke_in(r) for r in replies]
    assert len(set(jokes)) == len(jokes)


# --- Riddles and games -------------------------------------------------------

def test_riddle_flow_hint_wrong_right_and_reveal():
    replies, state = chat("give me a riddle")
    idx = state['activity']['idx']
    question, answers, answer_text, hint = C.RIDDLES[idx]
    assert question in replies[0]

    reply, state = generate_reply("is it a banana", None, state)
    assert state['activity']['type'] == 'riddle'  # still guessing
    reply, state = generate_reply("hint", None, state)
    assert hint in reply
    reply, state = generate_reply(f"a {answers[0]}", None, state)
    assert state['activity'] is None and state['offer'] == 'riddle'

    reply, state = generate_reply("yes", None, state)  # accept the offered riddle
    assert state['activity']['type'] == 'riddle'
    new_idx = state['activity']['idx']
    assert new_idx != idx
    reply, state = generate_reply("I give up", None, state)
    assert C.RIDDLES[new_idx][2][1:] in reply


def test_guess_the_number_game():
    _, state = chat("let's play the guessing game")
    secret = state['activity']['n']
    low = 1 if secret != 1 else 2
    reply, state = generate_reply(str(low), None, state)
    if low < secret:
        assert 'Higher' in reply
    reply, state = generate_reply(str(secret), None, state)
    assert str(secret) in reply and state['activity'] is None


def test_would_you_rather_and_menu():
    replies, state = chat("I'm so bored")
    assert state['activity']['type'] == 'menu'
    assert suggestions_for(state)
    reply, state = generate_reply("a game", None, state)
    reply, state = generate_reply("would you rather", None, state)
    assert reply.startswith("Would you rather")
    reply, state = generate_reply("the first one", None, state)
    assert 'another' in reply.lower()


def test_word_chain_validates_letters():
    _, state = chat("let's play word chain")
    last = state['activity']['last']
    wrong_start = 'z' if last[-1] != 'z' else 'a'
    reply, state = generate_reply(wrong_start + 'ebra', None, state)
    assert f"'{last[-1]}'" in reply
    candidates = [w for ws in C.WORD_BANK.values() for w in ws if w[0] == last[-1] and w != last]
    reply, state = generate_reply(candidates[0], None, state)
    assert 'nice' in reply.lower()


def test_stop_ends_game():
    _, state = chat("guessing game", "stop")
    assert state['activity'] is None


# --- Conversation behaviour ----------------------------------------------------

def test_greeting_is_short_and_warm():
    replies, _ = chat("Hey Mindy!")
    assert len(replies[0]) < 60
    assert 'assist' not in replies[0].lower()


def test_greeting_plus_request_answers_the_request():
    replies, _ = chat("hey mindy tell me a joke")
    assert joke_in(replies[0])


def test_bad_day_acknowledges_without_exercises():
    replies, _ = chat("I had such a terrible day at college.")
    r = replies[0].lower()
    assert '?' in r and ('what happened' in r or 'tell me' in r)
    for banned in ['breath', 'exercise', 'cbt', 'worksheet', 'rate your mood']:
        assert banned not in r


def test_feeling_left_out_is_validated_not_judged():
    replies, _ = chat("I feel like nobody in my friend group actually cares about me.")
    r = replies[0].lower()
    assert 'hurt' in r
    assert 'toxic' not in r and 'leave' not in r


def test_explicit_advice_request_gets_advice():
    replies, _ = chat("I don't know how to deal with my friend ignoring my messages. What should I do?")
    assert 'space' in replies[0] or 'check in' in replies[0]


def test_listen_mode_is_remembered():
    replies, state = chat("I don't want solutions. I just want to talk.",
                          "my exams are next week and I haven't studied at all",
                          "and my parents keep asking about it")
    assert state['no_advice'] is True
    advice_texts = [a for _, a, _ in C.ADVICE]
    for r in replies[1:]:
        assert not any(a in r for a in advice_texts)
        assert 'advice' not in r.lower()


def test_advice_after_listen_mode_when_explicitly_asked():
    replies, state = chat("just listen", "my exam is tomorrow", "ok actually what should I do?")
    assert state['no_advice'] is False
    assert 'advice mode' in replies[-1]


def test_good_news_is_celebrated():
    replies, _ = chat("I finally got selected for the club!")
    assert replies[0] in C.CELEBRATE


def test_technical_question_answered():
    replies, _ = chat("What is the difference between Git fetch and Git pull?")
    assert 'Fetch downloads' in replies[0]
    replies, _ = chat("explain recursion")
    assert 'base case' in replies[0]


def test_unknown_factual_question_is_honest():
    replies, _ = chat("What's the population of Peru?")
    assert "not sure" in replies[0].lower() or "don't want to give you a wrong answer" in replies[0]


def test_math():
    replies, _ = chat("what is 12 * 4")
    assert '48' in replies[0]
    replies, _ = chat("what is 1/0")
    assert 'zero' in replies[0]


def test_distract_changes_subject_and_follows_through():
    replies, state = chat("I don't want to think about that anymore. Distract me.")
    assert state['activity']['type'] == 'menu' and state['topic'] is None
    reply, state = generate_reply(suggestions_for(state)[0], None, state)
    assert state['activity'] is not None and state['activity']['type'] != 'menu'


def test_presentation_follow_up_uses_details():
    replies, _ = chat("My presentation went terribly.", "I forgot half of what I wanted to say.")
    assert 'presentation' in replies[0]
    assert 'blank' in replies[1] or 'brain-freeze' in replies[1]


def test_roommate_context_carries_through():
    replies, state = chat("My roommate and I argued yesterday.", "She said I never help clean.", "Exactly!")
    assert 'happened' in replies[0].lower()
    assert 'frustrating' in replies[1].lower() or 'a lot to hear' in replies[1].lower()
    assert state['topic']['id'] == 'roommate'
    assert '?' in replies[2] and replies[2] != replies[1]


def test_stop_asking_questions_is_respected():
    replies, state = chat("stop asking me questions", "my day was rough", "the bus was late too")
    assert state['no_questions']
    for r in replies[1:]:
        assert '?' not in r, r


def test_feature_questions_are_accurate():
    replies, _ = chat("is my data private?")
    assert 'encrypted' in replies[0] and "aren't encrypted" in replies[0]
    assert 'end-to-end' not in replies[0]
    replies, _ = chat("how do reports work?")
    assert 'PDF' in replies[0]


def test_about_mindy_is_honest():
    replies, _ = chat("are you a real person?")
    assert "not a human" in replies[0]


def test_mood_summary_uses_context_only():
    ctx = MindyContext(mood_counts={'Okay': 3, 'Good': 1}, entry_count=4, days=14, average_score=3.2, trend='up')
    replies, _ = chat("how have I been feeling lately?", context=ctx)
    assert "'Okay'" in replies[0] and '4 mood check-ins' in replies[0]
    assert 'not a diagnosis' in replies[0]
    replies, _ = chat("how have I been feeling lately?", context=MindyContext())
    assert "can't say" in replies[0]


# --- Safety --------------------------------------------------------------------

def test_safety_concern():
    phrases = [
        "I want to kill myself", "I want to die", "I don't want to be here anymore",
        "I don't want to be alive", "I'm going to hurt myself", "I keep thinking about suicide",
        "everyone would be better off without me",
    ]
    for phrase in phrases:
        reply, state = generate_reply(phrase, None, None)
        assert reply == SAFETY_MESSAGE, phrase
        assert state['last_intent'] == 'crisis'


def test_crisis_overrides_games_and_no_joke_in_reply():
    _, state = chat("tell me a joke")
    reply, state = generate_reply("honestly i want to die", None, state)
    assert reply == SAFETY_MESSAGE
    assert not joke_in(reply)
    assert state['activity'] is None


def test_idioms_are_not_crises():
    for phrase in ["this joke is killing me lol", "I'm dying to see that movie", "I almost died laughing"]:
        reply, state = generate_reply(phrase, None, None)
        assert state['last_intent'] != 'crisis', phrase


def test_safety_follow_up():
    replies, state = chat("I want to die", "yes, I'm safe")
    assert state['safety'] == 0 and 'glad' in replies[1]


def test_banned_clinical_vocabulary():
    banned = ["diagnos", "disorder", "clinical", "psychiatr", "medication", "you are depressed", "mental illness"]
    pools = [v for v in vars(C).values() if isinstance(v, list) and v and isinstance(v[0], str)]
    for pool in pools:
        for text in pool:
            for word in banned:
                assert word not in text.lower(), f"{word!r} in {text!r}"
    assert 'not a therapist' in SAFETY_MESSAGE


# --- State handling ------------------------------------------------------------

def test_state_sanitisation():
    for bad in [None, "junk", {"turn": "x"}, {"v": 2, "turn": "nope", "activity": 5, "used": []}]:
        reply, state = generate_reply("hi", None, bad)
        assert state['turn'] == 1
        assert reply


def test_empty_and_long_input():
    reply, _ = generate_reply("   ", None, None)
    assert reply
    reply, _ = generate_reply("blah " * 5000, None, None)
    assert reply


def test_recover_state_from_history():
    joke = C.JOKES['everyday'][0]
    state = recover_state(["just listen please", "tell me a joke"], ["Hi!", "Ha! " + joke])
    assert state['no_advice'] is True
    assert state['activity']['type'] == 'joke'
    reply, state = generate_reply("another", None, state)
    assert joke_in(reply) and joke not in reply


def test_greeting_templates_exist():
    assert TEMPLATES['greeting'] and TEMPLATES['end_conversation']
    assert classify("hi", new_state())[0] == 'greeting'
    assert sanitize_state({'v': 999})['turn'] == 0
