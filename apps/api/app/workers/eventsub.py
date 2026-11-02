import asyncio
import contextlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from websockets.asyncio.client import connect

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import close_redis, connect_redis
from app.core.security import decrypt_secret, encrypt_secret
from app.integrations.twitch.client import TwitchClient, TwitchAPIError
from app.integrations.twitch.dispatcher import dispatch_chat_message
from app.models.entities import TwitchConnection, User

logger = logging.getLogger(__name__)


class EventSubConnection:
    def __init__(self, connection_id: str, broadcaster_id: str, user_id: str, access_token: str):
        self.connection_id = connection_id
        self.broadcaster_id = broadcaster_id
        self.user_id = user_id
        self.access_token = access_token
        self._redis: Redis | None = None

    async def _subscribe(self, session_id: str) -> None:
        twitch = TwitchClient(self.access_token)
        try:
            await twitch.create_chat_subscription(self.broadcaster_id, self.user_id, session_id)
        finally:
            await twitch.close()
        logger.info("EventSub chat subscription established for broadcaster %s", self.broadcaster_id)

    async def _handle_notification(self, payload: dict[str, Any]) -> None:
        metadata = payload.get("metadata", {})
        if metadata.get("message_type") != "notification":
            return
        event_id = str(metadata.get("message_id", ""))
        subscription_type = payload.get("payload", {}).get("subscription", {}).get("type")
        event = payload.get("payload", {}).get("event", {})
        if subscription_type != "channel.chat.message" or not event_id:
            return
        async with AsyncSessionLocal() as db:
            connection = await db.get(TwitchConnection, self.connection_id)
            if connection is None or connection.status != "connected":
                return
            await dispatch_chat_message(
                db,
                event_id=event_id,
                event=event,
                connection=connection,
                access_token=self.access_token,
            )

    async def run(self) -> None:
        backoff = 2
        while True:
            websocket = None
            try:
                websocket = await connect(
                    settings.twitch_eventsub_url,
                    open_timeout=12,
                    close_timeout=5,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=2**20,
                )
                needs_subscription = True
                while True:
                    raw = await websocket.recv()
                    message = json.loads(raw)
                    metadata = message.get("metadata", {})
                    message_type = metadata.get("message_type")
                    payload = message.get("payload", {})

                    if message_type == "session_welcome":
                        session_id = payload.get("session", {}).get("id")
                        if session_id and needs_subscription:
                            await self._subscribe(session_id)
                        needs_subscription = False
                        backoff = 2
                    elif message_type == "session_keepalive":
                        continue
                    elif message_type == "session_reconnect":
                        reconnect_url = payload.get("session", {}).get("reconnect_url")
                        if not reconnect_url:
                            raise RuntimeError("EventSub reconnect message did not include a URL")

                        # Keep the current socket alive until Twitch confirms the replacement.
                        replacement = await connect(
                            reconnect_url,
                            open_timeout=12,
                            close_timeout=5,
                            ping_interval=20,
                            ping_timeout=20,
                            max_size=2**20,
                        )
                        try:
                            welcome_raw = await asyncio.wait_for(replacement.recv(), timeout=12)
                            welcome = json.loads(welcome_raw)
                            if welcome.get("metadata", {}).get("message_type") != "session_welcome":
                                raise RuntimeError("Twitch did not welcome the replacement EventSub socket")
                        except Exception:
                            await replacement.close()
                            raise
                        old_socket = websocket
                        websocket = replacement
                        # Reconnect URLs carry existing subscriptions; do not recreate them.
                        needs_subscription = False
                        await old_socket.close()
                    elif message_type == "notification":
                        try:
                            await self._handle_notification(message)
                        except asyncio.CancelledError:
                            raise
                        except Exception:
                            logger.exception(
                                "Unable to process EventSub notification for broadcaster %s",
                                self.broadcaster_id,
                            )
                    elif message_type == "revocation":
                        logger.warning("Twitch revoked EventSub subscription for %s", self.broadcaster_id)
                        raise RuntimeError("EventSub subscription revoked")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "EventSub connection for %s ended: %s",
                    self.broadcaster_id,
                    type(exc).__name__,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, settings.twitch_reconnect_backoff_max_seconds)
            finally:
                if websocket is not None:
                    with contextlib.suppress(Exception):
                        await websocket.close()



