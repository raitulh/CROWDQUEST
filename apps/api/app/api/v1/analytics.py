from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.entities import Contribution, CrowdSession, QuestRound, RoundStatus, Vote

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def summary(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    session_ids = select(CrowdSession.id).where(CrowdSession.owner_id == user.id)
    total_sessions = await db.scalar(select(func.count()).select_from(CrowdSession).where(CrowdSession.owner_id == user.id)) or 0
    total_rounds = await db.scalar(select(func.count()).select_from(QuestRound).where(QuestRound.session_id.in_(session_ids))) or 0
    completed_rounds = await db.scalar(select(func.count()).select_from(QuestRound).where(
        QuestRound.session_id.in_(session_ids), QuestRound.state == RoundStatus.COMPLETED.value
    )) or 0
    total_votes = await db.scalar(select(func.count()).select_from(Vote).join(QuestRound).where(QuestRound.session_id.in_(session_ids))) or 0
    unique_viewers = await db.scalar(select(func.count(func.distinct(Contribution.viewer_twitch_id))).join(QuestRound).where(QuestRound.session_id.in_(session_ids))) or 0
    community_xp = await db.scalar(select(func.coalesce(func.sum(CrowdSession.community_xp), 0)).where(CrowdSession.owner_id == user.id)) or 0
    return {
        "total_sessions": int(total_sessions),
        "total_rounds": int(total_rounds),
        "completed_rounds": int(completed_rounds),
        "completion_rate": round((completed_rounds / total_rounds) * 100, 1) if total_rounds else 0,
        "total_votes": int(total_votes),
        "unique_contributors": int(unique_viewers),
        "community_xp": int(community_xp),
    }
