from flask import Blueprint, render_template, g, redirect, url_for
from app.routes.auth import login_required
from datetime import datetime, timedelta

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
    from app.services.time_service import tz_offset_minutes, to_local

    # Dates and greeting follow the user's local clock (timestamps are stored in UTC).
    offset = tz_offset_minutes()
    local_now = to_local(datetime.utcnow(), offset)
    local_day = lambda e: to_local(e.created_at, offset).date()

    # Time aware greeting and key for Your Day cards
    hour = local_now.hour
    if hour < 12:
        greeting_time = "Good morning"
        time_of_day_key = "morning"
    elif hour < 17:
        greeting_time = "Good afternoon"
        time_of_day_key = "afternoon"
    elif hour < 21:
        greeting_time = "Good evening"
        time_of_day_key = "evening"
    else:
        greeting_time = "Good evening" # Keep greeting simple
        time_of_day_key = "night"

    recent_entries = JournalEntry.query.filter_by(user_id=g.user.id).order_by(JournalEntry.created_at.desc()).limit(10).all()
    all_entries_asc = JournalEntry.query.filter_by(user_id=g.user.id).order_by(JournalEntry.created_at.asc()).all()
    all_entries = list(reversed(all_entries_asc))

    # Check if checked in today
    today = local_now.date()
    checked_in_today = any(local_day(e) == today for e in recent_entries) if recent_entries else False
    today_entry = recent_entries[0] if checked_in_today else None

    # Current calendar week (Monday to Sunday)
    start_of_week = today - timedelta(days=today.weekday())
    this_week = []
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        # Get all entries for this day
        day_entries = [e for e in all_entries if local_day(e) == d]
        # Most recent entry for the day is the first one in the filtered list (since all_entries is ordered desc)
        latest_entry = day_entries[0] if day_entries else None
        this_week.append({
            'date': d,
            'day_name': d.strftime('%a')[:3], # Mon, Tue, etc.
            'day_num': d.day,
            'is_today': d == today,
            'entry': latest_entry,
            'count': len(day_entries)
        })

    dashboard_insight = None
    insights = generate_insights(all_entries_asc, "All time")
    if insights:
        dashboard_insight = insights[0]

    reflection_prompt = "Is there another way to look at how you're feeling right now?"
    if recent_entries:
        from app.services.reflection_service import prompt_for_entry
        reflection_prompt = prompt_for_entry(recent_entries[0])

    # Daily inspirational photo: chosen from the calendar date, not at random,
    # so it stays the same all day. The browser re-applies this with the local date.
    from app.services.inspiration_service import image_for_date, all_image_paths, INSPIRATION_DIR, FALLBACK_IMAGE
    daily_photo = image_for_date()
    daily_photo_options = all_image_paths()
    daily_photo_fallback = INSPIRATION_DIR + FALLBACK_IMAGE

    # Prepare chart data
    chart_dates = []
    chart_scores = []
    for entry in all_entries_asc[-14:]: # last 14 entries
        chart_dates.append(to_local(entry.created_at, offset).strftime('%b %d'))
        chart_scores.append(entry.mood_score)

    from app.services.encryption_service import decrypt_text
    for entry in recent_entries:
        entry.local_time = to_local(entry.created_at, offset)
        try:
            entry.preview_text = decrypt_text(entry.encrypted_content)
        except Exception:
            entry.preview_text = "[Encrypted Content]"

    consistency_days = sum(1 for d in this_week if d['count'] > 0)

    return render_template(
        'dashboard.html',
        consistency_days=consistency_days,
        recent_entries=recent_entries,
        all_entries=all_entries,
        entry_count=len(all_entries),
        dashboard_insight=dashboard_insight,
        reflection_prompt=reflection_prompt,
        greeting_time=greeting_time,
        time_of_day_key=time_of_day_key,
        this_week=this_week,
        checked_in_today=checked_in_today,
        today_entry=today_entry,
        daily_photo=daily_photo,
        daily_photo_options=daily_photo_options,
        daily_photo_fallback=daily_photo_fallback,
        now=local_now,
        chart_dates=chart_dates,
        chart_scores=chart_scores
    )
