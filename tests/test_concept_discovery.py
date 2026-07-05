from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_concept_discovery_sync_api_is_not_available():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/stocks/discover-concept-sync")

    assert response.status_code in {404, 405}


def test_frontend_contract_removes_concept_discovery_entry():
    root = Path(__file__).resolve().parent.parent
    panel = (root / "frontend" / "src" / "components" / "DataStatusPanel.vue").read_text(encoding="utf-8")
    store = (root / "frontend" / "src" / "stores" / "stockStore.ts").read_text(encoding="utf-8")
    api = (root / "frontend" / "src" / "api" / "index.ts").read_text(encoding="utf-8")

    assert "发现并同步全量概念股" not in panel
    assert "discoverSync" not in panel
    assert "discovering" not in store
    assert "discoverAndSyncConceptStocks" not in store
    assert "discoverConceptSync" not in api
    assert "DISCOVER_CONCEPT_SYNC_TIMEOUT_MS" not in api
    assert "getBaseDataStocks" in api
    assert "importBaseDataExcel" in api
