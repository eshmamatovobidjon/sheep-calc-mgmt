from datetime import date
from typing import Annotated
from urllib.parse import quote

from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile
from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.api import texts
from sheepbot.api.auth import CurrentUser, ViewUser
from sheepbot.api.deps import Session
from sheepbot.api.schemas import DebtorOut, DebtorsOut, ReportSentOut
from sheepbot.api.telegram import get_bot
from sheepbot.db.models import BotUser
from sheepbot.reports import files
from sheepbot.reports.data import debtors_data
from sheepbot.reports.files import ReportFile, ReportFormat
from sheepbot.services import trips

router = APIRouter()

Format = Annotated[ReportFormat, Query(alias="format")]


@router.get("/debtors")
async def get_debtors(_: CurrentUser, session: Session) -> DebtorsOut:
    data = await debtors_data(session)
    debt = sum(r.balance_uzs for r in data.rows if r.balance_uzs > 0)
    credit = -sum(r.balance_uzs for r in data.rows if r.balance_uzs < 0)
    return DebtorsOut(
        rows=[
            DebtorOut(
                client_id=r.client_id,
                name=r.client_name,
                balance=str(r.balance_uzs),
                last_sale_date=r.last_sale_date,
                last_payment_date=r.last_payment_date,
            )
            for r in data.rows
        ],
        total_debt=str(debt),
        total_credit=str(credit),
        net=str(data.total_uzs),
    )


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail)


async def _statement(
    session: AsyncSession,
    user: BotUser,
    client_id: int,
    date_from: date | None,
    date_to: date | None,
    fmt: ReportFormat,
) -> ReportFile:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, texts.DATE_RANGE)
    report = await files.statement_file(session, client_id, date_from, date_to, fmt, user.full_name)
    if report is None:
        raise _not_found(texts.CLIENT_NOT_FOUND)
    return report


async def _trip(session: AsyncSession, user: BotUser, number: int, fmt: ReportFormat) -> ReportFile:
    trip_id = await trips.trip_id_by_number(session, number)
    report = (
        await files.trip_file(session, trip_id, fmt, user.full_name)
        if trip_id is not None
        else None
    )
    if report is None:
        raise _not_found(texts.TRIP_NOT_FOUND)
    return report


def _download(report: ReportFile) -> Response:
    # RFC 5987 name for Cyrillic file names, plus an ASCII fallback.
    ascii_name = f"report.{report.filename.rsplit('.', 1)[-1]}"
    disposition = (
        f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(report.filename)}"
    )
    return Response(
        report.content,
        media_type=report.media_type,
        headers={"Content-Disposition": disposition, "Cache-Control": "no-store"},
    )


async def _send_to_user(user: BotUser, report: ReportFile) -> ReportSentOut:
    """The recipient is always the authenticated user's own chat."""
    try:
        await get_bot().send_document(
            user.telegram_id, BufferedInputFile(report.content, filename=report.filename)
        )
    except TelegramAPIError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, texts.SEND_FAILED) from None
    return ReportSentOut(filename=report.filename)


@router.get("/reports/statement")
async def statement_download(
    user: ViewUser,
    session: Session,
    client_id: int,
    fmt: Format = ReportFormat.PDF,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Response:
    return _download(await _statement(session, user, client_id, date_from, date_to, fmt))


@router.post("/reports/statement/send")
async def statement_send(
    user: ViewUser,
    session: Session,
    client_id: int,
    fmt: Format = ReportFormat.PDF,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ReportSentOut:
    return await _send_to_user(
        user, await _statement(session, user, client_id, date_from, date_to, fmt)
    )


@router.get("/reports/trip")
async def trip_download(
    user: ViewUser, session: Session, number: int, fmt: Format = ReportFormat.PDF
) -> Response:
    return _download(await _trip(session, user, number, fmt))


@router.post("/reports/trip/send")
async def trip_send(
    user: ViewUser, session: Session, number: int, fmt: Format = ReportFormat.PDF
) -> ReportSentOut:
    return await _send_to_user(user, await _trip(session, user, number, fmt))


@router.get("/reports/debtors")
async def debtors_download(
    user: ViewUser, session: Session, fmt: Format = ReportFormat.PDF
) -> Response:
    return _download(await files.debtors_file(session, fmt, user.full_name))


@router.post("/reports/debtors/send")
async def debtors_send(
    user: ViewUser, session: Session, fmt: Format = ReportFormat.PDF
) -> ReportSentOut:
    return await _send_to_user(user, await files.debtors_file(session, fmt, user.full_name))
