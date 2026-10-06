import re

THEME_CATEGORIES = {
    'Academics': [
        'exam', 'exams', 'assignment', 'assignments', 'deadline', 'deadlines', 
        'class', 'college', 'university', 'study', 'studying', 'project', 
        'projects', 'grade', 'grades', 'test', 'tests', 'lecture', 'semester'
    ],
    'Sleep': [
        'sleep', 'slept', 'sleeping', 'tired', 'fatigue', 'exhausted', 
        'insomnia', 'awake', 'rest', 'bedtime', 'stayed up late', 
        'stayed awake', 'couldn\'t sleep', 'didn\'t sleep', 'hardly slept', 
        'slept badly', 'sleep deprived', 'late night'
    ],
    'Social': [
        'friend', 'friends', 'friendship', 'roommate', 'roommates', 
        'party', 'social', 'hangout', 'outing'
    ],
    'Family': [
        'mom', 'mother', 'dad', 'father', 'parents', 'family', 
        'sister', 'brother', 'sibling', 'home'
    ],
    'Work': [
        'work', 'job', 'office', 'internship', 'intern', 'manager', 
        'colleague', 'meeting', 'workplace'
    ],
    'Exercise': [
        'gym', 'workout', 'exercise', 'running', 'run', 'walk', 
        'walking', 'yoga', 'fitness'
    ],
    'Finance': [
        'money', 'expense', 'expenses', 'fees', 'fee', 'rent', 
        'budget', 'salary', 'financial', 'finance', 'spending'
    ]
}

# Pre-compile regex patterns with word boundaries for case-insensitive matching
THEME_REGEXES = {}
for category, keywords in THEME_CATEGORIES.items():
    # \b ensures we only match whole words
    pattern = r'\b(' + '|'.join(map(re.escape, keywords)) + r')\b'
    THEME_REGEXES[category] = re.compile(pattern, re.IGNORECASE)

def detect_themes(text):
    """
    Detects recurring life-context themes in text using transparent keyword matching.
    Returns a list of detected theme names.
    """
    if not text or not text.strip():
        return []

    detected = set()
    for category, regex in THEME_REGEXES.items():
        if regex.search(text):
            detected.add(category)
            
    return sorted(list(detected))

def get_theme_explanation(theme_name):
    """
    Returns a short explainable reason for a detected theme.
    """
    explanations = {
        'Academics': 'Detected because your entry contains terms associated with exams, assignments, and studying.',
        'Sleep': 'Detected because your entry contains terms related to sleep, rest, or fatigue.',
        'Social': 'Detected because your entry mentions friends, social events, or roommates.',
        'Family': 'Detected because your entry mentions family members or home.',
        'Work': 'Detected because your entry mentions work, office, or colleagues.',
        'Exercise': 'Detected because your entry contains terms associated with working out, gym, or fitness.',
        'Finance': 'Detected because your entry mentions money, expenses, or budgeting.'
    }
    return explanations.get(theme_name, 'Detected based on keywords in your journal entry.')
