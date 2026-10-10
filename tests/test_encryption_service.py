import pytest
from app.services.encryption_service import encrypt_text, decrypt_text

def test_encryption_decryption_round_trip(app):
    with app.app_context():
        original = "Secret Journal Entry"
        encrypted = encrypt_text(original)
        assert original != encrypted

        decrypted = decrypt_text(encrypted)
        assert decrypted == original

def test_empty_string_handling(app):
    with app.app_context():
        assert encrypt_text("") == ""
        assert decrypt_text("") == ""

def test_none_handling(app):
    with app.app_context():
        assert encrypt_text(None) is None
        assert decrypt_text(None) is None

def test_unicode_and_long_text(app):
    with app.app_context():
        # Unicode
        original = "Hello 🌍! My thoughts are complex."
        assert decrypt_text(encrypt_text(original)) == original

        # Long text
        long_text = "A" * 10000
        assert decrypt_text(encrypt_text(long_text)) == long_text

def test_wrong_key_decryption_failure(app):
    with app.app_context():
        original = "My secret"
        encrypted = encrypt_text(original)

    # Change key temporarily to simulate failure (must be valid 32 url-safe base64 encoded bytes)
    import base64
    app.config['MINTRACK_ENCRYPTION_KEY'] = base64.urlsafe_b64encode(b'A'*32).decode('utf-8')
    with app.app_context():
        with pytest.raises(ValueError, match="Failed to decrypt text"):
            decrypt_text(encrypted)

def test_missing_key_configuration(app):
    app.config.pop('MINTRACK_ENCRYPTION_KEY', None)
    with app.app_context():
        with pytest.raises(ValueError, match="missing in configuration"):
            encrypt_text("test")

def test_plaintext_not_returned_as_ciphertext(app):
    with app.app_context():
        assert encrypt_text("hello") != "hello"

def test_decryption_of_plaintext_raises_error(app):
    with app.app_context():
        # Supplying raw plaintext to decrypt_text should fail the fernet token validation
        with pytest.raises(ValueError):
            decrypt_text("This is not a token")
