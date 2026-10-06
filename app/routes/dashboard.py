from flask import Blueprint, render_template, g, redirect, url_for
from app.routes.auth import login_required

bp = Blueprint('dashboard', __name__)

@bp.route('/')
def index():
    if g.user:
        return redirect(url_for('dashboard.dashboard_view'))
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard_view():
    from app.models.journal import JournalEntry
    from app.services.insight_service import generate_insights
    recent_entries = JournalEntry.query.filter_by(user_id=g.user.id).order_by(JournalEntry.created_at.desc()).limit(3).all()
    
    dashboard_insight = None
    all_entries = JournalEntry.query.filter_by(user_id=g.user.id).order_by(JournalEntry.created_at.desc()).all()
    insights = generate_insights(all_entries, "All time")
    if insights:
        dashboard_insight = insights[0]
        
    return render_template('dashboard.html', recent_entries=recent_entries, dashboard_insight=dashboard_insight)

