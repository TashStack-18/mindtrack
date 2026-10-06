import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(basedir), '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is missing.")
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(basedir), 'instance', 'mindtrack.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # Encryption
    MINTRACK_ENCRYPTION_KEY = os.environ.get('MINTRACK_ENCRYPTION_KEY')
    if not MINTRACK_ENCRYPTION_KEY:
        raise ValueError("MINTRACK_ENCRYPTION_KEY environment variable is missing. It must be configured for MindTrack to start securely.")
