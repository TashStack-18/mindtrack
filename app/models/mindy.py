from app.extensions import db
from datetime import datetime

class MindyConversation(db.Model):
    __tablename__ = 'mindy_conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), default="New Conversation")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="active") # active, completed
    
    messages = db.relationship('MindyMessage', backref='conversation', lazy=True, cascade='all, delete-orphan')

class MindyMessage(db.Model):
    __tablename__ = 'mindy_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('mindy_conversations.id'), nullable=False)
    sender = db.Column(db.String(10), nullable=False) # 'user' or 'mindy'
    encrypted_message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
