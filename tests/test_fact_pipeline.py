import json
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.database import AsyncSessionLocal, init_db
from backend.fact_service import create_candidate_facts_for_import, list_candidate_facts, list_evidence_items
from backend.main import app
from backend.models import CandidateFact, ConfirmedFact
from backend.models import ImportBatch
from backend.schemas.importing import EvidenceItemRead, ManualFinancialInput, SegmentInput


@pytest.mark.asyncio
async def test_init_db_creates_fact_pipeline_tables():
    await init_db()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name IN ('evidence_items', 'candidate_facts', 'confirmed_facts')
                """
            )
        )

    assert {row[0] for row in result.fetchall()} == {
        "evidence_items",
        "candidate_facts",
        "confirmed_facts",
    }


@pytest.mark.asyncio
async def test_candidate_fact_defaults_missing_dimensions_to_empty_strings():
    await init_db()

    async with AsyncSessionLocal() as session:
        candidate = CandidateFact(
            batch_id=900001,
            code="TST001",
            period="2025",
            fact_type="financial",
            metric_name="Revenue",
            metric_key="revenue",
            source_type="test",
        )
        session.add(candidate)
        await session.flush()

        assert candidate.dimension == ""
        assert candidate.dimension_value == ""

        await session.rollback()


@pytest.mark.asyncio
async def test_confirmed_fact_rejects_duplicate_identity():
    await init_db()

    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM confirmed_facts WHERE code = 'TSTUQ1'"))
        await session.commit()

        first = _confirmed_fact()
        session.add(first)
        await session.flush()

        session.add(_confirmed_fact())
        with pytest.raises(IntegrityError):
            await session.flush()

        await session.rollback()


def test_evidence_item_read_source_date_is_date():
    from datetime import date, datetime

    source_date = date(2026, 7, 9)
    item = EvidenceItemRead.model_validate(
        {
            "id": 1,
            "source_type": "pdf",
            "source_date": source_date,
            "collected_at": datetime(2026, 7, 9, 10, 0, 0),
            "topic": "financial",
            "snippet": "Revenue was disclosed in the annual report.",
            "trust_level": "A",
            "review_status": "pending",
            "created_at": datetime(2026, 7, 9, 10, 0, 0),
            "updated_at": datetime(2026, 7, 9, 10, 0, 0),
        }
    )

    assert type(item.source_date) is date
    assert item.source_date == source_date


def test_candidate_fact_batch_id_has_single_explicit_index():
    batch_indexes = {
        index.name
        for index in CandidateFact.__table__.indexes
        if {column.name for column in index.columns} == {"batch_id"}
    }

    assert batch_indexes == {"idx_candidate_batch"}


@pytest.mark.asyncio
async def test_create_candidate_facts_for_import_links_evidence():
    await init_db()

    async with AsyncSessionLocal() as session:
        batch = ImportBatch(
            import_type="pdf",
            file_name="report.txt",
            code="688017",
            report_period="2025年报",
            status="parsed",
            document_id=11,
            parse_job_id=22,
        )
        session.add(batch)
        await session.flush()

        created_count = await create_candidate_facts_for_import(
            session=session,
            batch=batch,
            financial=ManualFinancialInput(
                code="688017",
                report_period="2025年报",
                revenue=Decimal("570714025.26"),
            ),
            segments=[],
            expenses=None,
            extractions=None,
            field_sources={
                "revenue": {
                    "value": "570714025.26",
                    "label": "营业收入",
                    "section": "income",
                    "confidence": "0.90",
                    "unit": "元",
                    "line": "营业收入 570,714,025.26",
                }
            },
            confidence=Decimal("0.90"),
            parser_version="financial-table-v1",
        )
        await session.commit()
        facts = await list_candidate_facts(session, batch_id=batch.id)
        evidence = await list_evidence_items(session, batch_id=batch.id)

    assert created_count == 1
    assert len(facts) == 1
    assert facts[0].metric_key == "revenue"
    assert facts[0].metric_name == "营业收入"
    assert facts[0].fact_type == "financial"
    assert facts[0].metric_value == Decimal("570714025.2600")
    assert facts[0].metric_unit == "元"
    assert facts[0].source_type == "annual_report"
    assert facts[0].period_type == "annual"
    assert facts[0].trust_level == "A"
    assert facts[0].dimension == ""
    assert facts[0].dimension_value == ""
    assert facts[0].evidence_id is not None
    assert json.loads(facts[0].evidence_ids_json) == [facts[0].evidence_id]
    assert [item.id for item in evidence] == [facts[0].evidence_id]


@pytest.mark.asyncio
async def test_segment_candidate_facts_keep_dimensions_distinct():
    await init_db()

    async with AsyncSessionLocal() as session:
        batch = ImportBatch(
            import_type="pdf",
            file_name="report.txt",
            code="688017",
            report_period="2025年报",
            status="parsed",
        )
        session.add(batch)
        await session.flush()

        created_count = await create_candidate_facts_for_import(
            session=session,
            batch=batch,
            financial=ManualFinancialInput(code="688017", report_period="2025年报"),
            segments=[
                SegmentInput(segment_type="product", segment_name="谐波减速器", revenue=Decimal("100.00")),
                SegmentInput(segment_type="product", segment_name="机电一体化产品", revenue=Decimal("200.00")),
            ],
            expenses=None,
            extractions=None,
            field_sources={},
            confidence=Decimal("0.80"),
            parser_version="financial-table-v1",
        )
        await session.commit()
        facts = await list_candidate_facts(session, batch_id=batch.id)
        evidence = await list_evidence_items(session, batch_id=batch.id)

    assert created_count == 2
    assert [fact.metric_key for fact in facts] == ["segment_revenue", "segment_revenue"]
    assert {fact.dimension for fact in facts} == {"product"}
    assert {fact.dimension_value for fact in facts} == {"谐波减速器", "机电一体化产品"}
    assert {item.snippet for item in evidence} == {
        "分部收入[product=谐波减速器]: 100.00",
        "分部收入[product=机电一体化产品]: 200.00",
    }


@pytest.mark.asyncio
async def test_create_candidate_facts_for_import_replaces_pending_candidates_and_evidence():
    await init_db()

    async with AsyncSessionLocal() as session:
        batch = ImportBatch(
            import_type="pdf",
            file_name="report.txt",
            code="688017",
            report_period="2025年报",
            status="parsed",
        )
        session.add(batch)
        await session.flush()

        first_count = await create_candidate_facts_for_import(
            session=session,
            batch=batch,
            financial=ManualFinancialInput(
                code="688017",
                report_period="2025年报",
                revenue=Decimal("100.00"),
            ),
            segments=[],
            expenses=None,
            extractions=None,
            field_sources={
                "revenue": {
                    "line": "第一次 营业收入 100.00",
                }
            },
            confidence=Decimal("0.80"),
            parser_version="financial-table-v1",
        )
        first_facts = await list_candidate_facts(session, batch_id=batch.id)
        first_evidence = await list_evidence_items(session, batch_id=batch.id)

        second_count = await create_candidate_facts_for_import(
            session=session,
            batch=batch,
            financial=ManualFinancialInput(
                code="688017",
                report_period="2025年报",
                revenue=Decimal("200.00"),
            ),
            segments=[],
            expenses=None,
            extractions=None,
            field_sources={
                "revenue": {
                    "line": "第二次 营业收入 200.00",
                }
            },
            confidence=Decimal("0.90"),
            parser_version="financial-table-v1",
        )
        await session.commit()
        facts = await list_candidate_facts(session, batch_id=batch.id)
        evidence = await list_evidence_items(session, batch_id=batch.id)

    assert first_count == 1
    assert len(first_facts) == 1
    assert len(first_evidence) == 1
    assert second_count == 1
    assert len(facts) == 1
    assert len(evidence) == 1
    assert facts[0].metric_value == Decimal("200.0000")
    assert facts[0].evidence_id == evidence[0].id
    assert json.loads(facts[0].evidence_ids_json) == [evidence[0].id]
    assert evidence[0].snippet == "第二次 营业收入 200.00"


@pytest.mark.asyncio
async def test_upload_preview_returns_candidate_facts_and_list_endpoint():
    await init_db()
    text = """
证券代码：688017
2025年度报告
合并利润表
项目 2025年度 2024年度 单位：元
营业收入 570,714,025.26 500,000,000.00
归属于母公司股东的净利润 124,366,913.57 100,000,000.00
""".encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        upload = await client.post(
            "/api/imports/documents/upload",
            files={"file": ("report.txt", text, "text/plain")},
            data={"code": "688017", "report_period": "2025年报"},
        )
        assert upload.status_code == 200
        preview = upload.json()["data"]["preview"]
        batch_id = preview["batch"]["id"]

        listed = await client.get(f"/api/imports/candidate-facts?batch_id={batch_id}")
        evidence = await client.get(f"/api/imports/evidence?batch_id={batch_id}")

    assert any(item["metric_key"] == "revenue" for item in preview["candidate_facts"])
    assert listed.status_code == 200
    assert any(item["metric_key"] == "revenue" for item in listed.json()["data"])
    assert evidence.status_code == 200
    assert any(item["snippet"] for item in evidence.json()["data"])


def _confirmed_fact() -> ConfirmedFact:
    return ConfirmedFact(
        code="TSTUQ1",
        period="2025",
        fact_type="financial",
        metric_name="Revenue",
        metric_key="revenue",
        source_type="test",
    )
