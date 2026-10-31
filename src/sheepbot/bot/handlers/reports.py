"""/report, /debts, /trips handlers (Phase 06)."""

import asyncio
from datetime import date, timedelta
from enum import StrEnum
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.bot import client_picker, texts
from sheepbot.bot.filters import DialogText, HasPermission, Perm
from sheepbot.bot.handlers.payments import balance_value
from sheepbot.bot.keyboards import main_menu
from sheepbot.bot.states import ReportStates
from sheepbot.db.models import BotUser, Client
from sheepbot.domain.formatting import fmt_date, fmt_money, parse_date, plural, today
from sheepbot.reports.data import (
    debtors_data,
    report_filename,
    statement_data,
    trip_summary_data,
)
from sheepbot.reports.pdf_builder import (
    build_debtors_pdf,
    build_statement_pdf,
    build_trip_summary_pdf,
)
from sheepbot.reports.xlsx_builder import (
    build_debtors_xlsx,
    build_statement_xlsx,
    build_trip_summary_xlsx,
)
from sheepbot.services import trips

router = Router(name="reports")
router.message.filter(HasPermission(Perm.VIEW))
router.callback_query.filter(HasPermission(Perm.VIEW))

PICK_PURPOSE = "report_statement"
RECENT_TRIPS_LIMIT = 10
TOP_DEBTORS_LIMIT = 30


class ReportAction(StrEnum):
    TYPE = "t"
    PERIOD = "p"
    STATEMENT_FMT = "sf"
    TRIP_PICK = "tp"
    TRIP_FMT = "tf"
    DEBTORS_FMT = "df"


class ReportKind(StrEnum):
    STATEMENT = "s"
    TRIP = "t"
    DEBTORS = "d"


class PeriodChoice(StrEnum):
    ALL = "all"
    THIS_MONTH = "tm"
    LAST_MONTH = "lm"
    CUSTOM = "c"


class FileFormat(StrEnum):
    PDF = "pdf"
    XLSX = "xlsx"


class ReportCb(CallbackData, prefix="rep"):
    action: ReportAction
    value: str = ""
    item_id: int = 0


# --- keyboards ---


def _report_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.BTN_REPORT_STATEMENT,
        callback_data=ReportCb(action=ReportAction.TYPE, value=ReportKind.STATEMENT),
    )
    builder.button(
        text=texts.BTN_REPORT_TRIP,
        callback_data=ReportCb(action=ReportAction.TYPE, value=ReportKind.TRIP),
    )
    builder.button(
        text=texts.BTN_REPORT_DEBTORS,
        callback_data=ReportCb(action=ReportAction.TYPE, value=ReportKind.DEBTORS),
    )
    builder.adjust(1)
    return builder.as_markup()


def _period_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for label, choice in (
        (texts.BTN_PERIOD_ALL, PeriodChoice.ALL),
        (texts.BTN_PERIOD_THIS_MONTH, PeriodChoice.THIS_MONTH),
        (texts.BTN_PERIOD_LAST_MONTH, PeriodChoice.LAST_MONTH),
        (texts.BTN_PERIOD_CUSTOM, PeriodChoice.CUSTOM),
    ):
        builder.button(text=label, callback_data=ReportCb(action=ReportAction.PERIOD, value=choice))
    builder.adjust(2)
    return builder.as_markup()


def _format_keyboard(action: ReportAction, item_id: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.BTN_FORMAT_PDF,
        callback_data=ReportCb(action=action, value=FileFormat.PDF, item_id=item_id),
    )
    builder.button(
        text=texts.BTN_FORMAT_EXCEL,
        callback_data=ReportCb(action=action, value=FileFormat.XLSX, item_id=item_id),
    )
    builder.adjust(2)
    return builder.as_markup()


def _trips_keyboard(items: list[trips.TripOverview]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(
            text=texts.TRIP_BUTTON.format(number=item.number, date=fmt_date(item.departure_date)),
            callback_data=ReportCb(action=ReportAction.TRIP_PICK, item_id=item.id),
        )
    builder.adjust(2)
    return builder.as_markup()


def _debts_excel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.BTN_DOWNLOAD_EXCEL,
        callback_data=ReportCb(action=ReportAction.DEBTORS_FMT, value=FileFormat.XLSX),
    )
    return builder.as_markup()


async def _freeze(callback: CallbackQuery, text: str | None = None) -> None:
    if not isinstance(callback.message, Message):
        return
    if text is None:
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.message.edit_text(text, reply_markup=None)


def _parse_date_range(text: str) -> tuple[date, date] | None:
    cleaned = text.replace("–", " ").replace("—", " ").replace("-", " ")
    parts = cleaned.split()
    if len(parts) != 2:
        return None
    start = parse_date(parts[0])
    end = parse_date(parts[1])
    if start is None or end is None or start > end:
        return None
    return start, end


# --- /report and "Отчёты" ---


