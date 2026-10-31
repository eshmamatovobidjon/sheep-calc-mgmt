"""Trip upload services: file storage, preview, save."""

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sheepbot.config import get_settings
from sheepbot.db.models import BotUser, Client, Expense, Product, Purchase, Sale, Trip, Upload
from sheepbot.domain import calculations as calc
from sheepbot.domain.calculations import PurchaseLine, SaleLine, TripTotals
from sheepbot.domain.enums import UploadStatus
from sheepbot.excel.parser import ExpenseRow, ParsedTrip, PurchaseRow, SaleRow
from sheepbot.services.clients import get_or_create_client, normalize_client_name

FILE_NAME_MAX = 255


# --- uploads ---


async def create_upload(
    session: AsyncSession, file_name: str, data: bytes, user: BotUser
) -> Upload:
    """Store the file as uploads/<sha256>.xlsx and create a pending upload row."""
    digest = hashlib.sha256(data).hexdigest()
    path = get_settings().uploads_dir / f"{digest}.xlsx"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    upload = Upload(
        file_name=file_name[:FILE_NAME_MAX],
        file_hash=digest,
        stored_path=str(path),
        uploaded_by_id=user.id,
        status=UploadStatus.PENDING,
    )
    session.add(upload)
    await session.flush()
    return upload


async def get_pending_upload(session: AsyncSession, upload_id: int, user: BotUser) -> Upload | None:
    """The upload if it is still pending and belongs to the user (admin may act on any)."""
    upload = await session.get(Upload, upload_id)
    if upload is None or upload.status != UploadStatus.PENDING:
        return None
    if upload.uploaded_by_id != user.id and not user.is_admin:
        return None
    return upload


def read_upload_file(upload: Upload) -> bytes:
    return Path(upload.stored_path).read_bytes()


def set_upload_status(upload: Upload, status: UploadStatus, trip_number: int | None = None) -> None:
    upload.status = status
    if trip_number is not None:
        upload.trip_number = trip_number


# --- calculations over a parsed trip ---


@dataclass(frozen=True, slots=True)
class ComputedExpense:
    row: ExpenseRow
    amount: Decimal
    amount_uzs: int


@dataclass(frozen=True, slots=True)
class ComputedSale:
    row: SaleRow
    product: Product
    price_uzs_per_kg: int
    line: SaleLine


@dataclass(frozen=True, slots=True)
class ComputedTrip:
    purchases: list[tuple[PurchaseRow, PurchaseLine]]
    expenses: list[ComputedExpense]
    sales: list[ComputedSale]
    totals: TripTotals


async def _products(session: AsyncSession) -> dict[str, Product]:
    return {p.code: p for p in await session.scalars(select(Product))}


def compute_trip(parsed: ParsedTrip, products: dict[str, Product]) -> ComputedTrip:
    purchases = []
    for p in parsed.purchases:
        net = calc.purchase_net_kg(p.gross_kg, p.discount_kg)
        amount_kzt = calc.purchase_amount_kzt(net, p.price_kzt)
        line = PurchaseLine(
            animal_type=p.animal_type,
            heads=p.heads,
            gross_kg=p.gross_kg,
            net_kg=net,
            amount_kzt=amount_kzt,
            amount_uzs=calc.to_uzs(amount_kzt, parsed.rate_kzt),
        )
        purchases.append((p, line))

    expenses = []
    for e in parsed.expenses:
        amount = calc.expense_amount(e.qty, e.unit_price)
        rate = calc.currency_rate(e.currency, parsed.rate_kzt, parsed.rate_usd)
        expenses.append(ComputedExpense(e, amount, calc.to_uzs(amount, rate)))

    sales = []
    for s in parsed.sales:
        product = products[s.product_code]
        net = calc.sale_net_kg(s.gross_kg, s.heads, product.discount_per_head)
        price = calc.sale_price_uzs_per_kg(s.price_thousand_uzs)
        line = SaleLine(
            day=s.day,
            client_key=normalize_client_name(s.client),
            client_name=s.client,
            product_code=product.code,
            animal_type=product.animal_type,
            heads=s.heads,
            net_kg=net,
            amount_uzs=calc.sale_amount_uzs(net, price),
        )
        sales.append(ComputedSale(s, product, price, line))

    totals = calc.trip_totals(
        (line for _, line in purchases),
        (e.amount_uzs for e in expenses),
        (s.line for s in sales),
    )
    return ComputedTrip(purchases, expenses, sales, totals)


# --- preview and save ---


@dataclass(frozen=True, slots=True)
class TripPreview:
    number: int
    departure_date: date
    totals: TripTotals
    replaces_existing: bool
    new_client_names: list[str]


