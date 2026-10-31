import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from sheepbot.bot.handlers import ROUTERS
from sheepbot.bot.middlewares import DbSessionMiddleware
from sheepbot.config import get_settings
from sheepbot.db.seed import seed
from sheepbot.db.session import get_engine, get_sessionmaker, init_db

logger = logging.getLogger(__name__)


async def prepare_db() -> None:
    await init_db()
    async with get_sessionmaker()() as session:
        await seed(session)
        await session.commit()


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(DbSessionMiddleware(get_sessionmaker()))
    dp.include_routers(*ROUTERS)
    return dp


async def main() -> None:
    settings = get_settings()
    await prepare_db()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()

    logger.info("Starting polling")
    try:
        await dp.start_polling(bot)
    finally:
        await get_engine().dispose()