@router.message(Command("report"))
@router.message(F.text == texts.BTN_REPORTS)
async def cmd_report(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.REPORTS_MENU, reply_markup=_report_menu_keyboard())


async def _on_statement_client_picked(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: BotUser,
    client: Client,
) -> None:
    await state.set_state(ReportStates.statement_period)
    await state.set_data({"client_id": client.id})
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.REPORT_ASK_PERIOD, reply_markup=_period_keyboard())


client_picker.register(PICK_PURPOSE, _on_statement_client_picked)


@router.callback_query(ReportCb.filter(F.action == ReportAction.TYPE))
async def on_report_type(
    callback: CallbackQuery,
    callback_data: ReportCb,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    kind = ReportKind(callback_data.value)
    await state.clear()
    if kind is ReportKind.STATEMENT:
        await _freeze(callback, f"{texts.BTN_REPORTS}: <b>{texts.BTN_REPORT_STATEMENT}</b>")
        await client_picker.start(callback.message, state, PICK_PURPOSE)
    elif kind is ReportKind.TRIP:
        await _freeze(callback, f"{texts.BTN_REPORTS}: <b>{texts.BTN_REPORT_TRIP}</b>")
        recent = await trips.list_recent_trips(session, RECENT_TRIPS_LIMIT)
        if not recent:
            await callback.message.answer(texts.TRIPS_EMPTY)
        else:
            await callback.message.answer(
                texts.REPORT_ASK_TRIP, reply_markup=_trips_keyboard(recent)
            )
    elif kind is ReportKind.DEBTORS:
        await _freeze(callback, f"{texts.BTN_REPORTS}: <b>{texts.BTN_REPORT_DEBTORS}</b>")
        await callback.message.answer(
            texts.REPORT_ASK_FORMAT,
            reply_markup=_format_keyboard(ReportAction.DEBTORS_FMT),
        )
    await callback.answer()


async def _ask_statement_format(
    message: Message,
    state: FSMContext,
    date_from: date | None,
    date_to: date | None,
) -> None:
    await state.update_data(
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
    )
    await state.set_state(ReportStates.statement_format)
    await message.answer(
        texts.REPORT_ASK_FORMAT,
        reply_markup=_format_keyboard(ReportAction.STATEMENT_FMT),
    )


@router.callback_query(
    ReportStates.statement_period, ReportCb.filter(F.action == ReportAction.PERIOD)
)
async def on_statement_period(
    callback: CallbackQuery, callback_data: ReportCb, state: FSMContext
) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    choice = PeriodChoice(callback_data.value)
    if choice is PeriodChoice.CUSTOM:
        await state.set_state(ReportStates.statement_dates)
        await _freeze(callback, f"{texts.REPORT_ASK_PERIOD} {texts.BTN_PERIOD_CUSTOM}")
        await callback.message.answer(texts.REPORT_ASK_DATES)
        await callback.answer()
        return

    now_date = today()
    if choice is PeriodChoice.ALL:
        date_from, date_to = None, None
        label = texts.BTN_PERIOD_ALL
    elif choice is PeriodChoice.THIS_MONTH:
        date_from, date_to = now_date.replace(day=1), now_date
        label = f"{texts.BTN_PERIOD_THIS_MONTH} ({fmt_date(date_from)} – {fmt_date(date_to)})"
    else:
        last_prev = now_date.replace(day=1) - timedelta(days=1)
        date_from, date_to = last_prev.replace(day=1), last_prev
        label = f"{texts.BTN_PERIOD_LAST_MONTH} ({fmt_date(date_from)} – {fmt_date(date_to)})"

    await _freeze(callback, f"{texts.REPORT_ASK_PERIOD} {label}")
    await _ask_statement_format(callback.message, state, date_from, date_to)
    await callback.answer()


@router.message(ReportStates.statement_dates, DialogText)
async def on_statement_dates(message: Message, state: FSMContext) -> None:
    parsed = _parse_date_range(message.text or "")
    if parsed is None:
        await message.answer(texts.REPORT_DATES_INVALID)
        return
    date_from, date_to = parsed
    await _ask_statement_format(message, state, date_from, date_to)


@router.callback_query(
    ReportStates.statement_format, ReportCb.filter(F.action == ReportAction.STATEMENT_FMT)
)
async def on_statement_format(
    callback: CallbackQuery,
    callback_data: ReportCb,
    state: FSMContext,
    session: AsyncSession,
    user: BotUser,
    bot: Bot,
) -> None:
    data = await state.get_data()
    await state.clear()
    await _freeze(callback)
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    client_id = data.get("client_id")
    if not client_id:
        await callback.answer(texts.CALLBACK_EXPIRED, show_alert=True)
        return

    date_from = date.fromisoformat(data["date_from"]) if data.get("date_from") else None
    date_to = date.fromisoformat(data["date_to"]) if data.get("date_to") else None
    fmt = FileFormat(callback_data.value)

    await bot.send_chat_action(callback.message.chat.id, ChatAction.UPLOAD_DOCUMENT)
    report = await statement_data(session, client_id, date_from, date_to)
    if report is None:
        await callback.message.answer(texts.CLIENT_NOT_FOUND, reply_markup=main_menu(user))
        await callback.answer()
        return

    if fmt is FileFormat.PDF:
        content = await asyncio.to_thread(build_statement_pdf, report, user.full_name)
    else:
        content = await asyncio.to_thread(build_statement_xlsx, report)

    filename = report_filename(texts.FILE_TITLE_STATEMENT, report.client_name, fmt.value)
    await callback.message.answer_document(
        BufferedInputFile(content, filename=filename),
        reply_markup=main_menu(user),
    )
    await callback.answer()


# --- Trip summary callbacks ---


@router.callback_query(ReportCb.filter(F.action == ReportAction.TRIP_PICK))
async def on_trip_pick(callback: CallbackQuery, callback_data: ReportCb) -> None:
    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.REPORT_ASK_FORMAT,
            reply_markup=_format_keyboard(ReportAction.TRIP_FMT, item_id=callback_data.item_id),
        )
    await callback.answer()


