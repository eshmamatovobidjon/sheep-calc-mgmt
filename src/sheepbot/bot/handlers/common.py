"""/start, /menu, /cancel, error handler and the fallback router."""

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ErrorEvent, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.bot import texts
from sheepbot.bot.handlers.users import notify_admin_about_request
from sheepbot.bot.keyboards import find_menu_item, main_menu
from sheepbot.db.models import BotUser
from sheepbot.domain.enums import UserStatus
from sheepbot.services import users

logger = logging.getLogger(__name__)

router = Router(name="common")
# Must stay last in ROUTERS.
fallback_router = Router(name="fallback")


def _denied_text(user: BotUser | None) -> str:
    if user is None:
        return texts.NOT_REGISTERED
    if user.status == UserStatus.PENDING:
        return texts.REQUEST_PENDING
    return texts.ACCESS_CLOSED


async def _answer_denied(message: Message, user: BotUser | None) -> None:
    await message.answer(_denied_text(user), reply_markup=ReplyKeyboardRemove())


@router.message(CommandStart())
async def cmd_start(
    message: Message, session: AsyncSession, user: BotUser | None, bot: Bot, state: FSMContext
) -> None:
    await state.clear()
    if user is None:
        tg_user = message.from_user
        if tg_user is None:
            return
        user = await users.create_pending(session, tg_user.id, tg_user.full_name, tg_user.username)
        await message.answer(texts.REQUEST_SENT, reply_markup=ReplyKeyboardRemove())
        await notify_admin_about_request(bot, user)
        return

    if not users.is_allowed(user):
        await _answer_denied(message, user)
        return
    await message.answer(
        texts.GREETING.format(name=escape(user.full_name)), reply_markup=main_menu(user)
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, user: BotUser | None) -> None:
    if not users.is_allowed(user):
        await _answer_denied(message, user)
        return
    await message.answer(texts.MAIN_MENU, reply_markup=main_menu(user))


@router.message(Command("cancel"))
@router.message(F.text == texts.BTN_CANCEL)
async def cmd_cancel(message: Message, user: BotUser | None, state: FSMContext) -> None:
    await state.clear()
    if not users.is_allowed(user):
        await _answer_denied(message, user)
        return
    await message.answer(texts.CANCELLED, reply_markup=main_menu(user))


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    logger.error("Unhandled error", exc_info=event.exception)
    update = event.update
    try:
        if update.message is not None:
            await update.message.answer(texts.ERROR_GENERIC)
        elif update.callback_query is not None:
            await update.callback_query.answer(texts.ERROR_GENERIC, show_alert=True)
    except TelegramAPIError:
        logger.warning("Could not report the error to the user", exc_info=True)
    return True


@fallback_router.message()
async def fallback_message(message: Message, user: BotUser | None, state: FSMContext) -> None:
    if not users.is_allowed(user):
        await _answer_denied(message, user)
        return

    item = find_menu_item(message.text or "")
    if item is not None:
        await state.clear()  # a menu button leaves any open dialog
    if message.document is not None:
        text = texts.NO_ACCESS  # the upload router handles documents from Upload users
    elif item is None:
        text = texts.UNKNOWN_INPUT
    elif not users.has_permission(user, item.perm):
        text = texts.NO_ACCESS
    else:
        text = texts.IN_DEVELOPMENT
    await message.answer(text, reply_markup=main_menu(user))


@fallback_router.callback_query()
async def fallback_callback(callback: CallbackQuery, user: BotUser | None) -> None:
    text = texts.CALLBACK_EXPIRED if users.is_allowed(user) else _denied_text(user)
    await callback.answer(text)
