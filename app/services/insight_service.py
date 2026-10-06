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

    # 2. Trends (needs >= 6 entries)
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
