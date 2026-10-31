from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.db.models import Client


def normalize_client_name(name: str) -> str:
    """Matching key: trimmed, inner whitespace collapsed, casefolded, 'ё' -> 'е'."""
    return " ".join(name.split()).casefold().replace("ё", "е")


async def get_or_create_client(
    session: AsyncSession, name: str, created_by_id: int | None
) -> Client:
    name_key = normalize_client_name(name)
    client = await session.scalar(select(Client).where(Client.name_key == name_key))
    if client is None:
        client = Client(name=" ".join(name.split()), name_key=name_key, created_by_id=created_by_id)
        session.add(client)
        await session.flush()
    return client
