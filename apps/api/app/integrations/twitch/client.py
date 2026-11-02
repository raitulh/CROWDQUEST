from typing import Any

import httpx

from app.core.config import settings


class TwitchAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class TwitchClient:
    def __init__(self, access_token: str | None = None):
        self.access_token = access_token
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=7.0))

    async def close(self) -> None:
        await self.client.aclose()

    def _headers(self, *, require_auth: bool = True) -> dict[str, str]:
        headers = {"Client-ID": settings.twitch_client_id, "Content-Type": "application/json"}
        if require_auth:
            if not self.access_token:
                raise TwitchAPIError("Twitch access token is missing")
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def oauth_exchange(self, code: str) -> dict[str, Any]:
        response = await self.client.post(
            f"{settings.twitch_oauth_base_url}/token",
            data={
                "client_id": settings.twitch_client_id,
                "client_secret": settings.twitch_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.twitch_redirect_uri,
            },
        )
        if response.is_error:
            raise TwitchAPIError("Twitch OAuth code exchange failed", response.status_code, response.text)
        return response.json()

    async def refresh_oauth_token(self, refresh_token: str) -> dict[str, Any]:
        response = await self.client.post(
            f"{settings.twitch_oauth_base_url}/token",
            data={
                "client_id": settings.twitch_client_id,
                "client_secret": settings.twitch_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if response.is_error:
            raise TwitchAPIError("Twitch token refresh failed", response.status_code, response.text)
        return response.json()

    async def validate_token(self) -> dict[str, Any]:
        response = await self.client.get(
            f"{settings.twitch_oauth_base_url}/validate",
            headers={"Authorization": f"OAuth {self.access_token}"},
        )
        if response.is_error:
            raise TwitchAPIError("Twitch token validation failed", response.status_code, response.text)
        return response.json()

    async def revoke_token(self) -> None:
        if not self.access_token:
            return
        response = await self.client.post(
            f"{settings.twitch_oauth_base_url}/revoke",
            data={"client_id": settings.twitch_client_id, "token": self.access_token},
        )
        if response.is_error:
            raise TwitchAPIError("Twitch token revocation failed", response.status_code, response.text)

    async def get_current_user(self) -> dict[str, Any]:
        response = await self.client.get(f"{settings.twitch_api_base_url}/users", headers=self._headers())
        if response.is_error:
            raise TwitchAPIError("Unable to retrieve Twitch account", response.status_code, response.text)
        data = response.json().get("data", [])
        if not data:
            raise TwitchAPIError("Twitch returned no user for the authorized token")
        return data[0]

    async def create_chat_subscription(self, broadcaster_id: str, user_id: str, session_id: str) -> dict[str, Any]:
        response = await self.client.post(
            f"{settings.twitch_api_base_url}/eventsub/subscriptions",
            headers=self._headers(),
            json={
                "type": "channel.chat.message",
                "version": "1",
                "condition": {"broadcaster_user_id": broadcaster_id, "user_id": user_id},
                "transport": {"method": "websocket", "session_id": session_id},
            },
        )
        if response.status_code not in (200, 202):
            raise TwitchAPIError("Unable to create Twitch chat subscription", response.status_code, response.text)
        return response.json()

    async def send_chat_message(self, broadcaster_id: str, sender_id: str, message: str) -> dict[str, Any]:
        response = await self.client.post(
            f"{settings.twitch_api_base_url}/chat/messages",
            headers=self._headers(),
            params={"broadcaster_id": broadcaster_id, "sender_id": sender_id},
            json={"message": message[:500]},
        )
        if response.is_error:
            raise TwitchAPIError("Unable to send Twitch chat message", response.status_code, response.text)
        return response.json()
