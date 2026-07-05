from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.analysis_service import calculate_technical_indicators
from backend.database import get_session
from backend.schemas.analysis import TechnicalIndicators
from backend.schemas.common import ApiResponse, ResponseMeta


router = APIRouter(prefix="/api/technical", tags=["technical"])


@router.get("/{code}", response_model=ApiResponse[TechnicalIndicators])
async def read_technical(
    code: str,
    period: str = Query(default="day"),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[TechnicalIndicators]:
    data = await calculate_technical_indicators(session, code, period=period)
    return ApiResponse(data=data, meta=ResponseMeta(stale=not data.dates))
