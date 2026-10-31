"""Admin: access requests and /users."""

import logging
from enum import StrEnum
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.bot import texts
from sheepbot.bot.filters import HasPermission, Perm
from sheepbot.bot.keyboards import main_menu
from sheepbot.config import get_settings
from sheepbot.db.models import BotUser
from sheepbot.domain.enums import USER_STATUS_LABELS, UserStatus
from sheepbot.services import users

logger = logging.getLogger(__name__)

router = Router(name="users")
router.message.filter(HasPermission(Perm.ADMIN))
router.callback_query.filter(HasPermission(Perm.ADMIN))

STATUS_ORDER = (UserStatus.PENDING, UserStatus.ACTIVE, UserStatus.BLOCKED)


class UserAction(StrEnum):
    GRANT_UPLOAD = "gu"
    GRANT_VIEW = "gv"
    GRANT_BOTH = "gb"
    REJECT = "rj"
    LIST = "ls"
    OPEN = "op"
    TOGGLE_UPLOAD = "tu"
    TOGGLE_VIEW = "tv"
    BLOCK = "bl"
    UNBLOCK = "ub"


REQUEST_ACTIONS = (
    UserAction.GRANT_UPLOAD,
    UserAction.GRANT_VIEW,
    UserAction.GRANT_BOTH,
    UserAction.REJECT,
)
CARD_ACTIONS = (
    UserAction.TOGGLE_UPLOAD,
    UserAction.TOGGLE_VIEW,
    UserAction.BLOCK,
    UserAction.UNBLOCK,
)


class UserCb(CallbackData, prefix="usr"):
    action: UserAction
    user_id: int = 0


# --- text and keyboard builders ---


def _username(user: BotUser) -> str:
    return escape(f"@{user.username}") if user.username else "—"


def _perms_text(can_upload: bool, can_view: bool) -> str:
    perms = [p for p, on in ((texts.PERM_UPLOAD, can_upload), (texts.PERM_VIEW, can_view)) if on]
    return ", ".join(perms) or texts.NO_PERMS


def request_card_text(user: BotUser) -> str:
    return texts.REQUEST_CARD.format(
        name=escape(user.full_name), username=_username(user), tg_id=user.telegram_id
    )


def request_keyboard(user_id: int) -> InlineKeyboardMarkup:
    def button(text: str, action: UserAction) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=text, callback_data=UserCb(action=action, user_id=user_id).pack()
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button(texts.BTN_REQ_UPLOAD, UserAction.GRANT_UPLOAD),
                button(texts.BTN_REQ_VIEW, UserAction.GRANT_VIEW),
            ],
            [
                button(texts.BTN_REQ_BOTH, UserAction.GRANT_BOTH),
                button(texts.BTN_REQ_REJECT, UserAction.REJECT),
            ],
        ]
    )


def user_card_text(user: BotUser) -> str:
    return texts.USER_CARD.format(
        name=escape(user.full_name),
        username=_username(user),
        tg_id=user.telegram_id,
        status=USER_STATUS_LABELS[user.status],
        perms=_perms_text(user.can_upload, user.can_view),
    )


def user_card_keyboard(user: BotUser) -> InlineKeyboardMarkup:
    def mark(on: bool) -> str:
        return texts.MARK_ON if on else texts.MARK_OFF

    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.BTN_TOGGLE_UPLOAD.format(mark=mark(user.can_upload)),
        callback_data=UserCb(action=UserAction.TOGGLE_UPLOAD, user_id=user.id),
    )
    builder.button(
        text=texts.BTN_TOGGLE_VIEW.format(mark=mark(user.can_view)),
        callback_data=UserCb(action=UserAction.TOGGLE_VIEW, user_id=user.id),
    )
    if user.status == UserStatus.BLOCKED:
        builder.button(
            text=texts.BTN_UNBLOCK, callback_data=UserCb(action=UserAction.UNBLOCK, user_id=user.id)
        )
    else:
        builder.button(
            text=texts.BTN_BLOCK, callback_data=UserCb(action=UserAction.BLOCK, user_id=user.id)
        )
    builder.button(text=texts.BTN_BACK, callback_data=UserCb(action=UserAction.LIST))
    builder.adjust(2, 1, 1)
    return builder.as_markup()


async def users_list_view(session: AsyncSession) -> tuple[str, InlineKeyboardMarkup | None]:
    managed = [u for u in await users.list_users(session) if not u.is_admin]
    if not managed:
        return texts.USERS_EMPTY, None

    managed.sort(key=lambda u: STATUS_ORDER.index(u.status))
    counts = {status: sum(u.status == status for u in managed) for status in STATUS_ORDER}
    text = texts.USERS_TITLE.format(
        pending=counts[UserStatus.PENDING],
        active=counts[UserStatus.ACTIVE],
        blocked=counts[UserStatus.BLOCKED],
    )
    builder = InlineKeyboardBuilder()
    for u in managed:
        builder.button(
            text=f"{texts.STATUS_ICONS[u.status]} {u.full_name}",
            callback_data=UserCb(action=UserAction.OPEN, user_id=u.id),
        )
    builder.adjust(1)
    return text, builder.as_markup()


