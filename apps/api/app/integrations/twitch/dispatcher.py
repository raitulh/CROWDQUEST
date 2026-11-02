import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.integrations.twitch.commands import parse_chat_command
from app.integrations.twitch.client import TwitchClient, TwitchAPIError
from app.models.entities import CrowdSession, QuestRound, RoundStatus, SessionStatus, TwitchConnection
from app.services.game_service import process_contribution, process_vote

logger = logging.getLogger(__name__)


async def dispatch_chat_message(
    db: AsyncSession,
    *,
    event_id: str,
    event: dict,
    connection: TwitchConnection,
    access_token: str,
) -> None:
    message = event.get("message", {}).get("text", "")
    if not isinstance(message, str) or len(message) > settings.max_chat_message_length:
        return
    command = parse_chat_command(message)
    if command is None:
        return

    broadcaster_id = str(event.get("broadcaster_user_id", ""))
    viewer_id = str(event.get("chatter_user_id", ""))
    viewer_login = str(event.get("chatter_user_login", "viewer"))[:100]
    if not broadcaster_id or not viewer_id:
        return

    if command.name in {"quest", "stats", "leaderboard"}:
        allowed = await get_redis().set(
            f"{settings.redis_prefix}:chat-cooldown:{broadcaster_id}:{viewer_id}:{command.name}",
            event_id, ex=settings.chat_user_cooldown_seconds, nx=True,
        )
        if not allowed:
            return

    response_text: str | None = None
    if command.name == "vote" and command.argument is not None:
        result = await process_vote(
            db,
            event_id=event_id,
            broadcaster_id=broadcaster_id,
            viewer_id=viewer_id,
            viewer_login=viewer_login,
            option_id=int(command.argument),
        )
        if result.get("accepted"):
            response_text = f"{viewer_login}, your vote is in. The community is choosing its path."
        elif result.get("reason") == "already_voted":
            response_text = f"{viewer_login}, your vote has already been recorded for this round."
    elif command.name == "help":
        result = await process_contribution(
            db,
            event_id=event_id,
            broadcaster_id=broadcaster_id,
            viewer_id=viewer_id,
            viewer_login=viewer_login,
        )
        if result.get("accepted"):
            response_text = f"{viewer_login} contributed to the quest ({result['progress']}/{result['target']})."
    elif command.name in {"quest", "stats"}:
        session = await db.scalar(select(CrowdSession).where(
            CrowdSession.broadcaster_user_id == broadcaster_id,
            CrowdSession.status.notin_([SessionStatus.ENDED.value, SessionStatus.COMPLETED.value]),
        ).order_by(CrowdSession.created_at.desc()))
        if session and session.current_round_id:
            round_ = await db.get(QuestRound, session.current_round_id)
            if round_:
                if round_.state == RoundStatus.VOTING.value:
                    response_text = f"Current quest: {round_.title}. Vote with !vote 1, !vote 2, or !vote 3."
                elif round_.state == RoundStatus.ACTIVE.value:
                    response_text = f"Current objective: {round_.title}. Help the community with !help."
                else:
                    response_text = f"Current quest: {round_.title}. Watch the stream for the next action."
    elif command.name == "leaderboard":
        response_text = "The community leaderboard is available on the streamer's CrowdQuest page."

    if response_text and "user:write:chat" in (connection.scopes or []):
        # Gameplay processing is independent of chat replies. A per-broadcaster
        # gate prevents a busy channel from causing chat-send rate-limit bursts.
        response_gate = await get_redis().set(
            f"{settings.redis_prefix}:chat-response:{broadcaster_id}",
            event_id,
            ex=max(1, int(settings.twitch_chat_response_cooldown_seconds + 0.999)),
            nx=True,
        )
        if not response_gate:
            return
        twitch = TwitchClient(access_token)
        try:
            await twitch.send_chat_message(broadcaster_id, broadcaster_id, response_text)
        except TwitchAPIError as exc:
            logger.warning("Unable to reply in Twitch chat: %s", exc.status_code)
        finally:
            await twitch.close()
