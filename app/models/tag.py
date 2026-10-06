from app.extensions import db
from datetime import datetime

# Association table for Many-to-Many relationship between JournalEntry and Tag
journal_tags = db.Table('journal_tags',
    db.Column('journal_id', db.Integer, db.ForeignKey('journal_entries.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(50), nullable=False)

    user = db.relationship('User', back_populates='tags')
    
    # Relationship to JournalEntry is defined in JournalEntry model using back_populates

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_user_tag_name'),
    )

    def __repr__(self):
        return f'<Tag {self.name}>'
