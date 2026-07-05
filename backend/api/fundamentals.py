from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.analysis_service import (
    calculate_deep_fundamental_analysis,
    get_business_segments,
    get_expense_items,
    get_financial_reports,
)
from backend.database import get_session
from backend.schemas.analysis import BusinessSegmentRead, DeepFundamentalAnalysis, ExpenseItemRead, FinancialReportRead
from backend.schemas.common import ApiResponse, ResponseMeta


router = APIRouter(prefix="/api/fundamentals", tags=["fundamentals"])


@router.get("/{code}", response_model=ApiResponse[list[FinancialReportRead]])
async def read_financial_reports(
    code: str, session: AsyncSession = Depends(get_session)
) -> ApiResponse[list[FinancialReportRead]]:
    rows = await get_financial_reports(session, code)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(updated_at=updated_at, stale=not rows))


@router.get("/{code}/deep-analysis", response_model=ApiResponse[DeepFundamentalAnalysis])
async def read_deep_fundamental_analysis(
    code: str, session: AsyncSession = Depends(get_session)
) -> ApiResponse[DeepFundamentalAnalysis]:
    analysis = await calculate_deep_fundamental_analysis(session, code)
    return ApiResponse(data=analysis, meta=ResponseMeta(source="computed", stale=analysis.report_period is None))


@router.get("/{code}/segments", response_model=ApiResponse[list[BusinessSegmentRead]])
async def read_business_segments(
    code: str, session: AsyncSession = Depends(get_session)
) -> ApiResponse[list[BusinessSegmentRead]]:
    rows = await get_business_segments(session, code)
    source = rows[-1].source if rows else "sqlite"
    return ApiResponse(data=rows, meta=ResponseMeta(source=source or "sqlite", stale=not rows))


@router.get("/{code}/expenses", response_model=ApiResponse[list[ExpenseItemRead]])
async def read_expenses(
    code: str, session: AsyncSession = Depends(get_session)
) -> ApiResponse[list[ExpenseItemRead]]:
    rows = await get_expense_items(session, code)
    source = rows[-1].source if rows else "sqlite"
    return ApiResponse(data=rows, meta=ResponseMeta(source=source or "sqlite", stale=not rows))
