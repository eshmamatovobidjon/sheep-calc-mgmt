"""Client payments: create, list, soft delete."""

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sheepbot.db.models import Payment
from sheepbot.domain.enums import PaymentMethod


async def create_payment(
    session: AsyncSession,
    client_id: int,
    amount_uzs: int,
    method: PaymentMethod,
    payment_date: date,
    note: str | None,
    entered_by_id: int,
) -> Payment:
    payment = Payment(
        client_id=client_id,
        amount_uzs=amount_uzs,
        method=method,
        date=payment_date,
        note=note,
        entered_by_id=entered_by_id,
        is_deleted=False,
    )
    session.add(payment)
    await session.flush()
    return payment


async def list_recent(session: AsyncSession, limit: int = 20) -> list[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.is_deleted.is_(False))
        .options(selectinload(Payment.client), selectinload(Payment.entered_by))
        .order_by(Payment.id.desc())
        .limit(limit)
    )
    return list(await session.scalars(stmt))


async def get_payment(session: AsyncSession, payment_id: int) -> Payment | None:
    """A payment that is not deleted, with client and author loaded."""
    stmt = (
        select(Payment)
        .where(Payment.id == payment_id, Payment.is_deleted.is_(False))
        .options(selectinload(Payment.client), selectinload(Payment.entered_by))
    )
    return await session.scalar(stmt)


async def delete_payment(session: AsyncSession, payment_id: int, user_id: int) -> Payment | None:
    """Soft delete. Returns None if the payment doesn't exist or is already deleted."""
    payment = await get_payment(session, payment_id)
    if payment is None:
        return None
    payment.is_deleted = True
    payment.deleted_by_id = user_id
    payment.deleted_at = datetime.now(UTC)
    await session.flush()
    return payment
