"""DB -> report dataclasses (Phase 06)."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sheepbot.db.models import Payment, Product, Sale
from sheepbot.domain import calculations as calc
from sheepbot.domain.calculations import ZERO, PurchaseGroup, TripTotals
from sheepbot.domain.catalog import PRODUCT_CATALOG
from sheepbot.domain.enums import (
    ANIMAL_TYPE_LABELS,
    CURRENCY_LABELS,
    PAYMENT_METHOD_LABELS,
    AnimalType,
)
from sheepbot.domain.formatting import today
from sheepbot.services import balances, clients, trips

LINE_SHIPMENT = "Отгрузка"
LINE_PAYMENT = "Оплата"

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def report_filename(
    title: str, subject: str | None = None, ext: str = "pdf", on_date: date | None = None
) -> str:
    """Build `<Title>_<subject>_<YYYY-MM-DD>.<pdf|xlsx>` with invalid chars stripped."""
    parts = [title]
    if subject:
        parts.append(subject)
    parts.append((on_date or today()).isoformat())
    raw_stem = "_".join(parts)
    clean_stem = _INVALID_FILENAME_CHARS.sub("", raw_stem)
    clean_stem = "_".join(clean_stem.split())
    return f"{clean_stem}.{ext.lstrip('.')}"


# --- Client statement ---


@dataclass(frozen=True, slots=True)
class StatementLine:
    date: date
    type: str
    trip_number: int | None
    day: int | None
    product: str | None
    heads: int | None
    gross_kg: Decimal | None
    discount_kg: Decimal | None
    net_kg: Decimal | None
    price_uzs_per_kg: int | None
    amount_uzs: int
    payment_method: str | None
    note: str | None
    running_balance: int

    @property
    def is_shipment(self) -> bool:
        return self.type == LINE_SHIPMENT

    @property
    def price_per_kg(self) -> int | None:
        return self.price_uzs_per_kg

    @property
    def amount(self) -> int:
        return self.amount_uzs

    @property
    def method(self) -> str | None:
        return self.payment_method

    @property
    def shipped_uzs(self) -> int | None:
        return self.amount_uzs if self.is_shipment else None

    @property
    def paid_uzs(self) -> int | None:
        return None if self.is_shipment else self.amount_uzs


@dataclass(frozen=True, slots=True)
class StatementData:
    client_id: int
    client_name: str
    client_phone: str | None
    date_from: date | None
    date_to: date | None
    opening_balance: int
    lines: list[StatementLine]
    total_heads: int
    total_gross_kg: Decimal
    total_discount_kg: Decimal
    total_net_kg: Decimal
    shipped_uzs: int
    paid_uzs: int
    closing_balance: int

    @property
    def shipped(self) -> int:
        return self.shipped_uzs

    @property
    def total_shipped(self) -> int:
        return self.shipped_uzs

    @property
    def paid(self) -> int:
        return self.paid_uzs

    @property
    def total_paid(self) -> int:
        return self.paid_uzs


async def statement_data(
    session: AsyncSession,
    client_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> StatementData | None:
    """Build client statement for the given date range (inclusive), or all time if None."""
    client = await clients.get_client(session, client_id)
    if client is None:
        return None

    if date_from is None:
        opening_balance = 0
    else:
        opening_balance = await balances.client_balance(
            session, client_id, as_of=date_from - timedelta(days=1)
        )

    sale_stmt = (
        select(Sale)
        .where(Sale.client_id == client_id)
        .options(selectinload(Sale.trip), selectinload(Sale.product))
    )
    payment_stmt = select(Payment).where(
        Payment.client_id == client_id, Payment.is_deleted.is_(False)
    )
    if date_from is not None:
        sale_stmt = sale_stmt.where(Sale.date >= date_from)
        payment_stmt = payment_stmt.where(Payment.date >= date_from)
    if date_to is not None:
        sale_stmt = sale_stmt.where(Sale.date <= date_to)
        payment_stmt = payment_stmt.where(Payment.date <= date_to)

    sales = list(await session.scalars(sale_stmt))
    payments = list(await session.scalars(payment_stmt))

    events: list[tuple[date, int, int, Sale | Payment]] = [
        *((s.date, 0, s.id, s) for s in sales),
        *((p.date, 1, p.id, p) for p in payments),
    ]
    events.sort(key=lambda item: (item[0], item[1], item[2]))

    running = opening_balance
    total_heads = 0
    total_gross_kg = ZERO
    total_discount_kg = ZERO
    total_net_kg = ZERO
    shipped_uzs = 0
    paid_uzs = 0
    lines: list[StatementLine] = []

    for _, kind_order, _, obj in events:
        if kind_order == 0:
            assert isinstance(obj, Sale)
            discount_kg = calc.round_kg(obj.gross_kg - obj.net_kg)
            running += obj.amount_uzs
            shipped_uzs += obj.amount_uzs
            total_heads += obj.heads or 0
            total_gross_kg += obj.gross_kg
            total_discount_kg += discount_kg
            total_net_kg += obj.net_kg
            lines.append(
                StatementLine(
                    date=obj.date,
                    type=LINE_SHIPMENT,
                    trip_number=obj.trip.number,
                    day=obj.day,
                    product=obj.product.name,
                    heads=obj.heads,
                    gross_kg=obj.gross_kg,
                    discount_kg=discount_kg,
                    net_kg=obj.net_kg,
                    price_uzs_per_kg=obj.price_uzs_per_kg,
                    amount_uzs=obj.amount_uzs,
                    payment_method=None,
                    note=obj.note,
                    running_balance=running,
                )
            )
        else:
            assert isinstance(obj, Payment)
            running -= obj.amount_uzs
            paid_uzs += obj.amount_uzs
            lines.append(
                StatementLine(
                    date=obj.date,
                    type=LINE_PAYMENT,
                    trip_number=None,
                    day=None,
                    product=None,
                    heads=None,
                    gross_kg=None,
                    discount_kg=None,
                    net_kg=None,
                    price_uzs_per_kg=None,
                    amount_uzs=obj.amount_uzs,
                    payment_method=PAYMENT_METHOD_LABELS[obj.method],
                    note=obj.note,
                    running_balance=running,
                )
            )

    closing_balance = opening_balance + shipped_uzs - paid_uzs
    return StatementData(
        client_id=client.id,
        client_name=client.name,
        client_phone=client.phone,
        date_from=date_from,
        date_to=date_to,
        opening_balance=opening_balance,
        lines=lines,
        total_heads=total_heads,
        total_gross_kg=total_gross_kg,
        total_discount_kg=total_discount_kg,
        total_net_kg=total_net_kg,
        shipped_uzs=shipped_uzs,
        paid_uzs=paid_uzs,
        closing_balance=closing_balance,
    )


# --- Trip summary ---


@dataclass(frozen=True, slots=True)
class PurchaseTypeRow:
    animal_type: AnimalType | None
    type_label: str
    heads: int
    gross_kg: Decimal
    discount_kg: Decimal
    net_kg: Decimal
    avg_price_kzt: Decimal
    amount_kzt: Decimal
    amount_uzs: int


@dataclass(frozen=True, slots=True)
class ExpenseReportRow:
    item: str
    qty: Decimal
    unit_price: Decimal
    currency: str
    amount: Decimal
    amount_uzs: int
    note: str | None


@dataclass(frozen=True, slots=True)
class SaleDayRow:
    day: int
    date: date | None
    lines: int
    heads: int
    net_kg: Decimal
    amount_uzs: int


@dataclass(frozen=True, slots=True)
class SaleProductRow:
    product_code: str
    product_name: str
    heads: int
    net_kg: Decimal
    avg_price_uzs: int
    amount_uzs: int


@dataclass(frozen=True, slots=True)
class SaleClientRow:
    client_name: str
    heads: int
    net_kg: Decimal
    amount_uzs: int


@dataclass(frozen=True, slots=True)
class AnimalEconomicsRow:
    animal_type: AnimalType
    type_label: str
    purchased_heads: int
    purchased_net_kg: Decimal
    sold_heads: int
    sold_net_kg: Decimal
    cost_per_kg: int | None
    avg_sale_price: int | None
    diff_per_kg: int | None


@dataclass(frozen=True, slots=True)
class TripSummaryData:
    trip_id: int
    number: int
    departure_date: date
    arrival_date: date | None
    rate_kzt: Decimal
    rate_usd: Decimal
    note: str | None
    totals: TripTotals
    purchases_by_type: list[PurchaseTypeRow]
    purchase_totals: PurchaseTypeRow
    expenses: list[ExpenseReportRow]
    expenses_uzs: int
    sales_by_day: list[SaleDayRow]
    sales_by_product: list[SaleProductRow]
    sales_by_client: list[SaleClientRow]
    type_economics: list[AnimalEconomicsRow]
    revenue_uzs: int
    cost_uzs: int
    profit_uzs: int
    margin_pct: Decimal | None


def _purchase_row(
    animal_type: AnimalType | None, label: str, group: PurchaseGroup
) -> PurchaseTypeRow:
    discount_kg = calc.round_kg(group.gross_kg - group.net_kg)
    avg_kzt = calc.round_money(group.amount_kzt / group.net_kg) if group.net_kg else ZERO
    return PurchaseTypeRow(
        animal_type=animal_type,
        type_label=label,
        heads=group.heads,
        gross_kg=group.gross_kg,
        discount_kg=discount_kg,
        net_kg=group.net_kg,
        avg_price_kzt=avg_kzt,
        amount_kzt=group.amount_kzt,
        amount_uzs=group.amount_uzs,
    )


def _sales_by_day_rows(sales: list[Sale], totals: TripTotals) -> list[SaleDayRow]:
    day_dates: dict[int, date] = {}
    for s in sales:
        existing = day_dates.get(s.day)
        if existing is None or s.date < existing:
            day_dates[s.day] = s.date
    return [
        SaleDayRow(
            day=day,
            date=day_dates.get(day),
            lines=group.lines,
            heads=group.heads,
            net_kg=group.net_kg,
            amount_uzs=group.amount_uzs,
        )
        for day, group in sorted(totals.sales_by_day.items())
    ]


def _sales_by_product_rows(
    product_names: dict[str, str], totals: TripTotals
) -> list[SaleProductRow]:
    catalog_order = {p.code: idx for idx, p in enumerate(PRODUCT_CATALOG)}
    sorted_codes = sorted(
        totals.sales_by_product,
        key=lambda code: (catalog_order.get(code, len(catalog_order)), code),
    )
    rows: list[SaleProductRow] = []
    for code in sorted_codes:
        group = totals.sales_by_product[code]
        avg_price = calc.round_uzs(Decimal(group.amount_uzs) / group.net_kg) if group.net_kg else 0
        rows.append(
            SaleProductRow(
                product_code=code,
                product_name=product_names.get(code, code),
                heads=group.heads,
                net_kg=group.net_kg,
                avg_price_uzs=avg_price,
                amount_uzs=group.amount_uzs,
            )
        )
    return rows


def _type_economics_rows(totals: TripTotals) -> list[AnimalEconomicsRow]:
    rows: list[AnimalEconomicsRow] = []
    for t in AnimalType:
        p_group = totals.purchases_by_type.get(t)
        s_group = totals.sales_by_type.get(t)
        if p_group is None and s_group is None:
            continue
        cost_kg = totals.cost_per_kg(t)
        sale_kg = totals.avg_sale_price(t)
        diff = (sale_kg - cost_kg) if (cost_kg is not None and sale_kg is not None) else None
        rows.append(
            AnimalEconomicsRow(
                animal_type=t,
                type_label=ANIMAL_TYPE_LABELS[t],
                purchased_heads=p_group.heads if p_group else 0,
                purchased_net_kg=p_group.net_kg if p_group else ZERO,
                sold_heads=s_group.heads if s_group else 0,
                sold_net_kg=s_group.net_kg if s_group else ZERO,
                cost_per_kg=cost_kg,
                avg_sale_price=sale_kg,
                diff_per_kg=diff,
            )
        )
    return rows


async def trip_summary_data(session: AsyncSession, trip_id: int) -> TripSummaryData | None:
    """Build trip summary data from TripTotals so numbers match the upload preview."""
    trip = await trips.get_trip(session, trip_id)
    if trip is None:
        return None

    totals = trips.trip_totals_from_model(trip)
    purchases_by_type = [
        _purchase_row(t, ANIMAL_TYPE_LABELS[t], totals.purchases_by_type[t])
        for t in AnimalType
        if t in totals.purchases_by_type
    ]
    purchase_totals = _purchase_row(None, "Итого", totals.purchases)
    expenses = [
        ExpenseReportRow(
            item=e.item,
            qty=e.qty,
            unit_price=e.unit_price,
            currency=CURRENCY_LABELS[e.currency],
            amount=e.amount,
            amount_uzs=e.amount_uzs,
            note=e.note,
        )
        for e in trip.expenses
    ]
    product_names = {p.code: p.name for p in await session.scalars(select(Product))}
    sales_by_client = [
        SaleClientRow(
            client_name=group.name,
            heads=group.heads,
            net_kg=group.net_kg,
            amount_uzs=group.amount_uzs,
        )
        for group in sorted(
            totals.sales_by_client.values(),
            key=lambda g: (-g.amount_uzs, g.name.casefold()),
        )
    ]

    return TripSummaryData(
        trip_id=trip.id,
        number=trip.number,
        departure_date=trip.departure_date,
        arrival_date=trip.arrival_date,
        rate_kzt=trip.rate_kzt,
        rate_usd=trip.rate_usd,
        note=trip.note,
        totals=totals,
        purchases_by_type=purchases_by_type,
        purchase_totals=purchase_totals,
        expenses=expenses,
        expenses_uzs=totals.expenses_uzs,
        sales_by_day=_sales_by_day_rows(trip.sales, totals),
        sales_by_product=_sales_by_product_rows(product_names, totals),
        sales_by_client=sales_by_client,
        type_economics=_type_economics_rows(totals),
        revenue_uzs=totals.revenue_uzs,
        cost_uzs=totals.cost_uzs,
        profit_uzs=totals.profit_uzs,
        margin_pct=totals.margin_pct,
    )


# --- Debtors ---


@dataclass(frozen=True, slots=True)
class DebtorRow:
    client_id: int
    client_name: str
    shipped_uzs: int
    paid_uzs: int
    balance_uzs: int
    last_sale_date: date | None
    last_payment_date: date | None

    @property
    def name(self) -> str:
        return self.client_name

    @property
    def balance(self) -> int:
        return self.balance_uzs


@dataclass(frozen=True, slots=True)
class DebtorsData:
    as_of: date
    rows: list[DebtorRow]
    total_shipped_uzs: int
    total_paid_uzs: int
    total_uzs: int

    @property
    def total(self) -> int:
        return self.total_uzs

    @property
    def total_balance_uzs(self) -> int:
        return self.total_uzs


async def debtors_data(session: AsyncSession) -> DebtorsData:
    """Clients with balance != 0, sorted by balance descending."""
    non_zero = [b for b in await balances.all_balances(session) if b.balance != 0]
    non_zero.sort(key=lambda b: (-b.balance, b.name.casefold()))
    rows = [
        DebtorRow(
            client_id=b.client_id,
            client_name=b.name,
            shipped_uzs=b.shipped,
            paid_uzs=b.paid,
            balance_uzs=b.balance,
            last_sale_date=b.last_sale_date,
            last_payment_date=b.last_payment_date,
        )
        for b in non_zero
    ]
    total_shipped = sum(r.shipped_uzs for r in rows)
    total_paid = sum(r.paid_uzs for r in rows)
    total_balance = sum(r.balance_uzs for r in rows)
    return DebtorsData(
        as_of=today(),
        rows=rows,
        total_shipped_uzs=total_shipped,
        total_paid_uzs=total_paid,
        total_uzs=total_balance,
    )
