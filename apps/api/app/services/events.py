import json
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.redis import get_redis


def session_channel(session_id: str) -> str:
    return f"{settings.redis_prefix}:session:{session_id}:events"


async def publish_session_event(session_id: str, event_type: str, data: dict[str, Any]) -> None:
    payload = {
        "type": event_type,
        "session_id": session_id,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    await get_redis().publish(session_channel(session_id), json.dumps(payload, separators=(",", ":")))


async def publish_connection_update(user_id: str) -> None:
    await get_redis().publish(f"{settings.redis_prefix}:twitch:connections", user_id)
