from datetime import date, datetime, timedelta

from app.extensions import db
from app.models.journal import JournalEntry
from app.models.tag import Tag
from app.models.user import User
from app.services.encryption_service import encrypt_text
from app.services.insight_service import build_insights_view, resolve_period, entry_contexts

LABELS = {1: 'Very Low', 2: 'Low', 3: 'Okay', 4: 'Good', 5: 'Great'}


def _user(app, email='i@example.com'):
    with app.app_context():
        u = User(name='Ins', email=email)
        u.set_password('pw')
        db.session.add(u)
        db.session.commit()
        return u.id


def _entry(app, uid, days_ago, score, tags=(), text='private text', hour=12):
    with app.app_context():
        when = (datetime.utcnow() - timedelta(days=days_ago)).replace(hour=hour, minute=0, second=0, microsecond=0)
        e = JournalEntry(user_id=uid, title='t', encrypted_content=encrypt_text(text), mood_score=score,
                         mood_label=LABELS[score], created_at=when)
        for name in tags:
            tag = Tag.query.filter_by(user_id=uid, name=name).first() or Tag(user_id=uid, name=name)
            e.tags.append(tag)
        db.session.add(e)
        db.session.commit()


def _login(client, email='i@example.com'):
    client.post('/login', data={'email': email, 'password': 'pw'})


# --- Pure calculations ------------------------------------------------------------

class E:
    """Minimal stand-in for JournalEntry in pure calculation tests."""
    def __init__(self, day, score, tags=()):
        self.day, self.mood_score = day, score
        self.tags = [type('T', (), {'name': n})() for n in tags]
        self.detected_themes, self.feelings = [], []
        self.sentiment_polarity = 0.0
        self.created_at = datetime.combine(day, datetime.min.time())


def view_for(entries, prev=(), key='7', today=date(2026, 3, 10)):
    period = resolve_period(key, today, min((e.day for e in entries), default=today))
    return build_insights_view(list(entries), list(prev), period, lambda e: e.day)


def test_missing_days_are_not_filled():
    today = date(2026, 3, 10)
    v = view_for([E(today, 4), E(today - timedelta(days=3), 2)], today=today)
    values = [p['value'] for p in v['series']]
    assert len(values) == 7
    assert values.count(None) == 5
    assert v['points_with_data'] == 2
    assert not v['enough_data']
    # Only the plain check-in count is reported; no pattern claims from 2 entries.
    assert [o['kind'] for o in v['observations']] == ['frequency']
    assert v['suggestions'] == []


def test_statistics_match_records():
    today = date(2026, 3, 10)
    entries = [E(today, 4), E(today, 2), E(today - timedelta(days=1), 4), E(today - timedelta(days=2), 5)]
    v = view_for(entries, today=today)
    s = v['stats']
    assert s['count'] == 4 and s['days_with_entries'] == 3
    assert s['top_moods'] == ['Good'] and s['top_mood_count'] == 2
    assert s['average'] == 3.8 and s['good_count'] == 3
    assert v['series'][-1]['value'] == 3.0 and v['series'][-1]['count'] == 2  # two check-ins today, averaged
    assert 'average_change' not in s  # no valid previous period


def test_comparison_only_with_enough_data_in_both_periods():
    today = date(2026, 3, 10)
    cur = [E(today - timedelta(days=i), 4) for i in range(3)]
    prev = [E(today - timedelta(days=8 + i), 2) for i in range(3)]
    assert view_for(cur, prev, today=today)['stats']['average_change'] == 2.0
    assert 'average_change' not in view_for(cur, prev[:2], today=today)['stats']


def test_context_counts_and_mood_association():
    today = date(2026, 3, 10)
    entries = [E(today, 4, ['Study']), E(today - timedelta(days=1), 5, ['Study', 'Friends']),
               E(today - timedelta(days=2), 4, ['Academics']), E(today - timedelta(days=3), 3, ['Study'])]
    v = view_for(entries, today=today)
    study = next(c for c in v['contexts'] if c['name'] == 'Study')
    assert study['count'] == 4  # legacy "Academics" tag counted as Study
    assert (study['good'], study['okay'], study['low']) == (3, 1, 0)
    titles = [o['title'] for o in v['observations']]
    assert "You recorded a good mood in 3 of your 4 Study entries in the last 7 days." in titles
    assert v['suggestions'] and v['suggestions'][0]['context'] == 'Study'
    assert '3 of 4 Study entries' in v['suggestions'][0]['evidence']
    friends = next(c for c in v['contexts'] if c['name'] == 'Friends')
    assert friends['count'] == 1 and not any('Friends' in t for t in titles)  # too few to claim anything


