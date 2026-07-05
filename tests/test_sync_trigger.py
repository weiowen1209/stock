import pytest
from httpx import ASGITransport, AsyncClient


def test_sync_request_accepts_empty_json_defaults():
    from backend.schemas.market import SyncRequest

    request = SyncRequest.model_validate({})

    assert request.codes is None
    assert request.include_quotes is True
    assert request.include_kline is True
    assert request.period == "day"


@pytest.mark.asyncio
async def test_sync_trigger_without_body_uses_default_stock_pool():
    from backend.main import app

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/sync/trigger")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"data", "meta", "error"}
    assert isinstance(payload["data"], list)