async def build_preview(session: AsyncSession, parsed: ParsedTrip) -> TripPreview:
    computed = compute_trip(parsed, await _products(session))
    existing = await session.scalar(select(Trip.id).where(Trip.number == parsed.number))

    names: dict[str, str] = {}
    for sale in computed.sales:
        names.setdefault(sale.line.client_key, sale.line.client_name)
    known = set(await session.scalars(select(Client.name_key).where(Client.name_key.in_(names))))
    return TripPreview(
        number=parsed.number,
        departure_date=parsed.departure_date,
        totals=computed.totals,
        replaces_existing=existing is not None,
        new_client_names=[name for key, name in names.items() if key not in known],
    )


async def save_trip(
    session: AsyncSession, parsed: ParsedTrip, upload: Upload, user: BotUser
) -> Trip:
    """Replace any trip with the same number, create missing clients, insert all rows."""
    computed = compute_trip(parsed, await _products(session))

    existing = await session.scalar(select(Trip).where(Trip.number == parsed.number))
    if existing is not None:
        await session.delete(existing)
        await session.flush()

    clients: dict[str, Client] = {}
    for sale in computed.sales:
        key = sale.line.client_key
        if key not in clients:
            clients[key] = await get_or_create_client(session, sale.row.client, user.id)

    trip = Trip(
        number=parsed.number,
        departure_date=parsed.departure_date,
        arrival_date=parsed.arrival_date,
        rate_kzt=parsed.rate_kzt,
        rate_usd=parsed.rate_usd,
        note=parsed.note,
        upload_id=upload.id,
        purchases=[
            Purchase(
                row_no=row.row_no,
                date=row.date,
                animal_type=row.animal_type,
                heads=row.heads,
                gross_kg=row.gross_kg,
                discount_kg=row.discount_kg,
                net_kg=line.net_kg,
                price_kzt=row.price_kzt,
                amount_kzt=line.amount_kzt,
                amount_uzs=line.amount_uzs,
                note=row.note,
            )
            for row, line in computed.purchases
        ],
        expenses=[
            Expense(
                row_no=e.row.row_no,
                item=e.row.item,
                qty=e.row.qty if e.row.qty is not None else Decimal(1),
                unit_price=e.row.unit_price,
                currency=e.row.currency,
                amount=e.amount,
                amount_uzs=e.amount_uzs,
                note=e.row.note,
            )
            for e in computed.expenses
        ],
        sales=[
            Sale(
                row_no=s.row.row_no,
                day=s.row.day,
                date=s.row.date,
                client=clients[s.line.client_key],
                product=s.product,
                heads=s.row.heads,
                gross_kg=s.row.gross_kg,
                discount_per_head=s.product.discount_per_head,
                net_kg=s.line.net_kg,
                price_uzs_per_kg=s.price_uzs_per_kg,
                amount_uzs=s.line.amount_uzs,
                note=s.row.note,
            )
            for s in computed.sales
        ],
    )
    session.add(trip)
    set_upload_status(upload, UploadStatus.SAVED, parsed.number)
    await session.flush()
    return trip


# --- trip queries ---


@dataclass(frozen=True, slots=True)
class TripOverview:
    id: int
    number: int
    departure_date: date
    totals: TripTotals


def trip_totals_from_model(trip: Trip) -> TripTotals:
    """Build TripTotals from a Trip ORM instance with loaded purchases, expenses and sales."""
    purchases = (
        PurchaseLine(
            animal_type=p.animal_type,
            heads=p.heads,
            gross_kg=p.gross_kg,
            net_kg=p.net_kg,
            amount_kzt=p.amount_kzt,
            amount_uzs=p.amount_uzs,
        )
        for p in trip.purchases
    )
    expenses_uzs = (e.amount_uzs for e in trip.expenses)
    sales = (
        SaleLine(
            day=s.day,
            client_key=s.client.name_key,
            client_name=s.client.name,
            product_code=s.product.code,
            animal_type=s.product.animal_type,
            heads=s.heads,
            net_kg=s.net_kg,
            amount_uzs=s.amount_uzs,
        )
        for s in trip.sales
    )
    return calc.trip_totals(purchases, expenses_uzs, sales)


def _trip_load_options():
    return (
        selectinload(Trip.purchases),
        selectinload(Trip.expenses),
        selectinload(Trip.sales).selectinload(Sale.client),
        selectinload(Trip.sales).selectinload(Sale.product),
    )


async def get_trip(session: AsyncSession, trip_id: int) -> Trip | None:
    stmt = select(Trip).where(Trip.id == trip_id).options(*_trip_load_options())
    return await session.scalar(stmt)


async def trip_id_by_number(session: AsyncSession, number: int) -> int | None:
    return await session.scalar(select(Trip.id).where(Trip.number == number))


async def count_trips(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(Trip)) or 0


async def list_recent_trips(
    session: AsyncSession, limit: int = 10, offset: int = 0
) -> list[TripOverview]:
    stmt = (
        select(Trip)
        .options(*_trip_load_options())
        .order_by(Trip.departure_date.desc(), Trip.number.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = await session.scalars(stmt)
    return [
        TripOverview(
            id=t.id,
            number=t.number,
            departure_date=t.departure_date,
            totals=trip_totals_from_model(t),
        )
        for t in rows
    ]