def test_language_is_cautious():
    today = date(2026, 3, 10)
    entries = [E(today - timedelta(days=i), 1, ['Study']) for i in range(4)]
    v = view_for(entries, today=today)
    text = ' '.join(o['title'] + ' ' + o['note'] for o in v['observations']).lower()
    for banned in ['because', 'caused by', 'you should', 'diagnos is', 'depressed', 'disorder']:
        assert banned not in text
    assert v['suggestions'] == []  # low moods never become "do more of this"


def test_all_time_period_and_weekly_buckets():
    today = date(2026, 3, 10)
    entries = [E(today - timedelta(days=100), 3), E(today, 4)]
    v = view_for(entries, key='all', today=today)
    assert v['period']['prev_first'] is None
    assert v['series_unit'] == 'week'
    assert v['points_with_data'] == 2


# --- Through the app -------------------------------------------------------------

def test_insights_empty_state(client, app):
    _user(app)
    _login(client)
    html = client.get('/insights/').data.decode()
    assert "Nothing to notice yet" in html and 'href="/journal/"' in html
    assert 'moodChart' not in html


def test_range_filter_changes_data(client, app):
    uid = _user(app)
    _entry(app, uid, 1, 4, ['Friends'])
    _entry(app, uid, 2, 5, ['Friends'])
    _entry(app, uid, 20, 1, ['Study'])
    _login(client)
    week = client.get('/insights/?range=7').data.decode()
    month = client.get('/insights/?range=30').data.decode()
    assert '2 check-ins' in week and 'Study' not in week.split('Your top contexts')[1].split('</section>')[0]
    assert '3 check-ins' in month and 'Study' in month.split('Your top contexts')[1].split('</section>')[0]
    assert client.get('/insights/?range=bogus').status_code == 200


def test_sparse_data_explained(client, app):
    uid = _user(app)
    _entry(app, uid, 0, 4)
    _login(client)
    html = client.get('/insights/').data.decode()
    assert 'Not enough check-ins yet' in html
    assert 'A few more check-ins will make trends easier to see' in html
    assert 'A general prompt, not based on your data' in html


def test_users_only_see_their_own_analytics(client, app):
    a = _user(app, 'a@example.com')
    b = _user(app, 'b@example.com')
    for i in range(3):
        _entry(app, a, i, 5, ['Friends'])
        _entry(app, b, i, 1, ['Work'], text='b private words')
    _login(client, 'a@example.com')
    html = client.get('/insights/').data.decode()
    assert 'Work' not in html.split('Your top contexts')[1] and 'b private words' not in html
    assert 'Great' in html and '3 check-ins' in html


def test_insights_payload_has_no_journal_text(client, app):
    uid = _user(app)
    for i in range(4):
        _entry(app, uid, i, 3, ['Home'], text='my secret diary words')
    _login(client)
    html = client.get('/insights/').data.decode()
    assert 'my secret diary words' not in html


def test_local_day_boundary_uses_timezone_cookie(client, app):
    uid = _user(app)
    with app.app_context():
        # 20:00 UTC yesterday is 01:30 *today* in India (UTC+5:30).
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        e = JournalEntry(user_id=uid, title='t', encrypted_content='', mood_score=4, mood_label='Good',
                         created_at=datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=20))
        db.session.add(e)
        db.session.commit()
    _login(client)
    client.set_cookie('mt_tz', '330')
    ist = client.get('/insights/?range=7').data.decode()
    client.set_cookie('mt_tz', '0')
    utc = client.get('/insights/?range=7').data.decode()
    assert 'on 1 of 7 days' in ist and 'on 1 of 7 days' in utc
    import re
    def chart_days(html):
        import json
        series = json.loads(re.search(r'id="mood-series">(.*?)</script>', html, re.S).group(1))
        return [p['date'] for p in series if p['value'] is not None]
    assert chart_days(ist) != chart_days(utc)
