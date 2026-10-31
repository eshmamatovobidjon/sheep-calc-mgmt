from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.db.session import get_sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """One session per request; write endpoints must commit before returning."""
    async with get_sessionmaker()() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]
