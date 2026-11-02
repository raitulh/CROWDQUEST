import asyncio
import logging

from app.core.config import settings
from app.workers.eventsub import EventSubSupervisor
from app.workers.timers import run_timer_worker


async def main() -> None:
    logging.basicConfig(level=settings.log_level)
    supervisor = EventSubSupervisor()
    await asyncio.gather(supervisor.run(), run_timer_worker())


if __name__ == "__main__":
    asyncio.run(main())
