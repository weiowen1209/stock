from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.data_provider.base import KLineItem, ProviderError, QuoteData
from backend.data_provider.failover_manager import FailoverManager
from backend.data_provider.registry import ProviderRegistry
from backend.data_provider.sina_provider import SinaProvider, parse_sina_kline_payload, parse_sina_quote_payload
from backend.database import AsyncSessionLocal, init_db
from backend.main import app
from backend.models import KLineData, RealtimeQuote, SyncLog
from backend.sync_service import sync_kline, sync_quotes


class FailingProvider:
    name = "failing"

    async def get_realtime_quote(self, code: str) -> QuoteData:
        raise ProviderError("boom")

    async def get_kline(self, code: str, period: str = "day", start=None, end=None) -> list[KLineItem]:
        raise ProviderError("boom")


class StaticProvider:
    name = "static"

    async def get_realtime_quote(self, code: str) -> QuoteData:
        return QuoteData(
            code=code,
            price=Decimal("10.10"),
            change_pct=Decimal("1.20"),
            turnover_rate=Decimal("2.30"),
            source=self.name,
        )

    async def get_kline(self, code: str, period: str = "day", start=None, end=None) -> list[KLineItem]:
        return [
            KLineItem(
                code=code,
                period=period,
                date=date(2026, 7, 3),
                open=Decimal("10.00"),
                close=Decimal("10.10"),
                high=Decimal("10.20"),
                low=Decimal("9.90"),
                volume=100,
                turnover=Decimal("1000.00"),
                change_pct=Decimal("1.00"),
                source=self.name,
            )
        ]


def test_sina_provider_parses_quote_payload():
    payload = 'var hq_str_sz002049="紫光国微,65.620,65.360,65.260,66.220,64.920,0,0,123456,807654321.00,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-07-03,15:00:00,00";'

    quote = parse_sina_quote_payload("002049", payload)

    assert quote.code == "002049"
    assert quote.price == Decimal("65.260")
    assert quote.change_pct == Decimal("-0.15")
    assert quote.volume == 123456
    assert quote.turnover == Decimal("807654321.00")
    assert quote.source == "sina"


def test_sina_provider_parses_kline_payload():
    payload = 'var _=[{"day":"2026-07-03","open":"65.62","high":"66.22","low":"64.92","close":"65.26","volume":"123456"}]'

    rows = parse_sina_kline_payload("002049", "day", payload)

    assert len(rows) == 1
    assert rows[0].code == "002049"
    assert rows[0].date == date(2026, 7, 3)
    assert rows[0].close == Decimal("65.26")
    assert rows[0].source == "sina"


def test_provider_registry_prioritizes_stable_real_sources():
    registry = ProviderRegistry()

    assert registry.registered_names() == ["sina", "eastmoney"]
    assert [provider.name for provider in registry.chain_for("quote")] == ["sina", "eastmoney"]
    assert [provider.name for provider in registry.chain_for("kline")] == ["sina", "eastmoney"]
    assert isinstance(registry.chain_for("quote")[0], SinaProvider)



@pytest.mark.asyncio
async def test_failover_manager_switches_to_next_provider():
    await init_db()
    async with AsyncSessionLocal() as session:
        manager = FailoverManager([FailingProvider(), StaticProvider()])
        quote, provider_name = await manager.execute(
            session, lambda provider: provider.get_realtime_quote("688017")
        )

    assert provider_name == "static"
    assert quote.price == Decimal("10.10")


@pytest.mark.asyncio
async def test_sync_service_writes_quotes_and_kline(monkeypatch):
    await init_db()
    import backend.sync_service as sync_service

    class TestRegistry:
        def chain_for(self, data_type: str):
            return [StaticProvider()]

    monkeypatch.setattr(sync_service, "registry", TestRegistry())
    async with AsyncSessionLocal() as session:
        quote_result = await sync_quotes(session, ["688017"])
        kline_result = await sync_kline(session, ["688017"])
        quote = await session.get(RealtimeQuote, "688017")
        kline_rows = (await session.execute(select(KLineData).where(KLineData.code == "688017"))).scalars().all()
        logs = (await session.execute(select(SyncLog))).scalars().all()

    assert quote_result.records_count == 1
    assert kline_result.records_count == 1
    assert quote is not None
    assert len(kline_rows) >= 1
    assert len(logs) >= 2


@pytest.mark.asyncio
async def test_market_apis_return_unified_shape():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            quotes_response = await client.get("/api/quotes")
            kline_response = await client.get("/api/kline/688017")
            sync_status_response = await client.get("/api/sync/status")

    for response in [quotes_response, kline_response, sync_status_response]:
        assert response.status_code == 200
        assert set(response.json().keys()) == {"data", "meta", "error"}
