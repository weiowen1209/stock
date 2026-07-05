from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.models import RealtimeQuote
from backend.schemas.common import ApiResponse, ResponseMeta
from backend.schemas.market import QuoteRead


router = APIRouter(prefix="/api/quotes", tags=["quotes"])


@router.get("", response_model=ApiResponse[list[QuoteRead]])
async def read_quotes(
    codes: list[str] | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[QuoteRead]]:
    stmt = select(RealtimeQuote).order_by(RealtimeQuote.code)
    if codes:
        stmt = stmt.where(RealtimeQuote.code.in_(codes))
    result = await session.execute(stmt)
    quotes = list(result.scalars().all())
    updated_at = max((quote.updated_at for quote in quotes), default=None)
    return ApiResponse(data=quotes, meta=ResponseMeta(updated_at=updated_at, stale=not quotes))
