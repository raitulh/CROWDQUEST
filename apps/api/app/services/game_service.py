from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    Contribution,
    CrowdSession,
    ProcessedEvent,
    QuestRound,
    RoundStatus,
    SessionEvent,
    SessionStatus,
    Vote,
)
from app.schemas.quests import QuestGenerateRequest, QuestProposal
from app.services.events import publish_session_event


class GameRuleError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def record_event(db: AsyncSession, session_id: str, event_type: str, payload: dict[str, Any]) -> None:
    db.add(SessionEvent(session_id=session_id, event_type=event_type, payload_json=payload))


async def create_session(
    db: AsyncSession, owner_id: str, broadcaster_user_id: str, title: str, overlay_token_hash: str
) -> CrowdSession:
    session = CrowdSession(
        owner_id=owner_id,
        broadcaster_user_id=broadcaster_user_id,
        title=title,
        status=SessionStatus.CREATED.value,
        overlay_token_hash=overlay_token_hash,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def attach_quest(
    db: AsyncSession,
    session: CrowdSession,
    proposal: QuestProposal,
    request: QuestGenerateRequest,
    generation_source: str,
) -> QuestRound:
    if session.status in {SessionStatus.VOTING.value, SessionStatus.ACTIVE.value, SessionStatus.PAUSED.value}:
        raise GameRuleError("A quest cannot be replaced while the session is voting, active, or paused")
    round_ = QuestRound(
        session_id=session.id,
        title=proposal.title,
        narrative=proposal.narrative,
        success_message=proposal.success_message,
        failure_message=proposal.failure_message,
        theme=request.theme,
        difficulty=proposal.difficulty,
        options_json=[item.model_dump() for item in proposal.options],
        state=RoundStatus.READY.value,
        reward_xp=proposal.reward_xp,
        vote_duration_seconds=request.vote_duration_seconds,
    )
    db.add(round_)
    await db.flush()
    session.current_round_id = round_.id
    session.status = SessionStatus.READY.value
    await record_event(db, session.id, "quest.generated", {
        "round_id": round_.id,
        "title": round_.title,
        "narrative": round_.narrative,
        "options": round_.options_json,
        "generation_source": generation_source,
    })
    await db.commit()
    await db.refresh(round_)
    await publish_session_event(session.id, "quest.generated", {
        "round_id": round_.id,
        "title": round_.title,
        "narrative": round_.narrative,
        "options": round_.options_json,
        "generation_source": generation_source,
    })
    return round_


async def start_session(db: AsyncSession, session: CrowdSession) -> None:
    if session.status not in {SessionStatus.CREATED.value, SessionStatus.READY.value}:
        raise GameRuleError("Session cannot be started from its current state")
    if not session.current_round_id:
        raise GameRuleError("Generate a quest before starting the session")
    session.started_at = session.started_at or _utcnow()
    session.status = SessionStatus.READY.value
    await db.commit()
    await publish_session_event(session.id, "session.started", {"status": session.status})


async def start_voting(db: AsyncSession, session: CrowdSession) -> QuestRound:
    if session.status not in {SessionStatus.CREATED.value, SessionStatus.READY.value}:
        raise GameRuleError("Voting can only start when the session is ready")
    if not session.current_round_id:
        raise GameRuleError("No current quest is available")
    round_ = await db.scalar(select(QuestRound).where(QuestRound.id == session.current_round_id).with_for_update())
    if round_ is None or round_.state != RoundStatus.READY.value:
        raise GameRuleError("Current quest is not ready for voting")
    round_.state = RoundStatus.VOTING.value
    round_.vote_ends_at = _utcnow() + timedelta(seconds=round_.vote_duration_seconds)
    session.status = SessionStatus.VOTING.value
    await record_event(db, session.id, "quest.voting_started", {
        "round_id": round_.id,
        "ends_at": round_.vote_ends_at.isoformat(),
        "duration_seconds": round_.vote_duration_seconds,
        "options": round_.options_json,
    })
    await db.commit()
    await publish_session_event(session.id, "quest.voting_started", {
        "round_id": round_.id,
        "ends_at": round_.vote_ends_at.isoformat(),
        "duration_seconds": round_.vote_duration_seconds,
        "options": round_.options_json,
    })
    return round_


async def get_vote_totals(db: AsyncSession, round_id: str) -> list[dict[str, int]]:
    rows = await db.execute(
        select(Vote.option_id, func.count(Vote.id)).where(Vote.round_id == round_id).group_by(Vote.option_id)
    )
    counts = {int(option_id): int(count) for option_id, count in rows.all()}
    return [{"id": option_id, "votes": counts.get(option_id, 0)} for option_id in (1, 2, 3)]


async def process_vote(
    db: AsyncSession,
    *,
    event_id: str,
    broadcaster_id: str,
    viewer_id: str,
    viewer_login: str,
    option_id: int,
) -> dict[str, Any]:
    if await db.get(ProcessedEvent, event_id):
        return {"accepted": False, "reason": "duplicate_event"}
    session = await db.scalar(
        select(CrowdSession).where(
            CrowdSession.broadcaster_user_id == broadcaster_id,
            CrowdSession.status == SessionStatus.VOTING.value,
        ).with_for_update()
    )
    if session is None or not session.current_round_id:
        return {"accepted": False, "reason": "no_active_vote"}
    round_ = await db.scalar(select(QuestRound).where(QuestRound.id == session.current_round_id).with_for_update())
    if round_ is None or round_.state != RoundStatus.VOTING.value:
        return {"accepted": False, "reason": "voting_closed"}
    if round_.vote_ends_at and _as_utc(round_.vote_ends_at) <= _utcnow():
        return {"accepted": False, "reason": "voting_closed"}
    if option_id not in {item["id"] for item in round_.options_json}:
        return {"accepted": False, "reason": "invalid_option"}
    db.add(ProcessedEvent(event_id=event_id, event_type="channel.chat.message"))
    db.add(Vote(round_id=round_.id, viewer_twitch_id=viewer_id, viewer_login=viewer_login, option_id=option_id))
    await record_event(db, session.id, "vote.accepted", {
        "round_id": round_.id,
        "viewer": viewer_login,
        "option_id": option_id,
    })
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"accepted": False, "reason": "already_voted"}
    totals = await get_vote_totals(db, round_.id)
    await publish_session_event(session.id, "vote.updated", {
        "round_id": round_.id,
        "options": totals,
        "total_votes": sum(item["votes"] for item in totals),
    })
    return {"accepted": True, "reason": "accepted", "totals": totals, "session_id": session.id}


