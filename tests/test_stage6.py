import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.database import AsyncSessionLocal, init_db
from backend.import_service import confirm_import, create_manual_preview
from backend.models import FinancialReport
from backend.schemas.importing import ConfirmImportRequest, ManualFinancialInput


@pytest.mark.asyncio
async def test_manual_import_preview_and_confirm_writes_financial_data():
    await init_db()
    payload = ConfirmImportRequest(
        financial=ManualFinancialInput(
            code="688017",
            report_period="2025年报",
            report_date="2025-12-31",
            revenue="300000",
            net_profit="52000",
            gross_margin="36.5",
        ),
        segments=[],
        expenses=None,
    )
    async with AsyncSessionLocal() as session:
        preview = await create_manual_preview(session, payload)
        result = await confirm_import(session, preview.batch.id, payload)
        report = (
            await session.execute(
                select(FinancialReport).where(
                    FinancialReport.code == "688017",
                    FinancialReport.report_period == "2025年报",
                )
            )
        ).scalar_one_or_none()

    assert result.financial_records == 1
    assert report is not None
    assert report.import_id == preview.batch.id


@pytest.mark.asyncio
async def test_import_apis_return_unified_shape():
    from backend.main import app

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            manual_response = await client.post(
                "/api/imports/manual",
                json={
                    "financial": {
                        "code": "688017",
                        "report_period": "2026年报",
                        "report_date": "2026-12-31",
                        "revenue": "310000",
                        "gross_profit": None,
                        "gross_margin": "37.2",
                        "net_profit": "61000",
                        "operating_cash_flow": None,
                        "total_assets": None,
                        "net_assets": None,
                        "eps": None,
                        "roe": None,
                        "rd_ratio": None,
                    },
                    "segments": [],
                    "expenses": None,
                },
            )
            payload = manual_response.json()
            batch_id = payload["data"]["batch"]["id"]
            confirm_response = await client.post(
                f"/api/imports/{batch_id}/confirm",
                json={
                    "financial": payload["data"]["financial"],
                    "segments": payload["data"]["segments"],
                    "expenses": payload["data"]["expenses"],
                },
            )
            batches_response = await client.get("/api/imports")

    for response in [manual_response, confirm_response, batches_response]:
        assert response.status_code == 200
        assert set(response.json().keys()) == {"data", "meta", "error"}


@pytest.mark.asyncio
async def test_upload_import_parses_text_like_pdf():
    from backend.main import app

    content = "证券代码:688017 2027年报 营业收入:420000 净利润:72000 毛利率:38.5 ROE:16.2"
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/imports/upload",
                files={"file": ("report.txt", content.encode("utf-8"), "text/plain")},
            )

    payload = response.json()
    assert response.status_code == 200
    assert payload["data"]["financial"]["code"] == "688017"
    assert payload["data"]["financial"]["report_period"] == "2027年报"
    assert payload["data"]["financial"]["net_profit"] == "72000"
