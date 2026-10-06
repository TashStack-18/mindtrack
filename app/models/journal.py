from app.extensions import db
from datetime import datetime
from app.models.tag import journal_tags

class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    encrypted_content = db.Column(db.Text, nullable=False)
    mood_score = db.Column(db.Integer, nullable=False)
    mood_label = db.Column(db.String(20), nullable=False)
    sentiment_polarity = db.Column(db.Float, nullable=True)
    sentiment_subjectivity = db.Column(db.Float, nullable=True)
    sentiment_label = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='journal_entries')
    tags = db.relationship('Tag', secondary=journal_tags, backref=db.backref('journal_entries', lazy='dynamic'))
    reflections = db.relationship('Reflection', back_populates='journal', cascade='all, delete-orphan')
    detected_themes = db.relationship('DetectedTheme', back_populates='journal', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<JournalEntry {self.title}>'
