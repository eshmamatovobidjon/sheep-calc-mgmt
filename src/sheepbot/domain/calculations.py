"""Pure calculation functions and TripTotals (architecture section 7).

Decimal everywhere, ROUND_HALF_UP: kg -> 1 decimal, KZT/USD -> 2 decimals, UZS -> int.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sheepbot.domain.enums import AnimalType, Currency

KG_STEP = Decimal("0.1")
MONEY_STEP = Decimal("0.01")
PCT_STEP = Decimal("0.1")
ZERO = Decimal(0)
THOUSAND = Decimal(1000)


def round_kg(value: Decimal) -> Decimal:
    return value.quantize(KG_STEP, rounding=ROUND_HALF_UP)


def round_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


def round_uzs(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def purchase_net_kg(gross_kg: Decimal, discount_kg: Decimal) -> Decimal:
    return round_kg(gross_kg - discount_kg)


def purchase_amount_kzt(net_kg: Decimal, price_kzt: Decimal) -> Decimal:
    return round_money(net_kg * price_kzt)


def to_uzs(amount: Decimal, rate: Decimal) -> int:
    return round_uzs(amount * rate)


def expense_amount(qty: Decimal | None, unit_price: Decimal) -> Decimal:
    return round_money((qty if qty is not None else Decimal(1)) * unit_price)


def currency_rate(currency: Currency, rate_kzt: Decimal, rate_usd: Decimal) -> Decimal:
    if currency is Currency.KZT:
        return rate_kzt
    if currency is Currency.USD:
        return rate_usd
    return Decimal(1)


def sale_net_kg(gross_kg: Decimal, heads: int | None, discount_per_head: Decimal) -> Decimal:
    return round_kg(gross_kg - (heads or 0) * discount_per_head)


def sale_price_uzs_per_kg(price_thousand_uzs: Decimal) -> int:
    return round_uzs(price_thousand_uzs * THOUSAND)


def sale_amount_uzs(net_kg: Decimal, price_uzs_per_kg: int) -> int:
    return round_uzs(net_kg * price_uzs_per_kg)


def margin_pct(profit: int, cost: int) -> Decimal | None:
    if cost == 0:
        return None
    return (Decimal(profit) / Decimal(cost) * 100).quantize(PCT_STEP, rounding=ROUND_HALF_UP)


# --- trip totals ---


@dataclass(frozen=True, slots=True)
class PurchaseLine:
    animal_type: AnimalType
    heads: int
    gross_kg: Decimal
    net_kg: Decimal
    amount_kzt: Decimal
    amount_uzs: int


@dataclass(frozen=True, slots=True)
class SaleLine:
    day: int
    client_key: str
    client_name: str
    product_code: str
    animal_type: AnimalType | None
    heads: int | None
    net_kg: Decimal
    amount_uzs: int


@dataclass(slots=True)
class PurchaseGroup:
    heads: int = 0
    gross_kg: Decimal = ZERO
    net_kg: Decimal = ZERO
    amount_kzt: Decimal = ZERO
    amount_uzs: int = 0
    lines: int = 0

    def add(self, line: PurchaseLine) -> None:
        self.heads += line.heads
        self.gross_kg += line.gross_kg
        self.net_kg += line.net_kg
        self.amount_kzt += line.amount_kzt
        self.amount_uzs += line.amount_uzs
        self.lines += 1


@dataclass(slots=True)
class SaleGroup:
    name: str = ""
    heads: int = 0
    net_kg: Decimal = ZERO
    amount_uzs: int = 0
    lines: int = 0

    def add(self, line: SaleLine) -> None:
        self.heads += line.heads or 0
        self.net_kg += line.net_kg
        self.amount_uzs += line.amount_uzs
        self.lines += 1


@dataclass(slots=True)
class TripTotals:
    purchases: PurchaseGroup = field(default_factory=PurchaseGroup)
    purchases_by_type: dict[AnimalType, PurchaseGroup] = field(default_factory=dict)
    expenses_uzs: int = 0
    sales: SaleGroup = field(default_factory=SaleGroup)
    sales_by_day: dict[int, SaleGroup] = field(default_factory=dict)
    sales_by_product: dict[str, SaleGroup] = field(default_factory=dict)
    sales_by_client: dict[str, SaleGroup] = field(default_factory=dict)
    sales_by_type: dict[AnimalType, SaleGroup] = field(default_factory=dict)

    @property
    def revenue_uzs(self) -> int:
        return self.sales.amount_uzs

    @property
    def cost_uzs(self) -> int:
        return self.purchases.amount_uzs + self.expenses_uzs

    @property
    def profit_uzs(self) -> int:
        return self.revenue_uzs - self.cost_uzs

    @property
    def margin_pct(self) -> Decimal | None:
        return margin_pct(self.profit_uzs, self.cost_uzs)

    def cost_per_kg(self, animal_type: AnimalType) -> int | None:
        """(purchase_uzs_t + expenses_uzs * share_t) / net_kg_t, share by purchase value."""
        group = self.purchases_by_type.get(animal_type)
        if group is None or group.net_kg == 0 or self.purchases.amount_uzs == 0:
            return None
        share = Decimal(group.amount_uzs) / Decimal(self.purchases.amount_uzs)
        return round_uzs((group.amount_uzs + self.expenses_uzs * share) / group.net_kg)

    def avg_sale_price(self, animal_type: AnimalType) -> int | None:
        group = self.sales_by_type.get(animal_type)
        if group is None or group.net_kg == 0:
            return None
        return round_uzs(Decimal(group.amount_uzs) / group.net_kg)


def trip_totals(
    purchases: Iterable[PurchaseLine], expenses_uzs: Iterable[int], sales: Iterable[SaleLine]
) -> TripTotals:
    totals = TripTotals(expenses_uzs=sum(expenses_uzs))
    for p in purchases:
        totals.purchases.add(p)
        totals.purchases_by_type.setdefault(p.animal_type, PurchaseGroup()).add(p)
    for s in sales:
        totals.sales.add(s)
        totals.sales_by_day.setdefault(s.day, SaleGroup()).add(s)
        totals.sales_by_product.setdefault(s.product_code, SaleGroup(name=s.product_code)).add(s)
        totals.sales_by_client.setdefault(s.client_key, SaleGroup(name=s.client_name)).add(s)
        if s.animal_type is not None:
            totals.sales_by_type.setdefault(s.animal_type, SaleGroup()).add(s)
    return totals
