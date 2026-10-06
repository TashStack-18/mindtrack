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

    # Register blueprints
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.journal import bp as journal_bp
    from app.routes.insights import bp as insights_bp
    from app.routes.reports import bp as reports_bp
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(reports_bp)

    @app.route('/health')
    def health_check():
        return 'OK', 200

    return app
