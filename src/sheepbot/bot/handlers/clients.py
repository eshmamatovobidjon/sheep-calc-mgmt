"""/clients: find, add, list with balances, client card, rename, pay."""

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.bot import client_picker, texts
from sheepbot.bot.client_picker import ClientAction, ClientCb
from sheepbot.bot.filters import DialogText, HasPermission, Perm
from sheepbot.bot.handlers.payments import balance_value, format_balance, start_for_client
from sheepbot.bot.keyboards import cancel_keyboard, main_menu
from sheepbot.bot.states import ClientStates
from sheepbot.db.models import BotUser, Client
from sheepbot.domain.formatting import fmt_date, fmt_money
from sheepbot.services import balances, clients
from sheepbot.services.clients import ClientExistsError

router = Router(name="clients")
router.message.filter(HasPermission(Perm.UPLOAD))
router.callback_query.filter(HasPermission(Perm.UPLOAD))

PICK_PURPOSE = "client_card"
PAGE_SIZE = 20
NAME_MIN, NAME_MAX = 2, 100


def _menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_CLIENT_FIND, callback_data=ClientCb(action=ClientAction.FIND))
    builder.button(text=texts.BTN_CLIENT_ADD, callback_data=ClientCb(action=ClientAction.ADD))
    builder.button(text=texts.BTN_CLIENT_ALL, callback_data=ClientCb(action=ClientAction.LIST))
    builder.adjust(3)
    return builder.as_markup()


def _card_keyboard(client_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.BTN_CLIENT_RENAME,
        callback_data=ClientCb(action=ClientAction.RENAME, client_id=client_id),
    )
    builder.button(
        text=texts.BTN_CLIENT_PAY,
        callback_data=ClientCb(action=ClientAction.PAY, client_id=client_id),
    )
    builder.adjust(2)
    return builder.as_markup()


async def send_card(message: Message, session: AsyncSession, client_id: int) -> None:
    info = await balances.get_client_balance(session, client_id)
    if info is None:
        await message.answer(texts.CLIENT_NOT_FOUND)
        return
    text = texts.CLIENT_CARD.format(
        name=escape(info.name),
        balance=format_balance(info.balance),
        shipped=fmt_money(info.shipped),
        paid=fmt_money(info.paid),
        last_sale=fmt_date(info.last_sale_date) if info.last_sale_date else texts.NO_VALUE,
        last_payment=fmt_date(info.last_payment_date) if info.last_payment_date else texts.NO_VALUE,
    )
    await message.answer(text, reply_markup=_card_keyboard(client_id))


def _valid_name(text: str) -> str | None:
    name = " ".join(text.split())
    return name if NAME_MIN <= len(name) <= NAME_MAX else None


async def _on_client_picked(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: BotUser, client: Client
) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        await send_card(callback.message, session, client.id)


client_picker.register(PICK_PURPOSE, _on_client_picked)


@router.message(Command("clients"))
@router.message(F.text == texts.BTN_CLIENTS)
async def cmd_clients(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CLIENTS_MENU, reply_markup=_menu_keyboard())


@router.callback_query(ClientCb.filter(F.action == ClientAction.FIND))
async def on_find(callback: CallbackQuery, state: FSMContext, user: BotUser) -> None:
    if isinstance(callback.message, Message):
        await client_picker.start(callback.message, state, PICK_PURPOSE, keyboard=main_menu(user))
    await callback.answer()


@router.callback_query(ClientCb.filter(F.action == ClientAction.ADD))
async def on_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ClientStates.add_name)
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.CLIENT_ASK_NAME, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(ClientStates.add_name, DialogText)
async def on_add_name(
    message: Message, state: FSMContext, session: AsyncSession, user: BotUser
) -> None:
    name = _valid_name(message.text or "")
    if name is None:
        await message.answer(texts.CLIENT_NAME_INVALID.format(limit=NAME_MAX))
        return
    try:
        client = await clients.create_client(session, name, user.id)
    except ClientExistsError as exc:
        await message.answer(texts.CLIENT_EXISTS.format(name=escape(exc.client.name)))
        return
    await state.clear()
    await message.answer(
        texts.CLIENT_ADDED.format(name=escape(client.name)), reply_markup=main_menu(user)
    )
    await send_card(message, session, client.id)


