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

def test_failure_path(logged_in_client):
    r1 = logged_in_client.post('/mindy/init')
    c_id = r1.get_json()['conversation_id']
    
    with patch('app.routes.mindy.build_context', side_effect=Exception("Database down")):
        response = logged_in_client.post('/mindy/message', json={"message": "hello", "conversation_id": c_id})
        assert response.status_code == 200
        data = response.get_json()
        assert "Yeah, I'm here. Tell me a little more." in data['reply']
