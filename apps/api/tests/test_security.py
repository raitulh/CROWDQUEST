from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.security import decrypt_secret, encrypt_secret, hash_token, new_opaque_token


def test_opaque_token_is_high_entropy_and_unique():
    first = new_opaque_token()
    second = new_opaque_token()
    assert len(first) >= 50
    assert first != second


def test_token_hash_is_one_way_stable_digest():
    value = "private-overlay-token"
    assert hash_token(value) == hash_token(value)
    assert hash_token(value) != value
    assert len(hash_token(value)) == 64


def test_fernet_secret_round_trip(monkeypatch):
    monkeypatch.setattr(settings, "token_encryption_key", Fernet.generate_key().decode())
    secret = "twitch-refresh-token-value"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret
