from textblob import TextBlob
import logging

def analyze_text(text):
    """
    Analyzes text and returns polarity, subjectivity, and a classification label.
    This is text analysis only, not a clinical emotional assessment.
    """
    if not text or not text.strip():
        return {
            "polarity": 0.0,
            "subjectivity": 0.0,
            "label": "Neutral"
        }

    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        return {
            "polarity": polarity,
            "subjectivity": subjectivity,
            "label": classify_sentiment(polarity)
        }
    except Exception as e:
        logging.error(f"TextBlob analysis failed: {e}")
        return {
            "polarity": 0.0,
            "subjectivity": 0.0,
            "label": "Neutral"
        }

def classify_sentiment(polarity):
    """
    Classifies polarity based on simple product thresholds.
    """
    if polarity > 0.15:
        return "Positive"
    elif polarity < -0.15:
        return "Negative"
    else:
        return "Neutral"
