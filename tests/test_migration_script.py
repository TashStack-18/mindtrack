"""The SQLite -> PostgreSQL migration script, exercised SQLite -> SQLite
(the copy logic is engine-agnostic; PostgreSQL-only steps are dialect-guarded)."""
import hashlib
import importlib.util
import os
import sqlite3
from datetime import datetime

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet

from app.extensions import db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('migrate', os.path.join(ROOT, 'scripts', 'migrate_sqlite_to_postgres.py'))
migrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrate)

KEY = Fernet.generate_key().decode()


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def make_source(path, extra_sql=()):
    engine = sa.create_engine(f'sqlite:///{path}')
    db.metadata.create_all(engine)
    f = Fernet(KEY.encode())
    when = datetime(2026, 3, 1, 9, 30, 15, 123456)
    with engine.begin() as c:
        c.execute(sa.text("INSERT INTO users (id,name,email,password_hash,created_at,updated_at,last_hero_idx,last_mot_idx) "
                          "VALUES (1,'A','a@x.com','hash-a',:w,:w,3,4),(7,'B','b@x.com','hash-b',:w,:w,1,2)"), {'w': when})
        c.execute(sa.text("INSERT INTO tags (id,user_id,name) VALUES (1,1,'Study'),(2,7,'Friends')"))
        c.execute(sa.text("INSERT INTO journal_entries (id,user_id,title,encrypted_content,mood_score,mood_label,feelings_raw,"
                          "sentiment_polarity,sentiment_subjectivity,sentiment_label,created_at,updated_at) VALUES "
                          "(5,1,'t1',:e1,4,'Good','calm',0.3333333333,0.5,'Positive',:w,:w),"
                          "(9,7,'t2',:e2,2,'Low',NULL,-0.2,0.1,'Negative',:w,:w)"),
                  {'e1': f.encrypt(b'secret one').decode(), 'e2': f.encrypt(b'secret two').decode(), 'w': when})
        c.execute(sa.text("INSERT INTO journal_tags (journal_id, tag_id) VALUES (5,1),(9,2)"))
        c.execute(sa.text("INSERT INTO reflections (id,journal_id,prompt,response_encrypted,created_at) VALUES (1,5,'p',:r,:w)"),
                  {'r': f.encrypt(b'answer').decode(), 'w': when})
        c.execute(sa.text("INSERT INTO reports (id,user_id,start_date,end_date,includes_journal_text,created_at) VALUES (1,1,NULL,:w,1,:w)"), {'w': when})
        c.execute(sa.text("INSERT INTO mindy_conversations (id,user_id,title,created_at,updated_at,completed_at,status) VALUES (3,7,'c',:w,:w,NULL,'active')"), {'w': when})
        c.execute(sa.text("INSERT INTO mindy_messages (id,conversation_id,sender,encrypted_message,created_at) VALUES (1,3,'user',:m,:w)"),
                  {'m': f.encrypt(b'hi').decode(), 'w': when})
        for sql in extra_sql:
            c.execute(sa.text(sql))
    engine.dispose()


def quiet(*_):
    pass


def test_full_copy_preserves_everything(tmp_path):
    src, dst = tmp_path / 'src.db', tmp_path / 'dst.db'
    make_source(src)
    before = sha(src)
    report = migrate.run(str(src), f'sqlite:///{dst}', execute=True, key=KEY, out=quiet)
    assert report['executed']
    assert all(s['checksum_match'] and s['source'] == s['target'] for s in report['verification'].values())
    assert sha(src) == before  # source never modified

    con = sqlite3.connect(dst)
    assert con.execute("select id, email, password_hash, last_hero_idx from users order by id").fetchall() == \
        [(1, 'a@x.com', 'hash-a', 3), (7, 'b@x.com', 'hash-b', 1)]
    assert con.execute("select journal_id, tag_id from journal_tags order by journal_id").fetchall() == [(5, 1), (9, 2)]
    assert con.execute("select includes_journal_text from reports").fetchone() == (1,)
    stored = con.execute("select encrypted_content from journal_entries where id=5").fetchone()[0]
    assert Fernet(KEY.encode()).decrypt(stored.encode()) == b'secret one'  # same key still works
    assert 'secret' not in stored
    created = con.execute("select created_at from journal_entries where id=5").fetchone()[0]
    assert created.startswith('2026-03-01 09:30:15.123456')


def test_dry_run_writes_nothing(tmp_path):
    src, dst = tmp_path / 'src.db', tmp_path / 'dst.db'
    make_source(src)
    report = migrate.run(str(src), f'sqlite:///{dst}', execute=False, key=KEY, out=quiet)
    assert not report['executed']
    eng = sa.create_engine(f'sqlite:///{dst}')
    assert sa.inspect(eng).get_table_names() == []


def test_refuses_non_empty_target(tmp_path):
    src, dst = tmp_path / 'src.db', tmp_path / 'dst.db'
    make_source(src)
    migrate.run(str(src), f'sqlite:///{dst}', execute=True, key=KEY, out=quiet)
    with pytest.raises(migrate.MigrationError, match='already contains data'):
        migrate.run(str(src), f'sqlite:///{dst}', execute=True, key=KEY, out=quiet)


def test_detects_orphans_that_postgres_would_reject(tmp_path):
    src = tmp_path / 'src.db'
    # SQLite does not enforce foreign keys by default, so orphans can exist.
    make_source(src, ["INSERT INTO journal_entries (id,user_id,title,encrypted_content,mood_score,mood_label) VALUES (50,999,'x','',3,'Okay')"])
    with pytest.raises(migrate.MigrationError):
        migrate.run(str(src), None, key=KEY, out=quiet)


def test_detects_values_too_long_for_postgres(tmp_path):
    src = tmp_path / 'src.db'
    make_source(src, ["UPDATE tags SET name = '" + 'x' * 60 + "' WHERE id = 1"])
    lines = []
    with pytest.raises(migrate.MigrationError):
        migrate.run(str(src), None, key=KEY, out=lines.append)
    assert any('limit 50' in line for line in lines)


def test_wrong_key_is_caught_before_copying(tmp_path):
    src, dst = tmp_path / 'src.db', tmp_path / 'dst.db'
    make_source(src)
    with pytest.raises(migrate.MigrationError):
        migrate.run(str(src), f'sqlite:///{dst}', execute=True, key=Fernet.generate_key().decode(), out=quiet)
    assert not dst.exists() or sa.inspect(sa.create_engine(f'sqlite:///{dst}')).get_table_names() == []


def test_output_never_contains_secrets_or_emails(tmp_path):
    src, dst = tmp_path / 'src.db', tmp_path / 'dst.db'
    make_source(src)
    lines = []
    migrate.run(str(src), f'sqlite:///{dst}', execute=True, key=KEY, out=lines.append)
    text = '\n'.join(lines)
    assert KEY not in text and 'a@x.com' not in text and 'hash-a' not in text
    assert migrate.key_fingerprint(KEY) in text


def test_missing_source_is_reported(tmp_path):
    with pytest.raises(migrate.MigrationError, match='not found'):
        migrate.run(str(tmp_path / 'nope.db'), None, out=quiet)
