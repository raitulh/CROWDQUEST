from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.entities import Contribution, CrowdSession, QuestRound

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/leaderboard")
async def leaderboard(user: CurrentUser, db: AsyncSession = Depends(get_db), limit: int = 25) -> dict:
    limit = max(1, min(limit, 100))
    query = (
        select(
            Contribution.viewer_twitch_id,
            Contribution.viewer_login,
            func.sum(Contribution.xp_awarded).label("xp"),
            func.count(Contribution.id).label("contributions"),
        )
        .join(QuestRound, QuestRound.id == Contribution.round_id)
        .join(CrowdSession, CrowdSession.id == QuestRound.session_id)
        .where(CrowdSession.owner_id == user.id)
        .group_by(Contribution.viewer_twitch_id, Contribution.viewer_login)
        .order_by(func.sum(Contribution.xp_awarded).desc())
        .limit(limit)
    )
    rows = await db.execute(query)
    return {"items": [
        {"viewer_id": row.viewer_twitch_id, "viewer": row.viewer_login, "xp": int(row.xp or 0), "contributions": int(row.contributions)}
        for row in rows.all()
    ]}
