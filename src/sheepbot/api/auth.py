"""Telegram Mini App authentication: `Authorization: tma <initData>` on every request."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from aiogram.utils.web_app import safe_parse_webapp_init_data
from fastapi import Depends, HTTPException, Request, status

from sheepbot.api import texts
from sheepbot.api.deps import Session
from sheepbot.config import get_settings
from sheepbot.db.models import BotUser
from sheepbot.domain.enums import Perm
from sheepbot.services import users

AUTH_SCHEME = "tma"
MAX_INIT_DATA_LENGTH = 16 * 1024
CLOCK_SKEW = timedelta(minutes=5)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, {"WWW-Authenticate": AUTH_SCHEME})


def telegram_id_from_init_data(init_data: str) -> int:
    """Validate the signed launch data and return the Telegram user ID."""
    settings = get_settings()
    if len(init_data) > MAX_INIT_DATA_LENGTH:
        raise _unauthorized(texts.AUTH_INVALID)
    try:
        data = safe_parse_webapp_init_data(settings.bot_token, init_data)
    except Exception:
        raise _unauthorized(texts.AUTH_INVALID) from None
    if data.user is None:
        raise _unauthorized(texts.AUTH_INVALID)
    age = datetime.now(UTC) - data.auth_date
    if age > timedelta(hours=settings.webapp_auth_max_age_hours) or age < -CLOCK_SKEW:
        raise _unauthorized(texts.AUTH_EXPIRED)
    return data.user.id


def _request_telegram_id(request: Request) -> int:
    header = request.headers.get("Authorization")
    if header:
        scheme, _, value = header.partition(" ")
        if scheme.lower() != AUTH_SCHEME or not value.strip():
            raise _unauthorized(texts.AUTH_INVALID)
        return telegram_id_from_init_data(value.strip())
    settings = get_settings()
    if settings.dev_auth_enabled:
        assert settings.dev_auth_telegram_id is not None
        return settings.dev_auth_telegram_id
    raise _unauthorized(texts.AUTH_MISSING)


async def current_user(request: Request, session: Session) -> BotUser:
    """The approved user making the request; permissions are re-read from the DB every time."""
    user = await users.get_by_telegram_id(session, _request_telegram_id(request))
    if user is None or not users.is_allowed(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, texts.NO_ACCESS)
    return user


CurrentUser = Annotated[BotUser, Depends(current_user)]


def require(perm: Perm):
    """Dependency: the current user must have `perm` (admin passes every check)."""

    async def dependency(user: CurrentUser) -> BotUser:
        if not users.has_permission(user, perm):
            raise HTTPException(status.HTTP_403_FORBIDDEN, texts.FORBIDDEN)
        return user

    return dependency


UploadUser = Annotated[BotUser, Depends(require(Perm.UPLOAD))]
