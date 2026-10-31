from aiogram import F
from aiogram.filters import Filter
from aiogram.types import TelegramObject

from sheepbot.bot import texts
from sheepbot.bot.keyboards import MENU_ITEMS
from sheepbot.db.models import BotUser
from sheepbot.domain.enums import Perm
from sheepbot.services.users import has_permission, is_allowed

__all__ = ["DialogText", "HasPermission", "IsAllowed", "Perm"]

_RESERVED_TEXTS = {item.button for item in MENU_ITEMS} | {texts.BTN_CANCEL}

# Free text typed inside a dialog: not a command and not a menu button,
# so commands and menu buttons always reach their own handlers.
DialogText = F.text & ~F.text.startswith("/") & ~F.text.in_(_RESERVED_TEXTS)


class HasPermission(Filter):
    """Passes if the current user (from AuthMiddleware) has the permission."""

    def __init__(self, perm: Perm) -> None:
        self.perm = perm

    async def __call__(self, event: TelegramObject, user: BotUser | None = None) -> bool:
        return has_permission(user, self.perm)


class IsAllowed(Filter):
    """Passes if the user has at least one permission."""

    async def __call__(self, event: TelegramObject, user: BotUser | None = None) -> bool:
        return is_allowed(user)
