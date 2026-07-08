from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.data_provider.base import KLineItem, QuoteData
from backend.main import app


ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC = ROOT / "frontend" / "src"


class PageFlowStaticProvider:
    name = "page_flow_static"

    async def get_realtime_quote(self, code: str) -> QuoteData:
        return QuoteData(
            code=code,
            price=Decimal("21.88"),
            change_pct=Decimal("2.34"),
            turnover_rate=Decimal("3.21"),
            volume=123456,
            turnover=Decimal("2700000.00"),
            market_cap=Decimal("12000000000.00"),
            source=self.name,
        )

    async def get_kline(self, code: str, period: str = "day", start=None, end=None) -> list[KLineItem]:
        return [
            KLineItem(
                code=code,
                period=period,
                date=date(2030, 1, 2),
                open=Decimal("20.00"),
                close=Decimal("21.88"),
                high=Decimal("22.10"),
                low=Decimal("19.90"),
                volume=123456,
                turnover=Decimal("2700000.00"),
                change_pct=Decimal("2.34"),
                source=self.name,
            )
        ]


class PageFlowRegistry:
    def chain_for(self, data_type: str):
        return [PageFlowStaticProvider()]

    def registered_names(self):
        return ["page_flow_static"]


def read_frontend(relative_path: str) -> str:
    return (FRONTEND_SRC / relative_path).read_text(encoding="utf-8")


def assert_unified_response(payload: dict) -> None:
    assert set(payload.keys()) == {"data", "meta", "error"}


@pytest.mark.asyncio
async def test_tc01_homepage_initialization_and_global_status_contract():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            stocks_response = await client.get("/api/stocks")
            groups_response = await client.get("/api/stocks/by-industry")
            quotes_response = await client.get("/api/quotes")
            status_response = await client.get("/api/sync/status")

    for response in [stocks_response, groups_response, quotes_response, status_response]:
        assert response.status_code == 200
        assert_unified_response(response.json())

    stocks_payload = stocks_response.json()
    groups_payload = groups_response.json()
    status_payload = status_response.json()
    assert len(stocks_payload["data"]) >= 1
    assert len(groups_payload["data"]) >= 1
    assert all(item["is_active"] is True for item in stocks_payload["data"])
    assert {"missing_quotes", "missing_kline", "providers", "progress"}.issubset(status_payload["data"].keys())

    app_vue = read_frontend("App.vue")
    for phrase in [
        "机器人产业分析仪表板",
        "DataStatusPanel",
        "股票池",
        "产业链总览",
        "基本面深度分析",
        "技术面分析",
        "个股深度档案",
        "导入财报",
    ]:
        assert phrase in app_vue
    status_panel = read_frontend("components/DataStatusPanel.vue")
    assert "同步全部股票池" in status_panel
    assert "发现并同步全量概念股" not in status_panel
    assert "股票数据状态" in status_panel
    assert "同步当前股票" not in app_vue


@pytest.mark.asyncio
async def test_tc02_sync_current_stock_writes_quotes_kline_logs_and_refresh_contract(monkeypatch):
    import backend.sync_service as sync_service

    monkeypatch.setattr(sync_service, "registry", PageFlowRegistry())
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            sync_response = await client.post(
                "/api/sync/trigger",
                json={"codes": ["688017"], "include_quotes": True, "include_kline": True, "period": "day"},
            )
            quotes_response = await client.get("/api/quotes", params={"codes": "688017"})
            kline_response = await client.get("/api/kline/688017")
            status_response = await client.get("/api/sync/status")

    assert sync_response.status_code == 200
    sync_payload = sync_response.json()
    assert_unified_response(sync_payload)
    task_types = {item["task_type"] for item in sync_payload["data"]}
    assert "realtime" in task_types
    assert any(item.startswith("kline") for item in task_types)
    assert all(item["status"] in {"success", "fallback"} for item in sync_payload["data"])

    quotes_payload = quotes_response.json()
    kline_payload = kline_response.json()
    status_payload = status_response.json()
    assert any(item["code"] == "688017" for item in quotes_payload["data"])
    assert any(item["code"] == "688017" for item in kline_payload["data"])
    assert {"latest_logs", "progress"}.issubset(status_payload["data"].keys())
    assert status_payload["data"]["progress"]["stage"] in {"quotes", "kline", "kline_day", "done"}

    store_ts = read_frontend("stores/stockStore.ts")
    for phrase in ["syncStockByCode", "api.triggerSync([code], undefined, forceFull)", "api.getQuotes", "api.getSyncStatus", "loadStockAnalysis(currentCode.value)"]:
        assert phrase in store_ts


