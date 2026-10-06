import sys
import os

# Ensure the app context is reachable from scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.journal import JournalEntry
from app.models.reflection import Reflection
from app.services.encryption_service import decrypt_text, encrypt_text

def run_migration():
    app = create_app()
    with app.app_context():
        # Validate key
        try:
            # Just calling encrypt_text("") tests that _get_fernet() passes validation
            encrypt_text("")
        except ValueError as e:
            print(f"Error: {e}")
            print("Migration aborted.")
            return
            
        journals = JournalEntry.query.all()
        reflections = Reflection.query.all()
        
        j_count = 0
        r_count = 0
        
        for j in journals:
            if j.encrypted_content:
                try:
                    # If this succeeds, it's either empty or a valid fernet token
                    decrypt_text(j.encrypted_content)
                except Exception:
                    # If it fails, it's legacy plaintext
                    j.encrypted_content = encrypt_text(j.encrypted_content)
                    j_count += 1
                    
        for r in reflections:
            if r.response_encrypted:
                try:
                    decrypt_text(r.response_encrypted)
                except Exception:
                    r.response_encrypted = encrypt_text(r.response_encrypted)
                    r_count += 1
                    
        if j_count > 0 or r_count > 0:
            db.session.commit()
            
        print(f"Encrypted {j_count} journal entries.")
        print(f"Encrypted {r_count} reflection responses.")

if __name__ == '__main__':
    run_migration()
