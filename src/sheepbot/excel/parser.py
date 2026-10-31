"""Trip .xlsx -> ParsedTrip or a list of errors. No DB access; driven by template_spec."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook

from sheepbot.domain.catalog import PRODUCT_CATALOG
from sheepbot.domain.enums import ANIMAL_TYPE_LABELS, CURRENCY_LABELS, AnimalType, Currency
from sheepbot.domain.formatting import parse_date
from sheepbot.excel.template_spec import (
    EXPENSES_SHEET,
    FIRST_DATA_ROW,
    PURCHASES_SHEET,
    SALES_SHEET,
    TRIP_SHEET,
    ColumnKind,
    ColumnSpec,
    SheetSpec,
    normalize_header,
)

MAX_ERRORS = 50
MAX_ROWS = 5000

MSG_BAD_FILE = "Не удалось прочитать файл. Нужен Excel-файл .xlsx (заполненный шаблон)."
MSG_SHEET_MISSING = "лист не найден"
MSG_HEADER = "ожидается заголовок «{expected}», найдено «{found}»"
MSG_FIELD = "ожидается поле «{expected}», найдено «{found}»"
MSG_REQUIRED = "не заполнено"
MSG_INT = "ожидается целое число"
MSG_NUMBER = "ожидается число"
MSG_DATE = "ожидается дата в формате ДД.ММ.ГГГГ"
MSG_CHOICE = "недопустимое значение «{value}»; допустимо: {choices}"
MSG_GT = "должно быть больше {limit}"
MSG_GE = "должно быть не меньше {limit}"
MSG_NO_ROWS = "нет данных — заполните хотя бы одну строку"
MSG_TOO_MANY_ROWS = "слишком много строк (максимум {limit})"
MSG_HEADS_REQUIRED = "не заполнено (обязательно для туши {product})"

PRODUCTS = {p.code: p for p in PRODUCT_CATALOG}
ANIMAL_BY_LABEL = {label: animal for animal, label in ANIMAL_TYPE_LABELS.items()}
CURRENCY_BY_LABEL = {label: currency for currency, label in CURRENCY_LABELS.items()}


@dataclass(frozen=True, slots=True)
class ParseError:
    sheet: str | None
    row: int | None
    column: str | None
    message: str

    def __str__(self) -> str:
        parts = []
        if self.sheet:
            parts.append(f"Лист «{self.sheet}»")
        if self.row:
            parts.append(f"строка {self.row}")
        if self.column:
            parts.append(f"«{self.column}»")
        prefix = ", ".join(parts)
        return f"{prefix}: {self.message}" if prefix else self.message


@dataclass(frozen=True, slots=True)
class PurchaseRow:
    row_no: int
    date: date
    animal_type: AnimalType
    heads: int
    gross_kg: Decimal
    discount_kg: Decimal
    price_kzt: Decimal
    note: str | None


@dataclass(frozen=True, slots=True)
class ExpenseRow:
    row_no: int
    item: str
    qty: Decimal | None
    unit_price: Decimal
    currency: Currency
    note: str | None


@dataclass(frozen=True, slots=True)
class SaleRow:
    row_no: int
    day: int
    date: date
    client: str
    product_code: str
    heads: int | None
    gross_kg: Decimal
    price_thousand_uzs: Decimal
    note: str | None


@dataclass(frozen=True, slots=True)
class ParsedTrip:
    number: int
    departure_date: date
    arrival_date: date | None
    rate_kzt: Decimal
    rate_usd: Decimal
    note: str | None
    purchases: list[PurchaseRow]
    expenses: list[ExpenseRow]
    sales: list[SaleRow]


@dataclass(slots=True)
class ParseResult:
    trip: ParsedTrip | None
    errors: list[ParseError] = field(default_factory=list)
    too_many_errors: bool = False


class _TooManyErrors(Exception):
    pass


class _Errors:
    def __init__(self) -> None:
        self.items: list[ParseError] = []
        self.truncated = False

    def add(self, sheet: str | None, row: int | None, column: str | None, message: str) -> None:
        if len(self.items) >= MAX_ERRORS:
            self.truncated = True
            raise _TooManyErrors
        self.items.append(ParseError(sheet, row, column, message))


# --- cell conversion ---


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int | float):
        result = Decimal(str(value))
    elif isinstance(value, str):
        try:
            result = Decimal("".join(value.split()).replace(",", "."))
        except InvalidOperation:
            return None
    else:
        return None
    return result if result.is_finite() else None


def _to_int(value: Any) -> int | None:
    number = _to_decimal(value)
    if number is None or number != number.to_integral_value():
        return None
    return int(number)


def _to_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return parse_date(value)
    return None


def _to_text(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).split())


def _choice_key(text: str) -> str:
    return " ".join(text.split()).casefold().replace("ё", "е")


def _match_choice(column: ColumnSpec, value: Any) -> str | None:
    key = _choice_key(_to_text(value))
    return next((c for c in column.choices if _choice_key(c) == key), None)


def _check_range(column: ColumnSpec, number: Decimal) -> str | None:
    if column.gt is not None and number <= column.gt:
        return MSG_GT.format(limit=column.gt)
    if column.ge is not None and number < column.ge:
        return MSG_GE.format(limit=column.ge)
    return None


def _convert(column: ColumnSpec, raw: Any) -> tuple[Any, str | None]:
    """Return (value, error message or None)."""
    if _is_empty(raw):
        return None, MSG_REQUIRED if column.required else None

    match column.kind:
        case ColumnKind.TEXT:
            return _to_text(raw), None
        case ColumnKind.DATE:
            parsed_date = _to_date(raw)
            return parsed_date, None if parsed_date else MSG_DATE
        case ColumnKind.CHOICE:
            choice = _match_choice(column, raw)
            if choice is None:
                return None, MSG_CHOICE.format(
                    value=_to_text(raw), choices=", ".join(column.choices)
                )
            return choice, None
        case ColumnKind.INT:
            number = _to_int(raw)
            if number is None:
                return None, MSG_INT
            return number, _check_range(column, Decimal(number))
        case ColumnKind.DECIMAL:
            decimal = _to_decimal(raw)
            if decimal is None:
                return None, MSG_NUMBER
            return decimal, _check_range(column, decimal)
    raise AssertionError(column.kind)


# --- sheet reading ---


def _rows(
    wb: Workbook, sheet_name: str, width: int, max_row: int | None = None
) -> Iterator[tuple[Any, ...]]:
    for values in wb[sheet_name].iter_rows(max_row=max_row, max_col=width, values_only=True):
        yield tuple(values) + (None,) * (width - len(values))


def _parse_record(
    sheet: SheetSpec, row_no: int, values: Sequence[Any], errors: _Errors
) -> dict[str, Any] | None:
    record: dict[str, Any] = {}
    ok = True
    for column, raw in zip(sheet.columns, values, strict=False):
        value, message = _convert(column, raw)
        if message:
            errors.add(sheet.name, row_no, column.header, message)
            ok = False
        record[column.key] = value
    return record if ok else None


def _parse_trip_sheet(wb: Workbook, sheet_name: str, errors: _Errors) -> dict[str, Any] | None:
    last_row = FIRST_DATA_ROW + len(TRIP_SHEET.columns) - 1
    rows = list(_rows(wb, sheet_name, 2, max_row=last_row))
    record: dict[str, Any] = {}
    ok = True
    for row_no, column in enumerate(TRIP_SHEET.columns, start=FIRST_DATA_ROW):
        label, raw = rows[row_no - 1] if row_no <= len(rows) else (None, None)
        if normalize_header(_to_text(label or "")) != normalize_header(column.header):
            found = _to_text(label) if label is not None else ""
            message = MSG_FIELD.format(expected=column.header, found=found)
            errors.add(TRIP_SHEET.name, row_no, None, message)
            ok = False
            continue
        value, message = _convert(column, raw)
        if message:
            errors.add(TRIP_SHEET.name, row_no, column.header, message)
            ok = False
        record[column.key] = value
    return record if ok else None


def _parse_table(
    wb: Workbook, sheet_name: str, sheet: SheetSpec, errors: _Errors, need_rows: bool
) -> list[tuple[int, dict[str, Any]]]:
    width = len(sheet.columns)
    rows = _rows(wb, sheet_name, width)
    header = next(rows, (None,) * width)
    header_ok = True
    for column, found in zip(sheet.columns, header, strict=True):
        if normalize_header(_to_text(found or "")) != normalize_header(column.header):
            found_text = _to_text(found) if found is not None else ""
            message = MSG_HEADER.format(expected=column.header, found=found_text)
            errors.add(sheet.name, 1, column.header, message)
            header_ok = False
    if not header_ok:
        return []

    records: list[tuple[int, dict[str, Any]]] = []
    seen = 0
    for row_no, values in enumerate(rows, start=FIRST_DATA_ROW):
        if all(_is_empty(v) for v in values):
            break
        if seen >= MAX_ROWS:
            errors.add(sheet.name, None, None, MSG_TOO_MANY_ROWS.format(limit=MAX_ROWS))
            break
        seen += 1
        if (record := _parse_record(sheet, row_no, values, errors)) is not None:
            records.append((row_no, record))
    if need_rows and seen == 0:
        errors.add(sheet.name, None, None, MSG_NO_ROWS)
    return records


def _sale_rows(records: list[tuple[int, dict[str, Any]]], errors: _Errors) -> list[SaleRow]:
    heads_header = SALES_SHEET.column("heads").header
    result = []
    for row_no, r in records:
        product = PRODUCTS[r["product"]]
        heads = r["heads"]
        if product.animal_type is None:
            heads = None
        elif heads is None:
            message = MSG_HEADS_REQUIRED.format(product=product.code)
            errors.add(SALES_SHEET.name, row_no, heads_header, message)
            continue
        result.append(
            SaleRow(
                row_no=row_no,
                day=r["day"],
                date=r["date"],
                client=r["client"],
                product_code=product.code,
                heads=heads,
                gross_kg=r["gross_kg"],
                price_thousand_uzs=r["price_thousand_uzs"],
                note=r["note"],
            )
        )
    return result


def _parse(wb: Workbook, errors: _Errors) -> ParsedTrip | None:
    by_key = {normalize_header(name): name for name in wb.sheetnames}
    names: dict[str, str] = {}
    for spec in (TRIP_SHEET, PURCHASES_SHEET, EXPENSES_SHEET, SALES_SHEET):
        actual = by_key.get(normalize_header(spec.name))
        if actual is None:
            errors.add(spec.name, None, None, MSG_SHEET_MISSING)
        else:
            names[spec.name] = actual

    def table(spec: SheetSpec, need_rows: bool) -> list[tuple[int, dict[str, Any]]]:
        if spec.name not in names:
            return []
        return _parse_table(wb, names[spec.name], spec, errors, need_rows)

    trip = (
        _parse_trip_sheet(wb, names[TRIP_SHEET.name], errors) if TRIP_SHEET.name in names else None
    )
    purchases = [
        PurchaseRow(
            row_no=row_no,
            date=r["date"],
            animal_type=ANIMAL_BY_LABEL[r["animal_type"]],
            heads=r["heads"],
            gross_kg=r["gross_kg"],
            discount_kg=r["discount_kg"],
            price_kzt=r["price_kzt"],
            note=r["note"],
        )
        for row_no, r in table(PURCHASES_SHEET, need_rows=True)
    ]
    expenses = [
        ExpenseRow(
            row_no=row_no,
            item=r["item"],
            qty=r["qty"],
            unit_price=r["unit_price"],
            currency=CURRENCY_BY_LABEL[r["currency"]],
            note=r["note"],
        )
        for row_no, r in table(EXPENSES_SHEET, need_rows=False)
    ]
    sales = _sale_rows(table(SALES_SHEET, need_rows=True), errors)

    if errors.items or trip is None:
        return None
    return ParsedTrip(
        number=trip["number"],
        departure_date=trip["departure_date"],
        arrival_date=trip["arrival_date"],
        rate_kzt=trip["rate_kzt"],
        rate_usd=trip["rate_usd"],
        note=trip["note"],
        purchases=purchases,
        expenses=expenses,
        sales=sales,
    )


def parse_trip_workbook(data: bytes) -> ParseResult:
    try:
        wb = load_workbook(BytesIO(data), read_only=True, data_only=True)
    except Exception:  # openpyxl raises many error types for non-xlsx input
        return ParseResult(None, [ParseError(None, None, None, MSG_BAD_FILE)])

    errors = _Errors()
    trip = None
    try:
        trip = _parse(wb, errors)
    except _TooManyErrors:
        trip = None
    finally:
        wb.close()
    if errors.items:
        return ParseResult(None, errors.items, errors.truncated)
    return ParseResult(trip)
