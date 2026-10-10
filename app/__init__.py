from flask import Flask, session, g
from app.config import Config
from app.extensions import db, csrf

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        # Ensure tables are created
        from app import models
        db.create_all()

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

    @app.route('/health')
    def health_check():
        return 'OK', 200


    return app
