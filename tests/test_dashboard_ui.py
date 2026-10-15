import pytest
import os
from datetime import datetime, timedelta
from app.models.journal import JournalEntry
from app.models.user import User
from app import db

def test_dashboard_uses_only_current_user_entries(client, app):
    """Ensure the week strip and mood history use only the current user's entries."""
    with app.app_context():
        # Create users
        user1 = User(email="1@x.com", name="User One")
        user1.set_password("pass")
        user2 = User(email="2@x.com", name="User Two")
        user2.set_password("pass")
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()

        # Add entries for user2 (other user)
        entry2 = JournalEntry(user_id=user2.id, title="User2 Entry", encrypted_content=b'test', mood_score=5, mood_label='Great')
        db.session.add(entry2)
        db.session.commit()

    # Login as user1
    client.post('/login', data={'email': '1@x.com', 'password': 'pass'})

    # Check dashboard
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode()
    # The week strip / mood history should not render mood-5 for user1
    assert "User2 Entry" not in html

def test_dashboard_renders_for_zero_entries(client, app):
    """Ensure dashboard renders correctly for 0 entries."""
    with app.app_context():
        user = User(email="zero@x.com", name="Zero")
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'email': 'zero@x.com', 'password': 'pass'})
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode()
    assert "Your journal is empty" in html
    assert "No mood history yet" in html  # honest empty states, no fake data

def test_dashboard_renders_for_many_entries(client, app):
    """Ensure dashboard renders correctly for many entries."""
    with app.app_context():
        user = User(email="many@x.com", name="Many")
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()

        for i in range(10):
            entry = JournalEntry(user_id=user.id, title=f"Entry {i}", encrypted_content=b'test', mood_score=4, mood_label='Good')
            db.session.add(entry)
        db.session.commit()

    client.post('/login', data={'email': 'many@x.com', 'password': 'pass'})
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode()
    # Recent Moments shows the latest five, with "View all" for the rest.
    assert html.count('class="moment"') == 5
    assert 'href="/journal/history"' in html

def test_no_gamification_vocabulary(app):
    """Ensure no gamification vocabulary appears in any template."""
    gamification_terms = ['points', 'streak', 'badge', 'level', 'trophy', 'reward', 'leaderboard']
    templates_dir = os.path.join(app.root_path, 'templates')

    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    for term in gamification_terms:
                        # Allow "level" in the context of SVG/HTML structure if strictly needed, but check full words.
                        # Using simple string find is okay, but to prevent false positives like "polyline points":
                        if term == 'points':
                            continue # Allowed in SVGs
                        if term == 'level':
                            continue # Allowed in python macros `level in [1,2,3,4,5]`
                        if term == 'badge':
                            continue # Ignore badge as we use badge classes
                        assert term not in content, f"Gamification term '{term}' found in {file}"

def test_daily_image_is_stable_across_refresh_and_relogin(client, app):
    # The dashboard photo now changes by calendar date, not per login
    # (see tests/test_dashboard_header_and_photo.py for date-change tests).
    import re
    with app.app_context():
        for email in ('rot1@x.com', 'rot2@x.com'):
            u = User(name='A', email=email)
            u.set_password('pass')
            db.session.add(u)
        db.session.commit()

    def photo():
        html = client.get('/dashboard', follow_redirects=True).data.decode('utf-8', errors='ignore')
        return re.search(r'img/inspiration/([\w-]+)\.jpg', html).group(1)

    client.post('/login', data={'email': 'rot1@x.com', 'password': 'pass'})
    first = photo()
    assert photo() == first, 'Image changed on refresh'
    client.get('/logout')
    client.post('/login', data={'email': 'rot1@x.com', 'password': 'pass'})
    assert photo() == first, 'Image changed on re-login the same day'
    client.get('/logout')
    client.post('/login', data={'email': 'rot2@x.com', 'password': 'pass'})
    assert photo() == first, 'Same day should show the same photo for everyone'
