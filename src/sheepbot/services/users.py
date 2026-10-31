from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.db.models import BotUser
from sheepbot.domain.enums import Perm, UserStatus


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> BotUser | None:
    return await session.scalar(select(BotUser).where(BotUser.telegram_id == telegram_id))


async def get_by_id(session: AsyncSession, user_id: int) -> BotUser | None:
    return await session.get(BotUser, user_id)


async def create_pending(
    session: AsyncSession, telegram_id: int, full_name: str, username: str | None
) -> BotUser:
    user = BotUser(
        telegram_id=telegram_id,
        full_name=full_name,
        username=username,
        is_admin=False,
        can_upload=False,
        can_view=False,
        status=UserStatus.PENDING,
    )
    session.add(user)
    await session.flush()
    return user


def sync_profile(user: BotUser, full_name: str, username: str | None) -> None:
    """Keep the stored Telegram name and username up to date."""
    if user.full_name != full_name:
        user.full_name = full_name
    if user.username != username:
        user.username = username


async def set_permissions(
    session: AsyncSession, user_id: int, can_upload: bool, can_view: bool
) -> BotUser:
    user = await session.get_one(BotUser, user_id)
    user.can_upload = can_upload
    user.can_view = can_view
    await session.flush()
    return user


async def set_status(session: AsyncSession, user_id: int, status: UserStatus) -> BotUser:
    user = await session.get_one(BotUser, user_id)
    user.status = status
    await session.flush()
    return user


async def list_users(session: AsyncSession) -> list[BotUser]:
    result = await session.scalars(select(BotUser).order_by(BotUser.full_name, BotUser.id))
    return list(result)


def has_permission(user: BotUser | None, perm: Perm) -> bool:
    if user is None:
        return False
    if user.is_admin:
        return True
    if user.status != UserStatus.ACTIVE:
        return False
    if perm is Perm.UPLOAD:
        return user.can_upload
    if perm is Perm.VIEW:
        return user.can_view
    return False


def is_allowed(user: BotUser | None) -> bool:
    """True if the user may use the bot at all (has at least one permission)."""
    return any(has_permission(user, perm) for perm in Perm)
