import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from sheepbot.bot import texts
from sheepbot.bot.handlers import ROUTERS
from sheepbot.bot.middlewares import AuthMiddleware, DbSessionMiddleware
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
    # Registration order = execution order: Auth needs the session.
    dp.update.outer_middleware(DbSessionMiddleware(get_sessionmaker()))
    dp.update.outer_middleware(AuthMiddleware())
    dp.include_routers(*ROUTERS)
    return dp


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [BotCommand(command=name, description=desc) for name, desc in texts.COMMANDS.items()]
    )


async def main() -> None:
    settings = get_settings()
    await prepare_db()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()
    await set_commands(bot)

    logger.info("Starting polling")
    try:
        await dp.start_polling(bot)
    finally:
        await get_engine().dispose()
