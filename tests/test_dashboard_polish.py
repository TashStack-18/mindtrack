import re
from datetime import datetime, timedelta

from app.extensions import db
from app.models.journal import JournalEntry
from app.models.user import User


def _login(client, app, email='polish@example.com'):
    with app.app_context():
        u = User(name='Polly Test', email=email)
        u.set_password('pw')
        db.session.add(u)
        db.session.commit()
        uid = u.id
    client.post('/login', data={'email': email, 'password': 'pw'})
    return uid


def test_notification_bell_removed(client, app):
    _login(client, app)
    html = client.get('/dashboard').data.decode()
    assert 'aria-label="Notifications"' not in html
    assert 'notification-dot' not in html
    css = client.get('/static/css/style.css').data.decode()
    assert 'notification-dot' not in css and '.icon-button' not in css


def test_sidebar_routes_and_active_state(client, app):
    _login(client, app)
    pages = {'/dashboard': 'Home', '/journal/': 'Journal', '/insights/': 'Insights', '/reports/': 'Reports'}
    for path, label in pages.items():
        html = client.get(path).data.decode()
        sidebar = html.split('class="side-nav"')[1].split('</nav>')[0]
        active = re.findall(r'<a href="([^"]+)" class="active" aria-current="page">\s*<svg.*?<span>([^<]+)</span>', sidebar, re.S)
        assert active == [(path, label)], (path, active)
        for href in ('/dashboard', '/journal/', '/insights/', '/reports/'):
            assert f'href="{href}"' in sidebar
        assert 'data-open-mindy' in sidebar and 'onclick=' not in sidebar


def test_profile_trigger_and_logout_still_work(client, app):
    _login(client, app)
    html = client.get('/dashboard').data.decode()
    trigger = re.search(r'<button[^>]*id="profile-menu-button".*?</button>', html, re.S).group(0)
    assert '/logout' not in trigger and 'Polly Test' in trigger
    assert client.get('/logout').status_code == 302
    assert client.get('/dashboard').headers['Location'].endswith('/login')


def test_checkin_card_reflects_real_status(client, app):
    uid = _login(client, app)
    html = client.get('/dashboard').data.decode()
    assert 'Not checked in yet' in html
    with app.app_context():
        db.session.add(JournalEntry(user_id=uid, title='t', encrypted_content='', mood_score=4, mood_label='Good'))
        db.session.commit()
    html = client.get('/dashboard').data.decode()
    assert 'Not checked in yet' not in html
    assert "You've checked in today" in html and '<strong>Good</strong>' in html
    assert '1 <small>day this week' in html


def test_week_dots_use_local_date(client, app):
    uid = _login(client, app)
    ist = timedelta(minutes=330)
    ist_today = (datetime.utcnow() + ist).date()
    # 00:01 on today's date in India, which is still "yesterday" in UTC.
    created = datetime.combine(ist_today, datetime.min.time()) + timedelta(minutes=1) - ist
    with app.app_context():
        db.session.add(JournalEntry(user_id=uid, title='t', encrypted_content='', mood_score=3, mood_label='Okay',
                                    created_at=created))
        db.session.commit()
    client.set_cookie('mt_tz', '330')
    assert "You've checked in today" in client.get('/dashboard').data.decode()
    client.set_cookie('mt_tz', '0')
    utc_says_today = created.date() == datetime.utcnow().date()
    html = client.get('/dashboard').data.decode()
    assert ("You've checked in today" in html) == utc_says_today


def test_no_nested_interactive_controls(client, app):
    _login(client, app)
    html = client.get('/dashboard').data.decode()
    assert not re.search(r'<a [^>]*>\s*<button', html)
    assert 'class="scale"' not in html  # duplicate chart labels removed


def test_single_font_import_and_tokens(client):
    css = client.get('/static/css/style.css').data.decode()
    assert css.count('@import') == 1 and 'Inter' in css
    assert 'tailwindcss' not in css and 'Plus Jakarta' not in css
    for token in ('--mt-primary: #7965C1', '--mt-primary-deep: #55458F', '--mt-bg: #FAF8FC', '--mt-text: #302A40', '--mt-border: #E8E1F0'):
        assert token in css
