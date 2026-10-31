"""Trip .xlsx upload: validate -> preview -> Сохранить / Отмена."""

import asyncio
from enum import StrEnum
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.bot import texts
from sheepbot.bot.filters import HasPermission, Perm
from sheepbot.config import get_settings
from sheepbot.db.models import BotUser
from sheepbot.domain.enums import UploadStatus
from sheepbot.domain.formatting import fmt_date, fmt_kg, fmt_money, fmt_percent, plural
from sheepbot.excel.parser import ParseResult, parse_trip_workbook
from sheepbot.services import trips

router = Router(name="upload")
router.message.filter(HasPermission(Perm.UPLOAD))
router.callback_query.filter(HasPermission(Perm.UPLOAD))

MESSAGE_LIMIT = 4096
MESSAGE_RESERVE = 200  # room for the "…и ещё N" tail
MAX_NEW_CLIENTS_SHOWN = 20


class UploadAction(StrEnum):
    SAVE = "s"
    CANCEL = "c"


class UploadCb(CallbackData, prefix="upl"):
    action: UploadAction
    upload_id: int


def _preview_keyboard(upload_id: int) -> InlineKeyboardMarkup:
    def button(text: str, action: UploadAction) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=text, callback_data=UploadCb(action=action, upload_id=upload_id).pack()
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button(texts.BTN_SAVE, UploadAction.SAVE),
                button(texts.BTN_UPLOAD_CANCEL, UploadAction.CANCEL),
            ]
        ]
    )


def format_errors(result: ParseResult) -> str:
    lines = [texts.UPLOAD_REJECTED, ""]
    length = sum(len(line) + 1 for line in lines)
    shown = 0
    for i, error in enumerate(result.errors, start=1):
        line = f"{i}. {escape(str(error))}"
        if length + len(line) + 1 > MESSAGE_LIMIT - MESSAGE_RESERVE:
            break
        lines.append(line)
        length += len(line) + 1
        shown += 1
    rest = len(result.errors) - shown
    if rest:
        lines.append(texts.UPLOAD_ERRORS_MORE.format(n=rest, word=plural(rest, texts.ERROR_FORMS)))
    if result.too_many_errors:
        lines.append(texts.UPLOAD_ERRORS_STOPPED.format(n=len(result.errors)))
    return "\n".join(lines)


def format_preview(preview: trips.TripPreview) -> str:
    t = preview.totals
    title = texts.PREVIEW_TITLE.format(number=preview.number)
    if preview.replaces_existing:
        title += texts.PREVIEW_REPLACES
    sale_lines = t.sales.lines
    clients = len(t.sales_by_client)
    margin = t.margin_pct
    lines = [
        title,
        texts.PREVIEW_DEPARTURE.format(date=fmt_date(preview.departure_date)),
        texts.PREVIEW_PURCHASE.format(
            heads=t.purchases.heads,
            gross=fmt_kg(t.purchases.gross_kg),
            net=fmt_kg(t.purchases.net_kg),
            kzt=fmt_money(t.purchases.amount_kzt),
            uzs=fmt_money(t.purchases.amount_uzs),
        ),
        texts.PREVIEW_EXPENSES.format(uzs=fmt_money(t.expenses_uzs)),
        texts.PREVIEW_SALES.format(
            heads=t.sales.heads,
            net=fmt_kg(t.sales.net_kg),
            uzs=fmt_money(t.revenue_uzs),
            lines=sale_lines,
            lines_word=plural(sale_lines, texts.LINE_FORMS),
            clients=clients,
            clients_word=plural(clients, texts.CLIENT_FORMS),
        ),
        texts.PREVIEW_PROFIT.format(
            uzs=fmt_money(t.profit_uzs), pct=fmt_percent(margin) if margin is not None else "—"
        ),
    ]
    new = preview.new_client_names
    if new:
        names = ", ".join(escape(n) for n in new[:MAX_NEW_CLIENTS_SHOWN])
        if len(new) > MAX_NEW_CLIENTS_SHOWN:
            names += texts.PREVIEW_MORE.format(n=len(new) - MAX_NEW_CLIENTS_SHOWN)
        lines.append(texts.PREVIEW_NEW_CLIENTS.format(count=len(new), names=names))
    lines += ["", texts.PREVIEW_CONFIRM]
    return "\n".join(lines)


async def _close_preview(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)


@router.message(F.text == texts.BTN_UPLOAD)
async def ask_for_file(message: Message) -> None:
    await message.answer(texts.UPLOAD_PROMPT)


@router.message(F.document)
async def on_document(message: Message, session: AsyncSession, user: BotUser, bot: Bot) -> None:
    document = message.document
    assert document is not None
    file_name = document.file_name or ""
    if not file_name.lower().endswith(".xlsx"):
        await message.answer(texts.UPLOAD_WRONG_TYPE)
        return
    max_mb = get_settings().max_upload_mb
    if (document.file_size or 0) > max_mb * 1024 * 1024:
        await message.answer(texts.UPLOAD_TOO_BIG.format(mb=max_mb))
        return

    buffer = await bot.download(document)
    assert buffer is not None
    data = buffer.read()
    upload = await trips.create_upload(session, file_name, data, user)
    result = await asyncio.to_thread(parse_trip_workbook, data)
    if result.trip is None:
        trips.set_upload_status(upload, UploadStatus.REJECTED)
        await message.answer(format_errors(result))
        return

    trips.set_upload_status(upload, UploadStatus.PENDING, result.trip.number)
    preview = await trips.build_preview(session, result.trip)
    await message.answer(format_preview(preview), reply_markup=_preview_keyboard(upload.id))


@router.callback_query(UploadCb.filter(F.action == UploadAction.SAVE))
async def on_save(
    callback: CallbackQuery, callback_data: UploadCb, session: AsyncSession, user: BotUser
) -> None:
    upload = await trips.get_pending_upload(session, callback_data.upload_id, user)
    if upload is None:
        await callback.answer(texts.CALLBACK_EXPIRED, show_alert=True)
        return

    # Stateless: parse the stored file again, so saving works after a restart.
    result = await asyncio.to_thread(parse_trip_workbook, trips.read_upload_file(upload))
    await _close_preview(callback)
    if result.trip is None:
        trips.set_upload_status(upload, UploadStatus.REJECTED)
        if isinstance(callback.message, Message):
            await callback.message.answer(format_errors(result))
        await callback.answer()
        return

    trip = await trips.save_trip(session, result.trip, upload, user)
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.UPLOAD_SAVED.format(number=trip.number))
    await callback.answer()


@router.callback_query(UploadCb.filter(F.action == UploadAction.CANCEL))
async def on_cancel(
    callback: CallbackQuery, callback_data: UploadCb, session: AsyncSession, user: BotUser
) -> None:
    upload = await trips.get_pending_upload(session, callback_data.upload_id, user)
    if upload is None:
        await callback.answer(texts.CALLBACK_EXPIRED, show_alert=True)
        return
    trips.set_upload_status(upload, UploadStatus.CANCELLED)
    await _close_preview(callback)
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.UPLOAD_CANCELLED)
    await callback.answer()
