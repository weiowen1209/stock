import pytest
from httpx import ASGITransport, AsyncClient

from backend.database import init_db
from backend.main import app


@pytest.mark.asyncio
async def test_upload_report_document_includes_field_sources(tmp_path):
    await init_db()
    text = """
证券代码：688017
2025年度报告
合并利润表
项目 2025年度 2024年度 单位：元
营业收入 570,714,025.26 500,000,000.00
营业成本 360,091,140.11 300,000,000.00
归属于母公司股东的净利润 124,366,913.57 100,000,000.00
合并资产负债表
资产总计 3,929,127,498.81 3,000,000,000.00 单位：元
所有者权益合计 3,536,833,385.23 3,100,000,000.00 单位：元
合并现金流量表
经营活动产生的现金流量净额 152,003,651.27 120,000,000.00 单位：元
""".encode("utf-8")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/imports/documents/upload",
            files={"file": ("report.txt", text, "text/plain")},
            data={"code": "688017", "report_period": "2025年报"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]["preview"]
    assert payload["field_sources"]["revenue"]["value"] == "570714025.26"
    assert payload["field_sources"]["revenue"]["line"]
