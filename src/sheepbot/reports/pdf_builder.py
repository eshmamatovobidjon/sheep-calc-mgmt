"""PDF report builders (Phase 06)."""

from collections.abc import Sequence
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from sheepbot.config import get_settings
from sheepbot.domain.formatting import fmt_date, fmt_datetime, fmt_kg, fmt_money, fmt_percent
from sheepbot.reports.data import DebtorsData, StatementData, StatementLine, TripSummaryData

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"

HEADER_BG = colors.HexColor("#DDEBF7")
TOTAL_BG = colors.HexColor("#F2F2F2")
GRID_COLOR = colors.HexColor("#BFBFBF")

LABEL_TOTAL = "Итого"
COL_HEADS = "Голов"
COL_NET_KG = "Нетто, кг"
COL_AMOUNT_UZS = "Сумма, сум"
DASH = "—"


@cache
def register_fonts() -> None:
    """Register bundled DejaVu Sans fonts in ReportLab once."""
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(FONTS_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONTS_DIR / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily(
        FONT_REGULAR,
        normal=FONT_REGULAR,
        bold=FONT_BOLD,
        italic=FONT_REGULAR,
        boldItalic=FONT_BOLD,
    )


def _styles() -> dict[str, ParagraphStyle]:
    register_fonts()
    return {
        "company": ParagraphStyle(
            "Company",
            fontName=FONT_BOLD,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#444444"),
            spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "Title",
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName=FONT_REGULAR,
            fontSize=9.5,
            leading=13,
            spaceAfter=6,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName=FONT_BOLD,
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "cell": ParagraphStyle(
            "Cell",
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=10,
        ),
        "cell_bold": ParagraphStyle(
            "CellBold",
            fontName=FONT_BOLD,
            fontSize=8,
            leading=10,
        ),
    }


def _fmt_dec_money(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if quantized < 0 else ""
    whole, frac = f"{abs(quantized):.2f}".split(".")
    grouped = f"{int(whole):,}".replace(",", " ")
    return f"{sign}{grouped},{frac}"


def _fmt_rate(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    text = f"{quantized:f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


class _NumberedCanvas(canvas.Canvas):
    """Two-pass canvas that renders footer with generation time, user and 'Стр. N из M'."""

    def __init__(self, *args: Any, footer_left: str = "", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []
        self._footer_left = footer_left

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(total_pages)
            super().showPage()
        super().save()

    def _draw_footer(self, total_pages: int) -> None:
        self.saveState()
        self.setFont(FONT_REGULAR, 8)
        self.setFillColor(colors.HexColor("#555555"))
        width, _ = self._pagesize
        y = 8 * mm
        self.drawString(12 * mm, y, self._footer_left)
        self.drawRightString(width - 12 * mm, y, f"Стр. {self._pageNumber} из {total_pages}")
        self.restoreState()


def _footer_text(generated_by: str) -> str:
    stamp = fmt_datetime(datetime.now())
    user = generated_by.strip()
    if user:
        return f"Сформировано: {stamp}, {user}"
    return f"Сформировано: {stamp}"


def _build_pdf(
    story: list[Any],
    *,
    pagesize: tuple[float, float],
    generated_by: str,
) -> bytes:
    register_fonts()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=16 * mm,
    )
    footer_left = _footer_text(generated_by)
    doc.build(
        story,
        canvasmaker=lambda *args, **kwargs: _NumberedCanvas(
            *args, footer_left=footer_left, **kwargs
        ),
    )
    return buffer.getvalue()


def _header_block(
    styles: dict[str, ParagraphStyle], title: str, subtitle_lines: Sequence[str]
) -> list[Any]:
    flow: list[Any] = []
    company = get_settings().company_name.strip()
    if company:
        flow.append(Paragraph(escape(company), styles["company"]))
    flow.append(Paragraph(escape(title), styles["title"]))
    if subtitle_lines:
        joined = "<br/>".join(subtitle_lines)
        flow.append(Paragraph(joined, styles["subtitle"]))
    return flow


def _make_table(
    rows: list[list[Any]],
    col_widths: Sequence[float],
    right_cols: Sequence[int] = (),
    center_cols: Sequence[int] = (),
    has_total_row: bool = True,
    font_size: float = 8,
) -> Table:
    cmds: list[tuple[Any, ...]] = [
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2.5),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for col in right_cols:
        cmds.append(("ALIGN", (col, 1), (col, -1), "RIGHT"))
    for col in center_cols:
        cmds.append(("ALIGN", (col, 1), (col, -1), "CENTER"))
    if has_total_row and len(rows) > 1:
        cmds.append(("FONTNAME", (0, -1), (-1, -1), FONT_BOLD))
        cmds.append(("BACKGROUND", (0, -1), (-1, -1), TOTAL_BG))

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(cmds))
    return table


def _period_text(data: StatementData) -> str:
    if data.date_from and data.date_to:
        return f"{fmt_date(data.date_from)} – {fmt_date(data.date_to)}"
    if data.date_from:
        return f"с {fmt_date(data.date_from)}"
    if data.date_to:
        return f"по {fmt_date(data.date_to)}"
    return "Всё время"


def _opt_int(value: int | None) -> str:
    return str(value) if value is not None else DASH


def _opt_kg(value: Decimal | None) -> str:
    return fmt_kg(value) if value is not None else DASH


def _opt_money(value: int | None) -> str:
    return fmt_money(value) if value is not None else DASH


def _statement_line_cells(line: StatementLine, cell_style: ParagraphStyle) -> list[Any]:
    trip_day = f"№{line.trip_number} / д.{line.day}" if line.trip_number else DASH
    return [
        fmt_date(line.date),
        line.type,
        trip_day,
        Paragraph(escape(line.product or DASH), cell_style),
        _opt_int(line.heads),
        _opt_kg(line.gross_kg),
        _opt_kg(line.discount_kg),
        _opt_kg(line.net_kg),
        _opt_money(line.price_uzs_per_kg),
        _opt_money(line.shipped_uzs),
        _opt_money(line.paid_uzs),
        line.payment_method or DASH,
        Paragraph(escape(line.note or DASH), cell_style),
        fmt_money(line.running_balance),
    ]


def build_statement_pdf(data: StatementData, generated_by: str = "") -> bytes:
    """Build client statement PDF bytes."""
    styles = _styles()
    subtitles = [
        f"<b>Период:</b> {escape(_period_text(data))}",
        (
            f"<b>Начальный остаток (долг):</b> {fmt_money(data.opening_balance)} сум "
            f"&nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Отгружено:</b> {fmt_money(data.shipped_uzs)} сум &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Оплачено:</b> {fmt_money(data.paid_uzs)} сум &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Конечный остаток (долг):</b> {fmt_money(data.closing_balance)} сум"
        ),
    ]
    story = _header_block(styles, f"Выписка по клиенту: {data.client_name}", subtitles)

    headers = [
        "Дата",
        "Опер.",
        "Рейс/День",
        "Товар",
        "Гол.",
        "Брутто",
        "Скидка",
        "Нетто",
        "Цена/кг",
        "Отгружено",
        "Оплачено",
        "Способ",
        "Примечание",
        "Баланс",
    ]
    rows: list[list[Any]] = [
        headers,
        *(_statement_line_cells(line, styles["cell"]) for line in data.lines),
        [
            LABEL_TOTAL,
            "",
            "",
            "",
            str(data.total_heads) if data.total_heads else DASH,
            fmt_kg(data.total_gross_kg) if data.total_gross_kg else DASH,
            fmt_kg(data.total_discount_kg) if data.total_discount_kg else DASH,
            fmt_kg(data.total_net_kg) if data.total_net_kg else DASH,
            "",
            fmt_money(data.shipped_uzs),
            fmt_money(data.paid_uzs),
            "",
            "",
            fmt_money(data.closing_balance),
        ],
    ]

    widths = [
        18 * mm,
        15 * mm,
        18 * mm,
        19 * mm,
        11 * mm,
        16 * mm,
        15 * mm,
        16 * mm,
        18 * mm,
        24 * mm,
        24 * mm,
        16 * mm,
        35 * mm,
        28 * mm,
    ]
    story.append(
        _make_table(
            rows,
            col_widths=widths,
            right_cols=(4, 5, 6, 7, 8, 9, 10, 13),
            center_cols=(0, 1, 2, 11),
            has_total_row=True,
            font_size=7.5,
        )
    )
    return _build_pdf(story, pagesize=landscape(A4), generated_by=generated_by)


def _trip_purchases_table(data: TripSummaryData) -> Table:
    p_rows: list[list[Any]] = [
        [
            "Тип",
            COL_HEADS,
            "Брутто, кг",
            "Скидка, кг",
            COL_NET_KG,
            "Ср. цена, KZT/кг",
            "Сумма, KZT",
            COL_AMOUNT_UZS,
        ]
    ]
    for p in (*data.purchases_by_type, data.purchase_totals):
        p_rows.append(
            [
                p.type_label,
                str(p.heads),
                fmt_kg(p.gross_kg),
                fmt_kg(p.discount_kg),
                fmt_kg(p.net_kg),
                _fmt_dec_money(p.avg_price_kzt),
                _fmt_dec_money(p.amount_kzt),
                fmt_money(p.amount_uzs),
            ]
        )
    return _make_table(
        p_rows,
        col_widths=[28 * mm, 20 * mm, 26 * mm, 26 * mm, 26 * mm, 32 * mm, 36 * mm, 42 * mm],
        right_cols=(1, 2, 3, 4, 5, 6, 7),
    )


def _trip_economics_table(data: TripSummaryData) -> Table:
    ec_rows: list[list[Any]] = [
        [
            "Тип",
            "Закуп, гол.",
            "Закуп нетто, кг",
            "Продано, гол.",
            "Продано нетто, кг",
            "Себестоимость, сум/кг",
            "Ср. цена продажи, сум/кг",
            "Разница, сум/кг",
        ]
    ]
    for ec in data.type_economics:
        ec_rows.append(
            [
                ec.type_label,
                str(ec.purchased_heads),
                fmt_kg(ec.purchased_net_kg),
                str(ec.sold_heads),
                fmt_kg(ec.sold_net_kg),
                _opt_money(ec.cost_per_kg),
                _opt_money(ec.avg_sale_price),
                _opt_money(ec.diff_per_kg),
            ]
        )
    return _make_table(
        ec_rows,
        col_widths=[28 * mm, 22 * mm, 28 * mm, 24 * mm, 28 * mm, 36 * mm, 38 * mm, 32 * mm],
        right_cols=(1, 2, 3, 4, 5, 6, 7),
        has_total_row=False,
    )


def _trip_expenses_table(data: TripSummaryData, cell_style: ParagraphStyle) -> Table:
    e_rows: list[list[Any]] = [
        [
            "Статья",
            "Кол-во",
            "Цена за ед.",
            "Валюта",
            "Сумма в валюте",
            COL_AMOUNT_UZS,
            "Примечание",
        ]
    ]
    for e in data.expenses:
        e_rows.append(
            [
                Paragraph(escape(e.item), cell_style),
                _fmt_dec_money(e.qty),
                _fmt_dec_money(e.unit_price),
                e.currency,
                _fmt_dec_money(e.amount),
                fmt_money(e.amount_uzs),
                Paragraph(escape(e.note or DASH), cell_style),
            ]
        )
    e_rows.append([LABEL_TOTAL, "", "", "", "", fmt_money(data.expenses_uzs), ""])
    return _make_table(
        e_rows,
        col_widths=[42 * mm, 22 * mm, 28 * mm, 18 * mm, 32 * mm, 38 * mm, 56 * mm],
        right_cols=(1, 2, 4, 5),
        center_cols=(3,),
    )


def _trip_sales_tables(data: TripSummaryData, styles: dict[str, ParagraphStyle]) -> list[Any]:
    flow: list[Any] = []

    flow.append(Paragraph("Продажи по дням", styles["section"]))
    d_rows: list[list[Any]] = [["День", "Дата", "Строк", COL_HEADS, COL_NET_KG, COL_AMOUNT_UZS]]
    for d in data.sales_by_day:
        d_rows.append(
            [
                str(d.day),
                fmt_date(d.date) if d.date else DASH,
                str(d.lines),
                str(d.heads),
                fmt_kg(d.net_kg),
                fmt_money(d.amount_uzs),
            ]
        )
    d_rows.append(
        [
            LABEL_TOTAL,
            "",
            str(data.totals.sales.lines),
            str(data.totals.sales.heads),
            fmt_kg(data.totals.sales.net_kg),
            fmt_money(data.revenue_uzs),
        ]
    )
    flow.append(
        _make_table(
            d_rows,
            col_widths=[22 * mm, 28 * mm, 22 * mm, 24 * mm, 32 * mm, 44 * mm],
            right_cols=(2, 3, 4, 5),
            center_cols=(0, 1),
        )
    )

    flow.append(Paragraph("Продажи по товарам", styles["section"]))
    pr_rows: list[list[Any]] = [
        ["Код", "Товар", COL_HEADS, COL_NET_KG, "Ср. цена, сум/кг", COL_AMOUNT_UZS]
    ]
    for pr in data.sales_by_product:
        pr_rows.append(
            [
                pr.product_code,
                pr.product_name,
                str(pr.heads) if pr.heads else DASH,
                fmt_kg(pr.net_kg),
                fmt_money(pr.avg_price_uzs),
                fmt_money(pr.amount_uzs),
            ]
        )
    pr_rows.append(
        [
            LABEL_TOTAL,
            "",
            str(data.totals.sales.heads),
            fmt_kg(data.totals.sales.net_kg),
            "",
            fmt_money(data.revenue_uzs),
        ]
    )
    flow.append(
        _make_table(
            pr_rows,
            col_widths=[34 * mm, 32 * mm, 22 * mm, 30 * mm, 34 * mm, 44 * mm],
            right_cols=(2, 3, 4, 5),
        )
    )

    flow.append(Paragraph("Продажи по клиентам", styles["section"]))
    cl_rows: list[list[Any]] = [["Клиент", COL_HEADS, COL_NET_KG, COL_AMOUNT_UZS]]
    for cl in data.sales_by_client:
        cl_rows.append(
            [
                Paragraph(escape(cl.client_name), styles["cell"]),
                str(cl.heads) if cl.heads else DASH,
                fmt_kg(cl.net_kg),
                fmt_money(cl.amount_uzs),
            ]
        )
    cl_rows.append(
        [
            LABEL_TOTAL,
            str(data.totals.sales.heads),
            fmt_kg(data.totals.sales.net_kg),
            fmt_money(data.revenue_uzs),
        ]
    )
    flow.append(
        _make_table(
            cl_rows,
            col_widths=[76 * mm, 24 * mm, 32 * mm, 44 * mm],
            right_cols=(1, 2, 3),
        )
    )
    return flow


def build_trip_summary_pdf(data: TripSummaryData, generated_by: str = "") -> bytes:
    """Build trip summary PDF bytes."""
    styles = _styles()
    arrival_str = fmt_date(data.arrival_date) if data.arrival_date else DASH
    margin_str = f"{fmt_percent(data.margin_pct)}%" if data.margin_pct is not None else DASH
    subtitles = [
        (
            f"<b>Отправка:</b> {fmt_date(data.departure_date)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Прибытие:</b> {arrival_str} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Курс KZT→UZS:</b> {_fmt_rate(data.rate_kzt)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Курс USD→UZS:</b> {_fmt_rate(data.rate_usd)}"
        ),
        (
            f"<b>Выручка:</b> {fmt_money(data.revenue_uzs)} сум &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Себестоимость:</b> {fmt_money(data.cost_uzs)} сум "
            f"(закуп {fmt_money(data.purchase_totals.amount_uzs)}, "
            f"расходы {fmt_money(data.expenses_uzs)}) "
            f"&nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Прибыль:</b> {fmt_money(data.profit_uzs)} сум ({margin_str})"
        ),
    ]
    if data.note:
        subtitles.append(f"<b>Примечание:</b> {escape(data.note)}")

    story = _header_block(styles, f"Итоги рейса №{data.number}", subtitles)
    story.extend(
        [
            Paragraph("Закуп по видам", styles["section"]),
            _trip_purchases_table(data),
            Paragraph("Себестоимость и средняя цена продажи (за 1 кг нетто)", styles["section"]),
            _trip_economics_table(data),
            Paragraph("Расходы", styles["section"]),
            _trip_expenses_table(data, styles["cell"]),
            *_trip_sales_tables(data, styles),
            Spacer(1, 4 * mm),
        ]
    )
    return _build_pdf(story, pagesize=landscape(A4), generated_by=generated_by)


def build_debtors_pdf(data: DebtorsData, generated_by: str = "") -> bytes:
    """Build debtors report PDF bytes."""
    styles = _styles()
    subtitles = [
        (
            f"<b>Дата:</b> {fmt_date(data.as_of)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Клиентов:</b> {len(data.rows)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Итого баланс (долг):</b> {fmt_money(data.total_uzs)} сум"
        )
    ]
    story = _header_block(styles, "Должники", subtitles)

    headers = [
        "№",
        "Клиент",
        "Отгружено, сум",
        "Оплачено, сум",
        "Баланс (долг), сум",
        "Посл. продажа",
        "Посл. оплата",
    ]
    rows: list[list[Any]] = [headers]
    for idx, row in enumerate(data.rows, start=1):
        rows.append(
            [
                str(idx),
                Paragraph(escape(row.client_name), styles["cell"]),
                fmt_money(row.shipped_uzs),
                fmt_money(row.paid_uzs),
                fmt_money(row.balance_uzs),
                fmt_date(row.last_sale_date) if row.last_sale_date else DASH,
                fmt_date(row.last_payment_date) if row.last_payment_date else DASH,
            ]
        )
    rows.append(
        [
            "",
            LABEL_TOTAL,
            fmt_money(data.total_shipped_uzs),
            fmt_money(data.total_paid_uzs),
            fmt_money(data.total_uzs),
            "",
            "",
        ]
    )

    widths = [12 * mm, 52 * mm, 32 * mm, 32 * mm, 34 * mm, 24 * mm, 24 * mm]
    story.append(
        _make_table(
            rows,
            col_widths=widths,
            right_cols=(0, 2, 3, 4),
            center_cols=(5, 6),
            has_total_row=True,
        )
    )
    return _build_pdf(story, pagesize=landscape(A4), generated_by=generated_by)
