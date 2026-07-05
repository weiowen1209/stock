import pytest
from httpx import ASGITransport, AsyncClient

from backend.database import AsyncSessionLocal, init_db
from backend.sync.progress import progress_hub
from backend.sync.scheduler import configure_scheduler
from backend.sync_service import list_provider_health, list_registered_provider_health, sync_quotes


class StaticProvider:
    name = "stage5_static"

    async def get_realtime_quote(self, code: str):
        from decimal import Decimal
        from backend.data_provider.base import QuoteData

        return QuoteData(code=code, price=Decimal("12.34"), source=self.name)

    async def get_kline(self, code: str, period: str = "day", start=None, end=None):
        return []


@pytest.mark.asyncio
async def test_sync_status_includes_progress_and_provider_health(monkeypatch):
    await init_db()
    import backend.sync_service as sync_service

    class TestRegistry:
        def chain_for(self, data_type: str):
            return [StaticProvider()]

    monkeypatch.setattr(sync_service, "registry", TestRegistry())
    async with AsyncSessionLocal() as session:
        await sync_quotes(session, ["688017"])
        providers = await list_provider_health(session)

    assert any(item.provider == "stage5_static" for item in providers)
    assert progress_hub.latest["stage"] == "quotes"


@pytest.mark.asyncio
async def test_registered_provider_health_filters_test_providers(monkeypatch):
    await init_db()
    import backend.sync_service as sync_service

    class TestRegistry:
        def registered_names(self):
            return ["sina", "eastmoney"]

    monkeypatch.setattr(sync_service, "registry", TestRegistry())
    async with AsyncSessionLocal() as session:
        providers = await list_registered_provider_health(session)

    provider_names = {item.provider for item in providers}
    assert provider_names == {"sina", "eastmoney"}


@pytest.mark.asyncio
async def test_sync_status_api_returns_stage5_fields():
    from backend.main import app

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/sync/status")

    payload = response.json()
    assert response.status_code == 200
    assert "providers" in payload["data"]
    assert "progress" in payload["data"]
    provider_names = {item["provider"] for item in payload["data"]["providers"]}
    assert not {"failing", "static", "stage5_static", "page_flow_static"} & provider_names


def test_scheduler_registers_expected_jobs():
    scheduler = configure_scheduler()
    job_ids = {job.id for job in scheduler.get_jobs()}
    assert {"realtime_quotes", "daily_kline", "provider_probe"}.issubset(job_ids)