@pytest.mark.asyncio
async def test_tc03_industry_overview_filter_selection_and_table_contract():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            groups_response = await client.get("/api/stocks/by-industry")

    assert groups_response.status_code == 200
    payload = groups_response.json()
    assert_unified_response(payload)
    groups = payload["data"]
    assert all({"industry_chain", "stocks"}.issubset(group.keys()) for group in groups)
    for group in groups:
        assert all(stock["industry_chain"] == group["industry_chain"] for stock in group["stocks"])
    assert len(groups) >= 1
    assert all(stock["is_active"] is True for group in groups for stock in group["stocks"])

    overview_vue = read_frontend("views/IndustryOverview.vue")
    stock_table_vue = read_frontend("components/StockTable.vue")
    for phrase in ["产业链雷达", "一级分类", "二级分类", "三级分类", "股票列表", "StockTable"]:
        assert phrase in overview_vue
    for phrase in ["代码", "名称", "产业链", "细分定位", "涨跌幅", "最新价", "@row-click", "emit('select', row.code)"]:
        assert phrase in stock_table_vue


@pytest.mark.asyncio
async def test_tc04_fundamental_analysis_data_and_view_contract():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = [
                await client.get("/api/fundamentals/688017"),
                await client.get("/api/fundamentals/688017/segments"),
                await client.get("/api/fundamentals/688017/expenses"),
                await client.get("/api/valuation/688017"),
            ]

    for response in responses:
        assert response.status_code == 200
        assert_unified_response(response.json())
    assert len(responses[0].json()["data"]) >= 1
    assert len(responses[3].json()["data"]) >= 1

    fundamental_vue = read_frontend("views/Fundamental.vue")
    for phrase in ["增长潜力", "财务质量", "估值性价比", "基本面分析八模块", "业务贡献拆解", "收入", "毛利率", "市场定位与估值分位"]:
        assert phrase in fundamental_vue


@pytest.mark.asyncio
async def test_tc05_technical_analysis_indicator_and_view_contract(monkeypatch):
    import backend.sync_service as sync_service

    monkeypatch.setattr(sync_service, "registry", PageFlowRegistry())
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/sync/trigger",
                json={"codes": ["688017"], "include_quotes": True, "include_kline": True, "period": "day"},
            )
            technical_response = await client.get("/api/technical/688017")

    assert technical_response.status_code == 200
    payload = technical_response.json()
    assert_unified_response(payload)
    data = payload["data"]
    expected_keys = {"dates", "close", "ma5", "ma10", "ma20", "macd", "signal", "histogram", "rsi6"}
    assert expected_keys.issubset(data.keys())
    if data["dates"]:
        for key in ["close", "ma5", "ma10", "ma20", "macd", "signal", "histogram", "rsi6"]:
            assert len(data[key]) == len(data["dates"])

    technical_vue = read_frontend("views/Technical.vue")
    for phrase in ["KLineChart", "技术走势", "MACD", "RSI6", "filteredTechnicalSeries"]:
        assert phrase in technical_vue


@pytest.mark.asyncio
async def test_tc06_stock_detail_profile_quote_and_kline_contract():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            stocks_response = await client.get("/api/stocks")

    assert stocks_response.status_code == 200
    stock = stocks_response.json()["data"][0]
    assert stock["is_active"] is True
    assert stock["code"]
    assert stock["industry_chain"]
    assert stock["industry_chain_detail"]

    detail_vue = read_frontend("views/StockDetail.vue")
    for phrase in ["个股档案", "最新价", "换手率", "成交额", "总市值", "KLineChart", "supply_chain_tags", "JSON.parse"]:
        assert phrase in detail_vue


