"""Report files (PDF/XLSX) built from report data; used by the API."""

import asyncio
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.reports import pdf_builder, xlsx_builder
from sheepbot.reports.data import debtors_data, report_filename, statement_data, trip_summary_data

TITLE_STATEMENT = "Выписка"
TITLE_TRIP = "Рейс"
TITLE_DEBTORS = "Должники"

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ReportFormat(StrEnum):
    PDF = "pdf"
    XLSX = "xlsx"


@dataclass(frozen=True, slots=True)
class ReportFile:
    filename: str
    content: bytes

    @property
    def media_type(self) -> str:
        return MEDIA_TYPES[self.filename.rsplit(".", 1)[-1]]


async def statement_file(
    session: AsyncSession,
    client_id: int,
    date_from: date | None,
    date_to: date | None,
    fmt: ReportFormat,
    generated_by: str,
) -> ReportFile | None:
    data = await statement_data(session, client_id, date_from, date_to)
    if data is None:
        return None
    if fmt is ReportFormat.PDF:
        content = await asyncio.to_thread(pdf_builder.build_statement_pdf, data, generated_by)
    else:
        content = await asyncio.to_thread(xlsx_builder.build_statement_xlsx, data)
    return ReportFile(report_filename(TITLE_STATEMENT, data.client_name, fmt.value), content)


async def trip_file(
    session: AsyncSession, trip_id: int, fmt: ReportFormat, generated_by: str
) -> ReportFile | None:
    data = await trip_summary_data(session, trip_id)
    if data is None:
        return None
    if fmt is ReportFormat.PDF:
        content = await asyncio.to_thread(pdf_builder.build_trip_summary_pdf, data, generated_by)
    else:
        content = await asyncio.to_thread(xlsx_builder.build_trip_summary_xlsx, data)
    return ReportFile(report_filename(TITLE_TRIP, str(data.number), fmt.value), content)


async def debtors_file(session: AsyncSession, fmt: ReportFormat, generated_by: str) -> ReportFile:
    data = await debtors_data(session)
    if fmt is ReportFormat.PDF:
        content = await asyncio.to_thread(pdf_builder.build_debtors_pdf, data, generated_by)
    else:
        content = await asyncio.to_thread(xlsx_builder.build_debtors_xlsx, data)
    return ReportFile(report_filename(TITLE_DEBTORS, None, fmt.value), content)
