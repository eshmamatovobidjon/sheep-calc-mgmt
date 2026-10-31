import asyncio

from sheepbot.bot.app import main
from sheepbot.config import get_settings
from sheepbot.log import setup_logging


def run() -> None:
    setup_logging(get_settings().log_level)
    asyncio.run(main())


if __name__ == "__main__":
    run()