async def lock_voting(db: AsyncSession, round_id: str) -> dict[str, Any] | None:
    # Keep the global lock order consistent with process_vote/process_contribution:
    # session row first, then round row. Reversing this order can deadlock a timer
    # worker against a viewer command under concurrent PostgreSQL transactions.
    session_id = await db.scalar(select(QuestRound.session_id).where(QuestRound.id == round_id))
    if session_id is None:
        return None
    session = await db.scalar(select(CrowdSession).where(CrowdSession.id == session_id).with_for_update())
    if session is None or session.status != SessionStatus.VOTING.value:
        return None
    round_ = await db.scalar(select(QuestRound).where(QuestRound.id == round_id).with_for_update())
    if round_ is None or round_.session_id != session.id or round_.state != RoundStatus.VOTING.value:
        return None
    totals = await get_vote_totals(db, round_.id)
    max_votes = max(item["votes"] for item in totals)
    if max_votes == 0:
        round_.state = RoundStatus.FAILED.value
        session.status = SessionStatus.READY.value
        result = {"round_id": round_.id, "winner": None, "reason": "no_votes", "options": totals}
        await record_event(db, session.id, "quest.vote_locked", result)
        await db.commit()
        await publish_session_event(session.id, "quest.vote_locked", result)
        return result
    # Stable tie break: the lowest option ID wins when vote totals are equal.
    winning = min(item["id"] for item in totals if item["votes"] == max_votes)
    selected = next(item for item in round_.options_json if item["id"] == winning)
    round_.winning_option_id = winning
    round_.objective_type = selected["objective_type"]
    round_.objective_target = selected["target"]
    round_.objective_duration_seconds = selected.get("objective_duration_seconds", 120)
    round_.objective_ends_at = _utcnow() + timedelta(seconds=round_.objective_duration_seconds)
    round_.state = RoundStatus.ACTIVE.value
    session.status = SessionStatus.ACTIVE.value
    result = {
        "round_id": round_.id,
        "winner": selected,
        "winning_option_id": winning,
        "options": totals,
        "tie_break": "lowest_option_id" if sum(1 for item in totals if item["votes"] == max_votes) > 1 else None,
    }
    await record_event(db, session.id, "quest.selected", result)
    await db.commit()
    await publish_session_event(session.id, "quest.vote_locked", {"round_id": round_.id, "options": totals})
    await publish_session_event(session.id, "quest.selected", result)
    return result


