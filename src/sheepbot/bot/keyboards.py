from dataclasses import dataclass

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from sheepbot.bot import texts
from sheepbot.db.models import BotUser
from sheepbot.domain.enums import Perm
from sheepbot.services.users import has_permission


@dataclass(frozen=True, slots=True)
class MenuItem:
    button: str
    command: str | None
    perm: Perm


MENU_ITEMS: tuple[MenuItem, ...] = (
    MenuItem(texts.BTN_UPLOAD, None, Perm.UPLOAD),
    MenuItem(texts.BTN_TEMPLATE, "template", Perm.UPLOAD),
    MenuItem(texts.BTN_PAY, "pay", Perm.UPLOAD),
    MenuItem(texts.BTN_PAYMENTS, "payments", Perm.UPLOAD),
    MenuItem(texts.BTN_CLIENTS, "clients", Perm.UPLOAD),
    MenuItem(texts.BTN_REPORTS, "report", Perm.VIEW),
    MenuItem(texts.BTN_DEBTS, "debts", Perm.VIEW),
    MenuItem(texts.BTN_TRIPS, "trips", Perm.VIEW),
    MenuItem(texts.BTN_USERS, "users", Perm.ADMIN),
)

ROW_WIDTH = 2


def find_menu_item(text: str) -> MenuItem | None:
    """Match a menu button label or its command (e.g. '/pay' or '/pay@bot')."""
    text = text.strip()
    command = None
    if text.startswith("/"):
        parts = text[1:].split(maxsplit=1)
        if parts:
            command = parts[0].split("@", 1)[0].lower()
    for item in MENU_ITEMS:
        if text == item.button or (command and command == item.command):
            return item
    return None


def main_menu(user: BotUser | None) -> ReplyKeyboardMarkup:
    """Reply keyboard with only the buttons the user may use, grouped by permission."""
    rows: list[list[KeyboardButton]] = []
    for perm in (Perm.UPLOAD, Perm.VIEW, Perm.ADMIN):
        if not has_permission(user, perm):
            continue
        buttons = [KeyboardButton(text=i.button) for i in MENU_ITEMS if i.perm is perm]
        rows.extend(buttons[i : i + ROW_WIDTH] for i in range(0, len(buttons), ROW_WIDTH))
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.BTN_CANCEL)]], resize_keyboard=True
    )
