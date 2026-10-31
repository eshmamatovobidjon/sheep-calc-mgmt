"""/pay dialog and /payments (recent payments with soft delete)."""

from datetime import date, timedelta
from enum import StrEnum
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.bot import client_picker, texts
from sheepbot.bot.filters import DialogText, HasPermission, Perm
from sheepbot.bot.keyboards import cancel_keyboard, main_menu
from sheepbot.bot.states import PaymentStates
from sheepbot.db.models import BotUser, Client, Payment
from sheepbot.domain.enums import PAYMENT_METHOD_LABELS, PaymentMethod
from sheepbot.domain.formatting import fmt_date, fmt_money, parse_amount, parse_date, today
from sheepbot.services import balances, clients, payments

router = Router(name="payments")
router.message.filter(HasPermission(Perm.UPLOAD))
router.callback_query.filter(HasPermission(Perm.UPLOAD))

PICK_PURPOSE = "pay"
COMMENT_LIMIT = 500
RECENT_LIMIT = 20
DELETE_BUTTONS_PER_ROW = 4


class PayAction(StrEnum):
    METHOD = "m"
    DATE = "d"
    SKIP_COMMENT = "sk"
    SAVE = "s"
    CANCEL = "c"
    DELETE = "del"
    DELETE_YES = "y"
    DELETE_NO = "n"


class DateChoice(StrEnum):
    TODAY = "t"
    YESTERDAY = "y"
    OTHER = "o"


class PayCb(CallbackData, prefix="pay"):
    action: PayAction
    value: str = ""


# --- shared formatting (also used by /clients) ---


def format_balance(balance: int) -> str:
    if balance > 0:
        return texts.BALANCE_DEBT.format(amount=fmt_money(balance))
    if balance < 0:
        return texts.BALANCE_OVERPAID.format(amount=fmt_money(-balance))
    return texts.BALANCE_ZERO


def balance_value(balance: int) -> str:
    if balance < 0:
        return texts.BALANCE_VALUE_OVERPAID.format(amount=fmt_money(-balance))
    return fmt_money(balance)


def _payment_summary(payment: Payment) -> dict[str, str]:
    return {
        "date": fmt_date(payment.date),
        "client": escape(payment.client.name),
        "amount": fmt_money(payment.amount_uzs),
        "method": PAYMENT_METHOD_LABELS[payment.method],
    }


# --- keyboards ---


def _row_keyboard(buttons: list[tuple[str, PayCb]], per_row: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, cb in buttons:
        builder.button(text=text, callback_data=cb)
    builder.adjust(per_row)
    return builder.as_markup()


def _method_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        (label, PayCb(action=PayAction.METHOD, value=method.value))
        for method, label in PAYMENT_METHOD_LABELS.items()
    ]
    return _row_keyboard(buttons, per_row=3)


def _date_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        (texts.BTN_TODAY, PayCb(action=PayAction.DATE, value=DateChoice.TODAY)),
        (texts.BTN_YESTERDAY, PayCb(action=PayAction.DATE, value=DateChoice.YESTERDAY)),
        (texts.BTN_OTHER_DATE, PayCb(action=PayAction.DATE, value=DateChoice.OTHER)),
    ]
    return _row_keyboard(buttons, per_row=3)


def _skip_keyboard() -> InlineKeyboardMarkup:
    return _row_keyboard([(texts.BTN_SKIP, PayCb(action=PayAction.SKIP_COMMENT))], per_row=1)


def _confirm_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        (texts.BTN_PAY_SAVE, PayCb(action=PayAction.SAVE)),
        (texts.BTN_PAY_CANCEL, PayCb(action=PayAction.CANCEL)),
    ]
    return _row_keyboard(buttons, per_row=2)


async def _freeze(callback: CallbackQuery, text: str | None = None) -> None:
    """Remove the inline buttons from the step message, optionally replacing its text."""
    if not isinstance(callback.message, Message):
        return
    if text is None:
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.message.edit_text(text, reply_markup=None)


# --- /pay dialog ---


