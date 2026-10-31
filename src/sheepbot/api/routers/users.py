from fastapi import APIRouter, HTTPException, status

from sheepbot.api import texts
from sheepbot.api.auth import AdminUser
from sheepbot.api.deps import Session
from sheepbot.api.schemas import UserOut, UserUpdateIn
from sheepbot.api.telegram import get_bot
from sheepbot.bot.handlers.users import notify_closed, notify_granted
from sheepbot.db.models import BotUser
from sheepbot.domain.enums import USER_STATUS_LABELS, UserStatus
from sheepbot.services import users

router = APIRouter()

STATUS_ORDER = (UserStatus.PENDING, UserStatus.ACTIVE, UserStatus.BLOCKED)


def _user_out(user: BotUser) -> UserOut:
    return UserOut(
        id=user.id,
        telegram_id=user.telegram_id,
        full_name=user.full_name,
        username=user.username,
        status=user.status.value,
        status_label=USER_STATUS_LABELS[user.status],
        can_upload=user.can_upload,
        can_view=user.can_view,
    )


@router.get("/users")
async def list_users(_: AdminUser, session: Session) -> list[UserOut]:
    """Everyone except the configured admin, pending requests first."""
    managed = [u for u in await users.list_users(session) if not u.is_admin]
    managed.sort(key=lambda u: STATUS_ORDER.index(u.status))
    return [_user_out(u) for u in managed]


@router.patch("/users/{user_id}")
async def update_user(user_id: int, body: UserUpdateIn, _: AdminUser, session: Session) -> UserOut:
    """Same transitions as the bot's /users: granting a permission approves a pending request;
    blocking a pending user rejects it."""
    target = await users.get_by_id(session, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, texts.USER_NOT_FOUND)
    if target.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, texts.CANNOT_CHANGE_ADMIN)

    was_pending = target.status == UserStatus.PENDING
    if body.can_upload is not None or body.can_view is not None:
        await users.set_permissions(
            session,
            target.id,
            can_upload=target.can_upload if body.can_upload is None else body.can_upload,
            can_view=target.can_view if body.can_view is None else body.can_view,
        )
    if body.status is UserStatus.BLOCKED and was_pending:
        await users.set_permissions(session, target.id, can_upload=False, can_view=False)
    if body.status is not None:
        await users.set_status(session, target.id, body.status)
    elif was_pending and (target.can_upload or target.can_view):
        await users.set_status(session, target.id, UserStatus.ACTIVE)

    await session.commit()

    # Notifications only after commit; a failed message never undoes the change.
    if (
        was_pending
        and target.status == UserStatus.ACTIVE
        and (target.can_upload or target.can_view)
    ):
        await notify_granted(get_bot(), target)
    elif was_pending and target.status == UserStatus.BLOCKED:
        await notify_closed(get_bot(), target)
    return _user_out(target)
