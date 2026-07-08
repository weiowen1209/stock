from fastapi import APIRouter, Body, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.concept_service import sync_coverage
from backend.database import get_session
from backend.models import KLineData, RealtimeQuote, Stock
from backend.schemas.common import ApiResponse, ResponseMeta
from backend.schemas.market import ProviderHealthRead, SyncProgress, SyncRequest, SyncResult, SyncStatus
from backend.sync.progress import progress_hub
from backend.sync_service import (
    default_stock_codes,
    latest_sync_logs,
    list_registered_provider_health,
    sync_kline,
    sync_quotes,
)


router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/trigger", response_model=ApiResponse[list[SyncResult]])
async def trigger_sync(
    request: SyncRequest = Body(default_factory=SyncRequest),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[SyncResult]]:
    codes = request.codes or await default_stock_codes(session)
    results: list[SyncResult] = []
    if request.include_quotes:
        results.append(await sync_quotes(session, codes))
    if request.include_kline:
        periods = request.periods or [request.period]
        for period in periods:
            results.append(await sync_kline(session, codes, period=period, start=request.start_date, end=request.end_date, force_full=request.force_full))
    return ApiResponse(data=results, meta=ResponseMeta())


@router.get("/status", response_model=ApiResponse[SyncStatus])
async def read_sync_status(session: AsyncSession = Depends(get_session)) -> ApiResponse[SyncStatus]:
    stock_codes = set((await session.execute(select(Stock.code).where(Stock.is_active.is_(True)))).scalars())
    quote_codes = set((await session.execute(select(RealtimeQuote.code))).scalars())
    kline_codes = set((await session.execute(select(KLineData.code).distinct())).scalars())
    logs = await latest_sync_logs(session)
    providers = await list_registered_provider_health(session)
    data = SyncStatus(
        latest_logs=[
            {
                "task_type": item.task_type,
                "status": item.status,
                "records_count": item.records_count,
                "detail": item.detail,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in logs
        ],
        missing_quotes=sorted(stock_codes - quote_codes),
        missing_kline=sorted(stock_codes - kline_codes),
        providers=[
            ProviderHealthRead(
                provider=item.provider,
                status=item.status,
                consecutive_failures=item.consecutive_failures,
                last_success_at=item.last_success_at.isoformat() if item.last_success_at else None,
                last_failure_at=item.last_failure_at.isoformat() if item.last_failure_at else None,
                next_probe_at=item.next_probe_at.isoformat() if item.next_probe_at else None,
                error_message=item.error_message,
            )
            for item in providers
        ],
        progress=SyncProgress(**progress_hub.latest),
        coverage=await sync_coverage(session),
    )
    return ApiResponse(data=data, meta=ResponseMeta(stale=bool(data.missing_quotes or data.missing_kline)))


@router.websocket("/progress")
async def sync_progress(websocket: WebSocket) -> None:
    await progress_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        progress_hub.disconnect(websocket)
