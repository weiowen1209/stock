from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.analysis_service import get_valuation_metrics
from backend.database import get_session
from backend.schemas.analysis import ValuationRead
from backend.schemas.common import ApiResponse, ResponseMeta


router = APIRouter(prefix="/api/valuation", tags=["valuation"])


@router.get("/{code}", response_model=ApiResponse[list[ValuationRead]])
async def read_valuation(
    code: str, session: AsyncSession = Depends(get_session)
) -> ApiResponse[list[ValuationRead]]:
    rows = await get_valuation_metrics(session, code)
    source = rows[-1].source if rows else "sqlite"
    return ApiResponse(data=rows, meta=ResponseMeta(source=source or "sqlite", stale=not rows))