async def start_for_client(
    message: Message, state: FSMContext, session: AsyncSession, client: Client, show_name: bool
) -> None:
    """Start the payment dialog at the amount step for an already chosen client."""
    balance = await balances.client_balance(session, client.id)
    await state.set_state(PaymentStates.amount)
    await state.set_data({"client_id": client.id})
    text = texts.PAY_ASK_AMOUNT.format(balance=format_balance(balance))
    if show_name:
        text = texts.PICKER_CHOSEN.format(name=escape(client.name)) + "\n" + text
    await message.answer(text, reply_markup=cancel_keyboard())


async def _on_client_picked(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: BotUser, client: Client
) -> None:
    if isinstance(callback.message, Message):
        await start_for_client(callback.message, state, session, client, show_name=False)


client_picker.register(PICK_PURPOSE, _on_client_picked)


@router.message(Command("pay"))
@router.message(F.text == texts.BTN_PAY)
async def cmd_pay(message: Message, state: FSMContext) -> None:
    await state.clear()
    await client_picker.start(message, state, PICK_PURPOSE)


@router.message(PaymentStates.amount, DialogText)
async def on_amount(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text or "")
    if not amount:
        await message.answer(texts.PAY_AMOUNT_INVALID)
        return
    await state.update_data(amount=amount)
    await state.set_state(PaymentStates.method)
    await message.answer(texts.PAY_ASK_METHOD, reply_markup=_method_keyboard())


@router.callback_query(PaymentStates.method, PayCb.filter(F.action == PayAction.METHOD))
async def on_method(callback: CallbackQuery, callback_data: PayCb, state: FSMContext) -> None:
    method = PaymentMethod(callback_data.value)
    await state.update_data(method=method.value)
    await state.set_state(PaymentStates.date)
    await _freeze(callback, f"{texts.PAY_ASK_METHOD} {PAYMENT_METHOD_LABELS[method]}")
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.PAY_ASK_DATE, reply_markup=_date_keyboard())
    await callback.answer()


async def _ask_comment(message: Message, state: FSMContext, payment_date: date) -> None:
    await state.update_data(date=payment_date.isoformat())
    await state.set_state(PaymentStates.comment)
    await message.answer(texts.PAY_ASK_COMMENT, reply_markup=_skip_keyboard())


