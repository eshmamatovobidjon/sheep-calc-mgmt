"""Number and date formatting/parsing for user-facing text."""

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sheepbot.config import get_settings

DATE_FORMAT = "%d.%m.%Y"
DATETIME_FORMAT = "%d.%m.%Y %H:%M"


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def _group_thousands(digits: str) -> str:
    return f"{int(digits):,}".replace(",", " ")


def fmt_money(value: int | Decimal) -> str:
    """Whole so'm with space thousand separators: 85155400 -> '85 155 400'."""
    amount = int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    sign = "-" if amount < 0 else ""
    return sign + _group_thousands(str(abs(amount)))


def fmt_kg(value: Decimal | int | float) -> str:
    """Kilograms with one decimal and comma separator: 1077.0 -> '1 077,0'."""
    kg = Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    sign = "-" if kg < 0 else ""
    whole, frac = f"{abs(kg):.1f}".split(".")
    return f"{sign}{_group_thousands(whole)},{frac}"


def fmt_date(value: date) -> str:
    return value.strftime(DATE_FORMAT)


def fmt_percent(value: Decimal) -> str:
    """One decimal with comma separator: 7.25 -> '7,3'."""
    return f"{value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}".replace(".", ",")


def plural(n: int, forms: tuple[str, str, str]) -> str:
    """Russian plural form for n: forms = (one, few, many), e.g. ('строка', 'строки', 'строк')."""
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


def fmt_datetime(value: datetime) -> str:
    """Format in the configured timezone; naive values are treated as UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(_tz()).strftime(DATETIME_FORMAT)


def parse_amount(text: str) -> int | None:
    """'20 000 000' -> 20000000. Only digits and spaces are accepted."""
    compact = "".join(text.split())
    if not compact or not compact.isdecimal() or not compact.isascii():
        return None
    return int(compact)


def parse_date(text: str) -> date | None:
    """'31.10.2026' -> date(2026, 10, 31)."""
    try:
        return datetime.strptime(text.strip(), DATE_FORMAT).date()
    except ValueError:
        return None


def today() -> date:
    return datetime.now(_tz()).date()
