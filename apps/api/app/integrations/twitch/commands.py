import re
from dataclasses import dataclass


_COMMAND_RE = re.compile(r"^!(quest|help|vote|stats|leaderboard)(?:\s+([1-3]))?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ChatCommand:
    name: str
    argument: str | None


def parse_chat_command(message: str) -> ChatCommand | None:
    match = _COMMAND_RE.fullmatch(message.strip())
    if not match:
        return None
    name = match.group(1).lower()
    argument = match.group(2)
    if name == "vote" and argument is None:
        return None
    if name != "vote" and argument is not None:
        return None
    return ChatCommand(name=name, argument=argument)
