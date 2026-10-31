"""XLSX report builders (Phase 06)."""

from collections.abc import Sequence
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from sheepbot.config import get_settings
from sheepbot.reports.data import DebtorsData, StatementData, TripSummaryData

UZS_FORMAT = "# ##0"
INT_FORMAT = "# ##0"
KG_FORMAT = "# ##0.0"
MONEY_FORMAT = "# ##0.00"
RATE_FORMAT = "# ##0.0000"
PCT_FORMAT = "0.0"
DATE_FORMAT = "DD.MM.YYYY"

TITLE_FONT = Font(bold=True, size=13)
HEADER_FONT = Font(bold=True)
TOTAL_FONT = Font(bold=True)
HEADER_FILL = PatternFill("solid", fgColor="DDEBF7")
TOTAL_FILL = PatternFill("solid", fgColor="F2F2F2")

COL_HEADS = "Голов"
COL_NET_KG = "Нетто, кг"
COL_NOTE = "Примечание"
COL_AMOUNT_UZS = "Сумма, сум"


def _to_bytes(wb: Workbook) -> bytes:
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _set_widths(ws: Worksheet, widths: Sequence[int]) -> None:
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width


def _write_header_row(ws: Worksheet, row_idx: int, headers: Sequence[str]) -> None:
    for col_idx, text in enumerate(headers, start=1):
        cell = ws.cell(row_idx, col_idx, text)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _write_cell(
    ws: Worksheet, row_idx: int, col_idx: int, value: Any, num_format: str | None = None
) -> None:
    if value is None:
        return
    cell = ws.cell(row_idx, col_idx, value)
    if num_format:
        cell.number_format = num_format


def _sum_formula(col_idx: int, first_row: int, last_row: int) -> str | int:
    if last_row < first_row:
        return 0
    letter = get_column_letter(col_idx)
    return f"=SUM({letter}{first_row}:{letter}{last_row})"


def _style_total_row(
    ws: Worksheet,
    row_idx: int,
    col_count: int,
    label_col: int = 1,
    label: str = "Итого",
) -> None:
    ws.cell(row_idx, label_col, label)
    for col_idx in range(1, col_count + 1):
        cell = ws.cell(row_idx, col_idx)
        cell.font = TOTAL_FONT
        cell.fill = TOTAL_FILL


def _period_label(data: StatementData) -> str:
    if data.date_from and data.date_to:
        return f"{data.date_from:%d.%m.%Y} – {data.date_to:%d.%m.%Y}"
    if data.date_from:
        return f"с {data.date_from:%d.%m.%Y}"
    if data.date_to:
        return f"по {data.date_to:%d.%m.%Y}"
    return "Всё время"


