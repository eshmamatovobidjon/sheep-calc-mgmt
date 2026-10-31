from aiogram.filters import Filter
from aiogram.types import TelegramObject

from sheepbot.db.models import BotUser
from sheepbot.domain.enums import Perm
from sheepbot.services.users import has_permission

__all__ = ["HasPermission", "Perm"]


class HasPermission(Filter):
    """Passes if the current user (from AuthMiddleware) has the permission."""

    def __init__(self, perm: Perm) -> None:
        self.perm = perm

    async def __call__(self, event: TelegramObject, user: BotUser | None = None) -> bool:
        return has_permission(user, self.perm)
