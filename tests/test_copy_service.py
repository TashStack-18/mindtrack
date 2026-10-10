import pytest
from datetime import datetime, timezone
from app.services.copy_service import CopyService

BANNED_WORDS = [
    "depress", "anxiety", "disorder", "diagnos", "clinical", "therapy",
    "treatment", "cure", "medication", "you have", "caused", "because of this",
    "your picture is forming", "streak", "points", "badge", "level",
    "trophy", "reward", "score", "AI", "Beta",
    # these shouldn't be in low-mood buckets:
    "great", "amazing", "awesome", "fantastic", "wonderful", "yay", "celebrate"
]

def test_determinism():
    c1 = CopyService(user_id=1, local_date_str="2026-10-08", local_hour=9)
    c2 = CopyService(user_id=1, local_date_str="2026-10-08", local_hour=9)
    assert c1.get("greeting") == c2.get("greeting")

def test_variety_across_days():
    c1 = CopyService(user_id=1, local_date_str="2026-10-08", local_hour=9)
    c2 = CopyService(user_id=1, local_date_str="2026-10-09", local_hour=9)
    # Could technically be the same occasionally due to small pool, but the logic ensures no repeat of yesterday.
    assert c1.get("greeting") != c2.get("greeting")

def test_name_usage():
    c = CopyService(user_id=1, name="Tashvi", local_date_str="2026-10-08", local_hour=9)
    # Get greeting, should use name
    greet = c.get("greeting")
    # Get subline, should NOT use name because max one per page
    subline = c.get("subline")
    assert "Tashvi" not in subline
    
    # Just checking logic handles zero data
    c2 = CopyService()
    assert c2.get("greeting")

def test_banned_words_and_emoji():
    c = CopyService(user_id=1, local_date_str="2026-10-08", local_hour=9, latest_mood=1)
    # Check all pools
    pools = [
        "greeting", "subline", "checkin_prompt", "day_card_caption",
        "quick_reflection", "reflect_card_intro", "history_recap",
        "writing_placeholder", "post_save_note", "empty_state_recent",
        "empty_state_chart", "empty_state_search", "affirmation",
        "line_for_today", "week_caption", "sprig_line", "mindy_note_fallback"
    ]
    
    for slot in pools:
        import re
        for _ in range(5): # test a few times to hit different hashes
            c.date_str = f"2026-10-0{_+1}"
            val = c.get(slot).lower()
            for word in BANNED_WORDS:
                pattern = r'\b' + re.escape(word.lower()) + r'\b'
                assert not re.search(pattern, val), f"Banned word '{word}' found in {slot}: {val}"
            # Check for emoji (basic check for typical emoji ranges or just characters > 0xFFFF)
            for char in val:
                assert ord(char) < 0x2600, f"Possible emoji found: {char} in {val}"
                
def test_2_5_optional_card():
    # Will implement the actual fetching in another service or route, but copy_service can expose the logic
    pass