def build_statement_xlsx(data: StatementData) -> bytes:
    """Build client statement workbook (.xlsx bytes)."""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Выписка"

    company = get_settings().company_name.strip()
    title = f"Выписка по клиенту: {data.client_name}"
    if company:
        title = f"{company} — {title}"

    ws.cell(1, 1, title).font = TITLE_FONT
    ws.cell(2, 1, "Период:").font = HEADER_FONT
    ws.cell(2, 2, _period_label(data))
    ws.cell(3, 1, "Начальный остаток (долг), сум:").font = HEADER_FONT
    _write_cell(ws, 3, 2, data.opening_balance, UZS_FORMAT)
    ws.cell(4, 1, "Конечный остаток (долг), сум:").font = HEADER_FONT
    _write_cell(ws, 4, 2, data.closing_balance, UZS_FORMAT)

    header_row = 6
    headers = (
        "Дата",
        "Операция",
        "Рейс",
        "День",
        "Товар",
        COL_HEADS,
        "Брутто, кг",
        "Скидка, кг",
        COL_NET_KG,
        "Цена, сум/кг",
        "Отгружено, сум",
        "Оплачено, сум",
        "Способ оплаты",
        COL_NOTE,
        "Баланс (долг), сум",
    )
    _write_header_row(ws, header_row, headers)
    ws.freeze_panes = f"A{header_row + 1}"

    first_data_row = header_row + 1
    for offset, line in enumerate(data.lines):
        r = first_data_row + offset
        _write_cell(ws, r, 1, line.date, DATE_FORMAT)
        _write_cell(ws, r, 2, line.type)
        _write_cell(ws, r, 3, line.trip_number, INT_FORMAT)
        _write_cell(ws, r, 4, line.day, INT_FORMAT)
        _write_cell(ws, r, 5, line.product)
        _write_cell(ws, r, 6, line.heads, INT_FORMAT)
        _write_cell(ws, r, 7, line.gross_kg, KG_FORMAT)
        _write_cell(ws, r, 8, line.discount_kg, KG_FORMAT)
        _write_cell(ws, r, 9, line.net_kg, KG_FORMAT)
        _write_cell(ws, r, 10, line.price_uzs_per_kg, UZS_FORMAT)
        _write_cell(ws, r, 11, line.shipped_uzs, UZS_FORMAT)
        _write_cell(ws, r, 12, line.paid_uzs, UZS_FORMAT)
        _write_cell(ws, r, 13, line.payment_method)
        _write_cell(ws, r, 14, line.note)
        _write_cell(ws, r, 15, line.running_balance, UZS_FORMAT)

    last_data_row = first_data_row + len(data.lines) - 1
    total_row = first_data_row + len(data.lines)
    _write_cell(ws, total_row, 6, _sum_formula(6, first_data_row, last_data_row), INT_FORMAT)
    _write_cell(ws, total_row, 7, _sum_formula(7, first_data_row, last_data_row), KG_FORMAT)
    _write_cell(ws, total_row, 8, _sum_formula(8, first_data_row, last_data_row), KG_FORMAT)
    _write_cell(ws, total_row, 9, _sum_formula(9, first_data_row, last_data_row), KG_FORMAT)
    _write_cell(ws, total_row, 11, _sum_formula(11, first_data_row, last_data_row), UZS_FORMAT)
    _write_cell(ws, total_row, 12, _sum_formula(12, first_data_row, last_data_row), UZS_FORMAT)
    _write_cell(ws, total_row, 15, data.closing_balance, UZS_FORMAT)
    _style_total_row(ws, total_row, len(headers))

    _set_widths(ws, (13, 13, 9, 8, 16, 10, 13, 13, 13, 15, 18, 18, 16, 26, 20))
    return _to_bytes(wb)


def _fill_trip_overview_sheet(ws: Worksheet, data: TripSummaryData) -> None:
    _write_header_row(ws, 1, ("Показатель", "Значение"))
    ws.freeze_panes = "A2"

    company = get_settings().company_name.strip()
    items: list[tuple[str, Any, str | None]] = []
    if company:
        items.append(("Компания", company, None))
    items.extend(
        [
            ("Номер рейса", data.number, INT_FORMAT),
            ("Дата отправки", data.departure_date, DATE_FORMAT),
            ("Дата прибытия", data.arrival_date, DATE_FORMAT),
            ("Курс KZT→UZS", data.rate_kzt, RATE_FORMAT),
            ("Курс USD→UZS", data.rate_usd, RATE_FORMAT),
            (COL_NOTE, data.note or "—", None),
            ("Выручка, сум", data.revenue_uzs, UZS_FORMAT),
            ("Закуп, сум", data.purchase_totals.amount_uzs, UZS_FORMAT),
            ("Расходы, сум", data.expenses_uzs, UZS_FORMAT),
            ("Себестоимость всего, сум", data.cost_uzs, UZS_FORMAT),
            ("Прибыль, сум", data.profit_uzs, UZS_FORMAT),
            ("Рентабельность, %", data.margin_pct, PCT_FORMAT),
        ]
    )
    for row_idx, (label, value, fmt) in enumerate(items, start=2):
        ws.cell(row_idx, 1, label).font = HEADER_FONT
        _write_cell(ws, row_idx, 2, value, fmt)

    _set_widths(ws, (28, 24))


