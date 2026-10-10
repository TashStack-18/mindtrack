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
    
    # Time aware greeting and key for Your Day cards
    hour = datetime.now().hour
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
    all_entries = JournalEntry.query.filter_by(user_id=g.user.id).order_by(JournalEntry.created_at.desc()).all()
    
    # Check if checked in today
    today = datetime.now().date()
    checked_in_today = any(e.created_at.date() == today for e in recent_entries) if recent_entries else False
    today_entry = recent_entries[0] if checked_in_today else None

    # Current calendar week (Monday to Sunday)
    start_of_week = today - timedelta(days=today.weekday())
    this_week = []
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        # Get all entries for this day
        day_entries = [e for e in all_entries if e.created_at.date() == d]
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
    insights = generate_insights(all_entries, "All time")
    if insights:
        dashboard_insight = insights[0]
        
    reflection_prompt = "Is there another way to look at how you're feeling right now?"
    if recent_entries:
        from app.services.reflection_service import generate_prompt
        reflection_prompt = generate_prompt(recent_entries[0])
        
    from flask import session
    import random

    hero_idx = session.get('hero_idx')
    mot_idx = session.get('mot_idx')
    
    if not hero_idx or not mot_idx:
        hero_choices = [i for i in range(1, 31) if i != g.user.last_hero_idx]
        hero_idx = random.choice(hero_choices) if hero_choices else 1
        
        mot_choices = [i for i in range(1, 31) if i != g.user.last_mot_idx and i != hero_idx]
        if not mot_choices:
            mot_choices = [i for i in range(1, 31) if i != g.user.last_mot_idx]
        mot_idx = random.choice(mot_choices) if mot_choices else 2
        
        session['hero_idx'] = hero_idx
        session['mot_idx'] = mot_idx
        
        from app.extensions import db
        g.user.last_hero_idx = hero_idx
        g.user.last_mot_idx = mot_idx
        db.session.commit()

    return render_template(
        'dashboard.html', 
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
        hero_idx=hero_idx,
        mot_idx=mot_idx,
        now=datetime.now()
    )
