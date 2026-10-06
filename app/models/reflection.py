from app.extensions import db
from datetime import datetime

class Reflection(db.Model):
    __tablename__ = 'reflections'

    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id', ondelete='CASCADE'), nullable=False)
    prompt = db.Column(db.String(500), nullable=False)
    response_encrypted = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    journal = db.relationship('JournalEntry', back_populates='reflections')

    def __repr__(self):
        return f'<Reflection {self.id}>'