def _fill_trip_economics_sheet(ws: Worksheet, data: TripSummaryData) -> None:
    headers = (
        "Тип",
        "Закуп, голов",
        "Закуп нетто, кг",
        "Продано, голов",
        "Продано нетто, кг",
        "Себестоимость, сум/кг",
        "Ср. цена продажи, сум/кг",
        "Разница, сум/кг",
    )
    _write_header_row(ws, 1, headers)
    ws.freeze_panes = "A2"

    first_row = 2
    for offset, row in enumerate(data.type_economics):
        r = first_row + offset
        _write_cell(ws, r, 1, row.type_label)
        _write_cell(ws, r, 2, row.purchased_heads, INT_FORMAT)
        _write_cell(ws, r, 3, row.purchased_net_kg, KG_FORMAT)
        _write_cell(ws, r, 4, row.sold_heads, INT_FORMAT)
        _write_cell(ws, r, 5, row.sold_net_kg, KG_FORMAT)
        _write_cell(ws, r, 6, row.cost_per_kg, UZS_FORMAT)
        _write_cell(ws, r, 7, row.avg_sale_price, UZS_FORMAT)
        _write_cell(ws, r, 8, row.diff_per_kg, UZS_FORMAT)

    last_row = first_row + len(data.type_economics) - 1
    total_row = first_row + len(data.type_economics)
    _write_cell(ws, total_row, 2, _sum_formula(2, first_row, last_row), INT_FORMAT)
    _write_cell(ws, total_row, 3, _sum_formula(3, first_row, last_row), KG_FORMAT)
    _write_cell(ws, total_row, 4, _sum_formula(4, first_row, last_row), INT_FORMAT)
    _write_cell(ws, total_row, 5, _sum_formula(5, first_row, last_row), KG_FORMAT)
    _style_total_row(ws, total_row, len(headers))
    _set_widths(ws, (14, 15, 17, 15, 18, 22, 24, 18))


def _fill_trip_purchases_sheet(ws: Worksheet, data: TripSummaryData) -> None:
    headers = (
        "Тип",
        COL_HEADS,
        "Брутто, кг",
        "Скидка, кг",
        COL_NET_KG,
        "Ср. цена, KZT/кг",
        "Сумма, KZT",
        COL_AMOUNT_UZS,
    )
    _write_header_row(ws, 1, headers)
    ws.freeze_panes = "A2"

    first_row = 2
    for offset, row in enumerate(data.purchases_by_type):
        r = first_row + offset
        _write_cell(ws, r, 1, row.type_label)
        _write_cell(ws, r, 2, row.heads, INT_FORMAT)
        _write_cell(ws, r, 3, row.gross_kg, KG_FORMAT)
        _write_cell(ws, r, 4, row.discount_kg, KG_FORMAT)
        _write_cell(ws, r, 5, row.net_kg, KG_FORMAT)
        _write_cell(ws, r, 6, row.avg_price_kzt, MONEY_FORMAT)
        _write_cell(ws, r, 7, row.amount_kzt, MONEY_FORMAT)
        _write_cell(ws, r, 8, row.amount_uzs, UZS_FORMAT)

    last_row = first_row + len(data.purchases_by_type) - 1
    total_row = first_row + len(data.purchases_by_type)
    _write_cell(ws, total_row, 2, _sum_formula(2, first_row, last_row), INT_FORMAT)
    _write_cell(ws, total_row, 3, _sum_formula(3, first_row, last_row), KG_FORMAT)
    _write_cell(ws, total_row, 4, _sum_formula(4, first_row, last_row), KG_FORMAT)
    _write_cell(ws, total_row, 5, _sum_formula(5, first_row, last_row), KG_FORMAT)
    _write_cell(ws, total_row, 6, data.purchase_totals.avg_price_kzt, MONEY_FORMAT)
    _write_cell(ws, total_row, 7, _sum_formula(7, first_row, last_row), MONEY_FORMAT)
    _write_cell(ws, total_row, 8, _sum_formula(8, first_row, last_row), UZS_FORMAT)
    _style_total_row(ws, total_row, len(headers))
    _set_widths(ws, (14, 10, 14, 14, 14, 18, 18, 20))


