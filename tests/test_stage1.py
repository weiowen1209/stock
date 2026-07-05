import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from backend.database import AsyncSessionLocal, init_db
from backend.main import app
from backend.models import Base, Stock
from backend.services import seed_initial_stocks


@pytest.mark.asyncio
async def test_database_initializes_all_core_tables():
    await init_db()
    table_names = set(Base.metadata.tables.keys())
    assert {
        "stocks",
        "kline_data",
        "realtime_quotes",
        "financial_reports",
        "business_segments",
        "expense_items",
        "valuation_metrics",
        "industry_index",
        "import_batches",
        "provider_health",
        "sync_log",
    }.issubset(table_names)


@pytest.mark.asyncio
async def test_seed_initial_stocks_covers_required_industries():
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_initial_stocks(session)
        count = await session.scalar(select(func.count()).select_from(Stock))
        industries = await session.execute(select(Stock.industry_chain).distinct())

    assert count >= 20
    assert len(set(industries.scalars().all())) >= 6


@pytest.mark.asyncio
async def test_stock_api_uses_unified_response_shape():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/stocks")

    payload = response.json()
    assert response.status_code == 200
    assert set(payload.keys()) == {"data", "meta", "error"}
    assert payload["error"] is None
    assert len(payload["data"]) >= 1
    assert all(item["is_active"] is True for item in payload["data"])
    assert payload["meta"]["source"] == "sqlite"


@pytest.mark.asyncio
async def test_stock_api_can_group_by_industry():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/stocks/by-industry")

    payload = response.json()
    assert response.status_code == 200
    assert len(payload["data"]) >= 1
    assert all("industry_chain" in item and "stocks" in item for item in payload["data"])
    assert all(stock["is_active"] is True for item in payload["data"] for stock in item["stocks"])
