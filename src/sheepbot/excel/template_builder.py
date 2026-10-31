"""Builds the trip template workbook from template_spec, optionally filled with data."""

from collections.abc import Mapping, Sequence
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter, quote_sheetname
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from sheepbot.excel.template_spec import (
    CHOICE_ERROR,
    CHOICE_ERROR_TITLE,
    FIRST_DATA_ROW,
    HEADER_ROW,
    SHEET_INSTRUCTIONS,
    SHEET_LISTS,
    TABLE_SHEETS,
    TEMPLATE_VERSION,
    TRIP_HEADERS,
    TRIP_SHEET,
    ColumnKind,
    ColumnSpec,
    SheetSpec,
    instruction_lines,
)

Row = Mapping[str, Any]
ListRefs = dict[str, tuple[str, str, tuple[str, ...]]]

DATE_FORMAT = "DD.MM.YYYY"
KG_FORMAT = "0.0"
VALIDATION_LAST_ROW = 1000
HEADER_FONT = Font(bold=True)
HEADER_FILL = PatternFill("solid", fgColor="DDEBF7")


def _number_format(column: ColumnSpec) -> str | None:
    if column.kind is ColumnKind.DATE:
        return DATE_FORMAT
    if column.key.endswith("_kg"):
        return KG_FORMAT
    return None


def _style_header(ws: Worksheet, col: int, value: str) -> None:
    cell = ws.cell(HEADER_ROW, col, value)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL


def _write(ws: Worksheet, row: int, col: int, column: ColumnSpec, value: Any) -> None:
    if value is None:
        return
    cell = ws.cell(row, col, value)
    if fmt := _number_format(column):
        cell.number_format = fmt


def _list_refs() -> ListRefs:
    """Choice column key -> (column letter in Справочник, header, values). A1 holds the version."""
    refs: ListRefs = {}
    for sheet in TABLE_SHEETS:
        for column in sheet.columns:
            if column.kind is ColumnKind.CHOICE and column.key not in refs:
                letter = get_column_letter(len(refs) + 2)
                refs[column.key] = (letter, column.header, column.choices)
    return refs


def _fill_instructions(ws: Worksheet) -> None:
    ws.column_dimensions["A"].width = 110
    for row, line in enumerate(instruction_lines(), start=1):
        heading = line.startswith("# ")
        cell = ws.cell(row, 1, line.removeprefix("# "))
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if heading:
            cell.font = Font(bold=True, size=12)


def _fill_trip(ws: Worksheet, values: Row) -> None:
    for col, header in enumerate(TRIP_HEADERS, start=1):
        _style_header(ws, col, header)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 22
    for row, column in enumerate(TRIP_SHEET.columns, start=FIRST_DATA_ROW):
        ws.cell(row, 1, column.display_header).font = HEADER_FONT
        value_cell = ws.cell(row, 2)
        if fmt := _number_format(column):
            value_cell.number_format = fmt
        _write(ws, row, 2, column, values.get(column.key))
    ws.freeze_panes = "A2"


def _fill_table(
    ws: Worksheet,
    sheet: SheetSpec,
    rows: Sequence[Row],
    list_refs: ListRefs,
) -> None:
    for col, column in enumerate(sheet.columns, start=1):
        letter = get_column_letter(col)
        _style_header(ws, col, column.display_header)
        ws.column_dimensions[letter].width = column.width
        if fmt := _number_format(column):
            ws.column_dimensions[letter].number_format = fmt
        if column.kind is ColumnKind.CHOICE:
            list_letter, _, choices = list_refs[column.key]
            first, last = f"${list_letter}$2", f"${list_letter}${len(choices) + 1}"
            source = f"{quote_sheetname(SHEET_LISTS)}!{first}:{last}"
            validation = DataValidation(
                type="list",
                formula1=source,
                allow_blank=True,
                showErrorMessage=True,
                errorTitle=CHOICE_ERROR_TITLE,
                error=CHOICE_ERROR,
            )
            validation.add(f"{letter}{FIRST_DATA_ROW}:{letter}{VALIDATION_LAST_ROW}")
            ws.add_data_validation(validation)

    for row, record in enumerate(rows, start=FIRST_DATA_ROW):
        for col, column in enumerate(sheet.columns, start=1):
            _write(ws, row, col, column, record.get(column.key))
    ws.freeze_panes = "A2"


def _fill_lists(ws: Worksheet, list_refs: ListRefs) -> None:
    ws["A1"] = TEMPLATE_VERSION
    for letter, header, choices in list_refs.values():
        ws[f"{letter}1"] = header
        for row, value in enumerate(choices, start=2):
            ws[f"{letter}{row}"] = value
        ws.column_dimensions[letter].width = 18
    ws.sheet_state = "hidden"


def build_template(
    trip: Row | None = None, rows: Mapping[str, Sequence[Row]] | None = None
) -> bytes:
    """Return the template as .xlsx bytes. `rows` maps sheet name -> records keyed by column key."""
    rows = rows or {}
    list_refs = _list_refs()

    wb = Workbook()
    instructions = wb.active
    assert instructions is not None
    instructions.title = SHEET_INSTRUCTIONS
    _fill_instructions(instructions)
    _fill_trip(wb.create_sheet(TRIP_SHEET.name), trip or {})
    for sheet in TABLE_SHEETS:
        _fill_table(wb.create_sheet(sheet.name), sheet, rows.get(sheet.name, ()), list_refs)
    _fill_lists(wb.create_sheet(SHEET_LISTS), list_refs)
    wb.active = 0

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
