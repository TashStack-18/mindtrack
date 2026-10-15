"""Production configuration: DB URLs, cookies, startup checks, timezone endpoint."""
import json
import os
import subprocess
import sys

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.engine import make_url

from app import create_app
from app.config import normalize_database_url
from tests.conftest import TestConfig

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def config_in_subprocess(env_overrides, remove=()):
    """Evaluate app.config.Config in a fresh interpreter with a controlled environment."""
    env = {k: v for k, v in os.environ.items() if k not in remove}
    env.update({'SECRET_KEY': 'test-secret', 'MINTRACK_ENCRYPTION_KEY': Fernet.generate_key().decode()})
    env.update(env_overrides)
    code = (
        "import json; from app.config import Config as C;"
        "print(json.dumps({k: str(getattr(C, k, None)) for k in ['PRODUCTION','SQLALCHEMY_DATABASE_URI',"
        "'SESSION_COOKIE_NAME','SESSION_COOKIE_SECURE','AUTO_CREATE_TABLES','SEND_FILE_MAX_AGE_DEFAULT',"
        "'SQLALCHEMY_ENGINE_OPTIONS']}))"
    )
    # Variables set here win over the developer's .env (load_dotenv never overrides).
    r = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True, text=True,
                       timeout=60)
    return r


@pytest.mark.parametrize('given, expected', [
    ('postgres://u:p@host:5432/db', 'postgresql+psycopg://u:p@host:5432/db'),
    ('postgresql://u:p@host/db?sslmode=require', 'postgresql+psycopg://u:p@host/db?sslmode=require'),
    ('postgresql+psycopg://u:p@/db?host=/cloudsql/p:asia-south1:i', 'postgresql+psycopg://u:p@/db?host=/cloudsql/p:asia-south1:i'),
    ('sqlite:///instance/mindtrack.db', 'sqlite:///instance/mindtrack.db'),
    ('  postgres://u:p@h/db  ', 'postgresql+psycopg://u:p@h/db'),
    ('', ''),
])
def test_normalize_database_url(given, expected):
    assert normalize_database_url(given) == expected


def test_production_settings():
    r = config_in_subprocess({'MINDTRACK_ENV': 'production', 'DATABASE_URL': 'postgres://u:p@h/db'})
    assert r.returncode == 0, r.stderr
    c = json.loads(r.stdout)
    assert c['PRODUCTION'] == 'True'
    assert c['SQLALCHEMY_DATABASE_URI'] == 'postgresql+psycopg://u:p@h/db'
    assert c['SESSION_COOKIE_NAME'] == '__session'  # the only cookie Firebase Hosting forwards
    assert c['SESSION_COOKIE_SECURE'] == 'True'
    assert c['AUTO_CREATE_TABLES'] == 'False'
    assert c['SEND_FILE_MAX_AGE_DEFAULT'] == '3600'
    assert 'pool_pre_ping' in c['SQLALCHEMY_ENGINE_OPTIONS']


def test_cloud_run_is_detected_as_production():
    r = config_in_subprocess({'K_SERVICE': 'mindtrack', 'DATABASE_URL': 'postgresql://u:p@h/db'}, remove=('MINDTRACK_ENV',))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)['PRODUCTION'] == 'True'


def test_production_refuses_sqlite_fallback():
    r = config_in_subprocess({'MINDTRACK_ENV': 'production', 'DATABASE_URL': ''},
                             remove=('INSTANCE_CONNECTION_NAME', 'DB_NAME', 'DB_USER', 'DB_PASS'))
    assert r.returncode != 0
    assert 'must be set in production' in r.stderr


def test_cloud_sql_parts_compose_url_with_special_characters():
    password = 'p@ss:w/rd#?%'
    r = config_in_subprocess({'MINDTRACK_ENV': 'production', 'DATABASE_URL': '',
                              'INSTANCE_CONNECTION_NAME': 'proj:asia-south1:inst',
                              'DB_NAME': 'mindtrack', 'DB_USER': 'mindtrack_app', 'DB_PASS': password})
    assert r.returncode == 0, r.stderr
    url = make_url(json.loads(r.stdout)['SQLALCHEMY_DATABASE_URI'])
    assert url.drivername == 'postgresql+psycopg'
    assert url.password == password and url.username == 'mindtrack_app' and url.database == 'mindtrack'
    assert url.query['host'] == '/cloudsql/proj:asia-south1:inst'


def test_development_defaults():
    r = config_in_subprocess({'MINDTRACK_ENV': 'development', 'DATABASE_URL': ''}, remove=('K_SERVICE',))
    assert r.returncode == 0, r.stderr
    c = json.loads(r.stdout)
    assert c['PRODUCTION'] == 'False'
    assert c['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:///')
    assert c['SESSION_COOKIE_NAME'] == 'None'  # Flask default name "session"
    assert c['AUTO_CREATE_TABLES'] == 'True'


def test_invalid_encryption_key_fails_at_startup():
    class BadKey(TestConfig):
        MINTRACK_ENCRYPTION_KEY = 'not-a-fernet-key'
    with pytest.raises(ValueError) as exc:
        create_app(BadKey)
    assert 'not a valid Fernet key' in str(exc.value)
    assert 'not-a-fernet-key' not in str(exc.value)  # never echo the key


def test_tables_only_created_when_allowed_and_init_db_command():
    class NoAutoCreate(TestConfig):
        AUTO_CREATE_TABLES = False
    app = create_app(NoAutoCreate)
    from sqlalchemy import inspect
    from app.extensions import db
    with app.app_context():
        assert inspect(db.engine).get_table_names() == []
        result = app.test_cli_runner().invoke(args=['init-db'])
        assert 'Database tables are ready' in result.output
        assert 'users' in inspect(db.engine).get_table_names()


def test_timezone_endpoint_stores_offset_in_session(client, app):
    assert client.post('/tz', json={'offset': 'abc'}).status_code == 400
    assert client.post('/tz', json={'offset': 99999}).status_code == 400
    assert client.post('/tz', json={'offset': 330}).status_code == 204
    with client.session_transaction() as sess:
        assert sess['tz_offset'] == 330
    from app.services.time_service import tz_offset_minutes
    with app.test_request_context('/'):
        from flask import session
        session['tz_offset'] = 330
        assert tz_offset_minutes() == 330  # no mt_tz cookie (as behind Firebase Hosting)


def test_pages_are_never_publicly_cacheable(client):
    for path in ('/', '/login', '/register', '/health'):
        cc = client.get(path).headers.get('Cache-Control', '')
        assert 'private' in cc and 'public' not in cc, path


def test_static_assets_served(client):
    for path in ('/static/css/style.css', '/static/js/app.js', '/static/js/mindy.js', '/static/img/mindy-full.svg'):
        r = client.get(path)
        assert r.status_code == 200, path
        r.close()
