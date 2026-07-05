from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.schemas.common import ApiResponse, ResponseMeta
from backend.schemas.stock import IndustryGroup, StockRead
from backend.services import get_stock, group_stocks_by_industry, list_stocks


router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("", response_model=ApiResponse[list[StockRead]])
async def read_stocks(
    industry_chain: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[StockRead]]:
    stocks = await list_stocks(session, industry_chain=industry_chain, keyword=keyword)
    updated_at = max((stock.updated_at for stock in stocks), default=None)
    return ApiResponse(data=stocks, meta=ResponseMeta(updated_at=updated_at))


@router.get("/by-industry", response_model=ApiResponse[list[IndustryGroup]])
async def read_stocks_by_industry(
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[IndustryGroup]]:
    grouped = await group_stocks_by_industry(session)
    data = [IndustryGroup(industry_chain=key, stocks=value) for key, value in grouped.items()]
    updated_at = max((stock.updated_at for group in data for stock in group.stocks), default=None)
    return ApiResponse(data=data, meta=ResponseMeta(updated_at=updated_at))


@router.get("/{code}", response_model=ApiResponse[StockRead])
async def read_stock(code: str, session: AsyncSession = Depends(get_session)) -> ApiResponse[StockRead]:
    stock = await get_stock(session, code)
    if stock is None or not stock.is_active:
        raise HTTPException(status_code=404, detail="stock not found")
    return ApiResponse(data=stock, meta=ResponseMeta(updated_at=stock.updated_at))
