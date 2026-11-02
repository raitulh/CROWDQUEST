from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int = Field(ge=1, le=3)
    label: str = Field(min_length=3, max_length=80)
    description: str = Field(min_length=8, max_length=240)
    objective_type: Literal["community_action", "community_power", "community_rescue"]
    target: int = Field(ge=3, le=1000)
    objective_duration_seconds: int = Field(default=120, ge=30, le=600)


class QuestProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=4, max_length=160)
    narrative: str = Field(min_length=30, max_length=1800)
    difficulty: Literal["easy", "medium", "hard"]
    options: list[QuestOption] = Field(min_length=3, max_length=3)
    success_message: str = Field(min_length=5, max_length=240)
    failure_message: str = Field(min_length=5, max_length=240)
    reward_xp: int = Field(ge=20, le=1000)

    @field_validator("options")
    @classmethod
    def validate_option_ids(cls, value: list[QuestOption]) -> list[QuestOption]:
        if {item.id for item in value} != {1, 2, 3}:
            raise ValueError("Quest options must have unique IDs 1, 2, and 3")
        return value


class QuestGenerateRequest(BaseModel):
    theme: str = Field(min_length=3, max_length=80)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    tone: Literal["mysterious", "epic", "playful", "dark_adventure"] = "mysterious"
    audience_size: int = Field(default=20, ge=1, le=10000)
    custom_instructions: str | None = Field(default=None, max_length=500)
    vote_duration_seconds: int = Field(default=45, ge=15, le=180)


class SessionCreateRequest(BaseModel):
    title: str = Field(default="Community Quest", min_length=3, max_length=160)


class SessionActionResponse(BaseModel):
    session_id: str
    status: str
    message: str
