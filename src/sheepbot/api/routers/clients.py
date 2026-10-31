from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.api import texts
from sheepbot.api.auth import CurrentUser, UploadUser
from sheepbot.api.deps import Session
from sheepbot.api.schemas import (
    ClientBalanceOut,
    ClientCreateIn,
    ClientDetailOut,
    ClientPageOut,
    ClientUpdateIn,
    LedgerLineOut,
    LedgerOut,
)
from sheepbot.reports.data import statement_data
from sheepbot.services import balances, clients
from sheepbot.services.balances import BalanceFilter, ClientBalance

router = APIRouter()


def _balance_out(b: ClientBalance) -> ClientBalanceOut:
    return ClientBalanceOut(
        id=b.client_id,
        name=b.name,
        shipped=str(b.shipped),
        paid=str(b.paid),
        balance=str(b.balance),
        last_sale_date=b.last_sale_date,
        last_payment_date=b.last_payment_date,
    )


@router.get("/clients")
async def list_clients(
    _: CurrentUser,
    session: Session,
    q: Annotated[str, Query(max_length=100)] = "",
    kind: Annotated[BalanceFilter, Query(alias="filter")] = BalanceFilter.ALL,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ClientPageOut:
    items, total = await balances.page_balances(session, q, kind, offset, limit)
    return ClientPageOut(items=[_balance_out(b) for b in items], total=total)


@router.get("/clients/{client_id}")
async def get_client(client_id: int, _: CurrentUser, session: Session) -> ClientDetailOut:
    return await _detail(session, client_id)


async def _detail(session: AsyncSession, client_id: int) -> ClientDetailOut:
    client = await clients.get_client(session, client_id)
    balance = await balances.get_client_balance(session, client_id)
    if client is None or balance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, texts.CLIENT_NOT_FOUND)
    return ClientDetailOut(**_balance_out(balance).model_dump(), phone=client.phone)


def _exists(name: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, texts.CLIENT_EXISTS.format(name=name))


async def _commit(session: AsyncSession, name: str) -> None:
    try:
        await session.commit()
    except IntegrityError:
        # Another request created the same normalized name in the meantime.
        await session.rollback()
        raise _exists(name) from None


@router.post("/clients", status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreateIn, user: UploadUser, session: Session
) -> ClientDetailOut:
    try:
        client = await clients.create_client(session, body.name, user.id)
    except clients.ClientExistsError as e:
        raise _exists(e.client.name) from None
    if body.phone:
        await clients.set_phone(session, client.id, body.phone)
    client_id = client.id
    await _commit(session, body.name)
    return await _detail(session, client_id)


@router.patch("/clients/{client_id}")
async def update_client(
    client_id: int, body: ClientUpdateIn, _: UploadUser, session: Session
) -> ClientDetailOut:
    if await clients.get_client(session, client_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, texts.CLIENT_NOT_FOUND)
    if body.name is not None:
        try:
            await clients.rename_client(session, client_id, body.name)
        except clients.ClientExistsError as e:
            raise _exists(e.client.name) from None
    if "phone" in body.model_fields_set:
        await clients.set_phone(session, client_id, body.phone)
    await _commit(session, body.name or "")
    return await _detail(session, client_id)


@router.get("/clients/{client_id}/ledger")
async def get_ledger(
    client_id: int,
    _: CurrentUser,
    session: Session,
    date_from: date | None = None,
    date_to: date | None = None,
) -> LedgerOut:
    """Shipments and payments in order with running balance (same data as the statement)."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, texts.DATE_RANGE)
    data = await statement_data(session, client_id, date_from, date_to)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, texts.CLIENT_NOT_FOUND)
    return LedgerOut(
        client_id=data.client_id,
        client_name=data.client_name,
        date_from=data.date_from,
        date_to=data.date_to,
        opening_balance=str(data.opening_balance),
        shipped=str(data.shipped_uzs),
        paid=str(data.paid_uzs),
        closing_balance=str(data.closing_balance),
        lines=[
            LedgerLineOut(
                date=line.date,
                kind="shipment" if line.is_shipment else "payment",
                trip_number=line.trip_number,
                product=line.product,
                heads=line.heads,
                net_kg=None if line.net_kg is None else str(line.net_kg),
                price_uzs_per_kg=None
                if line.price_uzs_per_kg is None
                else str(line.price_uzs_per_kg),
                amount_uzs=str(line.amount_uzs),
                payment_method=line.payment_method,
                note=line.note,
                running_balance=str(line.running_balance),
            )
            for line in data.lines
        ],
    )