@router.callback_query(ClientCb.filter(F.action == ClientAction.LIST))
async def on_list(callback: CallbackQuery, callback_data: ClientCb, session: AsyncSession) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    total = await clients.count_clients(session)
    if total == 0:
        await callback.message.edit_text(texts.CLIENTS_EMPTY)
        await callback.answer()
        return

    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = min(max(callback_data.page, 0), pages - 1)
    page_clients = await clients.list_clients(session, page * PAGE_SIZE, PAGE_SIZE)
    info = await balances.balances_for(session, [c.id for c in page_clients])

    lines = [texts.CLIENTS_PAGE_TITLE.format(page=page + 1, pages=pages), ""]
    builder = InlineKeyboardBuilder()
    for client in page_clients:
        balance = info[client.id].balance
        lines.append(
            texts.CLIENT_LINE.format(name=escape(client.name), balance=balance_value(balance))
        )
        builder.button(
            text=client.name, callback_data=ClientCb(action=ClientAction.OPEN, client_id=client.id)
        )
    builder.adjust(2)
    nav = []
    if page > 0:
        nav.append((texts.BTN_PREV, page - 1))
    if page < pages - 1:
        nav.append((texts.BTN_NEXT, page + 1))
    if nav:
        nav_builder = InlineKeyboardBuilder()
        for text, target in nav:
            nav_builder.button(
                text=text, callback_data=ClientCb(action=ClientAction.LIST, page=target)
            )
        builder.attach(nav_builder)

    await callback.message.edit_text("\n".join(lines), reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(ClientCb.filter(F.action == ClientAction.OPEN))
async def on_open(callback: CallbackQuery, callback_data: ClientCb, session: AsyncSession) -> None:
    if isinstance(callback.message, Message):
        await send_card(callback.message, session, callback_data.client_id)
    await callback.answer()


@router.callback_query(ClientCb.filter(F.action == ClientAction.RENAME))
async def on_rename(
    callback: CallbackQuery, callback_data: ClientCb, state: FSMContext, session: AsyncSession
) -> None:
    client = await clients.get_client(session, callback_data.client_id)
    if client is None or not isinstance(callback.message, Message):
        await callback.answer(texts.CLIENT_NOT_FOUND, show_alert=True)
        return
    await state.set_state(ClientStates.rename)
    await state.set_data({"client_id": client.id})
    await callback.message.answer(
        texts.CLIENT_ASK_NEW_NAME.format(name=escape(client.name)), reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(ClientStates.rename, DialogText)
async def on_rename_name(
    message: Message, state: FSMContext, session: AsyncSession, user: BotUser
) -> None:
    name = _valid_name(message.text or "")
    if name is None:
        await message.answer(texts.CLIENT_NAME_INVALID.format(limit=NAME_MAX))
        return
    client_id = (await state.get_data())["client_id"]
    try:
        client = await clients.rename_client(session, client_id, name)
    except ClientExistsError as exc:
        await message.answer(texts.CLIENT_EXISTS.format(name=escape(exc.client.name)))
        return
    await state.clear()
    await message.answer(
        texts.CLIENT_RENAMED.format(name=escape(client.name)), reply_markup=main_menu(user)
    )
    await send_card(message, session, client.id)


@router.callback_query(ClientCb.filter(F.action == ClientAction.PAY))
async def on_pay(
    callback: CallbackQuery, callback_data: ClientCb, state: FSMContext, session: AsyncSession
) -> None:
    client = await clients.get_client(session, callback_data.client_id)
    if client is None or not isinstance(callback.message, Message):
        await callback.answer(texts.CLIENT_NOT_FOUND, show_alert=True)
        return
    await state.clear()
    await start_for_client(callback.message, state, session, client, show_name=True)
    await callback.answer()
