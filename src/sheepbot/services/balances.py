"""Client balances: Σ sales − Σ payments (not deleted). Positive = client owes."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.db.models import Client, Payment, Sale


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


def _balances_stmt(client_ids: Sequence[int] | None = None) -> Select:
    sales = (
        select(
            Sale.client_id,
            func.sum(Sale.amount_uzs).label("shipped"),
            func.max(Sale.date).label("last_sale"),
        )
        .group_by(Sale.client_id)
        .subquery()
    )
    payments = (
        select(
            Payment.client_id,
            func.sum(Payment.amount_uzs).label("paid"),
            func.max(Payment.date).label("last_payment"),
        )
        .where(Payment.is_deleted.is_(False))
        .group_by(Payment.client_id)
        .subquery()
    )
    stmt = (
        select(
            Client.id,
            Client.name,
            func.coalesce(sales.c.shipped, 0),
            func.coalesce(payments.c.paid, 0),
            sales.c.last_sale,
            payments.c.last_payment,
        )
        .outerjoin(sales, sales.c.client_id == Client.id)
        .outerjoin(payments, payments.c.client_id == Client.id)
        .order_by(Client.name_key)
    )
    if client_ids is not None:
        stmt = stmt.where(Client.id.in_(client_ids))
    return stmt


async def _load(session: AsyncSession, client_ids: Sequence[int] | None) -> list[ClientBalance]:
    rows = await session.execute(_balances_stmt(client_ids))
    return [ClientBalance(*row) for row in rows]


async def client_balance(session: AsyncSession, client_id: int, as_of: date | None = None) -> int:
    shipped = select(func.coalesce(func.sum(Sale.amount_uzs), 0)).where(Sale.client_id == client_id)
    paid = select(func.coalesce(func.sum(Payment.amount_uzs), 0)).where(
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
