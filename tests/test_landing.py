def _register_and_login(client):
    client.post('/register', data={'name': 'Landing User', 'email': 'landing@example.com', 'password': 'pw12345'})
    client.post('/login', data={'email': 'landing@example.com', 'password': 'pw12345'})


def test_landing_page_renders_for_logged_out_users(client):
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode()
    assert 'css/landing.css' in html
    assert 'Your thoughts deserve' in html
    assert 'id="features"' in html
    assert 'href="#features"' in html
    assert 'href="/register"' in html
    assert 'href="/login"' in html
    assert 'landing-footer' in html


def test_landing_page_does_not_overclaim_encryption(client):
    html = client.get('/').data.decode().lower()
    assert 'end-to-end' not in html
    assert 'all your data is encrypted' not in html


def test_login_and_register_pages_still_render(client):
    for path in ('/login', '/register'):
        response = client.get(path)
        assert response.status_code == 200
        html = response.data.decode()
        assert 'unauth-navbar' in html
        assert 'css/landing.css' not in html


def test_protected_routes_still_redirect_to_login(client):
    for path in ('/dashboard', '/journal/', '/insights/', '/reports/'):
        response = client.get(path)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']


def test_logged_in_users_skip_landing_page(client):
    _register_and_login(client)
    response = client.get('/')
    assert response.status_code == 302
    assert '/dashboard' in response.headers['Location']

    dashboard = client.get('/dashboard').data.decode()
    assert 'class="sidebar"' in dashboard
    assert 'css/landing.css' not in dashboard
    assert 'unauth-navbar' not in dashboard