def _fill_trip_expenses_sheet(ws: Worksheet, data: TripSummaryData) -> None:
    headers = (
        "Статья",
        "Кол-во",
        "Цена за ед.",
        "Валюта",
        "Сумма в валюте",
        COL_AMOUNT_UZS,
        COL_NOTE,
    )
    _write_header_row(ws, 1, headers)
    ws.freeze_panes = "A2"

    first_row = 2
    for offset, row in enumerate(data.expenses):
        r = first_row + offset
        _write_cell(ws, r, 1, row.item)
        _write_cell(ws, r, 2, row.qty, MONEY_FORMAT)
        _write_cell(ws, r, 3, row.unit_price, MONEY_FORMAT)
        _write_cell(ws, r, 4, row.currency)
        _write_cell(ws, r, 5, row.amount, MONEY_FORMAT)
        _write_cell(ws, r, 6, row.amount_uzs, UZS_FORMAT)
        _write_cell(ws, r, 7, row.note)

    last_row = first_row + len(data.expenses) - 1
    total_row = first_row + len(data.expenses)
    _write_cell(ws, total_row, 6, _sum_formula(6, first_row, last_row), UZS_FORMAT)
    _style_total_row(ws, total_row, len(headers))
    _set_widths(ws, (20, 12, 16, 10, 18, 20, 28))


def _fill_trip_sales_day_sheet(ws: Worksheet, data: TripSummaryData) -> None:
    headers = ("День", "Дата", "Строк", COL_HEADS, COL_NET_KG, COL_AMOUNT_UZS)
    _write_header_row(ws, 1, headers)
    ws.freeze_panes = "A2"

    first_row = 2
    for offset, row in enumerate(data.sales_by_day):
        r = first_row + offset
        _write_cell(ws, r, 1, row.day, INT_FORMAT)
        _write_cell(ws, r, 2, row.date, DATE_FORMAT)
        _write_cell(ws, r, 3, row.lines, INT_FORMAT)
        _write_cell(ws, r, 4, row.heads, INT_FORMAT)
        _write_cell(ws, r, 5, row.net_kg, KG_FORMAT)
        _write_cell(ws, r, 6, row.amount_uzs, UZS_FORMAT)

    last_row = first_row + len(data.sales_by_day) - 1
    total_row = first_row + len(data.sales_by_day)
    _write_cell(ws, total_row, 3, _sum_formula(3, first_row, last_row), INT_FORMAT)
    _write_cell(ws, total_row, 4, _sum_formula(4, first_row, last_row), INT_FORMAT)
    _write_cell(ws, total_row, 5, _sum_formula(5, first_row, last_row), KG_FORMAT)
    _write_cell(ws, total_row, 6, _sum_formula(6, first_row, last_row), UZS_FORMAT)
    _style_total_row(ws, total_row, len(headers))
    _set_widths(ws, (10, 14, 10, 12, 15, 20))


def _fill_trip_sales_product_sheet(ws: Worksheet, data: TripSummaryData) -> None:
    headers = ("Код", "Товар", COL_HEADS, COL_NET_KG, "Ср. цена, сум/кг", COL_AMOUNT_UZS)
    _write_header_row(ws, 1, headers)
    ws.freeze_panes = "A2"

    first_row = 2
    for offset, row in enumerate(data.sales_by_product):
        r = first_row + offset
        _write_cell(ws, r, 1, row.product_code)
        _write_cell(ws, r, 2, row.product_name)
        _write_cell(ws, r, 3, row.heads, INT_FORMAT)
        _write_cell(ws, r, 4, row.net_kg, KG_FORMAT)
        _write_cell(ws, r, 5, row.avg_price_uzs, UZS_FORMAT)
        _write_cell(ws, r, 6, row.amount_uzs, UZS_FORMAT)

    last_row = first_row + len(data.sales_by_product) - 1
    total_row = first_row + len(data.sales_by_product)
    _write_cell(ws, total_row, 3, _sum_formula(3, first_row, last_row), INT_FORMAT)
    _write_cell(ws, total_row, 4, _sum_formula(4, first_row, last_row), KG_FORMAT)
    _write_cell(ws, total_row, 6, _sum_formula(6, first_row, last_row), UZS_FORMAT)
    _style_total_row(ws, total_row, len(headers))
    _set_widths(ws, (18, 16, 12, 15, 18, 20))


