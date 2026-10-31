from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.db.models import Client


class ClientExistsError(Exception):
    def __init__(self, client: Client) -> None:
        super().__init__(client.name)
        self.client = client


def normalize_client_name(name: str) -> str:
    """Matching key: trimmed, inner whitespace collapsed, casefolded, 'ё' -> 'е'."""
    return " ".join(name.split()).casefold().replace("ё", "е")


def _display_name(name: str) -> str:
    return " ".join(name.split())


async def _get_by_key(session: AsyncSession, name_key: str) -> Client | None:
    return await session.scalar(select(Client).where(Client.name_key == name_key))


async def get_or_create_client(
    session: AsyncSession, name: str, created_by_id: int | None
) -> Client:
    name_key = normalize_client_name(name)
    client = await _get_by_key(session, name_key)
    if client is None:
        client = Client(name=_display_name(name), name_key=name_key, created_by_id=created_by_id)
        session.add(client)
        await session.flush()
    return client


async def get_client(session: AsyncSession, client_id: int) -> Client | None:
    return await session.get(Client, client_id)


async def search_clients(session: AsyncSession, query: str, limit: int = 10) -> list[Client]:
    key = normalize_client_name(query)
    stmt = (
        select(Client)
        .where(Client.name_key.contains(key, autoescape=True))
        .order_by(Client.name_key)
        .limit(limit)
    )
    return list(await session.scalars(stmt))


async def list_clients(session: AsyncSession, offset: int, limit: int) -> list[Client]:
    stmt = select(Client).order_by(Client.name_key).offset(offset).limit(limit)
    return list(await session.scalars(stmt))


async def count_clients(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(Client)) or 0


async def create_client(session: AsyncSession, name: str, created_by_id: int | None) -> Client:
    """Raises ClientExistsError if a client with the same normalized name exists."""
    name_key = normalize_client_name(name)
    if (existing := await _get_by_key(session, name_key)) is not None:
        raise ClientExistsError(existing)
    client = Client(name=_display_name(name), name_key=name_key, created_by_id=created_by_id)
    session.add(client)
    await session.flush()
    return client


async def rename_client(session: AsyncSession, client_id: int, new_name: str) -> Client:
    """Raises ClientExistsError if another client already has this name."""
    client = await session.get_one(Client, client_id)
    name_key = normalize_client_name(new_name)
    existing = await _get_by_key(session, name_key)
    if existing is not None and existing.id != client.id:
        raise ClientExistsError(existing)
    client.name = _display_name(new_name)
    client.name_key = name_key
    await session.flush()
    return client


async def set_phone(session: AsyncSession, client_id: int, phone: str | None) -> Client:
    client = await session.get_one(Client, client_id)
    client.phone = " ".join(phone.split()) if phone and phone.strip() else None
    await session.flush()
    return client