@router.callback_query(PaymentStates.date, PayCb.filter(F.action == PayAction.DATE))
async def on_date_choice(callback: CallbackQuery, callback_data: PayCb, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    choice = DateChoice(callback_data.value)
    if choice is DateChoice.OTHER:
        await state.set_state(PaymentStates.custom_date)
        await _freeze(callback)
        await callback.message.answer(texts.PAY_ASK_CUSTOM_DATE)
    else:
        payment_date = today() - timedelta(days=1 if choice is DateChoice.YESTERDAY else 0)
        await _freeze(callback, f"{texts.PAY_ASK_DATE} {fmt_date(payment_date)}")
        await _ask_comment(callback.message, state, payment_date)
    await callback.answer()


@router.message(PaymentStates.custom_date, DialogText)
async def on_custom_date(message: Message, state: FSMContext) -> None:
    payment_date = parse_date(message.text or "")
    if payment_date is None:
        await message.answer(texts.PAY_DATE_INVALID)
        return
    if payment_date > today():
        await message.answer(texts.PAY_DATE_FUTURE)
        return
    await _ask_comment(message, state, payment_date)


async def _show_confirmation(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    client = await clients.get_client(session, data["client_id"])
    if client is None:
        await state.clear()
        await message.answer(texts.CLIENT_NOT_FOUND)
        return
    before = await balances.client_balance(session, client.id)
    after = before - data["amount"]
    card = texts.PAY_CARD.format(
        client=escape(client.name),
        amount=fmt_money(data["amount"]),
        method=PAYMENT_METHOD_LABELS[PaymentMethod(data["method"])],
        date=fmt_date(date.fromisoformat(data["date"])),
        note=escape(data.get("note") or texts.NO_VALUE),
        before=balance_value(before),
        after=balance_value(after),
    )
    await state.set_state(PaymentStates.confirm)
    await message.answer(card, reply_markup=_confirm_keyboard())


@router.message(PaymentStates.comment, DialogText)
async def on_comment(message: Message, state: FSMContext, session: AsyncSession) -> None:
    note = " ".join((message.text or "").split())
    if len(note) > COMMENT_LIMIT:
        await message.answer(texts.PAY_COMMENT_TOO_LONG.format(limit=COMMENT_LIMIT))
        return
    await state.update_data(note=note or None)
    await _show_confirmation(message, state, session)


@router.callback_query(PaymentStates.comment, PayCb.filter(F.action == PayAction.SKIP_COMMENT))
async def on_skip_comment(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await state.update_data(note=None)
    await _freeze(callback)
    if isinstance(callback.message, Message):
        await _show_confirmation(callback.message, state, session)
    await callback.answer()


@router.callback_query(PaymentStates.confirm, PayCb.filter(F.action == PayAction.SAVE))
async def on_save(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: BotUser
) -> None:
    data = await state.get_data()
    await payments.create_payment(
        session,
        client_id=data["client_id"],
        amount_uzs=data["amount"],
        method=PaymentMethod(data["method"]),
        payment_date=date.fromisoformat(data["date"]),
        note=data.get("note"),
        entered_by_id=user.id,
    )
    await state.clear()
    await _freeze(callback)
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.PAY_SAVED, reply_markup=main_menu(user))
    await callback.answer()


@router.callback_query(PaymentStates.confirm, PayCb.filter(F.action == PayAction.CANCEL))
async def on_cancel(callback: CallbackQuery, state: FSMContext, user: BotUser) -> None:
    await state.clear()
    await _freeze(callback)
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.PAY_CANCELLED, reply_markup=main_menu(user))
    await callback.answer()


# --- /payments ---


@router.message(Command("payments"))
@router.message(F.text == texts.BTN_PAYMENTS)
async def cmd_payments(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    recent = await payments.list_recent(session, RECENT_LIMIT)
    if not recent:
        await message.answer(texts.PAYMENTS_EMPTY)
        return
    lines = [texts.PAYMENTS_TITLE, ""]
    buttons = []
    for n, payment in enumerate(recent, start=1):
        lines.append(
            texts.PAYMENT_LINE.format(
                n=n, author=escape(payment.entered_by.full_name), **_payment_summary(payment)
            )
        )
        buttons.append(
            (texts.BTN_DELETE_N.format(n=n), PayCb(action=PayAction.DELETE, value=str(payment.id)))
        )
    await message.answer(
        "\n".join(lines), reply_markup=_row_keyboard(buttons, DELETE_BUTTONS_PER_ROW)
    )


@router.callback_query(PayCb.filter(F.action == PayAction.DELETE))
async def on_delete(callback: CallbackQuery, callback_data: PayCb, session: AsyncSession) -> None:
    payment = await payments.get_payment(session, int(callback_data.value))
    if payment is None or not isinstance(callback.message, Message):
        await callback.answer(texts.CALLBACK_EXPIRED, show_alert=True)
        return
    keyboard = _row_keyboard(
        [
            (texts.BTN_YES, PayCb(action=PayAction.DELETE_YES, value=callback_data.value)),
            (texts.BTN_NO, PayCb(action=PayAction.DELETE_NO, value=callback_data.value)),
        ],
        per_row=2,
    )
    await callback.message.answer(
        texts.PAYMENT_DELETE_CONFIRM.format(**_payment_summary(payment)), reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(PayCb.filter(F.action == PayAction.DELETE_YES))
async def on_delete_yes(
    callback: CallbackQuery, callback_data: PayCb, session: AsyncSession, user: BotUser
) -> None:
    payment = await payments.delete_payment(session, int(callback_data.value), user.id)
    if payment is None:
        await callback.answer(texts.CALLBACK_EXPIRED, show_alert=True)
        return
    await _freeze(callback, texts.PAYMENT_DELETED.format(**_payment_summary(payment)))
    await callback.answer()


@router.callback_query(PayCb.filter(F.action == PayAction.DELETE_NO))
async def on_delete_no(callback: CallbackQuery) -> None:
    await _freeze(callback, texts.PAYMENT_DELETE_KEPT)
    await callback.answer()
