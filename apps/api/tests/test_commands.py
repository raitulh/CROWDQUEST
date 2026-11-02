from app.integrations.twitch.commands import parse_chat_command


def test_valid_vote_command():
    command = parse_chat_command("!vote 2")
    assert command is not None
    assert command.name == "vote"
    assert command.argument == "2"


def test_command_is_case_insensitive():
    assert parse_chat_command("!HELP").name == "help"


def test_invalid_command_is_ignored():
    assert parse_chat_command("hello world") is None
    assert parse_chat_command("!vote 4") is None
    assert parse_chat_command("!help now") is None
    assert parse_chat_command("!vote") is None
