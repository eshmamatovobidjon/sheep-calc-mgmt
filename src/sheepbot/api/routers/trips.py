from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from sheepbot.api import texts
from sheepbot.api.auth import CurrentUser
from sheepbot.api.deps import Session
from sheepbot.api.schemas import (
    TripClientRowOut,
    TripEconomicsRowOut,
    TripListItemOut,
    TripPageOut,
    TripProductRowOut,
    TripPurchaseRowOut,
    TripSummaryOut,
)
from sheepbot.reports.data import PurchaseTypeRow, trip_summary_data
from sheepbot.services import trips

router = APIRouter()


def _opt(value: object | None) -> str | None:
    return None if value is None else str(value)


@router.get("/trips")
async def list_trips(
    _: CurrentUser,
    session: Session,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TripPageOut:
    items = await trips.list_recent_trips(session, limit, offset)
    return TripPageOut(
        items=[
            TripListItemOut(
                number=t.number,
                departure_date=t.departure_date,
                purchased_heads=t.totals.purchases.heads,
                revenue=str(t.totals.revenue_uzs),
                cost=str(t.totals.cost_uzs),
                profit=str(t.totals.profit_uzs),
                margin_pct=_opt(t.totals.margin_pct),
            )
            for t in items
        ],
        total=await trips.count_trips(session),
    )


def _purchase_out(row: PurchaseTypeRow) -> TripPurchaseRowOut:
    return TripPurchaseRowOut(
        type_label=row.type_label,
        heads=row.heads,
        net_kg=str(row.net_kg),
        amount_kzt=str(row.amount_kzt),
        amount_uzs=str(row.amount_uzs),
    )


@router.get("/trips/{number}")
async def get_trip(number: int, _: CurrentUser, session: Session) -> TripSummaryOut:
    """Same figures as the upload preview and the trip summary report."""
    trip_id = await trips.trip_id_by_number(session, number)
    data = await trip_summary_data(session, trip_id) if trip_id is not None else None
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, texts.TRIP_NOT_FOUND)
    return TripSummaryOut(
        number=data.number,
        departure_date=data.departure_date,
        arrival_date=data.arrival_date,
        rate_kzt=str(data.rate_kzt),
        rate_usd=str(data.rate_usd),
        note=data.note,
        purchases=[_purchase_out(row) for row in data.purchases_by_type],
        purchase_total=_purchase_out(data.purchase_totals),
        expenses_uzs=str(data.expenses_uzs),
        sales_by_product=[
            TripProductRowOut(
                product_name=row.product_name,
                heads=row.heads,
                net_kg=str(row.net_kg),
                avg_price_uzs=str(row.avg_price_uzs),
                amount_uzs=str(row.amount_uzs),
            )
            for row in data.sales_by_product
        ],
        sales_by_client=[
            TripClientRowOut(
                client_name=row.client_name,
                heads=row.heads,
                net_kg=str(row.net_kg),
                amount_uzs=str(row.amount_uzs),
            )
            for row in data.sales_by_client
        ],
        economics=[
            TripEconomicsRowOut(
                type_label=row.type_label,
                purchased_heads=row.purchased_heads,
                sold_heads=row.sold_heads,
                cost_per_kg=_opt(row.cost_per_kg),
                avg_sale_price=_opt(row.avg_sale_price),
                diff_per_kg=_opt(row.diff_per_kg),
            )
            for row in data.type_economics
        ],
        revenue=str(data.revenue_uzs),
        cost=str(data.cost_uzs),
        profit=str(data.profit_uzs),
        margin_pct=_opt(data.margin_pct),
    )
