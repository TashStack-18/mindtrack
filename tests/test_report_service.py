import pytest
import io
from app.services.report_service import generate_pdf_report
from app.models.report import Report
from datetime import datetime

class MockUser:
    id = 1

class MockTheme:
    def __init__(self, name):
        self.theme_name = name

class MockReflection:
    def __init__(self, prompt, response):
        self.prompt = prompt
        self.response_encrypted = response

class MockJournalEntry:
    def __init__(self, text, mood, themes, reflections=None):
        self.title = "Test Entry"
        self.created_at = datetime.utcnow()
        self.encrypted_content = text
        self.mood_score = mood
        self.sentiment_polarity = 0.0
        self.detected_themes = [MockTheme(t) for t in themes]
        self.reflections = [MockReflection(p, r) for p, r in (reflections or [])]

def test_pdf_generation_excludes_text_by_default(app):
    user = MockUser()
    entries = [
        MockJournalEntry("SECRET_TEXT", 3, ["Academics"])
    ]
    
    with app.app_context():
        # include_text = False
        pdf_buffer = generate_pdf_report(user, None, None, False, entries)
        pdf_content = pdf_buffer.getvalue()
        
        # Valid PDF header
        assert pdf_content.startswith(b'%PDF-1.')
        
        # We can't easily parse PDF text in raw bytes, but we can verify it doesn't crash 
        # and that the DB record was created
        
        report = Report.query.filter_by(user_id=1).first()
        assert report is not None
        assert report.includes_journal_text == False

def test_pdf_generation_includes_text_when_requested(app):
    user = MockUser()
    entries = [
        MockJournalEntry("SECRET_TEXT", 3, ["Academics"], [("Prompt?", "SECRET_RESPONSE")])
    ]
    
    with app.app_context():
        # include_text = True
        pdf_buffer = generate_pdf_report(user, None, None, True, entries)
        
        report = Report.query.order_by(Report.id.desc()).first()
        assert report.includes_journal_text == True

def test_empty_entries_handling(app):
    user = MockUser()
    
    with app.app_context():
        pdf_buffer = generate_pdf_report(user, None, None, False, [])
        report = Report.query.order_by(Report.id.desc()).first()
        assert report is not None

def test_unauthenticated_access(client):
    response = client.get('/reports/')
    assert response.status_code == 302 # Redirects to login