@router.callback_query(ReportCb.filter(F.action == ReportAction.TRIP_FMT))
async def on_trip_format(
    callback: CallbackQuery,
    callback_data: ReportCb,
    session: AsyncSession,
    user: BotUser,
    bot: Bot,
) -> None:
    await _freeze(callback)
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    fmt = FileFormat(callback_data.value)
    await bot.send_chat_action(callback.message.chat.id, ChatAction.UPLOAD_DOCUMENT)
    report = await trip_summary_data(session, callback_data.item_id)
    if report is None:
        await callback.message.answer(texts.TRIP_NOT_FOUND, reply_markup=main_menu(user))
        await callback.answer()
        return

    if fmt is FileFormat.PDF:
        content = await asyncio.to_thread(build_trip_summary_pdf, report, user.full_name)
    else:
        content = await asyncio.to_thread(build_trip_summary_xlsx, report)

    filename = report_filename(texts.FILE_TITLE_TRIP, str(report.number), fmt.value)
    await callback.message.answer_document(
        BufferedInputFile(content, filename=filename),
        reply_markup=main_menu(user),
    )
    await callback.answer()


# --- Debtors callbacks and /debts ---


@router.callback_query(ReportCb.filter(F.action == ReportAction.DEBTORS_FMT))
async def on_debtors_format(
    callback: CallbackQuery,
    callback_data: ReportCb,
    session: AsyncSession,
    user: BotUser,
    bot: Bot,
) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    fmt = FileFormat(callback_data.value)
    await bot.send_chat_action(callback.message.chat.id, ChatAction.UPLOAD_DOCUMENT)
    report = await debtors_data(session)

    if fmt is FileFormat.PDF:
        content = await asyncio.to_thread(build_debtors_pdf, report, user.full_name)
    else:
        content = await asyncio.to_thread(build_debtors_xlsx, report)

    filename = report_filename(texts.FILE_TITLE_DEBTORS, None, fmt.value)
    await callback.message.answer_document(
        BufferedInputFile(content, filename=filename),
        reply_markup=main_menu(user),
    )
    await callback.answer()


@router.message(Command("debts"))
@router.message(F.text == texts.BTN_DEBTS)
async def cmd_debts(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    report = await debtors_data(session)
    if not report.rows:
        await message.answer(texts.DEBTS_EMPTY)
        return

    shown = report.rows[:TOP_DEBTORS_LIMIT]
    lines = [texts.DEBTS_TITLE, ""]
    for row in shown:
        lines.append(
            texts.DEBTS_LINE.format(
                name=escape(row.client_name),
                balance=balance_value(row.balance_uzs),
            )
        )
    rest = len(report.rows) - len(shown)
    if rest > 0:
        lines.append(texts.DEBTS_MORE.format(n=rest, word=plural(rest, texts.CLIENT_FORMS)))
    lines.extend(["", texts.DEBTS_TOTAL.format(total=fmt_money(report.total_uzs))])
    await message.answer("\n".join(lines), reply_markup=_debts_excel_keyboard())


# --- /trips and "Рейсы" ---


@router.message(Command("trips"))
@router.message(F.text == texts.BTN_TRIPS)
async def cmd_trips(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    recent = await trips.list_recent_trips(session, RECENT_TRIPS_LIMIT)
    if not recent:
        await message.answer(texts.TRIPS_EMPTY)
        return

    lines = [texts.TRIPS_TITLE, ""]
    for item in recent:
        lines.append(
            texts.TRIP_LINE.format(
                number=item.number,
                date=fmt_date(item.departure_date),
                revenue=fmt_money(item.totals.revenue_uzs),
                profit=fmt_money(item.totals.profit_uzs),
            )
        )
    await message.answer("\n".join(lines), reply_markup=_trips_keyboard(recent))
