"""Client balances: Σ sales − Σ payments (not deleted). Positive = client owes."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import BigInteger, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.db.models import Client, Payment, Sale
from sheepbot.services.clients import normalize_client_name


class BalanceFilter(StrEnum):
    ALL = "all"
    DEBT = "debt"
    CREDIT = "credit"
    ZERO = "zero"


def _sum_int(column):
    # PostgreSQL returns SUM(bigint) as numeric; keep balances as int.
    return func.coalesce(func.sum(column), 0).cast(BigInteger)


@dataclass(frozen=True, slots=True)
class ClientBalance:
    client_id: int
    name: str
    shipped: int
    paid: int
    last_sale_date: date | None
    last_payment_date: date | None

    @property
    def balance(self) -> int:
        return self.shipped - self.paid


def _balances_stmt(
    client_ids: Sequence[int] | None = None,
    query: str = "",
    kind: BalanceFilter = BalanceFilter.ALL,
) -> Select:
    sales = (
        select(
            Sale.client_id,
            _sum_int(Sale.amount_uzs).label("shipped"),
            func.max(Sale.date).label("last_sale"),
        )
        .group_by(Sale.client_id)
        .subquery()
    )
    payments = (
        select(
            Payment.client_id,
            _sum_int(Payment.amount_uzs).label("paid"),
            func.max(Payment.date).label("last_payment"),
        )
        .where(Payment.is_deleted.is_(False))
        .group_by(Payment.client_id)
        .subquery()
    )
    shipped = func.coalesce(sales.c.shipped, 0)
    paid = func.coalesce(payments.c.paid, 0)
    stmt = (
        select(
            Client.id,
            Client.name,
            shipped,
            paid,
            sales.c.last_sale,
            payments.c.last_payment,
        )
        .outerjoin(sales, sales.c.client_id == Client.id)
        .outerjoin(payments, payments.c.client_id == Client.id)
        .order_by(Client.name_key, Client.id)
    )
    if client_ids is not None:
        stmt = stmt.where(Client.id.in_(client_ids))
    if key := normalize_client_name(query):
        stmt = stmt.where(Client.name_key.contains(key, autoescape=True))
    if kind is BalanceFilter.DEBT:
        stmt = stmt.where(shipped > paid)
    elif kind is BalanceFilter.CREDIT:
        stmt = stmt.where(shipped < paid)
    elif kind is BalanceFilter.ZERO:
        stmt = stmt.where(shipped == paid)
    return stmt


async def _load(session: AsyncSession, client_ids: Sequence[int] | None) -> list[ClientBalance]:
    rows = await session.execute(_balances_stmt(client_ids))
    return [ClientBalance(*row) for row in rows]


async def client_balance(session: AsyncSession, client_id: int, as_of: date | None = None) -> int:
    shipped = select(_sum_int(Sale.amount_uzs)).where(Sale.client_id == client_id)
    paid = select(_sum_int(Payment.amount_uzs)).where(
        Payment.client_id == client_id, Payment.is_deleted.is_(False)
    )
    if as_of is not None:
        shipped = shipped.where(Sale.date <= as_of)
        paid = paid.where(Payment.date <= as_of)
    return (await session.scalar(shipped) or 0) - (await session.scalar(paid) or 0)


async def get_client_balance(session: AsyncSession, client_id: int) -> ClientBalance | None:
    result = await _load(session, [client_id])
    return result[0] if result else None


async def balances_for(
    session: AsyncSession, client_ids: Sequence[int]
) -> dict[int, ClientBalance]:
    return {b.client_id: b for b in await _load(session, client_ids)}


async def all_balances(session: AsyncSession) -> list[ClientBalance]:
    return await _load(session, None)


async def page_balances(
    session: AsyncSession, query: str, kind: BalanceFilter, offset: int, limit: int
) -> tuple[list[ClientBalance], int]:
    """One page of client balances matching the name query and filter, plus the total count."""
    stmt = _balances_stmt(query=query, kind=kind)
    total = await session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = await session.execute(stmt.offset(offset).limit(limit))
    return [ClientBalance(*row) for row in rows], total or 0
