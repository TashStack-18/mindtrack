from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

def _get_fernet():
    key = current_app.config.get('MINTRACK_ENCRYPTION_KEY')
    if not key:
        raise ValueError("Encryption key is missing in configuration.")
    try:
        return Fernet(key.encode('utf-8'))
    except Exception as e:
        raise ValueError("Invalid encryption key configured.")

def encrypt_text(text: str) -> str:
    """Encrypts plaintext into a Fernet token string."""
    if text is None:
        return None
    if text == "":
        return ""
    
    f = _get_fernet()
    # Fernet expects bytes and returns bytes, we return string for DB
    return f.encrypt(text.encode('utf-8')).decode('utf-8')

def decrypt_text(encrypted_text: str) -> str:
    """Decrypts a Fernet token string into plaintext."""
    if encrypted_text is None:
        return None
    if encrypted_text == "":
        return ""
    
    f = _get_fernet()
    try:
        return f.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')
    except (InvalidToken, TypeError, ValueError):
        # We raise a specific error to allow safe fallback in migration
        raise ValueError("Failed to decrypt text. It may be invalid or legacy plaintext.")
