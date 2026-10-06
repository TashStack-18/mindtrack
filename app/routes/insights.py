from flask import Blueprint, render_template, request, g
from datetime import datetime, timedelta
from app.utils.decorators import login_required
from app.models.journal import JournalEntry
from app.services.insight_service import generate_insights

bp = Blueprint('insights', __name__, url_prefix='/insights')

@bp.route('/')
@login_required
def index():
    date_range = request.args.get('range', '7')
    
    query = JournalEntry.query.filter_by(user_id=g.user.id)
    range_label = "All time"
    
    if date_range != 'all':
        try:
            days = int(date_range)
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(JournalEntry.created_at >= cutoff)
            range_label = f"Last {days} days"
        except ValueError:
            pass
            
    entries = query.order_by(JournalEntry.created_at.desc()).all()
    insights = generate_insights(entries, range_label)
    
    return render_template('insights.html', insights=insights, current_range=date_range, entry_count=len(entries))
