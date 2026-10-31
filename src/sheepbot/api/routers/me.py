from enum import StrEnum

from fastapi import APIRouter
from sqlalchemy import select

from sheepbot.api.auth import CurrentUser
from sheepbot.api.deps import Session
from sheepbot.api.schemas import CatalogOut, MeOut, OptionOut, ProductOut
from sheepbot.db.models import Product
from sheepbot.domain.enums import (
    ANIMAL_TYPE_LABELS,
    CURRENCY_LABELS,
    PAYMENT_METHOD_LABELS,
    USER_STATUS_LABELS,
    Perm,
)
from sheepbot.services import users

router = APIRouter()


def _options[E: StrEnum](labels: dict[E, str]) -> list[OptionOut]:
    return [OptionOut(value=member.value, label=label) for member, label in labels.items()]


@router.get("/me")
async def me(user: CurrentUser) -> MeOut:
    return MeOut(
        id=user.id,
        telegram_id=user.telegram_id,
        full_name=user.full_name,
        username=user.username,
        status=user.status.value,
        status_label=USER_STATUS_LABELS[user.status],
        permissions=[perm.value for perm in Perm if users.has_permission(user, perm)],
    )


@router.get("/catalog")
async def catalog(_: CurrentUser, session: Session) -> CatalogOut:
    products = await session.scalars(select(Product).order_by(Product.id))
    return CatalogOut(
        products=[
            ProductOut(
                code=p.code,
                name=p.name,
                category=p.category.value,
                animal_type=p.animal_type.value if p.animal_type else None,
                discount_per_head=str(p.discount_per_head),
            )
            for p in products
        ],
        animal_types=_options(ANIMAL_TYPE_LABELS),
        currencies=_options(CURRENCY_LABELS),
        payment_methods=_options(PAYMENT_METHOD_LABELS),
    )
