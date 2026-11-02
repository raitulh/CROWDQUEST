#!/usr/bin/env python3
"""Create a local .env file with cryptographically random secrets."""
from pathlib import Path
import base64
import secrets

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.example"
TARGET = ROOT / ".env"


def main() -> None:
    if TARGET.exists():
        raise SystemExit(".env already exists; refusing to overwrite secrets.")
    text = EXAMPLE.read_text(encoding="utf-8")
    app_secret = secrets.token_urlsafe(48)
    encryption_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    postgres_password = secrets.token_urlsafe(32)
    redis_password = secrets.token_urlsafe(32)
    replacements = {
        "APP_SECRET_KEY=CHANGE_ME_WITH_A_LONG_RANDOM_SECRET": f"APP_SECRET_KEY={app_secret}",
        "TOKEN_ENCRYPTION_KEY=GENERATE_A_FERNET_KEY": f"TOKEN_ENCRYPTION_KEY={encryption_key}",
        "POSTGRES_PASSWORD=CHANGE_ME_POSTGRES_PASSWORD": f"POSTGRES_PASSWORD={postgres_password}",
        "REDIS_PASSWORD=CHANGE_ME_REDIS_PASSWORD": f"REDIS_PASSWORD={redis_password}",
        "DATABASE_URL=postgresql+asyncpg://crowdquest:CHANGE_ME_POSTGRES_PASSWORD@localhost:5432/crowdquest": f"DATABASE_URL=postgresql+asyncpg://crowdquest:{postgres_password}@localhost:5432/crowdquest",
        "REDIS_URL=redis://:CHANGE_ME_REDIS_PASSWORD@localhost:6379/0": f"REDIS_URL=redis://:{redis_password}@localhost:6379/0",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    TARGET.write_text(text, encoding="utf-8")
    try:
        TARGET.chmod(0o600)
    except OSError:
        pass
    print("Created .env with unique application, encryption, PostgreSQL, and Redis secrets.")
    print("Next: add Twitch Client ID/Secret and configure the redirect URI in Twitch Developer Console.")


if __name__ == "__main__":
    main()
