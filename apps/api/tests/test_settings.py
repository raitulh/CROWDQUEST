import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import Settings


def test_production_requires_secure_https_configuration():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            app_secret_key="x" * 64,
            token_encryption_key=Fernet.generate_key().decode(),
            twitch_client_id="client-id",
            twitch_client_secret="client-secret",
            cookie_secure=True,
            frontend_url="http://example.com",
            backend_url="https://example.com",
            twitch_redirect_uri="https://example.com/api/v1/auth/twitch/callback",
            cors_origins=["https://example.com"],
        )


def test_production_rejects_invalid_fernet_key():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            app_secret_key="x" * 64,
            token_encryption_key="not-a-fernet-key",
            twitch_client_id="client-id",
            twitch_client_secret="client-secret",
            cookie_secure=True,
            frontend_url="https://example.com",
            backend_url="https://example.com",
            twitch_redirect_uri="https://example.com/api/v1/auth/twitch/callback",
            cors_origins=["https://example.com"],
        )


def test_valid_production_configuration_is_accepted():
    configuration = Settings(
        app_env="production",
        app_secret_key="production-secret-" + "x" * 48,
        token_encryption_key=Fernet.generate_key().decode(),
        twitch_client_id="twitch-client-id",
        twitch_client_secret="twitch-client-secret",
        cookie_secure=True,
        frontend_url="https://crowdquest.example.com",
        backend_url="https://crowdquest.example.com",
        twitch_redirect_uri="https://crowdquest.example.com/api/v1/auth/twitch/callback",
        cors_origins=["https://crowdquest.example.com"],
    )
    assert configuration.app_env == "production"
    assert configuration.cookie_secure is True


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            app_secret_key="production-secret-" + "x" * 48,
            token_encryption_key=Fernet.generate_key().decode(),
            twitch_client_id="twitch-client-id",
            twitch_client_secret="twitch-client-secret",
            cookie_secure=True,
            frontend_url="https://crowdquest.example.com",
            backend_url="https://crowdquest.example.com",
            twitch_redirect_uri="https://crowdquest.example.com/api/v1/auth/twitch/callback",
            cors_origins=["*"],
        )