# --- notifications ---


async def _send(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None = None,
) -> None:
    try:
        await bot.send_message(chat_id, text, reply_markup=reply_markup)
    except TelegramAPIError:
        logger.warning("Could not send a message to %s", chat_id, exc_info=True)


async def notify_admin_about_request(bot: Bot, user: BotUser) -> None:
    await _send(
        bot,
        get_settings().admin_telegram_id,
        request_card_text(user),
        reply_markup=request_keyboard(user.id),
    )


async def _notify_granted(bot: Bot, user: BotUser) -> None:
    text = texts.ACCESS_GRANTED.format(perms=_perms_text(user.can_upload, user.can_view))
    await _send(bot, user.telegram_id, text, reply_markup=main_menu(user))


async def _edit(
    callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None
) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=reply_markup)


async def _load_target(
    session: AsyncSession, callback: CallbackQuery, user_id: int
) -> BotUser | None:
    target = await users.get_by_id(session, user_id)
    if target is None:
        await callback.answer(texts.USER_NOT_FOUND, show_alert=True)
        return None
    if target.is_admin:
        await callback.answer(texts.CANNOT_CHANGE_ADMIN, show_alert=True)
        return None
    return target


# --- handlers ---


@router.callback_query(UserCb.filter(F.action.in_(REQUEST_ACTIONS)))
async def on_request_decision(
    callback: CallbackQuery, callback_data: UserCb, session: AsyncSession, bot: Bot
) -> None:
    target = await _load_target(session, callback, callback_data.user_id)
    if target is None:
        return

    action = callback_data.action
    if action is UserAction.REJECT:
        await users.set_permissions(session, target.id, can_upload=False, can_view=False)
        await users.set_status(session, target.id, UserStatus.BLOCKED)
        result = texts.REQUEST_REJECTED
        await _send(bot, target.telegram_id, texts.ACCESS_CLOSED, ReplyKeyboardRemove())
    else:
        can_upload = action in (UserAction.GRANT_UPLOAD, UserAction.GRANT_BOTH)
        can_view = action in (UserAction.GRANT_VIEW, UserAction.GRANT_BOTH)
        await users.set_permissions(session, target.id, can_upload=can_upload, can_view=can_view)
        await users.set_status(session, target.id, UserStatus.ACTIVE)
        result = texts.REQUEST_GRANTED.format(perms=_perms_text(can_upload, can_view))
        await _notify_granted(bot, target)

    await _edit(callback, f"{request_card_text(target)}\n\n{result}", reply_markup=None)
    await callback.answer()


@router.message(Command("users"))
@router.message(F.text == texts.BTN_USERS)
async def cmd_users(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    text, markup = await users_list_view(session)
    await message.answer(text, reply_markup=markup)


@router.callback_query(UserCb.filter(F.action == UserAction.LIST))
async def on_users_list(callback: CallbackQuery, session: AsyncSession) -> None:
    text, markup = await users_list_view(session)
    await _edit(callback, text, markup)
    await callback.answer()


@router.callback_query(UserCb.filter(F.action == UserAction.OPEN))
async def on_user_open(
    callback: CallbackQuery, callback_data: UserCb, session: AsyncSession
) -> None:
    target = await _load_target(session, callback, callback_data.user_id)
    if target is None:
        return
    await _edit(callback, user_card_text(target), user_card_keyboard(target))
    await callback.answer()


@router.callback_query(UserCb.filter(F.action.in_(CARD_ACTIONS)))
async def on_user_change(
    callback: CallbackQuery, callback_data: UserCb, session: AsyncSession, bot: Bot
) -> None:
    target = await _load_target(session, callback, callback_data.user_id)
    if target is None:
        return

    action = callback_data.action
    if action is UserAction.BLOCK:
        await users.set_status(session, target.id, UserStatus.BLOCKED)
    elif action is UserAction.UNBLOCK:
        await users.set_status(session, target.id, UserStatus.ACTIVE)
    else:
        can_upload = target.can_upload ^ (action is UserAction.TOGGLE_UPLOAD)
        can_view = target.can_view ^ (action is UserAction.TOGGLE_VIEW)
        await users.set_permissions(session, target.id, can_upload=can_upload, can_view=can_view)
        # Granting a permission to a pending user approves their request.
        if target.status == UserStatus.PENDING and (can_upload or can_view):
            await users.set_status(session, target.id, UserStatus.ACTIVE)
            await _notify_granted(bot, target)

    await _edit(callback, user_card_text(target), user_card_keyboard(target))
    await callback.answer()
