from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.quest_generator import QuestGenerator
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.security import hash_token, new_opaque_token
from app.models.entities import CrowdSession, QuestRound, SessionEvent, SessionStatus, TwitchConnection, User
from app.schemas.quests import QuestGenerateRequest, SessionCreateRequest
from app.services.events import publish_session_event
from app.services.game_service import (
    GameRuleError,
    attach_quest,
    create_session,
    get_vote_totals,
    lock_voting,
    set_session_status,
    start_session,
    start_voting,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def owned_session(
    db: AsyncSession, user_id: str, session_id: str, *, for_update: bool = False
) -> CrowdSession:
    statement = select(CrowdSession).where(
        CrowdSession.id == session_id,
        CrowdSession.owner_id == user_id,
    )
    if for_update:
        statement = statement.with_for_update()
    session = await db.scalar(statement)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("", status_code=201)
async def create_new_session(
    payload: SessionCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    connection = await db.scalar(select(TwitchConnection).where(
        TwitchConnection.user_id == user.id,
        TwitchConnection.status == "connected",
    ))
    if connection is None:
        raise HTTPException(status_code=409, detail="Connect your Twitch account before creating a live session")
    # Lock the owner row so concurrent requests cannot create overlapping sessions.
    await db.scalar(select(User).where(User.id == user.id).with_for_update())
    active_session = await db.scalar(
        select(CrowdSession).where(
            CrowdSession.owner_id == user.id,
            CrowdSession.status.in_([
                SessionStatus.CREATED.value,
                SessionStatus.READY.value,
                SessionStatus.VOTING.value,
                SessionStatus.ACTIVE.value,
                SessionStatus.PAUSED.value,
            ]),
        ).limit(1)
    )
    if active_session:
        raise HTTPException(
            status_code=409,
            detail="End or complete the existing session before creating another live session",
        )
    raw_overlay_token = new_opaque_token()
    session = await create_session(
        db,
        owner_id=user.id,
        broadcaster_user_id=user.twitch_user_id,
        title=payload.title,
        overlay_token_hash=hash_token(raw_overlay_token),
    )
    return {"session": _session_json(session), "overlay_token": raw_overlay_token}


@router.get("")
async def list_sessions(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await db.scalars(
        select(CrowdSession).where(CrowdSession.owner_id == user.id).order_by(desc(CrowdSession.created_at)).limit(100)
    )
    return [_session_json(row) for row in rows.all()]


@router.get("/{session_id}/events")
async def list_session_events(
    session_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=40, ge=1, le=100),
) -> dict:
    await owned_session(db, user.id, session_id)
    rows = await db.scalars(
        select(SessionEvent)
        .where(SessionEvent.session_id == session_id)
        .order_by(desc(SessionEvent.created_at))
        .limit(limit)
    )
    return {"items": [
        {
            "id": event.id,
            "type": event.event_type,
            "data": event.payload_json,
            "created_at": event.created_at.isoformat(),
        }
        for event in rows.all()
    ]}


@router.get("/{session_id}")
async def get_session(session_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    session = await owned_session(db, user.id, session_id)
    round_ = None
    if session.current_round_id:
        round_ = await db.get(QuestRound, session.current_round_id)
    return {
        "session": _session_json(session),
        "current_round": _round_json(round_) if round_ else None,
        "vote_totals": await get_vote_totals(db, round_.id) if round_ else [],
    }


@router.post("/{session_id}/start")
async def start(session_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    session = await owned_session(db, user.id, session_id, for_update=True)
    try:
        await start_session(db, session)
    except GameRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": session.status}


@router.post("/{session_id}/quests/generate")
async def generate_quest(
    session_id: str,
    payload: QuestGenerateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    session = await owned_session(db, user.id, session_id, for_update=True)
    proposal, generation_source = await QuestGenerator().generate(payload)
    try:
        round_ = await attach_quest(db, session, proposal, payload, generation_source)
    except GameRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"round": _round_json(round_), "generation_source": generation_source}


@router.post("/{session_id}/voting/start")
async def begin_voting(session_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    session = await owned_session(db, user.id, session_id, for_update=True)
    try:
        round_ = await start_voting(db, session)
    except GameRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"round": _round_json(round_)}


@router.post("/{session_id}/pause")
async def pause(session_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    session = await owned_session(db, user.id, session_id, for_update=True)
    try:
        await set_session_status(db, session, "pause")
    except GameRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": session.status}


@router.post("/{session_id}/resume")
async def resume(session_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    session = await owned_session(db, user.id, session_id, for_update=True)
    try:
        await set_session_status(db, session, "resume")
    except GameRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": session.status}


@router.post("/{session_id}/end")
async def end(session_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    session = await owned_session(db, user.id, session_id, for_update=True)
    try:
        await set_session_status(db, session, "end")
    except GameRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": session.status}


@router.post("/{session_id}/voting/close")
async def close_voting(session_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    session = await owned_session(db, user.id, session_id, for_update=True)
    if not session.current_round_id:
        raise HTTPException(status_code=409, detail="No current quest")
    result = await lock_voting(db, session.current_round_id)
    if result is None:
        raise HTTPException(status_code=409, detail="Voting is not active")
    return result


@router.post("/{session_id}/overlay-token/rotate")
async def rotate_overlay_token(session_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    session = await owned_session(db, user.id, session_id, for_update=True)
    raw_token = new_opaque_token()
    session.overlay_token_hash = hash_token(raw_token)
    await db.commit()
    await publish_session_event(session.id, "overlay.token_rotated", {})
    return {"overlay_token": raw_token, "overlay_url": f"{settings.frontend_url}/overlay/{raw_token}"}


def _session_json(session: CrowdSession) -> dict:
    return {
        "id": session.id,
        "title": session.title,
        "status": session.status,
        "current_round_id": session.current_round_id,
        "community_xp": session.community_xp,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "created_at": session.created_at.isoformat(),
    }


def _round_json(round_: QuestRound) -> dict:
    return {
        "id": round_.id,
        "title": round_.title,
        "narrative": round_.narrative,
        "success_message": round_.success_message,
        "failure_message": round_.failure_message,
        "theme": round_.theme,
        "difficulty": round_.difficulty,
        "options": round_.options_json,
        "state": round_.state,
        "winning_option_id": round_.winning_option_id,
        "objective_type": round_.objective_type,
        "objective_target": round_.objective_target,
        "objective_duration_seconds": round_.objective_duration_seconds,
        "objective_ends_at": round_.objective_ends_at.isoformat() if round_.objective_ends_at else None,
        "objective_progress": round_.objective_progress,
        "reward_xp": round_.reward_xp,
        "vote_duration_seconds": round_.vote_duration_seconds,
        "vote_ends_at": round_.vote_ends_at.isoformat() if round_.vote_ends_at else None,
    }
