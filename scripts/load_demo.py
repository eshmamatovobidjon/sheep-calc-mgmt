"""Load the demo trips and fictional payments into an empty database.

Usage: python scripts/load_demo.py [--reset] [--yes]

Trips go through the same parser and save service as the bot. Refuses to run when trips
already exist unless --reset is given; --reset empties all business tables (users and
products stay) after confirmation.
"""

import argparse
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from sheepbot.config import get_settings
from sheepbot.db.models import BotUser, Client, Payment, Trip
from sheepbot.db.seed import seed
from sheepbot.db.session import get_engine, get_sessionmaker, init_db
from sheepbot.domain.enums import PaymentMethod
from sheepbot.excel.parser import parse_trip_workbook
from sheepbot.services import balances, payments, trips, users

DEMO_DIR = Path(__file__).resolve().parent.parent / "assets" / "demo"
DEMO_FILES = ("demo_trip_101.xlsx", "demo_trip_102.xlsx")
BUSINESS_TABLES = "payment, sale, purchase, expense, trip, upload, client"
METHODS = (PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.BANK)
OVERPAYMENT_UZS = 500_000
ROUND_UZS = 100_000


def _round_down(amount: int) -> int:
    return amount // ROUND_UZS * ROUND_UZS


def _confirm_reset(assume_yes: bool) -> bool:
    if assume_yes:
        return True
    url = get_settings().database_url.rsplit("@", 1)[-1]
    answer = input(f"Delete all trips, clients, uploads and payments in {url}? Type 'yes': ")
    return answer.strip() == "yes"


async def _load_trips(session: AsyncSession, admin: BotUser) -> None:
    for name in DEMO_FILES:
        data = (DEMO_DIR / name).read_bytes()
        upload = await trips.create_upload(session, name, data, admin)
        result = await asyncio.to_thread(parse_trip_workbook, data)
        if result.trip is None or result.errors:
            raise SystemExit(f"{name}: parse failed: {result.errors[:5]}")
        await trips.save_trip(session, result.trip, upload, admin)


def _payment_plan(index: int, debt: int, first: date, second: date) -> list[tuple[int, date]]:
    """Cycle through: paid in full (first client overpays), half, nothing, 30%, two halves."""
    pattern = index % 5
    if pattern == 0:
        return [(debt + (OVERPAYMENT_UZS if index == 0 else 0), first)]
    if pattern == 1:
        return [(_round_down(debt // 2), first)]
    if pattern == 3:
        return [(_round_down(debt * 3 // 10), first)]
    if pattern == 4:
        half = _round_down(debt // 2)
        return [(half, first), (debt - half, second)]
    return []


async def _load_payments(session: AsyncSession, admin: BotUser) -> None:
    today = date.today()
    count = 0
    for index, b in enumerate(await balances.all_balances(session)):
        if b.balance <= 0 or b.last_sale_date is None:
            continue
        first = min(b.last_sale_date + timedelta(days=7 + index % 5), today)
        second = min(first + timedelta(days=10), today)
        for amount, paid_on in _payment_plan(index, b.balance, first, second):
            if amount <= 0:
                continue
            method = METHODS[count % len(METHODS)]
            await payments.create_payment(
                session, b.client_id, amount, method, paid_on, "Демо", admin.id
            )
            count += 1


async def _summary(session: AsyncSession) -> str:
    all_balances = await balances.all_balances(session)
    trip_count = await session.scalar(select(func.count()).select_from(Trip))
    client_count = await session.scalar(select(func.count()).select_from(Client))
    payment_count = await session.scalar(select(func.count()).select_from(Payment))
    debt = sum(b.balance for b in all_balances if b.balance > 0)
    credit = -sum(b.balance for b in all_balances if b.balance < 0)
    return (
        f"Trips: {trip_count}, clients: {client_count}, payments: {payment_count}\n"
        f"Total debt: {debt:,} UZS, total credit: {credit:,} UZS"
    )


async def main(reset: bool, assume_yes: bool) -> int:
    await init_db()
    settings = get_settings()
    try:
        async with get_sessionmaker()() as session:
            has_trips = await session.scalar(select(func.count()).select_from(Trip))
            if has_trips and not reset:
                print("The database already has trips. Use --reset to replace all business data.")
                return 1
            if reset:
                if not _confirm_reset(assume_yes):
                    print("Cancelled.")
                    return 1
                await session.execute(text(f"TRUNCATE {BUSINESS_TABLES} RESTART IDENTITY CASCADE"))

            await seed(session)
            admin = await users.get_by_telegram_id(session, settings.admin_telegram_id)
            assert admin is not None
            await _load_trips(session, admin)
            await _load_payments(session, admin)
            await session.commit()
            print(await _summary(session))
    finally:
        await get_engine().dispose()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="empty business tables first")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.reset, args.yes)))
