import os
import re
from datetime import date, timedelta

from app.services.inspiration_service import image_for_date, all_image_paths, INSPIRATION_IMAGES, FALLBACK_IMAGE


def _login(client):
    client.post('/register', data={'name': 'Tashvi Test', 'email': 'dash@example.com', 'password': 'pw12345'})
    client.post('/login', data={'email': 'dash@example.com', 'password': 'pw12345'})


def _profile_trigger(html):
    m = re.search(r'<button[^>]*id="profile-menu-button".*?</button>', html, re.S)
    assert m, "profile trigger button missing"
    return m.group(0)


# --- Profile dropdown ----------------------------------------------------------

def test_profile_trigger_is_a_button_not_a_logout_link(client):
    _login(client)
    html = client.get('/dashboard').data.decode()
    trigger = _profile_trigger(html)
    assert '/logout' not in trigger and 'href' not in trigger
    assert 'aria-haspopup="menu"' in trigger and 'aria-expanded="false"' in trigger
    assert 'Tashvi Test' in trigger and '>T<' in trigger  # real name and initial


def test_dropdown_links_to_real_routes(client):
    _login(client)
    html = client.get('/dashboard').data.decode()
    menu = re.search(r'id="profile-menu-list".*?</div>', html, re.S).group(0)
    assert 'href="/profile"' in menu and 'My Profile' in menu
    assert 'href="/logout"' in menu and 'Log Out' in menu
    assert 'Settings' not in menu  # no settings route exists yet
    # The logout link appears exactly once on the page, inside the menu.
    assert html.count('href="/logout"') == 1


def test_viewing_dashboard_does_not_log_out(client):
    _login(client)
    for _ in range(3):
        assert client.get('/dashboard').status_code == 200
    assert client.get('/profile').status_code == 200


def test_logout_still_works_and_protects_routes(client):
    _login(client)
    assert client.get('/logout').status_code == 302
    for path in ('/dashboard', '/journal/', '/profile'):
        r = client.get(path)
        assert r.status_code == 302 and '/login' in r.headers['Location']


# --- Privacy card removed, daily photo -----------------------------------------

def test_privacy_card_removed_and_photo_present(client):
    _login(client)
    html = client.get('/dashboard').data.decode()
    assert 'Your space is private' not in html
    assert 'privacy-note' not in html
    assert 'Better days' in html and 'data-daily-photo' in html
    assert f'/static/{image_for_date()}' in html
    assert 'id="mindy-launcher"' in html


def test_photo_is_stable_within_a_day_and_changes_daily():
    day = date(2026, 3, 14)
    assert image_for_date(day) == image_for_date(day)
    picks = [image_for_date(day + timedelta(days=i)) for i in range(len(INSPIRATION_IMAGES))]
    # Consecutive days always differ, and a full cycle uses every image once.
    assert all(a != b for a, b in zip(picks, picks[1:]))
    assert sorted(picks) == sorted(all_image_paths())


def test_photo_rendered_by_server_follows_date(client, monkeypatch):
    import app.services.inspiration_service as svc

    class FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 1, 2)

    _login(client)
    monkeypatch.setattr(svc, 'date', FakeDate)
    first = client.get('/dashboard').data.decode()
    again = client.get('/dashboard').data.decode()
    expected = svc.INSPIRATION_IMAGES[FakeDate(2026, 1, 2).toordinal() % len(svc.INSPIRATION_IMAGES)]
    assert expected in first and expected in again

    class NextDay(FakeDate):
        @classmethod
        def today(cls):
            return cls(2026, 1, 3)

    monkeypatch.setattr(svc, 'date', NextDay)
    assert expected not in re.search(r'<img class="inspiration-photo" src="[^"]+"', client.get('/dashboard').data.decode()).group(0)


def test_all_images_and_fallback_exist(app):
    static = app.static_folder
    for path in all_image_paths():
        full = os.path.join(static, path)
        assert os.path.isfile(full), path
        assert os.path.getsize(full) < 200 * 1024  # optimised for the small card
    assert FALLBACK_IMAGE in INSPIRATION_IMAGES


def test_bundled_images_are_served(client):
    _login(client)
    for path in all_image_paths():
        r = client.get('/static/' + path)
        assert r.status_code == 200 and r.mimetype == 'image/jpeg'
        r.close()
