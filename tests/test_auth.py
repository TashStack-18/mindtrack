def test_register(client, app):
    response = client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 302
    assert response.headers['Location'] == '/login'
    
    with app.app_context():
        from app.models.user import User
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.name == 'Test User'

def test_register_duplicate_email(client):
    client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123'
    })
    response = client.post('/register', data={
        'name': 'Test User 2',
        'email': 'test@example.com',
        'password': 'password456'
    })
    assert response.status_code == 200
    assert b'is already registered' in response.data

def test_login_logout(client, app):
    client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123'
    })
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 302
    assert response.headers['Location'] == '/'

    with client.session_transaction() as session:
        assert 'user_id' in session

    # Test authenticated access to dashboard
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'Good ' in response.data

    # Test logout
    response = client.get('/logout')
    assert response.status_code == 302
    
    with client.session_transaction() as session:
        assert 'user_id' not in session

def test_login_invalid_credentials(client):
    response = client.post('/login', data={
        'email': 'wrong@example.com',
        'password': 'wrong'
    })
    assert response.status_code == 200
    assert b'Invalid credentials' in response.data

def test_unauthenticated_access_dashboard(client):
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert response.headers['Location'] == '/login'
