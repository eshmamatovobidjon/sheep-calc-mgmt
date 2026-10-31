"""Reusable "search and pick a client" step.

Usage from another dialog:
    client_picker.register("my_purpose", on_picked)      # once, at module import
    await client_picker.start(message, state, "my_purpose")
The picker handles the typing and the buttons, then calls
    await on_picked(callback, state, session, user, client)
with the FSM still in the picker state; the handler sets the next state (or clears it).
The picker answers the callback query itself, so the handler must not.
"""

from collections.abc import Awaitable, Callable
from enum import StrEnum
from html import escape

from aiogram import F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.bot import texts
from sheepbot.bot.filters import DialogText, IsAllowed
from sheepbot.bot.keyboards import cancel_keyboard
from sheepbot.bot.states import ClientPickerStates
from sheepbot.db.models import BotUser, Client
from sheepbot.services import clients

PickedHandler = Callable[
    [CallbackQuery, FSMContext, AsyncSession, BotUser, Client], Awaitable[None]
]

MIN_QUERY = 2
MAX_RESULTS = 10
PURPOSE_KEY = "picker_purpose"

_handlers: dict[str, PickedHandler] = {}

router = Router(name="client_picker")
router.message.filter(IsAllowed())
router.callback_query.filter(IsAllowed())


class ClientAction(StrEnum):
    PICK = "pk"
    FIND = "f"
    ADD = "a"
    LIST = "l"
    OPEN = "o"
    RENAME = "r"
    PAY = "p"


class ClientCb(CallbackData, prefix="cli"):
    """Shared by the picker and the /clients screens."""

    action: ClientAction
    client_id: int = 0
    page: int = 0


def register(purpose: str, handler: PickedHandler) -> None:
    _handlers[purpose] = handler


async def start(
    message: Message,
    state: FSMContext,
    purpose: str,
    keyboard: ReplyKeyboardMarkup | None = None,
) -> None:
    """Enter the picker step. `keyboard` defaults to the single "Отмена" button."""
    await state.set_state(ClientPickerStates.query)
    await state.update_data({PURPOSE_KEY: purpose})
    await message.answer(texts.PICKER_PROMPT, reply_markup=keyboard or cancel_keyboard())


@router.message(ClientPickerStates.query, DialogText)
async def on_query(message: Message, session: AsyncSession) -> None:
    query = message.text or ""
    if len(clients.normalize_client_name(query)) < MIN_QUERY:
        await message.answer(texts.PICKER_TOO_SHORT)
        return
    found = await clients.search_clients(session, query, MAX_RESULTS)
    if not found:
        await message.answer(texts.PICKER_NOT_FOUND)
        return
    builder = InlineKeyboardBuilder()
    for client in found:
        builder.button(
            text=client.name, callback_data=ClientCb(action=ClientAction.PICK, client_id=client.id)
        )
    builder.adjust(1)
    await message.answer(texts.PICKER_CHOOSE, reply_markup=builder.as_markup())


@router.callback_query(ClientPickerStates.query, ClientCb.filter(F.action == ClientAction.PICK))
async def on_pick(
    callback: CallbackQuery,
    callback_data: ClientCb,
    state: FSMContext,
    session: AsyncSession,
    user: BotUser,
) -> None:
    client = await clients.get_client(session, callback_data.client_id)
    if client is None:
        await callback.answer(texts.CLIENT_NOT_FOUND, show_alert=True)
        return
    handler = _handlers.get((await state.get_data()).get(PURPOSE_KEY, ""))
    if handler is None:
        await state.clear()
        await callback.answer(texts.CALLBACK_EXPIRED, show_alert=True)
        return

    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.PICKER_CHOSEN.format(name=escape(client.name)))
    await handler(callback, state, session, user, client)
    await callback.answer()