@pytest.mark.asyncio
async def test_tc07_import_workbench_upload_preview_and_batch_contract():
    content = "证券代码:688017 2031年报 营业收入:420000 净利润:72000 毛利率:38.5 ROE:16.2"
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            upload_response = await client.post(
                "/api/imports/upload",
                files={"file": ("page-flow-report.txt", content.encode("utf-8"), "text/plain")},
            )
            batches_response = await client.get("/api/imports")

    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    assert_unified_response(upload_payload)
    preview = upload_payload["data"]
    assert {"batch", "financial", "segments", "expenses", "warnings", "confidence"}.issubset(preview.keys())
    assert preview["financial"]["code"] == "688017"
    assert preview["financial"]["report_period"] == "2031年报"
    assert any(item["id"] == preview["batch"]["id"] for item in batches_response.json()["data"])

    import_vue = read_frontend("views/ImportWorkbench.vue")
    for phrase in ["请先选择 PDF 文件", "上传完成", "api.uploadReportDocument", "loadDocuments", "loadPreview"]:
        assert phrase in import_vue


@pytest.mark.asyncio
async def test_tc08_manual_import_preview_confirm_and_fundamental_refresh_contract():
    payload = {
        "financial": {
            "code": "688017",
            "report_period": "2030年报",
            "report_date": "2030-12-31",
            "revenue": "520000",
            "gross_profit": None,
            "gross_margin": "39.2",
            "net_profit": "83000",
            "operating_cash_flow": None,
            "total_assets": None,
            "net_assets": None,
            "eps": None,
            "roe": "17.5",
            "rd_ratio": "12.3",
        },
        "segments": [],
        "expenses": None,
    }
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            manual_response = await client.post("/api/imports/manual", json=payload)
            preview = manual_response.json()["data"]
            confirm_response = await client.post(
                f"/api/imports/{preview['batch']['id']}/confirm",
                json={
                    "financial": preview["financial"],
                    "segments": preview["segments"],
                    "expenses": preview["expenses"],
                },
            )
            fundamentals_response = await client.get("/api/fundamentals/688017")
            batches_response = await client.get("/api/imports")

    assert manual_response.status_code == 200
    assert manual_response.json()["meta"]["source"] == "manual"
    assert confirm_response.status_code == 200
    assert confirm_response.json()["data"]["financial_records"] == 1
    assert any(item["report_period"] == "2030年报" for item in fundamentals_response.json()["data"])
    batch = next(item for item in batches_response.json()["data"] if item["id"] == preview["batch"]["id"])
    assert batch["status"] in {"confirmed", "success"}

    import_vue = read_frontend("views/ImportWorkbench.vue")
    for phrase in ["api.confirmImport", "确认导入完成", "生成手工预览", "核心指标补录"]:
        assert phrase in import_vue
    assert "api.createManualImport" not in import_vue


@pytest.mark.asyncio
async def test_tc09_report_documents_table_contract():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            documents_response = await client.get("/api/imports/documents")

    assert documents_response.status_code == 200
    assert_unified_response(documents_response.json())

    import_vue = read_frontend("views/ImportWorkbench.vue")
    for phrase in ["文档资产库", "loadDocuments", "全部文档", "最近上传", "报告期", "状态", "更新时间", "查看预览"]:
        assert phrase in import_vue
    assert "loadBatches" not in import_vue


@pytest.mark.asyncio
async def test_tc10_empty_data_and_error_fallback_contract():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            fundamentals_response = await client.get("/api/fundamentals/NO_SUCH_CODE")
            technical_response = await client.get("/api/technical/NO_SUCH_CODE")

    assert fundamentals_response.status_code == 200
    assert_unified_response(fundamentals_response.json())
    assert fundamentals_response.json()["data"] == []
    assert fundamentals_response.json()["meta"]["stale"] is True
    assert technical_response.status_code == 200
    assert_unified_response(technical_response.json())
    assert technical_response.json()["data"]["dates"] == []
    assert technical_response.json()["meta"]["stale"] is True

    store_ts = read_frontend("stores/stockStore.ts")
    import_vue = read_frontend("views/ImportWorkbench.vue")
    for phrase in ["catch (err)", "error.value", "kline.value = []", "technical.value = null"]:
        assert phrase in store_ts
    for phrase in ["PDF 上传失败", "确认导入失败", "文档资产库加载失败", "解析预览加载失败"]:
        assert phrase in import_vue
