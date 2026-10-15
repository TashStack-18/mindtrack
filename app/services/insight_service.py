from datetime import datetime
from statistics import mean

def generate_insights(entries, date_range_label="All time"):
    """
    Generates explainable insights based on a list of JournalEntry objects.
    All insights are dynamically generated and rule-based.
    """
    insights = []
    
    if not entries:
        return insights
        
    num_entries = len(entries)
    
    # Pre-calculate overall stats
    overall_moods = [e.mood_score for e in entries]
    overall_avg_mood = mean(overall_moods) if overall_moods else 0
    
    # 1. Recurring Theme & Mood Association Insights (needs >= 3 entries overall, and >= 3 per theme)
    if num_entries >= 3:
        theme_counts = {}
        theme_moods = {}
        
        for entry in entries:
            for dt in entry.detected_themes:
                name = dt.theme_name
                theme_counts[name] = theme_counts.get(name, 0) + 1
                theme_moods.setdefault(name, []).append(entry.mood_score)
                
        for theme, count in theme_counts.items():
            if count >= 3:
                # RECURRING THEME
                insights.append({
                    "type": "recurring_theme",
                    "title": f"{theme} appeared frequently in your recent entries.",
                    "description": f"You mentioned {theme} in {count} of your last {num_entries} entries.",
                    "why": [
                        f"Detected in {count} entries",
                        f"Selected period: {date_range_label}"
                    ],
                    "severity": "info",
                    "reflection_hook": theme.lower()
                })
                
                # MOOD / CONTEXT ASSOCIATION
                theme_avg_mood = mean(theme_moods[theme])
                diff = theme_avg_mood - overall_avg_mood
                
                if abs(diff) >= 0.5: # Meaningful difference threshold
                    direction = "lower" if diff < 0 else "higher"
                    insights.append({
                        "type": "mood_association",
                        "title": f"Entries mentioning {theme} had a {direction} recorded mood than your overall average.",
                        "description": f"There appears to be an association between {theme} and {direction} recorded moods during this period.",
                        "why": [
                            f"{theme} entries: {count}",
                            f"{theme}-entry average mood: {theme_avg_mood:.1f}/5",
                            f"Overall average mood: {overall_avg_mood:.1f}/5",
                            f"Date range: {date_range_label}"
                        ],
                        "severity": "notable",
                        "reflection_hook": theme.lower()
                    })

    # 2. Frequent Feelings (needs >= 3 entries)
    if num_entries >= 3:
        feeling_counts = {}
        for entry in entries:
            for f in entry.feelings:
                feeling_counts[f] = feeling_counts.get(f, 0) + 1
                
        for feeling, count in feeling_counts.items():
            # If a feeling appears in at least 3 entries
            if count >= 3:
                insights.append({
                    "type": "frequent_feeling",
                    "title": f"You chose {feeling.capitalize()} on several recent entries.",
                    "description": f"You recorded feeling {feeling} in {count} of your last {num_entries} entries.",
                    "why": [
                        f"Selected in {count} entries",
                        f"Selected period: {date_range_label}"
                    ],
                    "severity": "info",
                    "reflection_hook": feeling.lower()
                })

    # 3. Trends (needs >= 6 entries)
    if num_entries >= 6:
        # Sort chronologically for trend comparison (assuming input is reverse-chron or chron, let's ensure chron)
        chron_entries = sorted(entries, key=lambda e: e.created_at)
        half = num_entries // 2
        
        previous_half = chron_entries[:half]
        recent_half = chron_entries[half:]
        
        # MOOD TREND
        prev_mood_avg = mean([e.mood_score for e in previous_half])
        recent_mood_avg = mean([e.mood_score for e in recent_half])
        
        mood_diff = recent_mood_avg - prev_mood_avg
        if abs(mood_diff) >= 0.5:
            direction = "decreased" if mood_diff < 0 else "increased"
            insights.append({
                "type": "mood_trend",
                "title": f"Your recorded mood has {direction} recently.",
                "description": "Based on your recorded entries, there is a visible shift in your mood scores.",
                "why": [
                    f"Recent average: {recent_mood_avg:.1f}/5",
                    f"Previous average: {prev_mood_avg:.1f}/5",
                    f"Based on the last {num_entries} entries"
                ],
                "severity": "notable",
                "reflection_hook": "trend"
            })
            
        # SENTIMENT TREND
        prev_sent_avg = mean([e.sentiment_polarity or 0.0 for e in previous_half])
        recent_sent_avg = mean([e.sentiment_polarity or 0.0 for e in recent_half])
        
        sent_diff = recent_sent_avg - prev_sent_avg
        if abs(sent_diff) >= 0.2:
            direction = "negative" if sent_diff < 0 else "positive"
            insights.append({
                "type": "sentiment_trend",
                "title": f"The language in your recent journal entries has been more {direction} than earlier entries.",
                "description": "The text-analysis sentiment model detected a shift in polarity.",
                "why": [
                    f"Recent average polarity: {recent_sent_avg:.2f}",
                    f"Previous average polarity: {prev_sent_avg:.2f}",
                    f"Based on the last {num_entries} entries"
                ],
                "severity": "info",
                "reflection_hook": "sentiment"
            })

    return insights


