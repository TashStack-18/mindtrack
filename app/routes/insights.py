from flask import Blueprint, render_template, request, g
from app.routes.auth import login_required
from app.models.journal import JournalEntry
from app.services.insight_service import build_insights_view, resolve_period, RANGES
from app.services.time_service import tz_offset_minutes, local_today, to_local, utc_range_for_local_days

bp = Blueprint('insights', __name__, url_prefix='/insights')


def _entries_between(user_id, first_day, last_day, offset):
    start, end = utc_range_for_local_days(first_day, last_day, offset)
    return (JournalEntry.query
            .filter(JournalEntry.user_id == user_id, JournalEntry.created_at >= start, JournalEntry.created_at < end)
            .order_by(JournalEntry.created_at.asc())
            .all())


@bp.route('/')
@login_required
def index():
    range_key = request.args.get('range', '7')
    if range_key not in RANGES:
        range_key = '7'

    offset = tz_offset_minutes()
    today = local_today(offset)

    def local_day_of(entry):
        return to_local(entry.created_at, offset).date()

    earliest = None
    if range_key == 'all':
        first = JournalEntry.query.filter_by(user_id=g.user.id).order_by(JournalEntry.created_at.asc()).first()
        earliest = local_day_of(first) if first else today

    period = resolve_period(range_key, today, earliest)
    entries = _entries_between(g.user.id, period['first_day'], period['last_day'], offset)
    prev_entries = (_entries_between(g.user.id, period['prev_first'], period['prev_last'], offset)
                    if period['prev_first'] else [])

    view = build_insights_view(entries, prev_entries, period, local_day_of)
    total_entries = JournalEntry.query.filter_by(user_id=g.user.id).count()

    return render_template('insights.html', view=view, current_range=range_key, total_entries=total_entries,
                           # kept for templates/tests that use the previous names
                           insights=view['observations'], entry_count=view['count'], entries=entries)
