import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

JWT_ALGORITHM = "HS256"


def issue_access_token(user_id: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=JWT_ALGORITHM), payload["jti"]


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access" or not payload.get("sub"):
            return None
        return payload
    except jwt.PyJWTError:
        return None


def _fernet() -> Fernet:
    if settings.token_encryption_key:
        key = settings.token_encryption_key.encode()
    else:
        # Local development must set a stable key to survive process restarts.
        raise RuntimeError("Set TOKEN_ENCRYPTION_KEY. Generate one with: Fernet.generate_key().decode()")
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored credential cannot be decrypted; check TOKEN_ENCRYPTION_KEY") from exc


def new_opaque_token() -> str:
    return secrets.token_urlsafe(40)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
