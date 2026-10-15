import re
from datetime import datetime, timedelta

from app.extensions import db
from app.models.journal import JournalEntry
from app.models.user import User
from app.services.encryption_service import encrypt_text, decrypt_text


def _login(client, email='j@example.com', name='Jo'):
    client.post('/register', data={'name': name, 'email': email, 'password': 'pw12345'})
    client.post('/login', data={'email': email, 'password': 'pw12345'})


def _nonce(client):
    html = client.get('/journal/').data.decode()
    return re.search(r'name="nonce" value="([^"]+)"', html).group(1)


def _checkin(client, **fields):
    data = {'nonce': _nonce(client), 'mood': '4', 'note': '', **fields}
    return client.post('/journal/checkin', data=data)


def test_journal_page_renders_with_empty_state(client):
    _login(client)
    r = client.get('/journal/')
    html = r.data.decode()
    assert r.status_code == 200
    assert 'How are you feeling right now?' in html
    assert 'Your journal is waiting for its first page' in html
    assert 'href="/journal/history"' not in html.split('Recent Entries')[1].split('</div>')[0]  # no "View all" with 0 entries
    assert 'Mood-only check-in' not in html  # no fake entries


def test_checkin_saves_mood_note_and_contexts(client, app):
    _login(client)
    r = _checkin(client, mood='2', note='Stayed up late studying.', contexts=['Study', 'Sleep', 'NotAContext'])
    assert r.status_code == 302 and '/journal/' in r.headers['Location']
    with app.app_context():
        user = User.query.filter_by(email='j@example.com').first()
        entry = JournalEntry.query.filter_by(user_id=user.id).one()
        assert entry.mood_score == 2 and entry.mood_label == 'Low'
        assert sorted(t.name for t in entry.tags) == ['Sleep', 'Study']
        assert 'Stayed up' not in entry.encrypted_content  # stored encrypted
        assert decrypt_text(entry.encrypted_content) == 'Stayed up late studying.'
        assert {t.theme_name for t in entry.detected_themes} >= {'Sleep', 'Academics'}
    html = client.get('/journal/').data.decode()
    assert 'Check-in saved' in html
    assert 'Stayed up late studying.' in html and 'Study' in html
    assert 'href="/journal/history"' in html


def test_mood_only_checkin_is_allowed(client, app):
    _login(client)
    assert _checkin(client, mood='5').status_code == 302
    with app.app_context():
        entry = JournalEntry.query.one()
        assert entry.encrypted_content == '' and entry.mood_label == 'Great'
    assert 'Mood-only check-in' in client.get('/journal/').data.decode()
    # The existing edit page still works for a text-free entry.
    eid = JournalEntry.query.one().id if False else None
    with app.app_context():
        eid = JournalEntry.query.one().id
    r = client.post(f'/journal/{eid}/edit', data={'title': 'x', 'content': '', 'mood': '4'})
    assert r.status_code == 302


def test_checkin_validation_errors(client, app):
    _login(client)
    r = _checkin(client, mood='9', note='hello')
    assert r.status_code == 400
    html = r.data.decode()
    assert 'Pick the mood that feels closest' in html
    assert 'hello' in html  # input preserved
    r = _checkin(client, mood='3', note='x' * 2001)
    assert r.status_code == 400 and 'under 2000 characters' in r.data.decode()
    with app.app_context():
        assert JournalEntry.query.count() == 0


def test_repeated_submission_does_not_duplicate(client, app):
    _login(client)
    nonce = _nonce(client)
    data = {'nonce': nonce, 'mood': '3', 'note': 'Same thing'}
    first = client.post('/journal/checkin', data=data)
    second = client.post('/journal/checkin', data=data)  # double-click / resubmit with a used token
    assert first.status_code == 302 and second.status_code == 302
    with app.app_context():
        assert JournalEntry.query.count() == 1
    assert 'already saved' in client.get('/journal/').data.decode()


def test_stale_form_with_new_content_asks_before_saving(client, app):
    _login(client)
    nonce = _nonce(client)
    client.post('/journal/checkin', data={'nonce': nonce, 'mood': '3', 'note': 'first'})
    r = client.post('/journal/checkin', data={'nonce': nonce, 'mood': '1', 'note': 'something different'})
    assert r.status_code == 409 and 'something different' in r.data.decode()
    with app.app_context():
        assert JournalEntry.query.count() == 1


def test_multiple_checkins_per_day_are_preserved(client, app):
    _login(client)
    _checkin(client, mood='2', note='morning')
    _checkin(client, mood='4', note='evening')
    with app.app_context():
        assert JournalEntry.query.count() == 2
    assert "checked in 2 times today" in client.get('/journal/').data.decode()


def test_recent_entries_are_own_and_ordered(client, app):
    _login(client, 'a@example.com', 'A')
    with app.app_context():
        me = User.query.filter_by(email='a@example.com').first()
        other = User(name='B', email='b@example.com')
        other.set_password('x')
        db.session.add(other)
        db.session.commit()
        now = datetime.utcnow()
        for i, title in enumerate(['oldest', 'middle', 'newest']):
            db.session.add(JournalEntry(user_id=me.id, title=title, encrypted_content=encrypt_text(f'text {title}'),
                                        mood_score=3, mood_label='Okay', created_at=now - timedelta(days=3 - i)))
        db.session.add(JournalEntry(user_id=other.id, title='someone else secret', encrypted_content=encrypt_text('nope'),
                                    mood_score=1, mood_label='Very Low'))
        db.session.commit()
    html = client.get('/journal/').data.decode()
    assert 'someone else secret' not in html
    assert html.index('newest') < html.index('middle') < html.index('oldest')
    assert 'View all 3' in html


def test_history_moved_but_links_work(client):
    _login(client)
    _checkin(client, mood='4', note='hi there')
    r = client.get('/journal/history')
    assert r.status_code == 200 and 'hi there' in r.data.decode()
    assert client.get('/journal/history?q=hi').status_code == 200


def test_reflection_card_is_general_without_recent_entry(client):
    _login(client)
    html = client.get('/journal/').data.decode()
    assert 'A gentle prompt for today' in html
    _checkin(client, mood='2', note='I always mess everything up')
    html = client.get('/journal/').data.decode()
    assert 'Based on your latest entry' in html
    # The reflection service now reads the decrypted text, so absolute language is noticed.
    assert 'absolute statement' in html


def test_checkin_requires_login(client):
    r = client.post('/journal/checkin', data={'mood': '3'})
    assert r.status_code == 302 and '/login' in r.headers['Location']
    assert client.get('/journal/').status_code == 302
