from flask import Flask, session, g
from app.config import Config
from app.extensions import db, csrf

def _check_encryption_key(key):
    """Fail fast at startup if the Fernet key is malformed, instead of on the
    first journal read. Never logs the key. Existing data can only be read
    with the ORIGINAL key, so a replacement must never be generated here."""
    from cryptography.fernet import Fernet
    try:
        Fernet(key.encode('utf-8'))
    except Exception:
        raise ValueError("MINTRACK_ENCRYPTION_KEY is not a valid Fernet key (expected 32 url-safe base64-encoded bytes).") from None


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    _check_encryption_key(app.config.get('MINTRACK_ENCRYPTION_KEY'))

    db.init_app(app)
    csrf.init_app(app)

    from app import models  # noqa: F401  (register all tables on db.metadata)
    if app.config.get('AUTO_CREATE_TABLES', True):
        with app.app_context():
            db.create_all()

    @app.cli.command('init-db')
    def init_db_command():
        """Create any missing tables (safe to re-run; never drops or alters data)."""
        db.create_all()
        print('Database tables are ready.')

    # Load user into g before every request
    @app.before_request
    def load_logged_in_user():
        user_id = session.get('user_id')
        if user_id is None:
            g.user = None
        else:
            from app.models.user import User
            g.user = User.query.get(user_id)

    @app.context_processor
    def inject_copy():
        from app.services.copy_service import CopyService
        from datetime import datetime, timezone
        from app.models.journal import JournalEntry
        from flask import request
        
        def _get_copy(slot, **kwargs):
            if not g.user:
                return CopyService().get(slot, **kwargs)
                
            entries = JournalEntry.query.filter_by(user_id=g.user.id).order_by(JournalEntry.created_at.desc()).all()
            entry_count = len(entries)
            
            latest_mood = None
            gap_days = 0
            if entries:
                latest_mood = entries[0].mood_score
                # rough gap logic
                gap_delta = datetime.utcnow() - entries[0].created_at
                gap_days = gap_delta.days
                
            # The client sets time of day via JS data attribute later, but we use server time as default
            # To get accurate time, the request object might carry a timezone offset in future, but for now utcnow
            
            c = CopyService(
                user_id=g.user.id, 
                name=g.user.name,
                entry_count=entry_count,
                latest_mood=latest_mood,
                gap_days=gap_days
            )
            return c.get(slot, **kwargs)
            
        return dict(copy=_get_copy)

    # Register blueprints
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.journal import bp as journal_bp
    from app.routes.insights import bp as insights_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.mindy import bp as mindy_bp
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(mindy_bp)

    @app.after_request
    def keep_pages_private(response):
        """Pages contain personal data: tell Firebase Hosting's CDN (and any
        shared cache) never to store them. Static files keep their own
        public caching headers."""
        from flask import request
        if not request.path.startswith('/static/') and not response.headers.get('Cache-Control'):
            response.headers['Cache-Control'] = 'private, no-cache'
        return response

    @app.route('/health')
    def health_check():
        return 'OK', 200

    @app.route('/tz', methods=['POST'])
    def set_timezone():
        """Remember the browser's UTC offset in the session. Needed behind
        Firebase Hosting, which strips every cookie except __session (so the
        mt_tz cookie never reaches the app there). CSRF-protected."""
        from flask import request, session
        from app.services.time_service import MAX_OFFSET_MINUTES
        data = request.get_json(silent=True) or {}
        try:
            offset = int(data.get('offset'))
        except (TypeError, ValueError):
            return {'error': 'invalid offset'}, 400
        if not -MAX_OFFSET_MINUTES <= offset <= MAX_OFFSET_MINUTES:
            return {'error': 'invalid offset'}, 400
        session['tz_offset'] = offset
        return '', 204


    return app
