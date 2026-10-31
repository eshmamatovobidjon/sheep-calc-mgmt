"""Trip template v1: single source of truth for the template builder and the parser."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from sheepbot.domain.catalog import PRODUCT_CATALOG, PRODUCT_CODES
from sheepbot.domain.enums import ANIMAL_TYPE_LABELS, CURRENCY_LABELS

TEMPLATE_VERSION = "trip_template_v1"
TEMPLATE_FILE_NAME = f"{TEMPLATE_VERSION}.xlsx"

SHEET_INSTRUCTIONS = "Инструкция"
SHEET_TRIP = "Рейс"
SHEET_PURCHASES = "Закуп"
SHEET_EXPENSES = "Расходы"
SHEET_SALES = "Продажи"
SHEET_LISTS = "Справочник"
SHEET_ORDER = (
    SHEET_INSTRUCTIONS,
    SHEET_TRIP,
    SHEET_PURCHASES,
    SHEET_EXPENSES,
    SHEET_SALES,
    SHEET_LISTS,
)

HEADER_ROW = 1
FIRST_DATA_ROW = 2
REQUIRED_MARK = "*"


class ColumnKind(StrEnum):
    TEXT = "text"
    INT = "int"
    DECIMAL = "decimal"
    DATE = "date"
    CHOICE = "choice"


class SheetKind(StrEnum):
    KEY_VALUE = "key_value"  # field names in column A, values in column B
    TABLE = "table"  # header row, one record per row


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    key: str
    header: str
    kind: ColumnKind
    required: bool
    choices: tuple[str, ...] = ()
    gt: Decimal | None = None  # value must be > gt
    ge: Decimal | None = None  # value must be >= ge
    width: int = 14

    @property
    def display_header(self) -> str:
        return f"{self.header} {REQUIRED_MARK}" if self.required else self.header


@dataclass(frozen=True, slots=True)
class SheetSpec:
    name: str
    kind: SheetKind
    columns: tuple[ColumnSpec, ...]

    def column(self, key: str) -> ColumnSpec:
        return next(c for c in self.columns if c.key == key)


ZERO = Decimal(0)
ONE = Decimal(1)

TRIP_SHEET = SheetSpec(
    SHEET_TRIP,
    SheetKind.KEY_VALUE,
    (
        ColumnSpec("number", "Номер рейса", ColumnKind.INT, True, gt=ZERO),
        ColumnSpec("departure_date", "Дата отправки", ColumnKind.DATE, True),
        ColumnSpec("arrival_date", "Дата прибытия", ColumnKind.DATE, False),
        ColumnSpec("rate_kzt", "Курс KZT→UZS", ColumnKind.DECIMAL, True, gt=ZERO),
        ColumnSpec("rate_usd", "Курс USD→UZS", ColumnKind.DECIMAL, True, gt=ZERO),
        ColumnSpec("note", "Примечание", ColumnKind.TEXT, False),
    ),
)
TRIP_HEADERS = ("Поле", "Значение")

PURCHASES_SHEET = SheetSpec(
    SHEET_PURCHASES,
    SheetKind.TABLE,
    (
        ColumnSpec("date", "Дата", ColumnKind.DATE, True, width=13),
        ColumnSpec(
            "animal_type",
            "Тип",
            ColumnKind.CHOICE,
            True,
            choices=tuple(ANIMAL_TYPE_LABELS.values()),
            width=12,
        ),
        ColumnSpec("heads", "Голов", ColumnKind.INT, True, gt=ZERO, width=10),
        ColumnSpec("gross_kg", "Вес брутто, кг", ColumnKind.DECIMAL, True, gt=ZERO, width=16),
        ColumnSpec("discount_kg", "Скидка, кг", ColumnKind.DECIMAL, True, ge=ZERO, width=13),
        ColumnSpec("price_kzt", "Цена, KZT/кг", ColumnKind.DECIMAL, True, gt=ZERO, width=14),
        ColumnSpec("note", "Примечание", ColumnKind.TEXT, False, width=30),
    ),
)

EXPENSES_SHEET = SheetSpec(
    SHEET_EXPENSES,
    SheetKind.TABLE,
    (
        ColumnSpec("item", "Статья", ColumnKind.TEXT, True, width=24),
        ColumnSpec("qty", "Кол-во", ColumnKind.DECIMAL, False, gt=ZERO, width=10),
        ColumnSpec("unit_price", "Цена за ед.", ColumnKind.DECIMAL, True, gt=ZERO, width=14),
        ColumnSpec(
            "currency",
            "Валюта",
            ColumnKind.CHOICE,
            True,
            choices=tuple(CURRENCY_LABELS.values()),
            width=10,
        ),
        ColumnSpec("note", "Примечание", ColumnKind.TEXT, False, width=30),
    ),
)

SALES_SHEET = SheetSpec(
    SHEET_SALES,
    SheetKind.TABLE,
    (
        ColumnSpec("day", "День", ColumnKind.INT, True, ge=ONE, width=8),
        ColumnSpec("date", "Дата", ColumnKind.DATE, True, width=13),
        ColumnSpec("client", "Клиент", ColumnKind.TEXT, True, width=28),
        ColumnSpec("product", "Товар", ColumnKind.CHOICE, True, choices=PRODUCT_CODES, width=17),
        # Required for animal products only; the parser enforces that.
        ColumnSpec("heads", "Голов", ColumnKind.INT, False, gt=ZERO, width=10),
        ColumnSpec("gross_kg", "Вес брутто, кг", ColumnKind.DECIMAL, True, gt=ZERO, width=16),
        ColumnSpec(
            "price_thousand_uzs",
            "Цена, тыс. сум/кг",
            ColumnKind.DECIMAL,
            True,
            gt=ZERO,
            width=18,
        ),
        ColumnSpec("note", "Примечание", ColumnKind.TEXT, False, width=30),
    ),
)

DATA_SHEETS = (TRIP_SHEET, PURCHASES_SHEET, EXPENSES_SHEET, SALES_SHEET)
TABLE_SHEETS = (PURCHASES_SHEET, EXPENSES_SHEET, SALES_SHEET)

CHOICE_ERROR_TITLE = "Неверное значение"
CHOICE_ERROR = "Выберите значение из выпадающего списка."


def normalize_header(text: str) -> str:
    """Header comparison key: trimmed, '*' removed, spaces collapsed, case-insensitive."""
    return " ".join(text.replace(REQUIRED_MARK, " ").split()).casefold()


def instruction_lines() -> list[str]:
    """Russian instructions; lines starting with '# ' are headings."""
    products = [
        f"   {p.code} — {p.name}, скидка {str(p.discount_per_head).replace('.', ',')} кг с головы"
        if p.animal_type
        else f"   {p.code} — {p.name} (субпродукт, без скидки)"
        for p in PRODUCT_CATALOG
    ]
    return [
        f"# Шаблон рейса ({TEMPLATE_VERSION})",
        "Один файл = один рейс (одна фура). Заполните листы и отправьте файл боту.",
        "",
        "# Листы",
        f"«{SHEET_TRIP}» — номер рейса, даты и курсы валют. Значения вводятся в столбец B.",
        f"«{SHEET_PURCHASES}» — закуп скота в Казахстане по партиям: дата, тип, голов, "
        "вес брутто, скидка (кг на всю партию), цена в тенге за 1 кг.",
        f"«{SHEET_EXPENSES}» — расходы рейса: статья, количество, цена за единицу и валюта "
        "(KZT, USD или UZS). Сумма = кол-во × цена; если кол-во не указано, считается 1.",
        f"«{SHEET_SALES}» — продажи в Ташкенте: день продажи (1, 2, 3 …), дата, клиент, "
        "товар, голов, вес брутто, цена.",
        "",
        "# Правила заполнения",
        f"Поля со звёздочкой ({REQUIRED_MARK}) обязательны.",
        "Цена закупа — в тенге (KZT) за 1 кг.",
        "Цена продажи — в ТЫСЯЧАХ сум за 1 кг: 115 означает 115 000 сум/кг.",
        "Курсы — сколько сум стоит 1 KZT и 1 USD (например, 26,8 и 11 900).",
        "Даты — в формате ДД.ММ.ГГГГ. Числа — без текста и единиц измерения.",
        "Тип, Валюта и Товар выбирайте из выпадающего списка.",
        "Код товара содержит скидку с головы. Вес нетто = брутто − голов × скидка:",
        *products,
        "Для субпродуктов столбец «Голов» не заполняется.",
        "Имя клиента пишите одинаково во всех рейсах.",
        "",
        "# Важно",
        "Не переименовывайте листы и заголовки столбцов и не меняйте их порядок.",
        "Не оставляйте пустых строк внутри таблицы: бот читает строки до первой пустой.",
        "Формулы не нужны — бот сам считает нетто, суммы, себестоимость и прибыль.",
        "Оплаты клиентов в этот файл НЕ вносятся — их вводят в боте (кнопка «Оплата»).",
    ]
