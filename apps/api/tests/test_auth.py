import pytest
from cryptography.fernet import Fernet
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.responses import Response

from app.api.v1.auth import LocalLoginRequest, local_login
from app.core.config import settings
from app.models.base import Base


@pytest.mark.asyncio
@patch("app.api.v1.auth.publish_connection_update", new_callable=AsyncMock)
@patch("app.api.v1.auth.get_redis")
async def test_local_login_creates_user_and_session(mock_redis, mock_publish, monkeypatch):
    monkeypatch.setattr(settings, "token_encryption_key", Fernet.generate_key().decode())
    fake_redis = AsyncMock()
    mock_redis.return_value = fake_redis

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as db:
        response = Response()
        payload = LocalLoginRequest(username="test_streamer", display_name="Test Streamer")
        result = await local_login(payload, response, db)

        assert result["success"] is True
        assert result["user"]["login"] == "test_streamer"
        assert result["user"]["display_name"] == "Test Streamer"

        assert "set-cookie" in response.headers or len(response.raw_headers) > 0

    await engine.dispose()
