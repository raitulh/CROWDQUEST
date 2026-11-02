import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.entities import CrowdSession, ProcessedEvent, QuestRound, RoundStatus, SessionEvent, SessionStatus
from app.services.game_service import fail_expired_objective, lock_voting

logger = logging.getLogger(__name__)


async def _prune_expired_event_records() -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        await db.execute(delete(ProcessedEvent).where(
            ProcessedEvent.processed_at < now - timedelta(days=settings.processed_event_retention_days)
        ))
        await db.execute(delete(SessionEvent).where(
            SessionEvent.created_at < now - timedelta(days=settings.session_event_retention_days)
        ))
        await db.commit()


async def run_timer_worker() -> None:
    next_cleanup_at = 0.0
    while True:
        try:
            if time.monotonic() >= next_cleanup_at:
                next_cleanup_at = time.monotonic() + 5 * 60
                try:
                    await _prune_expired_event_records()
                except Exception:
                    logger.exception("Event retention cleanup failed; retrying in five minutes")
                else:
                    next_cleanup_at = time.monotonic() + 24 * 60 * 60
            now = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as db:
                result = await db.scalars(
                    select(QuestRound.id)
                    .join(CrowdSession, CrowdSession.id == QuestRound.session_id)
                    .where(
                        QuestRound.state == RoundStatus.VOTING.value,
                        CrowdSession.status == SessionStatus.VOTING.value,
                        QuestRound.vote_ends_at <= now,
                    )
                    .limit(100)
                )
                for round_id in result.all():
                    await lock_voting(db, round_id)
                expired_objectives = await db.scalars(
                    select(QuestRound.id)
                    .join(CrowdSession, CrowdSession.id == QuestRound.session_id)
                    .where(
                        QuestRound.state == RoundStatus.ACTIVE.value,
                        CrowdSession.status == SessionStatus.ACTIVE.value,
                        QuestRound.objective_ends_at <= now,
                    )
                    .limit(100)
                )
                for round_id in expired_objectives.all():
                    await fail_expired_objective(db, round_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Voting timer worker iteration failed")
        await asyncio.sleep(1.0)
