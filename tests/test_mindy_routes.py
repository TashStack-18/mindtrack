import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.journal import JournalEntry
from app.models.mindy import MindyConversation, MindyMessage
from app.services.encryption_service import encrypt_text, decrypt_text
from unittest.mock import patch
import json

@pytest.fixture
def logged_in_client(client, app):
    with app.app_context():
        user = User(name='Test User', email='test@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
    
    client.post('/login', data={'email': 'test@example.com', 'password': 'password'})
    return client

def test_logged_out_access(client):
    response = client.post('/mindy/message', json={"message": "hello", "conversation_id": 1})
    assert response.status_code == 401
    assert response.get_json()['error'] == 'auth_required'

def test_init_creates_conversation(logged_in_client, app):
    response = logged_in_client.post('/mindy/init')
    assert response.status_code == 200
    data = response.get_json()
    assert 'conversation_id' in data
    assert data['is_new'] == True
    
    with app.app_context():
        conv = MindyConversation.query.get(data['conversation_id'])
        assert conv is not None
        assert conv.status == 'active'
        msgs = MindyMessage.query.filter_by(conversation_id=conv.id).all()
        assert len(msgs) == 1
        assert msgs[0].sender == 'mindy'

def test_init_resumes_conversation(logged_in_client, app):
    # First init
    r1 = logged_in_client.post('/mindy/init')
    c_id = r1.get_json()['conversation_id']
    
    # Second init should return the same one
    r2 = logged_in_client.post('/mindy/init')
    data = r2.get_json()
    assert data['conversation_id'] == c_id
    assert data['is_new'] == False

def test_missing_message(logged_in_client):
    response = logged_in_client.post('/mindy/message', json={})
    assert response.status_code == 400

def test_valid_message(logged_in_client):
    r1 = logged_in_client.post('/mindy/init')
    c_id = r1.get_json()['conversation_id']
    
    response = logged_in_client.post('/mindy/message', json={"message": "hello mindy", "conversation_id": c_id})
    assert response.status_code == 200
    data = response.get_json()
    assert 'reply' in data
    assert 'state' in data
    assert response.headers['Cache-Control'] == 'no-store'

def test_cross_user_isolation(client, app):
    with app.app_context():
        user_a = User(name='User A', email='a@example.com')
        user_a.set_password('pass')
        user_b = User(name='User B', email='b@example.com')
        user_b.set_password('pass')
        
        db.session.add_all([user_a, user_b])
        db.session.commit()
        
        conv_a = MindyConversation(user_id=user_a.id, title='Title', status='active')
        db.session.add(conv_a)
        db.session.commit()

        b_id = user_b.id
        a_id = user_a.id
        conv_a_id = conv_a.id
        
    # Log in as B
    client.post('/login', data={'email': 'b@example.com', 'password': 'pass'})
    
    # Send a message pretending to pass A's conversation ID
    response = client.post('/mindy/message', json={"message": "hello", "conversation_id": conv_a_id})
    assert response.status_code == 404

def test_end_conversation(logged_in_client, app):
    r1 = logged_in_client.post('/mindy/init')
    c_id = r1.get_json()['conversation_id']
    
    # End request
    r_end_req = logged_in_client.post('/mindy/end_request', json={"conversation_id": c_id})
    assert r_end_req.status_code == 200
    
    # End confirm
    r_end_conf = logged_in_client.post('/mindy/end_confirm', json={"conversation_id": c_id})
    assert r_end_conf.status_code == 200
    
    with app.app_context():
        conv = MindyConversation.query.get(c_id)
        assert conv.status == 'completed'
        
    # Next init should create a new one
    r2 = logged_in_client.post('/mindy/init')
    assert r2.get_json()['conversation_id'] != c_id
    assert r2.get_json()['is_new'] == True

def test_history_and_rename(logged_in_client, app):
    r1 = logged_in_client.post('/mindy/init')
    c_id = r1.get_json()['conversation_id']
    logged_in_client.post('/mindy/end_confirm', json={"conversation_id": c_id})
    
    r_hist = logged_in_client.get('/mindy/history')
    data = r_hist.get_json()
    assert len(data['history']) == 1
    
    r_rename = logged_in_client.put(f'/mindy/conversation/{c_id}/title', json={'title': 'New Title'})
    assert r_rename.status_code == 200
    
    with app.app_context():
        conv = MindyConversation.query.get(c_id)
        assert conv.title == 'New Title'

def test_delete(logged_in_client, app):
    r1 = logged_in_client.post('/mindy/init')
    c_id = r1.get_json()['conversation_id']
    
    r_del = logged_in_client.delete(f'/mindy/conversation/{c_id}')
    assert r_del.status_code == 200
    
    with app.app_context():
        conv = MindyConversation.query.get(c_id)
        assert conv is None

def test_encryption_untouched(logged_in_client, app):
    r1 = logged_in_client.post('/mindy/init')
    c_id = r1.get_json()['conversation_id']
    
    response = logged_in_client.post('/mindy/message', json={"message": "hello", "conversation_id": c_id})
    assert response.status_code == 200
    
    with app.app_context():
        # Make sure it's stored encrypted
        msg = MindyMessage.query.filter_by(conversation_id=c_id, sender='user').first()
        assert "hello" not in msg.encrypted_message

def test_failure_path_returns_error_and_saves_nothing(logged_in_client, app):
    r1 = logged_in_client.post('/mindy/init')
    c_id = r1.get_json()['conversation_id']

    with patch('app.routes.mindy.generate_reply', side_effect=Exception("boom")):
        response = logged_in_client.post('/mindy/message', json={"message": "hello", "conversation_id": c_id})
    assert response.status_code == 500
    assert response.get_json() == {"error": "reply_failed"}  # no internals leaked

    with app.app_context():
        # Earlier messages are untouched, and the failed turn isn't half-saved.
        msgs = MindyMessage.query.filter_by(conversation_id=c_id).all()
        assert [m.sender for m in msgs] == ['mindy']


def _send(client, c_id, text):
    r = client.post('/mindy/message', json={"message": text, "conversation_id": c_id})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def test_context_persists_between_requests(logged_in_client):
    from app.services import mindy_content as C
    c_id = logged_in_client.post('/mindy/init').get_json()['conversation_id']
    all_jokes = [j for js in C.JOKES.values() for j in js]
    first = _send(logged_in_client, c_id, "tell me a joke")
    second = _send(logged_in_client, c_id, "another")
    j1 = next(j for j in all_jokes if j in first['reply'])
    j2 = next(j for j in all_jokes if j in second['reply'])
    assert j1 != j2
    assert second['state'] == {'activity': 'joke'}
    assert second['suggestions']


def test_client_supplied_state_is_ignored(logged_in_client):
    c_id = logged_in_client.post('/mindy/init').get_json()['conversation_id']
    forged = {"v": 2, "activity": {"type": "guess", "n": 7, "tries": 0}}
    r = logged_in_client.post('/mindy/message', json={"message": "7", "conversation_id": c_id, "state": forged})
    reply = r.get_json()['reply']
    assert "It was 7" not in reply and "YES" not in reply


def test_state_not_readable_in_cookie(logged_in_client):
    c_id = logged_in_client.post('/mindy/init').get_json()['conversation_id']
    _send(logged_in_client, c_id, "my roommate and I argued about cleaning")
    with logged_in_client.session_transaction() as sess:
        blob = sess.get('mindy_state')
    assert blob and 'roommate' not in blob and 'cleaning' not in blob


def test_state_recovered_after_relogin(logged_in_client):
    c_id = logged_in_client.post('/mindy/init').get_json()['conversation_id']
    _send(logged_in_client, c_id, "I don't want advice, just listen")
    logged_in_client.get('/logout')
    logged_in_client.post('/login', data={'email': 'test@example.com', 'password': 'password'})
    with logged_in_client.session_transaction() as sess:
        assert 'mindy_state' not in sess
    data = _send(logged_in_client, c_id, "my exam is tomorrow and I haven't started studying")
    assert 'advice' not in data['reply'].lower()


def test_new_conversation(logged_in_client, app):
    c1 = logged_in_client.post('/mindy/init').get_json()['conversation_id']
    # A conversation with only Mindy's greeting is discarded, not saved to history.
    r = logged_in_client.post('/mindy/new')
    c2 = r.get_json()['conversation_id']
    assert r.get_json()['is_new'] and r.get_json()['suggestions']
    with app.app_context():
        # (SQLite may reuse the freed id, so check the table rather than the id.)
        assert MindyConversation.query.count() == 1
        assert MindyMessage.query.filter_by(conversation_id=c2).count() == 1

    _send(logged_in_client, c2, "tell me a joke")
    c3 = logged_in_client.post('/mindy/new').get_json()['conversation_id']
    with app.app_context():
        assert MindyConversation.query.get(c2).status == 'completed'
        assert MindyConversation.query.get(c3).status == 'active'
    # Fresh context: "another" has nothing to continue.
    assert "Another what" in _send(logged_in_client, c3, "another")['reply']
    assert len(logged_in_client.get('/mindy/history').get_json()['history']) == 1


def test_invalid_inputs(logged_in_client):
    c_id = logged_in_client.post('/mindy/init').get_json()['conversation_id']
    cases = [
        {"message": "", "conversation_id": c_id},
        {"message": "   ", "conversation_id": c_id},
        {"message": "x" * 1001, "conversation_id": c_id},
        {"message": 123, "conversation_id": c_id},
        {"message": "hi", "conversation_id": "abc"},
        {"message": ["hi"], "conversation_id": c_id},
    ]
    for body in cases:
        assert logged_in_client.post('/mindy/message', json=body).status_code == 400, body
    assert logged_in_client.post('/mindy/message', data="not json", content_type='text/plain').status_code == 400
    assert logged_in_client.post('/mindy/end_confirm').status_code == 400


def test_html_is_stored_as_text(logged_in_client):
    c_id = logged_in_client.post('/mindy/init').get_json()['conversation_id']
    _send(logged_in_client, c_id, "<script>alert(1)</script>")
    msgs = logged_in_client.get(f'/mindy/conversation/{c_id}').get_json()['messages']
    # Returned as plain data; the chat UI renders it with textContent, never innerHTML.
    assert msgs[1]['message'] == "<script>alert(1)</script>"


def test_other_users_cannot_read_or_continue_conversations(client, app):
    with app.app_context():
        for name in ('a', 'b'):
            u = User(name=name.upper(), email=f'{name}@example.com')
            u.set_password('pass')
            db.session.add(u)
        db.session.commit()
    client.post('/login', data={'email': 'a@example.com', 'password': 'pass'})
    c_id = client.post('/mindy/init').get_json()['conversation_id']
    _send(client, c_id, "my secret worry")
    client.get('/logout')

    client.post('/login', data={'email': 'b@example.com', 'password': 'pass'})
    assert client.get(f'/mindy/conversation/{c_id}').status_code == 404
    assert client.delete(f'/mindy/conversation/{c_id}').status_code == 404
    assert client.post('/mindy/end_confirm', json={"conversation_id": c_id}).status_code == 400
    b_conv = client.post('/mindy/init').get_json()
    assert b_conv['conversation_id'] != c_id
    assert all('secret' not in m['message'] for m in b_conv['messages'])


def test_mood_summary_reads_only_own_moods(logged_in_client, app):
    with app.app_context():
        me = User.query.filter_by(email='test@example.com').first()
        other = User(name='Other', email='other@example.com')
        other.set_password('x')
        db.session.add(other)
        db.session.commit()
        for uid, label, score in [(me.id, 'Good', 4), (other.id, 'Very Low', 1), (other.id, 'Very Low', 1)]:
            db.session.add(JournalEntry(user_id=uid, title='t', encrypted_content=encrypt_text('private words'),
                                        mood_score=score, mood_label=label))
        db.session.commit()
    c_id = logged_in_client.post('/mindy/init').get_json()['conversation_id']
    reply = _send(logged_in_client, c_id, "how have I been feeling lately?")['reply']
    assert "'Good'" in reply and '1 mood check-in' in reply
    assert 'Very Low' not in reply and 'private words' not in reply


def test_unauthenticated_endpoints(client):
    assert client.post('/mindy/init').status_code == 401
    assert client.post('/mindy/new').status_code == 401
    assert client.get('/mindy/history').status_code == 401
    assert client.get('/mindy/conversation/1').status_code == 401
