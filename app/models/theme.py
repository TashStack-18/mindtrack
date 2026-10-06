from app.extensions import db

class DetectedTheme(db.Model):
    __tablename__ = 'detected_themes'

    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id', ondelete='CASCADE'), nullable=False)
    theme_name = db.Column(db.String(50), nullable=False)

    journal = db.relationship('JournalEntry', back_populates='detected_themes')

    def __repr__(self):
        return f'<DetectedTheme {self.theme_name} for Journal {self.journal_id}>'
