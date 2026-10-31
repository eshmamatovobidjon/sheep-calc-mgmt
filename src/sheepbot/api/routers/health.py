from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from sheepbot.api import texts
from sheepbot.api.deps import Session
from sheepbot.api.schemas import HealthOut

router = APIRouter()


@router.get("/health")
async def health(session: Session) -> HealthOut:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, texts.DB_UNAVAILABLE) from None
    return HealthOut(status="ok")
