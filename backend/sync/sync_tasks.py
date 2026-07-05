from backend.database import AsyncSessionLocal
from backend.sync.progress import progress_hub
from backend.sync_service import default_stock_codes, sync_kline, sync_quotes


async def sync_realtime_quotes_task() -> None:
    async with AsyncSessionLocal() as session:
        codes = await default_stock_codes(session)
        await sync_quotes(session, codes)


async def sync_daily_kline_task() -> None:
    async with AsyncSessionLocal() as session:
        codes = await default_stock_codes(session)
        await sync_kline(session, codes, period="day")


async def provider_health_probe_task() -> None:
    await progress_hub.publish("probe", "Provider健康探测完成", percent=100)
