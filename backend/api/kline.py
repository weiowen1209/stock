from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.models import KLineData
from backend.schemas.common import ApiResponse, ResponseMeta
from backend.schemas.market import KLineRead


router = APIRouter(prefix="/api/kline", tags=["kline"])


@router.get("/{code}", response_model=ApiResponse[list[KLineRead]])
async def read_kline(
    code: str,
    period: str = Query(default="day"),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[KLineRead]]:
    stmt = (
        select(KLineData)
        .where(KLineData.code == code, KLineData.period == period)
        .order_by(KLineData.date)
    )
    if start:
        stmt = stmt.where(KLineData.date >= start)
    if end:
        stmt = stmt.where(KLineData.date <= end)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(updated_at=updated_at, stale=not rows))
