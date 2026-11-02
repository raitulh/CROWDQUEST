import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.entities import (
    Contribution,
    CrowdSession,
    QuestRound,
    User,
    Vote,
)


def _create_domain_rows(db: Session) -> None:
    user = User(
        id="user-1",
        twitch_user_id="10001",
        login="streamer",
        display_name="Streamer",
    )
    session = CrowdSession(
        id="session-1",
        owner_id=user.id,
        broadcaster_user_id=user.twitch_user_id,
        title="Test expedition",
        status="voting",
        overlay_token_hash="a" * 64,
    )
    round_ = QuestRound(
        id="round-1",
        session_id=session.id,
        title="The Lost Crystal",
        narrative="An ancient crystal has vanished from the forgotten forest.",
        success_message="The crystal is recovered.",
        failure_message="The guardian escapes.",
        theme="Fantasy Adventure",
        difficulty="medium",
        options_json=[
            {"id": 1, "label": "Explore", "description": "Search for clues.", "objective_type": "community_action", "target": 8},
            {"id": 2, "label": "Fight", "description": "Defeat the guardian.", "objective_type": "community_power", "target": 10},
            {"id": 3, "label": "Rescue", "description": "Bring the scout home.", "objective_type": "community_rescue", "target": 7},
        ],
        state="voting",
    )
    session.current_round_id = round_.id
    db.add_all([user, session, round_])
    db.commit()


def test_database_unique_vote_per_viewer_per_round():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            _create_domain_rows(db)
            db.add(Vote(round_id="round-1", viewer_twitch_id="viewer-1", viewer_login="viewer", option_id=1))
            db.commit()
            db.add(Vote(round_id="round-1", viewer_twitch_id="viewer-1", viewer_login="viewer", option_id=2))
            with pytest.raises(IntegrityError):
                db.commit()
    finally:
        engine.dispose()


def test_database_unique_contribution_per_viewer_type_and_round():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            _create_domain_rows(db)
            db.add(Contribution(
                round_id="round-1", viewer_twitch_id="viewer-1", viewer_login="viewer",
                contribution_type="help", xp_awarded=5,
            ))
            db.commit()
            db.add(Contribution(
                round_id="round-1", viewer_twitch_id="viewer-1", viewer_login="viewer",
                contribution_type="help", xp_awarded=5,
            ))
            with pytest.raises(IntegrityError):
                db.commit()
    finally:
        engine.dispose()


def test_processed_event_table_has_retention_index():
    index_names = {index.name for index in __import__("app.models.entities", fromlist=["ProcessedEvent"]).ProcessedEvent.__table__.indexes}
    assert "ix_processed_events_processed_at" in index_names
