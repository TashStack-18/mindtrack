import re
from app.models.theme import DetectedTheme

def generate_prompt(entry):
    """
    Generates a single CBT-inspired reflection prompt based on journal data.
    Uses a deterministic priority system.
    """
    text = entry.encrypted_content or ""
    text_lower = text.lower()
    
    # 1. Absolute-language/evidence check
    absolutes = ["always", "never", "everyone", "nobody", "nothing", "everything"]
    if any(word in text_lower for word in absolutes):
        return "Your entry uses an absolute statement. What experiences support that thought, and are there exceptions?"
        
    # 2. Strongly negative sentiment -> self-compassion or evidence reflection
    polarity = entry.sentiment_polarity or 0.0
    if polarity < -0.4:
        return "If a friend described this same situation to you, what would you say to them?"
        
    if polarity < -0.15:
        return "Is there another possible way to interpret what happened, even if your first interpretation still feels understandable?"
        
    # 3. Theme-aware reflection
    if entry.detected_themes:
        theme_names = [t.theme_name for t in entry.detected_themes]
        if "Academics" in theme_names:
            return "What part of the academic situation feels most important to you right now?"
        elif "Sleep" in theme_names:
            return "What might have contributed to how your sleep affected your day?"
        elif "Social" in theme_names:
            return "What about this interaction mattered most to you?"
        elif "Family" in theme_names:
            return "What feelings or thoughts came up most strongly around this situation?"
        elif "Work" in theme_names:
            return "What part of the work situation felt most significant to you?"
        elif "Exercise" in theme_names:
            return "How did this activity affect how you experienced the rest of your day?"
        elif "Finance" in theme_names:
            return "What part of the financial situation is taking up the most space in your thoughts?"
            
    # 4. Positive reflection
    if polarity > 0.15:
        return "What helped make this moment feel positive? Is there something from this experience you'd like to carry forward?"
        
    # 5. Neutral/general reflection
    return "What stands out most to you about this experience?"