def _fill_trip_sales_client_sheet(ws: Worksheet, data: TripSummaryData) -> None:
    headers = ("Клиент", COL_HEADS, COL_NET_KG, COL_AMOUNT_UZS)
    _write_header_row(ws, 1, headers)
    ws.freeze_panes = "A2"

    first_row = 2
    for offset, row in enumerate(data.sales_by_client):
        r = first_row + offset
        _write_cell(ws, r, 1, row.client_name)
        _write_cell(ws, r, 2, row.heads, INT_FORMAT)
        _write_cell(ws, r, 3, row.net_kg, KG_FORMAT)
        _write_cell(ws, r, 4, row.amount_uzs, UZS_FORMAT)

    last_row = first_row + len(data.sales_by_client) - 1
    total_row = first_row + len(data.sales_by_client)
    _write_cell(ws, total_row, 2, _sum_formula(2, first_row, last_row), INT_FORMAT)
    _write_cell(ws, total_row, 3, _sum_formula(3, first_row, last_row), KG_FORMAT)
    _write_cell(ws, total_row, 4, _sum_formula(4, first_row, last_row), UZS_FORMAT)
    _style_total_row(ws, total_row, len(headers))
    _set_widths(ws, (28, 12, 15, 20))


def build_trip_summary_xlsx(data: TripSummaryData) -> bytes:
    """Build trip summary workbook (.xlsx bytes) with one sheet per section."""
    wb = Workbook()
    overview = wb.active
    assert overview is not None
    overview.title = "Сводка"
    _fill_trip_overview_sheet(overview, data)
    _fill_trip_economics_sheet(wb.create_sheet("Себестоимость"), data)
    _fill_trip_purchases_sheet(wb.create_sheet("Закуп"), data)
    _fill_trip_expenses_sheet(wb.create_sheet("Расходы"), data)
    _fill_trip_sales_day_sheet(wb.create_sheet("Продажи по дням"), data)
    _fill_trip_sales_product_sheet(wb.create_sheet("Продажи по товарам"), data)
    _fill_trip_sales_client_sheet(wb.create_sheet("Продажи по клиентам"), data)
    wb.active = 0
    return _to_bytes(wb)


def build_debtors_xlsx(data: DebtorsData) -> bytes:
    """Build debtors report workbook (.xlsx bytes)."""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Должники"

    headers = (
        "№",
        "Клиент",
        "Отгружено, сум",
        "Оплачено, сум",
        "Баланс (долг), сум",
        "Последняя продажа",
        "Последняя оплата",
    )
    _write_header_row(ws, 1, headers)
    ws.freeze_panes = "A2"

    first_row = 2
    for offset, row in enumerate(data.rows):
        r = first_row + offset
        _write_cell(ws, r, 1, offset + 1, INT_FORMAT)
        _write_cell(ws, r, 2, row.client_name)
        _write_cell(ws, r, 3, row.shipped_uzs, UZS_FORMAT)
        _write_cell(ws, r, 4, row.paid_uzs, UZS_FORMAT)
        _write_cell(ws, r, 5, row.balance_uzs, UZS_FORMAT)
        _write_cell(ws, r, 6, row.last_sale_date, DATE_FORMAT)
        _write_cell(ws, r, 7, row.last_payment_date, DATE_FORMAT)

    last_row = first_row + len(data.rows) - 1
    total_row = first_row + len(data.rows)
    _write_cell(ws, total_row, 3, _sum_formula(3, first_row, last_row), UZS_FORMAT)
    _write_cell(ws, total_row, 4, _sum_formula(4, first_row, last_row), UZS_FORMAT)
    _write_cell(ws, total_row, 5, _sum_formula(5, first_row, last_row), UZS_FORMAT)
    _style_total_row(ws, total_row, len(headers), label_col=2)

    _set_widths(ws, (6, 28, 20, 20, 20, 18, 18))
    return _to_bytes(wb)
