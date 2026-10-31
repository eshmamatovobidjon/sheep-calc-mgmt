import logging
from functools import lru_cache

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sheepbot.config import get_settings
from sheepbot.db import models  # noqa: F401  (registers all tables on Base.metadata)

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def init_db() -> None:
    """Create storage folders. The schema is managed by Alembic (`alembic upgrade head`)."""
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    url = make_url(settings.database_url)
    logger.info("Database: %s", url.render_as_string(hide_password=True))
