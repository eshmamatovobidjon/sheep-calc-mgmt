from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sheepbot.services import users


class DbSessionMiddleware(BaseMiddleware):
    """One session per update: commit after the handler, rollback on error."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.sessionmaker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            await session.commit()
            return result


class AuthMiddleware(BaseMiddleware):
    """Injects `user: BotUser | None` by Telegram ID. Never creates users."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        user = None
        if tg_user is not None:
            user = await users.get_by_telegram_id(data["session"], tg_user.id)
            if user is not None:
                users.sync_profile(user, tg_user.full_name, tg_user.username)
        data["user"] = user
        return await handler(event, data)