async def process_contribution(
    db: AsyncSession,
    *,
    event_id: str,
    broadcaster_id: str,
    viewer_id: str,
    viewer_login: str,
) -> dict[str, Any]:
    if await db.get(ProcessedEvent, event_id):
        return {"accepted": False, "reason": "duplicate_event"}
    session = await db.scalar(
        select(CrowdSession).where(
            CrowdSession.broadcaster_user_id == broadcaster_id,
            CrowdSession.status == SessionStatus.ACTIVE.value,
        ).with_for_update()
    )
    if session is None or not session.current_round_id:
        return {"accepted": False, "reason": "no_active_objective"}
    round_ = await db.scalar(select(QuestRound).where(QuestRound.id == session.current_round_id).with_for_update())
    if round_ is None or round_.state != RoundStatus.ACTIVE.value:
        return {"accepted": False, "reason": "objective_closed"}
    if round_.objective_ends_at and _as_utc(round_.objective_ends_at) <= _utcnow():
        round_.state = RoundStatus.FAILED.value
        round_.completed_at = _utcnow()
        round_.objective_ends_at = None
        session.status = SessionStatus.READY.value
        expiry_result = {
            "round_id": round_.id,
            "progress": round_.objective_progress,
            "target": round_.objective_target,
            "failure_message": round_.failure_message,
        }
        await record_event(db, session.id, "quest.failed", expiry_result)
        await db.commit()
        await publish_session_event(session.id, "quest.failed", expiry_result)
        return {"accepted": False, "reason": "objective_expired"}
    db.add(ProcessedEvent(event_id=event_id, event_type="channel.chat.message"))
    db.add(Contribution(
        round_id=round_.id,
        viewer_twitch_id=viewer_id,
        viewer_login=viewer_login,
        contribution_type="help",
        xp_awarded=5,
    ))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"accepted": False, "reason": "already_contributed"}
    round_.objective_progress += 1
    session.community_xp += 5
    completed = bool(round_.objective_target and round_.objective_progress >= round_.objective_target)
    if completed:
        round_.state = RoundStatus.COMPLETED.value
        round_.completed_at = _utcnow()
        round_.objective_ends_at = None
        session.status = SessionStatus.READY.value
        session.community_xp += round_.reward_xp
    progress = {
        "round_id": round_.id,
        "progress": round_.objective_progress,
        "target": round_.objective_target,
        "percent": min(100, round_.objective_progress * 100 // max(1, round_.objective_target or 1)),
    }
    await record_event(db, session.id, "contribution.accepted", {
        **progress,
        "viewer": viewer_login,
    })
    await record_event(db, session.id, "quest.progress_updated", progress)
    if completed:
        await record_event(db, session.id, "quest.completed", {
            **progress,
            "reward_xp": round_.reward_xp,
            "community_xp": session.community_xp,
        })
    await db.commit()
    await publish_session_event(session.id, "quest.progress_updated", progress)
    if completed:
        await publish_session_event(session.id, "quest.completed", {
            **progress,
            "reward_xp": round_.reward_xp,
            "community_xp": session.community_xp,
        })
    return {"accepted": True, "completed": completed, **progress}


async def fail_expired_objective(db: AsyncSession, round_id: str) -> dict[str, Any] | None:
    # Use the same session -> round lock ordering as votes and contributions.
    session_id = await db.scalar(select(QuestRound.session_id).where(QuestRound.id == round_id))
    if session_id is None:
        return None
    session = await db.scalar(select(CrowdSession).where(CrowdSession.id == session_id).with_for_update())
    if session is None or session.status != SessionStatus.ACTIVE.value:
        return None
    round_ = await db.scalar(select(QuestRound).where(QuestRound.id == round_id).with_for_update())
    now = _utcnow()
    if (
        round_ is None
        or round_.session_id != session.id
        or round_.state != RoundStatus.ACTIVE.value
        or round_.objective_ends_at is None
        or round_.objective_ends_at > now
    ):
        return None
    round_.state = RoundStatus.FAILED.value
    round_.completed_at = now
    round_.objective_ends_at = None
    session.status = SessionStatus.READY.value
    result = {
        "round_id": round_.id,
        "progress": round_.objective_progress,
        "target": round_.objective_target,
        "failure_message": round_.failure_message,
    }
    await record_event(db, session.id, "quest.failed", result)
    await db.commit()
    await publish_session_event(session.id, "quest.failed", result)
    return result


async def set_session_status(db: AsyncSession, session: CrowdSession, action: str) -> None:
    allowed = {
        "pause": ({SessionStatus.VOTING.value, SessionStatus.ACTIVE.value}, SessionStatus.PAUSED.value),
        "resume": ({SessionStatus.PAUSED.value}, SessionStatus.ACTIVE.value),
        "end": ({SessionStatus.CREATED.value, SessionStatus.READY.value, SessionStatus.VOTING.value, SessionStatus.ACTIVE.value, SessionStatus.PAUSED.value}, SessionStatus.ENDED.value),
    }
    if action not in allowed:
        raise GameRuleError("Unsupported session action")
    sources, target = allowed[action]
    if session.status not in sources:
        raise GameRuleError(f"Session cannot {action} from its current state")
    settings_json = dict(session.settings_json or {})
    if action == "pause":
        settings_json["paused_from_status"] = session.status
        if session.current_round_id:
            round_ = await db.scalar(
                select(QuestRound).where(QuestRound.id == session.current_round_id).with_for_update()
            )
            if round_ and session.status == SessionStatus.VOTING.value and round_.vote_ends_at:
                remaining = (_as_utc(round_.vote_ends_at) - _utcnow()).total_seconds()
                settings_json["paused_vote_remaining_seconds"] = max(0, int(remaining + 0.999))
            if round_ and session.status == SessionStatus.ACTIVE.value and round_.objective_ends_at:
                remaining = (_as_utc(round_.objective_ends_at) - _utcnow()).total_seconds()
                settings_json["paused_objective_remaining_seconds"] = max(0, int(remaining + 0.999))
        session.settings_json = settings_json
        session.status = target
    elif action == "resume":
        previous = settings_json.pop("paused_from_status", SessionStatus.ACTIVE.value)
        remaining = settings_json.pop("paused_vote_remaining_seconds", None)
        objective_remaining = settings_json.pop("paused_objective_remaining_seconds", None)
        if session.current_round_id:
            round_ = await db.scalar(
                select(QuestRound).where(QuestRound.id == session.current_round_id).with_for_update()
            )
            if round_ and round_.state == RoundStatus.VOTING.value and previous == SessionStatus.VOTING.value and remaining is not None:
                round_.vote_ends_at = _utcnow() + timedelta(seconds=max(0, int(remaining)))
            if round_ and round_.state == RoundStatus.ACTIVE.value and previous == SessionStatus.ACTIVE.value and objective_remaining is not None:
                round_.objective_ends_at = _utcnow() + timedelta(seconds=max(0, int(objective_remaining)))
        session.settings_json = settings_json
        session.status = previous if previous in {SessionStatus.VOTING.value, SessionStatus.ACTIVE.value} else SessionStatus.ACTIVE.value
    else:
        session.status = target
        if session.current_round_id:
            round_ = await db.scalar(
                select(QuestRound).where(QuestRound.id == session.current_round_id).with_for_update()
            )
            if round_ and round_.state in {RoundStatus.VOTING.value, RoundStatus.ACTIVE.value}:
                round_.state = RoundStatus.FAILED.value
                round_.completed_at = _utcnow()
                round_.vote_ends_at = None
                round_.objective_ends_at = None
    if action == "end":
        session.ended_at = _utcnow()
    await record_event(db, session.id, f"session.{action}", {"status": target})
    await db.commit()
    await publish_session_event(session.id, f"session.{action}d" if action != "end" else "session.ended", {"status": target})
