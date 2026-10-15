"""
Copy MindTrack data from the local SQLite database into PostgreSQL.

Safe by default:
  * The SQLite source is opened READ-ONLY; it is never modified.
  * Without --execute this is a DRY RUN: it validates and reports, writes nothing.
  * It refuses to write into a target that already contains MindTrack rows.
  * All writes happen in ONE transaction: any error rolls everything back.
  * Encrypted columns are copied byte-for-byte (never decrypted or re-encrypted),
    so the ORIGINAL MINTRACK_ENCRYPTION_KEY keeps working. If the key is set, the
    script checks that every encrypted value decrypts with it before copying.
  * After copying, it compares per-table row counts and checksums.
  * It never prints row contents, emails, or secrets (only counts, ids and a short
    key fingerprint you can compare with the production secret).

Usage (from the mindtrack folder, with .env present locally):
  # 1. Dry run (no writes anywhere)
  python scripts/migrate_sqlite_to_postgres.py --source instance/mindtrack.db --target "postgresql+psycopg://USER:PASS@127.0.0.1:5432/mindtrack"
  # 2. Real copy into an EMPTY database
  python scripts/migrate_sqlite_to_postgres.py --source instance/mindtrack.db --target "..." --execute

The target can also be given via the TARGET_DATABASE_URL environment variable.
To repeat a migration, recreate the (empty) target database and run again.
"""
import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa  # noqa: E402

from app.config import normalize_database_url  # noqa: E402
from app.extensions import db  # noqa: E402
import app.models  # noqa: E402,F401  (registers every table on db.metadata)

# Columns holding Fernet tokens. They are copied verbatim.
ENCRYPTED_COLUMNS = {
    ('journal_entries', 'encrypted_content'),
    ('reflections', 'response_encrypted'),
    ('mindy_messages', 'encrypted_message'),
}


class MigrationError(Exception):
    pass


def key_fingerprint(key):
    """Short, non-reversible fingerprint to confirm two environments use the same key."""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:12] if key else None