# ---------------------------------------------------------------------------
# Personalised Insights page (date range, chart series, contexts, evidence).
# Everything below is computed from the given user's own entries only.
# User-selected contexts (tags) and auto-detected themes are kept separate.
# ---------------------------------------------------------------------------
from collections import Counter
from datetime import timedelta

MOOD_NAMES = {1: 'Very Low', 2: 'Low', 3: 'Okay', 4: 'Good', 5: 'Great'}
GOOD_SCORES = (4, 5)
LOW_SCORES = (1, 2)

# Context tags offered in the journal. Older tag names are mapped onto them.
CONTEXT_TAGS = ['Study', 'Friends', 'Family', 'Home', 'Sleep', 'Health', 'Work', 'Achievement', 'Other']
CONTEXT_LABELS = {'Health': 'Health & wellbeing', 'Achievement': 'Personal achievement'}
CONTEXT_ALIASES = {'Academics': 'Study', 'Friends/Social': 'Friends', 'Social': 'Friends', 'Exercise': 'Health'}

RANGES = {'7': 7, '30': 30, 'all': None}
MIN_ENTRIES_FOR_INSIGHTS = 3
MIN_ENTRIES_PER_CONTEXT = 3

SUGGESTION_COPY = {
    'Friends': "You've recorded several good moments alongside time with friends. If it feels right, consider making a little room for the connections you enjoy.",
    'Study': "Several of your Study entries were recorded with a good mood. You could notice which parts of your study routine felt rewarding, rather than simply doing more of it.",
    'Family': "Some of your good moments came alongside family. It might be worth noticing what made those moments feel good.",
    'Home': "Several better-feeling entries happened alongside Home. Maybe notice what about being at home felt restoring.",
    'Sleep': "A number of entries tagged Sleep were recorded with a good mood. It could be worth noticing what helped you rest.",
    'Health': "You recorded good moods alongside health and wellbeing. If it feels good, keep making space for whatever helped.",
    'Achievement': "You noted achievements on several good days. Giving yourself credit for small wins seems worth keeping.",
    'Work': "Some of your good moments came alongside work. You might notice which parts of it felt satisfying.",
}
GENERAL_PROMPTS = [
    "What was one small thing that made today a little better?",
    "What would you like to give yourself credit for today?",
    "What do you need a little more of tomorrow?",
    "What's something you're looking forward to, even a tiny thing?",
    "Who or what helped you feel more like yourself recently?",
]


def context_label(name):
    return CONTEXT_LABELS.get(name, name)


def entry_contexts(entry):
    """User-selected contexts for an entry, with legacy tag names normalised."""
    names = []
    for tag in entry.tags or []:
        name = CONTEXT_ALIASES.get(tag.name, tag.name)
        if name not in names:
            names.append(name)
    return names


def general_prompt_for(day):
    """A general reflection prompt that rotates by date (never claims a pattern)."""
    return GENERAL_PROMPTS[day.toordinal() % len(GENERAL_PROMPTS)]


def resolve_period(range_key, today, earliest_day=None):
    """Return the selected local-date period and the equivalent previous period."""
    if range_key not in RANGES:
        range_key = '7'
    days = RANGES[range_key]
    if days is None:
        first = min(earliest_day or today, today)
        return {
            'key': 'all', 'label': 'All time', 'phrase': 'across all your entries',
            'first_day': first, 'last_day': today, 'days': (today - first).days + 1,
            'prev_first': None, 'prev_last': None,
        }
    first = today - timedelta(days=days - 1)
    return {
        'key': range_key, 'label': f'Last {days} days', 'phrase': f'in the last {days} days',
        'first_day': first, 'last_day': today, 'days': days,
        'prev_first': first - timedelta(days=days), 'prev_last': first - timedelta(days=1),
    }


