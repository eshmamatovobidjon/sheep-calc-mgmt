import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.config import get_settings
from sheepbot.db.models import BotUser, Product
from sheepbot.domain.catalog import PRODUCT_CATALOG
from sheepbot.domain.enums import UserStatus

logger = logging.getLogger(__name__)

ADMIN_DEFAULT_NAME = "Администратор"


async def _seed_products(session: AsyncSession) -> None:
    existing = {p.code: p for p in await session.scalars(select(Product))}
    for item in PRODUCT_CATALOG:
        product = existing.get(item.code)
        if product is None:
            product = Product(code=item.code)
            session.add(product)
        product.name = item.name
        product.category = item.category
        product.animal_type = item.animal_type
        product.discount_per_head = item.discount_per_head


async def _seed_admin(session: AsyncSession) -> None:
    telegram_id = get_settings().admin_telegram_id
    admin = await session.scalar(select(BotUser).where(BotUser.telegram_id == telegram_id))
    if admin is None:
        admin = BotUser(telegram_id=telegram_id, full_name=ADMIN_DEFAULT_NAME)
        session.add(admin)
    admin.is_admin = True
    admin.can_upload = True
    admin.can_view = True
    admin.status = UserStatus.ACTIVE


async def seed(session: AsyncSession) -> None:
    """Idempotent upsert of the product catalog and the admin user. Does not commit."""
    await _seed_products(session)
    await _seed_admin(session)
    await session.flush()
    logger.info(
        "Seed done: %d products, admin %s", len(PRODUCT_CATALOG), get_settings().admin_telegram_id
    )
