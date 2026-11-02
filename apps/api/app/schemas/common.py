from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: str
    twitch_user_id: str
    login: str
    display_name: str
    profile_image_url: str | None = None
    twitch_connected: bool = False

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    id: str
    title: str
    status: str
    current_round_id: str | None
    community_xp: int
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventEnvelope(BaseModel):
    type: str
    session_id: str
    occurred_at: datetime
    data: dict[str, Any]
