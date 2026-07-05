import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.database import AsyncSessionLocal, init_db
from backend.init_data.analysis_seed import seed_analysis_data
from backend.main import app
from backend.models import FinancialReport, ValuationMetric


@pytest.mark.asyncio
async def test_analysis_seed_creates_financial_and_valuation_data():
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_analysis_data(session)
        financial = (await session.execute(select(FinancialReport).where(FinancialReport.code == "688017"))).scalars().all()
        valuation = (await session.execute(select(ValuationMetric).where(ValuationMetric.code == "688017"))).scalars().all()

    assert len(financial) >= 3
    assert len(valuation) >= 6


@pytest.mark.asyncio
async def test_stage4_analysis_apis_return_unified_shape():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = [
                await client.get("/api/fundamentals/688017"),
                await client.get("/api/fundamentals/688017/segments"),
                await client.get("/api/fundamentals/688017/expenses"),
                await client.get("/api/valuation/688017"),
                await client.get("/api/fundamentals/688017/deep-analysis"),
                await client.get("/api/technical/688017"),
            ]

    for response in responses:
        assert response.status_code == 200
        assert set(response.json().keys()) == {"data", "meta", "error"}


@pytest.mark.asyncio
async def test_deep_fundamental_analysis_returns_growth_potential():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/fundamentals/688017/deep-analysis")

    payload = response.json()
    assert response.status_code == 200
    assert payload["data"]["code"] == "688017"
    assert "growth_potential_score" in payload["data"]
    assert payload["data"]["score_factors"]
    assert payload["data"]["score_factors"][0]["level"]
    assert payload["data"]["trend_breakdown"][-1]["signal"]
    assert "roe_estimated" in payload["data"]["dupont"][-1]
    assert "sample_size" in payload["data"]["valuation_percentiles"][0]
    assert payload["data"]["ai_insight"]["conclusion"]


@pytest.mark.asyncio
async def test_technical_api_calculates_indicators():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/technical/688017")

    payload = response.json()
    assert response.status_code == 200
    assert len(payload["data"]["dates"]) >= 1
    assert len(payload["data"]["ma5"]) == len(payload["data"]["dates"])
    assert len(payload["data"]["macd"]) == len(payload["data"]["dates"])