def open_sqlite_readonly(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise MigrationError(f"Source database not found: {path}")
    uri = path.as_uri() + '?mode=ro'
    return sa.create_engine('sqlite://', creator=lambda: sqlite3.connect(uri, uri=True))


def _normalize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return repr(round(value, 12))
    return value


def table_checksum(rows, columns):
    h = hashlib.sha256()
    for row in rows:
        h.update(repr(tuple(_normalize(row[c]) for c in columns)).encode('utf-8'))
    return h.hexdigest()


def _pk_columns(table):
    return [c.name for c in table.primary_key.columns]


def read_source(engine):
    """Read every model table from the source using the model column types
    (so SQLite datetime strings and 0/1 booleans become real Python values)."""
    insp = sa.inspect(engine)
    source_tables = set(insp.get_table_names())
    data, notes, errors = {}, [], []
    with engine.connect() as conn:
        for table in db.metadata.sorted_tables:
            if table.name not in source_tables:
                notes.append(f"{table.name}: not in source (will be created empty)")
                data[table.name] = {'columns': [], 'rows': []}
                continue
            src_cols = {c['name'] for c in insp.get_columns(table.name)}
            model_cols = [c.name for c in table.columns]
            extra = sorted(src_cols - set(model_cols))
            if extra:
                errors.append(f"{table.name}: source has columns not in the models {extra}; their data would be lost")
            missing = [c for c in model_cols if c not in src_cols]
            if missing:
                notes.append(f"{table.name}: source lacks columns {missing}; they will use defaults/NULL")
            common = [c for c in model_cols if c in src_cols]
            order = [table.c[c] for c in _pk_columns(table) if c in common]
            stmt = sa.select(*[table.c[c] for c in common]).order_by(*order)
            rows = [dict(r._mapping) for r in conn.execute(stmt)]
            data[table.name] = {'columns': common, 'rows': rows}
    return data, notes, errors


def validate(data, key=None):
    """Find problems PostgreSQL would reject (SQLite doesn't enforce them)."""
    errors, warnings = [], []
    tables = {t.name: t for t in db.metadata.sorted_tables}

    for name, info in data.items():
        table = tables[name]
        for row in info['rows']:
            ident = {c: row.get(c) for c in _pk_columns(table)}
            for col in table.columns:
                if col.name not in row:
                    continue
                value = row[col.name]
                if value is None and not col.nullable and not col.primary_key:
                    errors.append(f"{name} {ident}: {col.name} is NULL but NOT NULL in PostgreSQL")
                length = getattr(col.type, 'length', None)
                if length and isinstance(value, str) and len(value) > length:
                    errors.append(f"{name} {ident}: {col.name} has {len(value)} chars, limit {length}")

        # Foreign keys: SQLite was not enforcing them; PostgreSQL will.
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            parent_values = {r.get(fk.column.name) for r in data.get(parent, {}).get('rows', [])}
            for row in info['rows']:
                value = row.get(fk.parent.name)
                if value is not None and value not in parent_values:
                    ident = {c: row.get(c) for c in _pk_columns(table)}
                    errors.append(f"{name} {ident}: {fk.parent.name}={value} has no matching {parent}.{fk.column.name}")

    # Encrypted data must decrypt with the key production will use.
    enc_stats = {}
    if key:
        from cryptography.fernet import Fernet, InvalidToken
        fernet = Fernet(key.encode('utf-8'))
        for name, col in sorted(ENCRYPTED_COLUMNS):
            ok = bad = empty = 0
            for row in data.get(name, {}).get('rows', []):
                value = row.get(col)
                if not value:
                    empty += 1
                    continue
                try:
                    fernet.decrypt(value.encode('utf-8'))
                    ok += 1
                except (InvalidToken, ValueError, TypeError):
                    bad += 1
            enc_stats[f"{name}.{col}"] = {'decrypts': ok, 'fails': bad, 'empty': empty}
            if bad:
                errors.append(f"{name}.{col}: {bad} value(s) do not decrypt with the configured key "
                              f"(wrong key, or legacy plaintext; see scripts/encrypt_existing_data.py)")
    else:
        warnings.append("MINTRACK_ENCRYPTION_KEY not set: encrypted columns were not verified")
    return errors, warnings, enc_stats


def target_row_counts(engine):
    insp = sa.inspect(engine)
    existing = set(insp.get_table_names())
    counts = {}
    with engine.connect() as conn:
        for table in db.metadata.sorted_tables:
            if table.name in existing:
                counts[table.name] = conn.execute(sa.select(sa.func.count()).select_from(table)).scalar()
    return counts


def reset_postgres_sequences(conn):
    for table in db.metadata.sorted_tables:
        pks = list(table.primary_key.columns)
        if len(pks) == 1 and isinstance(pks[0].type, sa.Integer) and pks[0].autoincrement in (True, 'auto'):
            col = pks[0].name
            conn.execute(sa.text(
                f'SELECT setval(pg_get_serial_sequence(:t, :c), COALESCE(MAX("{col}"), 1), MAX("{col}") IS NOT NULL) '
                f'FROM "{table.name}"'
            ), {'t': table.name, 'c': col})


def copy_data(data, target_engine):
    tables = {t.name: t for t in db.metadata.sorted_tables}
    db.metadata.create_all(target_engine)  # creates missing tables only; never drops
    with target_engine.begin() as conn:  # one transaction: all or nothing
        for table in db.metadata.sorted_tables:  # parents before children
            rows = data.get(table.name, {}).get('rows', [])
            if rows:
                conn.execute(tables[table.name].insert(), rows)
        if target_engine.dialect.name == 'postgresql':
            reset_postgres_sequences(conn)


def verify_copy(data, target_engine):
    problems, summary = [], {}
    with target_engine.connect() as conn:
        for table in db.metadata.sorted_tables:
            info = data.get(table.name, {'columns': [], 'rows': []})
            cols = info['columns'] or [c.name for c in table.columns]
            order = [table.c[c] for c in _pk_columns(table)]
            rows = [dict(r._mapping) for r in conn.execute(sa.select(*[table.c[c] for c in cols]).order_by(*order))]
            same = table_checksum(rows, cols) == table_checksum(info['rows'], cols)
            summary[table.name] = {'source': len(info['rows']), 'target': len(rows), 'checksum_match': same}
            if len(rows) != len(info['rows']) or not same:
                problems.append(f"{table.name}: target does not match source")
    return problems, summary


def run(source, target=None, execute=False, key=None, out=print):
    """Returns a report dict. Raises MigrationError when it must stop."""
    report = {'executed': False}
    out(f"Source (read-only): {Path(source).resolve()}")
    src = open_sqlite_readonly(source)
    data, notes, schema_errors = read_source(src)
    src.dispose()
    report['source_counts'] = {name: len(info['rows']) for name, info in data.items()}
    for name, count in report['source_counts'].items():
        out(f"  {name:22s} {count} row(s)")
    for note in notes:
        out(f"  note: {note}")

    errors, warnings, enc_stats = validate(data, key)
    errors = schema_errors + errors
    report.update(errors=errors, warnings=warnings, encryption=enc_stats, key_fingerprint=key_fingerprint(key))
    if key:
        out(f"Encryption key fingerprint: {report['key_fingerprint']} (compare with the production secret)")
        for col, s in enc_stats.items():
            out(f"  {col}: {s['decrypts']} decrypt OK, {s['fails']} fail, {s['empty']} empty")
    for w in warnings:
        out(f"WARNING: {w}")
    if errors:
        for e in errors:
            out(f"ERROR: {e}")
        raise MigrationError(f"{len(errors)} problem(s) found; nothing was written.")

    if not target:
        out("No --target given: source validated only.")
        return report

    target_url = normalize_database_url(target)
    tgt = sa.create_engine(target_url)
    out(f"Target: {tgt.url.render_as_string(hide_password=True)}")
    try:
        existing = target_row_counts(tgt)
        nonempty = {t: n for t, n in existing.items() if n}
        if nonempty:
            raise MigrationError(f"Target already contains data {nonempty}; refusing to write. Use an empty database.")
        if not execute:
            out("DRY RUN: validation passed and the target is empty. Re-run with --execute to copy.")
            return report

        copy_data(data, tgt)
        problems, summary = verify_copy(data, tgt)
        report['executed'] = True
        report['verification'] = summary
        for name, s in summary.items():
            out(f"  {name:22s} source={s['source']} target={s['target']} checksum={'OK' if s['checksum_match'] else 'MISMATCH'}")
        if problems:
            raise MigrationError("Verification failed: " + '; '.join(problems))
        out("Migration complete and verified.")
        return report
    finally:
        tgt.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source', default='instance/mindtrack.db', help='SQLite file (opened read-only)')
    parser.add_argument('--target', default=os.environ.get('TARGET_DATABASE_URL'),
                        help='Target database URL (or TARGET_DATABASE_URL env var)')
    parser.add_argument('--execute', action='store_true', help='Actually copy (default is a dry run)')
    args = parser.parse_args(argv)
    try:
        run(args.source, args.target, args.execute, key=os.environ.get('MINTRACK_ENCRYPTION_KEY'))
    except MigrationError as e:
        print(f"STOPPED: {e}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
