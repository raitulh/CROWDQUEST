from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser

router = APIRouter(prefix="/settings", tags=["settings"])


class Preferences(BaseModel):
    default_theme: str = Field(default="Fantasy Adventure", min_length=3, max_length=80)
    default_difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    vote_duration_seconds: int = Field(default=45, ge=15, le=180)
    overlay_density: str = Field(default="balanced", pattern="^(compact|balanced|cinematic)$")


@router.get("")
async def get_preferences(user: CurrentUser) -> dict:
    return user.preferences_json or Preferences().model_dump()


@router.put("")
async def update_preferences(payload: Preferences, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    user.preferences_json = payload.model_dump()
    await db.commit()
    return user.preferences_json