def _group(score):
    return 'good' if score in GOOD_SCORES else 'low' if score in LOW_SCORES else 'okay'


def build_insights_view(entries, prev_entries, period, local_day_of):
    """
    entries:      this user's entries inside the period
    prev_entries: this user's entries in the previous equivalent period ([] for 'all')
    local_day_of: function(entry) -> the entry's local calendar date
    """
    n = len(entries)
    scores = [e.mood_score for e in entries]
    view = {'period': period, 'count': n}

    # --- Summary statistics ------------------------------------------------
    stats = {'count': n, 'days_with_entries': len({local_day_of(e) for e in entries})}
    if n:
        counts = Counter(scores)
        top = max(counts.values())
        stats['top_moods'] = [MOOD_NAMES[s] for s in sorted(counts, reverse=True) if counts[s] == top]
        stats['top_mood_count'] = top
        stats['average'] = round(mean(scores), 1)
        stats['average_label'] = MOOD_NAMES[min(5, max(1, int(round(mean(scores)))))]
        stats['good_count'] = sum(1 for s in scores if s in GOOD_SCORES)
        stats['distribution'] = [{'score': s, 'label': MOOD_NAMES[s], 'count': counts.get(s, 0)} for s in range(5, 0, -1)]
    prev_n = len(prev_entries)
    stats['previous_count'] = prev_n if period['prev_first'] else None
    if period['prev_first'] and n >= MIN_ENTRIES_FOR_INSIGHTS and prev_n >= MIN_ENTRIES_FOR_INSIGHTS:
        prev_avg = mean(e.mood_score for e in prev_entries)
        stats['previous_average'] = round(prev_avg, 1)
        stats['average_change'] = round(mean(scores) - prev_avg, 1)
    view['stats'] = stats

    # --- Chart series: one point per day (or per week for long ranges) -----
    by_day = {}
    for e in entries:
        by_day.setdefault(local_day_of(e), []).append(e)
    weekly = period['days'] > 62
    span = 7 if weekly else 1
    points = []
    day = period['first_day']
    while day <= period['last_day']:
        bucket = [e for i in range(span) for e in by_day.get(day + timedelta(days=i), [])]
        bucket_scores = [e.mood_score for e in bucket]
        points.append({
            'date': day.isoformat(),
            'label': f"Week of {day.strftime('%b %d')}" if weekly else day.strftime('%a %d %b'),
            'short': day.strftime('%a') if period['days'] <= 7 else day.strftime('%b %d'),
            'value': round(mean(bucket_scores), 2) if bucket_scores else None,  # None = no check-in; never filled in
            'count': len(bucket_scores),
            'moods': [MOOD_NAMES[s] for s in bucket_scores],
            'contexts': sorted({context_label(c) for e in bucket for c in entry_contexts(e)}),
        })
        day += timedelta(days=span)
    view['series'] = points
    view['series_unit'] = 'week' if weekly else 'day'
    view['points_with_data'] = sum(1 for p in points if p['value'] is not None)

    # Plain-language summary of the chart for screen readers / text users.
    recorded = [p for p in points if p['value'] is not None]
    unit = 'weeks' if weekly else 'days'
    if recorded:
        parts = [f"{p['label']}: {', '.join(p['moods'])}" for p in recorded[-14:]]
        view['chart_summary'] = (f"Recorded moods {period['phrase']} ({len(recorded)} of {len(points)} {unit} have check-ins). "
                                 + '; '.join(parts) + '.')
    else:
        view['chart_summary'] = f"No mood check-ins {period['phrase']}."

    # --- Contexts (user-selected) and themes (auto-detected) ---------------
    ctx = {}
    for e in entries:
        for name in entry_contexts(e):
            c = ctx.setdefault(name, {'name': name, 'label': context_label(name), 'count': 0,
                                      'by_score': {s: 0 for s in range(1, 6)}, 'good': 0, 'okay': 0, 'low': 0})
            c['count'] += 1
            c['by_score'][e.mood_score] += 1
            c[_group(e.mood_score)] += 1
    contexts = sorted(ctx.values(), key=lambda c: (-c['count'], c['name']))
    for c in contexts:
        c['share'] = round(100 * c['count'] / n) if n else 0
    view['contexts'] = contexts
    view['entries_with_context'] = sum(1 for e in entries if entry_contexts(e))

    theme_counts = Counter(t.theme_name for e in entries for t in (e.detected_themes or []))
    view['themes'] = [{'name': k, 'count': v} for k, v in theme_counts.most_common()]

    # --- Evidence-based observations -----------------------------------------
    observations = []
    if n >= MIN_ENTRIES_FOR_INSIGHTS:
        good = stats['good_count']
        low = sum(1 for s in scores if s in LOW_SCORES)
        if good * 2 > n:
            title = f"{good} of your {n} check-ins {period['phrase']} were Good or Great."
        elif low * 2 > n:
            title = f"{low} of your {n} check-ins {period['phrase']} were Low or Very Low."
        else:
            title = f"Your {n} check-ins {period['phrase']} were spread across different moods."
        observations.append({
            'kind': 'distribution', 'title': title,
            'evidence': [f"{d['label']}: {d['count']}" for d in stats['distribution'] if d['count']],
            'note': "These are the moods you selected, not a diagnosis.",
        })

        for c in contexts:
            if c['count'] < MIN_ENTRIES_PER_CONTEXT:
                continue
            label = c['label']
            evidence = [f"{label} appeared in {c['count']} of {n} entries {period['phrase']}",
                        f"Good/Great: {c['good']} · Okay: {c['okay']} · Low/Very Low: {c['low']}"]
            if c['good'] / c['count'] >= 0.6:
                observations.append({
                    'kind': 'context_mood', 'context': c['name'],
                    'title': f"You recorded a good mood in {c['good']} of your {c['count']} {label} entries {period['phrase']}.",
                    'evidence': evidence,
                    'note': "Appearing together doesn't mean one caused the other. It's just something to notice.",
                })
            elif c['low'] / c['count'] >= 0.6:
                observations.append({
                    'kind': 'context_mood', 'context': c['name'],
                    'title': f"{c['low']} of your {c['count']} {label} entries {period['phrase']} were recorded with a low mood.",
                    'evidence': evidence,
                    'note': f"If it feels useful, you could reflect on what tends to come up around {label.lower()}. Not a diagnosis, just a clue.",
                })

    if period['prev_first'] and (n or prev_n):
        prev_days = len({local_day_of(e) for e in prev_entries})
        observations.append({
            'kind': 'frequency',
            'title': (f"You checked in on {stats['days_with_entries']} of the last {period['days']} days, "
                      f"compared with {prev_days} in the {period['days']} days before."),
            'evidence': [f"This period: {n} entries", f"Previous period: {prev_n} entries"],
            'note': "Checking in more or less often is completely okay. This is just for your awareness.",
        })

    # Reuse the existing rule-based insights (detected themes, feelings, trends).
    for item in generate_insights(entries, period['label']):
        if item['type'] in ('recurring_theme', 'mood_association'):
            note = "Based on keywords detected in your writing, not on the contexts you selected."
        elif item['type'] == 'sentiment_trend':
            note = "Based on the tone of your writing (an automatic estimate), separate from the moods you chose."
        else:
            note = "Just something to notice, not a diagnosis."
        observations.append({'kind': item['type'], 'title': item['title'], 'evidence': item['why'], 'note': note})
    seen = set()
    view['observations'] = [o for o in observations if not (o['title'] in seen or seen.add(o['title']))]

    # --- Little things worth keeping -----------------------------------------
    suggestions = []
    for c in contexts:
        if c['count'] >= MIN_ENTRIES_PER_CONTEXT and c['good'] >= 2 and c['good'] / c['count'] >= 0.6:
            suggestions.append({
                'context': c['name'], 'label': c['label'],
                'text': SUGGESTION_COPY.get(c['name'], f"You recorded several good moments alongside {c['label']}. It might be worth noticing what made them feel good."),
                'evidence': f"{c['good']} of {c['count']} {c['label']} entries {period['phrase']} were Good or Great.",
            })
    view['suggestions'] = suggestions[:3]
    view['general_prompt'] = general_prompt_for(period['last_day'])
    view['enough_data'] = n >= MIN_ENTRIES_FOR_INSIGHTS
    return view
