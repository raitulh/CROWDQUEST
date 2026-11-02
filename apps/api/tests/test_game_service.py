import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.entities import CrowdSession, RoundStatus, SessionStatus, User
from app.schemas.quests import QuestGenerateRequest, QuestProposal
from app.services.game_service import (
    GameRuleError,
    attach_quest,
    create_session,
    lock_voting,
    process_contribution,
    process_vote,
    set_session_status,
    start_session,
    start_voting,
)

SAMPLE_PROPOSAL = QuestProposal.model_validate({
    "title": "The Whispering Cavern",
    "narrative": "A dark cavern looms ahead. Viewers must decide which path to take.",
    "difficulty": "medium",
    "options": [
        {"id": 1, "label": "Left Cave", "description": "Loot the chest", "objective_type": "community_action", "target": 5},
        {"id": 2, "label": "Right Cave", "description": "Fight the spider", "objective_type": "community_power", "target": 6},
        {"id": 3, "label": "Middle Path", "description": "Solve the riddle", "objective_type": "community_rescue", "target": 4},
    ],
    "success_message": "The cavern is conquered!",
    "failure_message": "Darkness swallows the cavern.",
    "reward_xp": 100,
})

SAMPLE_REQUEST = QuestGenerateRequest(theme="Fantasy Adventure", difficulty="medium", vote_duration_seconds=45)


@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        user = User(id="user-1", twitch_user_id="streamer-123", login="streamer", display_name="Streamer")
        session.add(user)
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
@patch("app.services.game_service.publish_session_event", new_callable=AsyncMock)
async def test_session_lifecycle_and_voting(mock_publish, async_db: AsyncSession):
    session = await create_session(async_db, "user-1", "streamer-123", "Epic Journey", "hash" * 16)
    session_id = session.id
    assert session.status == SessionStatus.CREATED.value

    # Attach quest
    round_ = await attach_quest(async_db, session, SAMPLE_PROPOSAL, SAMPLE_REQUEST, "ollama")
    assert round_.state == RoundStatus.READY.value
    assert session.current_round_id == round_.id

    # Start session and voting
    await start_session(async_db, session)
    await start_voting(async_db, session)

    # Cannot re-attach during active voting
    current_session = await async_db.get(CrowdSession, session_id)
    with pytest.raises(GameRuleError):
        await attach_quest(async_db, current_session, SAMPLE_PROPOSAL, SAMPLE_REQUEST, "ollama")

    # Process votes
    v1 = await process_vote(
        async_db,
        event_id="evt-1",
        broadcaster_id="streamer-123",
        viewer_id="v1",
        viewer_login="viewer1",
        option_id=2,
    )
    assert v1["accepted"] is True

    # Duplicate event is rejected
    dup_evt = await process_vote(
        async_db,
        event_id="evt-1",
        broadcaster_id="streamer-123",
        viewer_id="v2",
        viewer_login="viewer2",
        option_id=1,
    )
    assert dup_evt["accepted"] is False
    assert dup_evt["reason"] == "duplicate_event"

    # Second vote by same viewer is rejected (first-vote-wins)
    dup_viewer = await process_vote(
        async_db,
        event_id="evt-2",
        broadcaster_id="streamer-123",
        viewer_id="v1",
        viewer_login="viewer1",
        option_id=1,
    )
    assert dup_viewer["accepted"] is False
    assert dup_viewer["reason"] == "already_voted"

    # Invalid option is rejected
    inv_opt = await process_vote(
        async_db,
        event_id="evt-3",
        broadcaster_id="streamer-123",
        viewer_id="v3",
        viewer_login="viewer3",
        option_id=99,
    )
    assert inv_opt["accepted"] is False
    assert inv_opt["reason"] == "invalid_option"


@pytest.mark.asyncio
@patch("app.services.game_service.publish_session_event", new_callable=AsyncMock)
async def test_tie_breaking_policy(mock_publish, async_db: AsyncSession):
    session = await create_session(async_db, "user-1", "streamer-123", "Tie Test", "hash" * 16)
    round_ = await attach_quest(async_db, session, SAMPLE_PROPOSAL, SAMPLE_REQUEST, "ollama")
    round_id = round_.id
    await start_session(async_db, session)
    await start_voting(async_db, session)

    # Vote 1 for option 2, Vote 1 for option 1 -> Tie!
    await process_vote(async_db, event_id="e1", broadcaster_id="streamer-123", viewer_id="u1", viewer_login="u1", option_id=2)
    await process_vote(async_db, event_id="e2", broadcaster_id="streamer-123", viewer_id="u2", viewer_login="u2", option_id=1)

    # Lock voting - lowest option id (1) should win deterministic tie
    result = await lock_voting(async_db, round_id)
    assert result is not None
    assert result["winning_option_id"] == 1
    assert result["tie_break"] == "lowest_option_id"


@pytest.mark.asyncio
@patch("app.services.game_service.publish_session_event", new_callable=AsyncMock)
async def test_contributions_and_pause_resume(mock_publish, async_db: AsyncSession):
    session = await create_session(async_db, "user-1", "streamer-123", "Contribution Test", "hash" * 16)
    session_id = session.id
    round_ = await attach_quest(async_db, session, SAMPLE_PROPOSAL, SAMPLE_REQUEST, "ollama")
    round_id = round_.id
    await start_session(async_db, session)
    await start_voting(async_db, session)
    await process_vote(async_db, event_id="e1", broadcaster_id="streamer-123", viewer_id="u1", viewer_login="u1", option_id=1)
    await lock_voting(async_db, round_id)

    # Contribution in active round
    c1 = await process_contribution(async_db, event_id="c-1", broadcaster_id="streamer-123", viewer_id="u1", viewer_login="u1")
    assert c1["accepted"] is True
    assert c1["progress"] == 1

    # Duplicate contribution by same viewer in same round is rejected
    c1_dup = await process_contribution(async_db, event_id="c-2", broadcaster_id="streamer-123", viewer_id="u1", viewer_login="u1")
    assert c1_dup["accepted"] is False
    assert c1_dup["reason"] == "already_contributed"

    # Pause and resume
    active_session = await async_db.get(CrowdSession, session_id)
    await set_session_status(async_db, active_session, "pause")
    assert active_session.status == SessionStatus.PAUSED.value

    await set_session_status(async_db, active_session, "resume")
    assert active_session.status == SessionStatus.ACTIVE.value
