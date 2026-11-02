from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"), env_file_encoding="utf-8", extra="ignore", case_sensitive=False, env_ignore_empty=True
    )

    app_name: str = "CrowdQuest"
    app_env: Literal["development", "test", "production"] = "development"
    app_secret_key: str = "replace-this-development-secret-before-deployment-32-chars"
    token_encryption_key: str = ""
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    cookie_secure: bool = False
    cookie_domain: str | None = None
    access_token_ttl_minutes: int = 60 * 24 * 7

    database_url: str = "postgresql+asyncpg://crowdquest:crowdquest@localhost:5432/crowdquest"
    redis_url: str = "redis://localhost:6379/0"
    redis_prefix: str = "crowdquest"

    twitch_client_id: str = ""
    twitch_client_secret: str = ""
    twitch_redirect_uri: str = "http://localhost:8000/api/v1/auth/twitch/callback"
    twitch_scopes: list[str] = Field(default_factory=lambda: ["user:read:chat", "user:write:chat"])
    twitch_eventsub_url: str = "wss://eventsub.wss.twitch.tv/ws"
    twitch_api_base_url: str = "https://api.twitch.tv/helix"
    twitch_oauth_base_url: str = "https://id.twitch.tv/oauth2"
    twitch_worker_poll_seconds: float = 12.0
    twitch_reconnect_backoff_max_seconds: int = 60

    ai_provider: Literal["ollama", "openai_compatible"] = "ollama"
    ai_timeout_seconds: float = 45.0
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""

    session_cookie_name: str = "cq_session"
    oauth_state_ttl_seconds: int = 600
    websocket_heartbeat_seconds: int = 25
    voting_min_seconds: int = 15
    voting_max_seconds: int = 180
    chat_user_cooldown_seconds: int = 3
    twitch_chat_response_cooldown_seconds: float = 1.5
    max_chat_message_length: int = 500
    processed_event_retention_days: int = 30
    session_event_retention_days: int = 180
    log_level: str = "INFO"

    @field_validator("cors_origins", "twitch_scopes", mode="before")
    @classmethod
    def parse_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.processed_event_retention_days < 7 or self.session_event_retention_days < 30:
            raise ValueError("Event retention must be at least 7 days for processed events and 30 days for session events")
        if self.app_env == "production":
            if len(self.app_secret_key) < 32 or "replace-this" in self.app_secret_key:
                raise ValueError("APP_SECRET_KEY must be a unique secret of at least 32 characters")
            if not self.token_encryption_key:
                raise ValueError("TOKEN_ENCRYPTION_KEY is required in production")
            try:
                Fernet(self.token_encryption_key.encode())
            except (TypeError, ValueError) as exc:
                raise ValueError("TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from exc
            if not self.twitch_client_id or not self.twitch_client_secret:
                raise ValueError("Twitch OAuth credentials are required in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            for name, value in (
                ("FRONTEND_URL", self.frontend_url),
                ("BACKEND_URL", self.backend_url),
                ("TWITCH_REDIRECT_URI", self.twitch_redirect_uri),
            ):
                if urlparse(value).scheme != "https":
                    raise ValueError(f"{name} must use HTTPS in production")
            if not self.cors_origins or any(urlparse(origin).scheme != "https" for origin in self.cors_origins):
                raise ValueError("CORS_ORIGINS must contain explicit HTTPS origins in production")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origins are not permitted in production")
            if self.ai_provider == "openai_compatible" and (
                not self.openai_compatible_base_url or not self.openai_compatible_model
            ):
                raise ValueError("OpenAI-compatible AI provider requires a base URL and model")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
