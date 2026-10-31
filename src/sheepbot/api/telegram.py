from functools import lru_cache

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from sheepbot.config import get_settings


@lru_cache
def get_bot() -> Bot:
    """Bot client for sending messages from the API process; it never polls."""
    return Bot(get_settings().bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
