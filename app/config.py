import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
# Local development reads secrets from .env. In production (Cloud Run) the
# variables come from the service configuration / Secret Manager instead;
# load_dotenv never overrides variables that are already set.
load_dotenv(os.path.join(os.path.dirname(basedir), '.env'))

DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(basedir), 'instance', 'mindtrack.db')


def _env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def is_production():
    """Production when explicitly requested, or when running on Cloud Run (K_SERVICE is set there)."""
    env = os.environ.get('MINDTRACK_ENV', '').strip().lower()
    if env:
        return env == 'production'
    return bool(os.environ.get('K_SERVICE'))


def normalize_database_url(url):
    """Make a DATABASE_URL usable by SQLAlchemy with the psycopg (v3) driver.

    - postgres://...           -> postgresql+psycopg://...   (Heroku-style scheme)
    - postgresql://...         -> postgresql+psycopg://...   (default driver is psycopg2, not installed)
    - postgresql+psycopg://... -> unchanged
    - sqlite:///...            -> unchanged
    Credentials and query parameters (e.g. ?host=/cloudsql/...) are preserved as-is.
    """
    if not url:
        return url
    url = url.strip()
    for prefix in ('postgres://', 'postgresql://'):
        if url.startswith(prefix):
            return 'postgresql+psycopg://' + url[len(prefix):]
    return url


def build_database_uri():
    """DATABASE_URL if set; otherwise compose a Cloud SQL socket URL from parts;
    otherwise (development only) the local SQLite file."""
    url = os.environ.get('DATABASE_URL')
    if url:
        return normalize_database_url(url)

    # Alternative to DATABASE_URL: separate parts, so a password with special
    # characters never has to be URL-encoded by hand.
    instance = os.environ.get('INSTANCE_CONNECTION_NAME')
    name, user = os.environ.get('DB_NAME'), os.environ.get('DB_USER')
    if instance and name and user:
        from sqlalchemy.engine import URL
        return URL.create(
            drivername='postgresql+psycopg',
            username=user,
            password=os.environ.get('DB_PASS'),
            database=name,
            query={'host': f'/cloudsql/{instance}'},
        ).render_as_string(hide_password=False)

    if is_production():
        # Cloud Run's filesystem is ephemeral; a SQLite file would silently lose data.
        raise ValueError("DATABASE_URL (or INSTANCE_CONNECTION_NAME, DB_NAME, DB_USER, DB_PASS) must be set in production.")
    return 'sqlite:///' + DEFAULT_SQLITE_PATH


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is missing.")

    PRODUCTION = is_production()

    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    if SQLALCHEMY_DATABASE_URI.startswith('postgresql'):
        # Small pool per instance (Cloud SQL has a connection limit), and check
        # connections before use so idle ones dropped by the server are replaced.
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 1800,
            'pool_size': int(os.environ.get('DB_POOL_SIZE', 5)),
            'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 2)),
        }

    # Tables are created automatically for local SQLite. In production the
    # schema is created explicitly (flask init-db / the migration script) so
    # several Cloud Run instances starting at once don't race on CREATE TABLE.
    AUTO_CREATE_TABLES = _env_flag('AUTO_CREATE_TABLES', default=not PRODUCTION)

    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = PRODUCTION  # HTTPS-only cookie in production
    if PRODUCTION:
        # Firebase Hosting forwards ONLY a cookie named "__session" to Cloud Run;
        # any other cookie name would silently break logins and CSRF.
        SESSION_COOKIE_NAME = '__session'
        PREFERRED_URL_SCHEME = 'https'
        # Let Firebase's CDN cache /static files for an hour (pages are not cached).
        SEND_FILE_MAX_AGE_DEFAULT = int(os.environ.get('STATIC_MAX_AGE', 3600))

    # Encryption
    MINTRACK_ENCRYPTION_KEY = os.environ.get('MINTRACK_ENCRYPTION_KEY')
    if not MINTRACK_ENCRYPTION_KEY:
        raise ValueError("MINTRACK_ENCRYPTION_KEY environment variable is missing. It must be configured for MindTrack to start securely.")
