from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from sheepbot.api import texts
from sheepbot.api.auth import UploadUser
from sheepbot.api.deps import Session
from sheepbot.api.schemas import PaymentIn, PaymentOut, PaymentPageOut, PaymentResultOut
from sheepbot.db.models import Payment
from sheepbot.domain.enums import PAYMENT_METHOD_LABELS
from sheepbot.services import balances, clients, payments

router = APIRouter()


def _payment_out(payment: Payment, client_name: str, entered_by: str) -> PaymentOut:
    return PaymentOut(
        id=payment.id,
        client_id=payment.client_id,
        client_name=client_name,
        amount_uzs=str(payment.amount_uzs),
        method=payment.method.value,
        method_label=PAYMENT_METHOD_LABELS[payment.method],
        date=payment.date,
        note=payment.note,
        entered_by=entered_by,
        created_at=payment.created_at,
    )


@router.get("/payments")
async def list_payments(
    _: UploadUser,
    session: Session,
    client_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaymentPageOut:
    items, total = await payments.page_payments(session, client_id, offset, limit)
    return PaymentPageOut(
        items=[_payment_out(p, p.client.name, p.entered_by.full_name) for p in items],
        total=total,
    )


@router.post("/payments", status_code=status.HTTP_201_CREATED)
async def create_payment(body: PaymentIn, user: UploadUser, session: Session) -> PaymentResultOut:
    client = await clients.get_client(session, body.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, texts.CLIENT_NOT_FOUND)
    payment = await payments.create_payment(
        session, client.id, int(body.amount_uzs), body.method, body.date, body.note, user.id
    )
    result = PaymentResultOut(
        payment=_payment_out(payment, client.name, user.full_name),
        balance=str(await balances.client_balance(session, client.id)),
    )
    await session.commit()
    return result


@router.delete("/payments/{payment_id}")
async def delete_payment(payment_id: int, user: UploadUser, session: Session) -> PaymentResultOut:
    """Soft delete: the payment stays recorded with who deleted it and when."""
    payment = await payments.delete_payment(session, payment_id, user.id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, texts.PAYMENT_NOT_FOUND)
    result = PaymentResultOut(
        payment=_payment_out(payment, payment.client.name, payment.entered_by.full_name),
        balance=str(await balances.client_balance(session, payment.client_id)),
    )
    await session.commit()
    return result