async def _refresh_or_validate(connection: TwitchConnection, expected_twitch_user_id: str) -> tuple[str, str] | None:
    now = datetime.now(timezone.utc)
    access = decrypt_secret(connection.access_token_ciphertext)
    refresh = decrypt_secret(connection.refresh_token_ciphertext)
    expires_at = connection.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    token_near_expiry = expires_at <= now + timedelta(minutes=5)
    last_validated = connection.last_validated_at
    if last_validated and last_validated.tzinfo is None:
        last_validated = last_validated.replace(tzinfo=timezone.utc)
    validation_due = last_validated is None or last_validated <= now - timedelta(minutes=50)

    twitch = TwitchClient(access)

    async def persist(status: str = "connected") -> None:
        async with AsyncSessionLocal() as db:
            current = await db.get(TwitchConnection, connection.id)
            if current:
                current.access_token_ciphertext = connection.access_token_ciphertext
                current.refresh_token_ciphertext = connection.refresh_token_ciphertext
                current.expires_at = connection.expires_at
                current.scopes = connection.scopes
                current.last_validated_at = connection.last_validated_at
                current.status = status
                await db.commit()

    async def refresh_and_persist() -> bool:
        nonlocal access, refresh, expires_at
        token_data = await twitch.refresh_oauth_token(refresh)
        access = token_data["access_token"]
        refresh = token_data.get("refresh_token", refresh)
        expires_at = now + timedelta(seconds=int(token_data["expires_in"]))
        connection.access_token_ciphertext = encrypt_secret(access)
        connection.refresh_token_ciphertext = encrypt_secret(refresh)
        connection.expires_at = expires_at
        connection.scopes = token_data.get("scope", connection.scopes)
        twitch.access_token = access
        # Persist a rotated refresh token immediately. Twitch may invalidate the old one.
        await persist()
        return True

    async def mark_reauthorization_required() -> None:
        await persist(status="reauthorization_required")

    refreshed = False
    try:
        if token_near_expiry:
            try:
                await refresh_and_persist()
                refreshed = True
            except TwitchAPIError as exc:
                if exc.status_code is None or exc.status_code >= 500:
                    logger.warning("Twitch token refresh temporarily unavailable for %s", expected_twitch_user_id)
                    return None
                await mark_reauthorization_required()
                return None

        if validation_due:
            try:
                validation = await twitch.validate_token()
            except TwitchAPIError as exc:
                if exc.status_code is None or exc.status_code >= 500:
                    logger.warning("Twitch token validation temporarily unavailable for %s", expected_twitch_user_id)
                    return None
                if refreshed:
                    await mark_reauthorization_required()
                    return None
                try:
                    await refresh_and_persist()
                    refreshed = True
                    validation = await twitch.validate_token()
                except TwitchAPIError as refresh_exc:
                    if refresh_exc.status_code is None or refresh_exc.status_code >= 500:
                        logger.warning("Twitch token recovery temporarily unavailable for %s", expected_twitch_user_id)
                        return None
                    await mark_reauthorization_required()
                    return None

            if validation.get("client_id") != settings.twitch_client_id:
                await mark_reauthorization_required()
                return None
            if str(validation.get("user_id")) != expected_twitch_user_id:
                await mark_reauthorization_required()
                return None
            granted_scopes = set(validation.get("scopes", []))
            if "user:read:chat" not in granted_scopes:
                await mark_reauthorization_required()
                return None
            connection.scopes = list(granted_scopes)
            connection.last_validated_at = now
            await persist()

        return access, refresh
    except asyncio.CancelledError:
        raise
    except Exception:
        # Network and unexpected infrastructure errors must not be misreported as revoked consent.
        logger.exception("Unexpected Twitch token maintenance failure for %s", expected_twitch_user_id)
        return None
    finally:
        await twitch.close()



class EventSubSupervisor:
    def __init__(self) -> None:
        self.tasks: dict[str, asyncio.Task] = {}
        self.stop_event = asyncio.Event()

    async def _load_connections(self) -> list[tuple[TwitchConnection, str]]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TwitchConnection, User.twitch_user_id)
                .join(User, User.id == TwitchConnection.user_id)
                .where(TwitchConnection.status == "connected")
            )
            return [(row[0], row[1]) for row in result.all()]

    async def run(self) -> None:
        await connect_redis()
        redis = __import__("app.core.redis", fromlist=["get_redis"]).get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"{settings.redis_prefix}:twitch:connections")
        try:
            while not self.stop_event.is_set():
                connections = await self._load_connections()
                active_ids = {connection.id for connection, _ in connections}
                for connection_id in list(self.tasks):
                    task = self.tasks[connection_id]
                    if connection_id not in active_ids or task.done():
                        if not task.done():
                            task.cancel()
                        self.tasks.pop(connection_id, None)
                for connection, broadcaster_id in connections:
                    existing_task = self.tasks.get(connection.id)
                    expires_at = connection.expires_at
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    last_validated = connection.last_validated_at
                    if last_validated and last_validated.tzinfo is None:
                        last_validated = last_validated.replace(tzinfo=timezone.utc)
                    needs_token_maintenance = (
                        expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5)
                        or last_validated is None
                        or last_validated <= datetime.now(timezone.utc) - timedelta(minutes=50)
                    )
                    if existing_task and not existing_task.done() and not needs_token_maintenance:
                        continue
                    if existing_task:
                        existing_task.cancel()
                        await asyncio.gather(existing_task, return_exceptions=True)
                        self.tasks.pop(connection.id, None)
                    token_pair = await _refresh_or_validate(connection, broadcaster_id)
                    if token_pair is None:
                        continue
                    access_token, _ = token_pair
                    worker = EventSubConnection(connection.id, broadcaster_id, broadcaster_id, access_token)
                    self.tasks[connection.id] = asyncio.create_task(worker.run(), name=f"eventsub:{connection.id}")
                try:
                    await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0), timeout=1.5)
                except TimeoutError:
                    pass
                await asyncio.sleep(settings.twitch_worker_poll_seconds)
        finally:
            for task in self.tasks.values():
                task.cancel()
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
            await pubsub.aclose()
            await close_redis()


async def main() -> None:
    logging.basicConfig(level=settings.log_level)
    supervisor = EventSubSupervisor()
    await supervisor.run()


if __name__ == "__main__":
    asyncio.run(main())
