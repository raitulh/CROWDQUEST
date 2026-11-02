import asyncio
import contextlib
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.security import decode_access_token, hash_token
from app.models.entities import CrowdSession, QuestRound
from app.services.events import session_channel
from app.services.game_service import get_vote_totals

router = APIRouter(prefix="/public/overlays", tags=["overlay"])


async def _find_overlay_session(token: str) -> CrowdSession | None:
    async with AsyncSessionLocal() as db:
        return await db.scalar(
            select(CrowdSession).where(CrowdSession.overlay_token_hash == hash_token(token))
        )


@router.get("/{token}")
async def overlay_snapshot(token: str) -> dict:
    async with AsyncSessionLocal() as db:
        session = await db.scalar(
            select(CrowdSession).where(CrowdSession.overlay_token_hash == hash_token(token))
        )
        if session is None:
            raise HTTPException(status_code=404, detail="Overlay not found")
        round_ = await db.get(QuestRound, session.current_round_id) if session.current_round_id else None
        totals = await get_vote_totals(db, round_.id) if round_ else []
        return {
            "session": {
                "id": session.id,
                "title": session.title,
                "status": session.status,
                "community_xp": session.community_xp,
            },
            "round": {
                "id": round_.id,
                "title": round_.title,
                "narrative": round_.narrative,
                "success_message": round_.success_message,
                "failure_message": round_.failure_message,
                "options": round_.options_json,
                "state": round_.state,
                "winning_option_id": round_.winning_option_id,
                "objective_target": round_.objective_target,
                "objective_progress": round_.objective_progress,
                "vote_ends_at": round_.vote_ends_at.isoformat() if round_.vote_ends_at else None,
            } if round_ else None,
            "vote_totals": totals,
        }


async def _serve_session_socket(
    websocket: WebSocket, session_id: str, *, revoke_on_rotation: bool = False
) -> None:
    await websocket.accept()
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(session_channel(session_id))

    async def read_client() -> None:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")

    async def publish_events() -> None:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("data"):
                event_text = message["data"]
                if revoke_on_rotation:
                    try:
                        event_payload = json.loads(event_text)
                    except (TypeError, ValueError):
                        event_payload = {}
                    if event_payload.get("type") == "overlay.token_rotated":
                        with contextlib.suppress(Exception):
                            await websocket.close(code=4403, reason="Overlay token was rotated")
                        return
                await websocket.send_text(event_text)

    reader = asyncio.create_task(read_client(), name=f"ws-reader:{session_id}")
    publisher = asyncio.create_task(publish_events(), name=f"ws-publisher:{session_id}")
    try:
        done, _ = await asyncio.wait(
            {reader, publisher}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            exception = task.exception()
            if exception:
                raise exception
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    except Exception:
        with contextlib.suppress(Exception):
            await websocket.close(code=1011, reason="Realtime channel failed")
    finally:
        for task in (reader, publisher):
            if not task.done():
                task.cancel()
        await asyncio.gather(reader, publisher, return_exceptions=True)
        await pubsub.aclose()


@router.websocket("/ws/{token}")
async def overlay_events(websocket: WebSocket, token: str) -> None:
    session = await _find_overlay_session(token)
    if session is None:
        await websocket.close(code=4404, reason="Overlay not found")
        return
    await _serve_session_socket(websocket, session.id, revoke_on_rotation=True)


@router.websocket("/owner-ws/{session_id}")
async def owner_session_events(websocket: WebSocket, session_id: str) -> None:
    origin = websocket.headers.get("origin")
    allowed_origins = set(settings.cors_origins) | {settings.frontend_url}
    if not origin or origin not in allowed_origins:
        await websocket.close(code=4403, reason="WebSocket origin is not allowed")
        return
    token = websocket.cookies.get(settings.session_cookie_name)
    payload = decode_access_token(token) if token else None
    if not payload or not payload.get("jti"):
        await websocket.close(code=4401, reason="Authentication required")
        return
    redis_key = f"{settings.redis_prefix}:app-session:{payload['jti']}"
    if not await get_redis().exists(redis_key):
        await websocket.close(code=4401, reason="Session revoked")
        return
    async with AsyncSessionLocal() as db:
        session = await db.scalar(
            select(CrowdSession).where(
                CrowdSession.id == session_id,
                CrowdSession.owner_id == payload["sub"],
            )
        )
    if session is None:
        await websocket.close(code=4404, reason="Session not found")
        return
    await _serve_session_socket(websocket, session_id)
