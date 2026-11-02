import pytest
from pydantic import ValidationError

from app.schemas.quests import QuestProposal


VALID = {
    "title": "The Lost Crystal",
    "narrative": "An ancient crystal has vanished and the community must find it.",
    "difficulty": "medium",
    "options": [
        {"id": 1, "label": "Explore", "description": "Search the forest for clues.", "objective_type": "community_action", "target": 8},
        {"id": 2, "label": "Fight", "description": "Defeat the guardian together.", "objective_type": "community_power", "target": 10},
        {"id": 3, "label": "Rescue", "description": "Bring the explorer back to safety.", "objective_type": "community_rescue", "target": 7},
    ],
    "success_message": "The crystal is recovered!",
    "failure_message": "The guardian escapes.",
    "reward_xp": 100,
}


def test_valid_quest_schema():
    proposal = QuestProposal.model_validate(VALID)
    assert len(proposal.options) == 3


def test_duplicate_option_ids_are_rejected():
    invalid = {**VALID, "options": [VALID["options"][0], VALID["options"][0], VALID["options"][2]]}
    with pytest.raises(ValidationError):
        QuestProposal.model_validate(invalid)


def test_out_of_range_target_is_rejected():
    invalid = {**VALID, "options": [{**VALID["options"][0], "target": 100000}, *VALID["options"][1:]]}
    with pytest.raises(ValidationError):
        QuestProposal.model_validate(invalid)
