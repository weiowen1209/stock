import json
from datetime import datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from backend import import_service
from backend.database import AsyncSessionLocal, init_db
from backend.fact_service import create_candidate_facts_for_import, list_candidate_facts, list_evidence_items
from backend.import_service import confirm_import, create_manual_preview
from backend.main import app
from backend.models import AnnualReportExtraction, CandidateFact, ConfirmedFact, FinancialReport, ImportBatch
from backend.schemas.importing import (
    ConfirmImportRequest,
    EvidenceItemRead,
    ExpenseInput,
    ManualFinancialInput,
    ReportExtractions,
    SegmentInput,
)


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


@pytest.mark.asyncio
async def test_manual_preview_rolls_back_batch_when_candidate_creation_fails(monkeypatch):
    await init_db()
    code = "TSTTX3"

    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM import_batches WHERE code = :code"), {"code": code})
        await session.commit()

    async def fail_candidate_creation(**kwargs):
        raise RuntimeError("candidate creation failed")

    monkeypatch.setattr(import_service, "create_candidate_facts_for_import", fail_candidate_creation)
    payload = ConfirmImportRequest(
        financial=ManualFinancialInput(
            code=code,
            report_period="2025年报",
            revenue=Decimal("123.45"),
        ),
        segments=[],
        expenses=None,
        extractions=None,
    )

    async with AsyncSessionLocal() as session:
        with pytest.raises(RuntimeError, match="candidate creation failed"):
            await import_service.create_manual_preview(session, payload)
        await session.rollback()

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM import_batches WHERE code = :code"), {"code": code})

    assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_manual_preview_api_returns_candidate_facts_with_manual_source():
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/imports/manual",
            json={
                "financial": {
                    "code": "688018",
                    "report_period": "2025年报",
                    "revenue": "123.45",
                },
                "segments": [],
                "expenses": None,
                "extractions": None,
            },
        )

    assert response.status_code == 200
    candidate_facts = response.json()["data"]["candidate_facts"]
    assert candidate_facts
    assert candidate_facts[0]["source_type"] == "manual_note"


@pytest.mark.asyncio
async def test_confirmed_facts_static_route_accepts_period_filter():
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/imports/confirmed-facts?period=不存在的报告期-任务3")

    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_document_preview_returns_saved_candidate_facts():
    await init_db()
    text = """
证券代码：688019
2025年度报告
合并利润表
项目 2025年度 2024年度 单位：元
营业收入 570,714,025.26 500,000,000.00
""".encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        upload = await client.post(
            "/api/imports/documents/upload",
            files={"file": ("saved-preview-report.txt", text, "text/plain")},
            data={"code": "688019", "report_period": "2025年报"},
        )
        assert upload.status_code == 200
        document_id = upload.json()["data"]["document"]["id"]

        preview = await client.get(f"/api/imports/documents/{document_id}/preview")

    assert preview.status_code == 200
    assert any(item["metric_key"] == "revenue" for item in preview.json()["data"]["candidate_facts"])


@pytest.mark.asyncio
async def test_confirm_import_materializes_confirmed_facts():
    await init_db()

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                DELETE FROM confirmed_facts
                WHERE code = '688017'
                AND period = '2025年报'
                """
            )
        )
        preview = await create_manual_preview(
            session,
            ConfirmImportRequest(
                financial=ManualFinancialInput(
                    code="688017",
                    report_period="2025年报",
                    revenue=Decimal("570714025.26"),
                    net_profit=Decimal("124366913.57"),
                ),
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        result = await confirm_import(
            session,
            preview.batch.id,
            ConfirmImportRequest(
                financial=preview.financial,
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        confirmed = await session.execute(
            select(ConfirmedFact).where(
                ConfirmedFact.code == "688017",
                ConfirmedFact.period == "2025年报",
            )
        )

    rows = list(confirmed.scalars().all())
    assert result.confirmed_fact_records == 2
    assert result.candidate_records == 2
    assert {row.metric_key for row in rows} == {"revenue", "net_profit"}
    assert all(row.review_status == "confirmed" for row in rows)
    assert all(row.import_id == preview.batch.id for row in rows)


@pytest.mark.asyncio
async def test_confirm_import_materializes_non_financial_confirmed_facts():
    await init_db()
    code = "TSTCFX1"
    period = "2099年报"

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                DELETE FROM confirmed_facts
                WHERE code = :code
                AND period = :period
                """
            ),
            {"code": code, "period": period},
        )
        preview = await create_manual_preview(
            session,
            ConfirmImportRequest(
                financial=ManualFinancialInput(code=code, report_period=period),
                segments=[
                    SegmentInput(
                        segment_type="product",
                        segment_name="机器人",
                        revenue=Decimal("10.00"),
                        gross_margin=Decimal("20.00"),
                    )
                ],
                expenses=ExpenseInput(rd_expense=Decimal("30.00")),
                extractions=ReportExtractions(operating_profit=Decimal("40.00")),
            ),
        )
        result = await confirm_import(
            session,
            preview.batch.id,
            ConfirmImportRequest(
                financial=preview.financial,
                segments=preview.segments,
                expenses=preview.expenses,
                extractions=preview.extractions,
            ),
        )
        confirmed = await session.execute(
            select(ConfirmedFact).where(
                ConfirmedFact.code == code,
                ConfirmedFact.period == period,
            )
        )

    facts_by_key = {row.metric_key: row for row in confirmed.scalars().all()}
    assert result.confirmed_fact_records == 4
    assert result.candidate_records == 4
    assert set(facts_by_key) == {
        "segment_revenue",
        "segment_gross_margin",
        "rd_expense",
        "operating_profit",
    }
    assert facts_by_key["segment_revenue"].fact_type == "segment"
    assert facts_by_key["segment_revenue"].dimension == "product"
    assert facts_by_key["segment_revenue"].dimension_value == "机器人"
    assert facts_by_key["segment_revenue"].candidate_fact_id is not None
    assert facts_by_key["segment_gross_margin"].fact_type == "segment"
    assert facts_by_key["segment_gross_margin"].dimension == "product"
    assert facts_by_key["segment_gross_margin"].dimension_value == "机器人"
    assert facts_by_key["segment_gross_margin"].candidate_fact_id is not None
    assert facts_by_key["rd_expense"].fact_type == "profit_impact"
    assert facts_by_key["rd_expense"].dimension == ""
    assert facts_by_key["operating_profit"].fact_type == "profit_impact"
    assert facts_by_key["operating_profit"].dimension == ""


@pytest.mark.asyncio
async def test_confirm_import_does_not_overwrite_legacy_values_with_nulls():
    await init_db()

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                DELETE FROM financial_reports
                WHERE code = '688017'
                AND report_period = '2025年报'
                """
            )
        )
        session.add(
            FinancialReport(
                code="688017",
                report_period="2025年报",
                revenue=Decimal("100.00"),
                net_profit=Decimal("50.00"),
                source="seed",
                review_status="confirmed",
            )
        )
        await session.commit()

        preview = await create_manual_preview(
            session,
            ConfirmImportRequest(
                financial=ManualFinancialInput(
                    code="688017",
                    report_period="2025年报",
                    revenue=None,
                    net_profit=Decimal("60.00"),
                ),
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        await confirm_import(
            session,
            preview.batch.id,
            ConfirmImportRequest(
                financial=preview.financial,
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        report = await session.execute(
            select(FinancialReport).where(
                FinancialReport.code == "688017",
                FinancialReport.report_period == "2025年报",
            )
        )

    row = report.scalar_one()
    assert row.revenue == Decimal("100.00")
    assert row.net_profit == Decimal("60.00")


@pytest.mark.asyncio
async def test_confirm_import_rejects_candidates_missing_from_final_payload():
    await init_db()
    code = "TSTRJ1"
    period = "2099年报"

    async with AsyncSessionLocal() as session:
        preview = await create_manual_preview(
            session,
            ConfirmImportRequest(
                financial=ManualFinancialInput(
                    code=code,
                    report_period=period,
                    revenue=Decimal("100.00"),
                    net_profit=Decimal("50.00"),
                ),
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )

        result = await confirm_import(
            session,
            preview.batch.id,
            ConfirmImportRequest(
                financial=ManualFinancialInput(
                    code=code,
                    report_period=period,
                    revenue=Decimal("100.00"),
                    net_profit=None,
                ),
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        candidates = await session.execute(select(CandidateFact).where(CandidateFact.batch_id == preview.batch.id))

    status_by_metric = {row.metric_key: row.review_status for row in candidates.scalars().all()}
    assert result.confirmed_fact_records == 1
    assert status_by_metric == {"revenue": "confirmed", "net_profit": "rejected"}


@pytest.mark.asyncio
async def test_confirm_import_preserves_existing_fact_provenance_when_batch_has_no_candidate():
    await init_db()
    code = "TSTPV1"
    period = "2099年报"

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                DELETE FROM confirmed_facts
                WHERE code = :code
                AND period = :period
                """
            ),
            {"code": code, "period": period},
        )
        first_preview = await create_manual_preview(
            session,
            ConfirmImportRequest(
                financial=ManualFinancialInput(
                    code=code,
                    report_period=period,
                    revenue=Decimal("100.00"),
                ),
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        await confirm_import(
            session,
            first_preview.batch.id,
            ConfirmImportRequest(
                financial=first_preview.financial,
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        first_fact = (
            await session.execute(
                select(ConfirmedFact).where(
                    ConfirmedFact.code == code,
                    ConfirmedFact.period == period,
                    ConfirmedFact.metric_key == "revenue",
                )
            )
        ).scalar_one()
        original_evidence_id = first_fact.evidence_id
        original_evidence_ids_json = first_fact.evidence_ids_json
        original_candidate_fact_id = first_fact.candidate_fact_id
        assert original_evidence_id is not None
        assert original_evidence_ids_json is not None
        assert original_candidate_fact_id is not None

        second_preview = await create_manual_preview(
            session,
            ConfirmImportRequest(
                financial=ManualFinancialInput(code=code, report_period=period),
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        await confirm_import(
            session,
            second_preview.batch.id,
            ConfirmImportRequest(
                financial=ManualFinancialInput(
                    code=code,
                    report_period=period,
                    revenue=Decimal("200.00"),
                ),
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        session.expire_all()
        updated_fact = (
            await session.execute(
                select(ConfirmedFact).where(
                    ConfirmedFact.code == code,
                    ConfirmedFact.period == period,
                    ConfirmedFact.metric_key == "revenue",
                )
            )
        ).scalar_one()

    assert updated_fact.metric_value == Decimal("200.00")
    assert updated_fact.evidence_id == original_evidence_id
    assert updated_fact.evidence_ids_json == original_evidence_ids_json
    assert updated_fact.candidate_fact_id == original_candidate_fact_id


@pytest.mark.asyncio
async def test_confirm_import_refreshes_financial_report_updated_at_on_conflict():
    await init_db()
    code = "TSTUPD1"
    period = "2099年报"
    old_updated_at = datetime(2000, 1, 1, 0, 0, 0)

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                DELETE FROM financial_reports
                WHERE code = :code
                AND report_period = :period
                """
            ),
            {"code": code, "period": period},
        )
        session.add(
            FinancialReport(
                code=code,
                report_period=period,
                revenue=Decimal("100.00"),
                source="seed",
                review_status="confirmed",
                updated_at=old_updated_at,
            )
        )
        await session.commit()

        preview = await create_manual_preview(
            session,
            ConfirmImportRequest(
                financial=ManualFinancialInput(
                    code=code,
                    report_period=period,
                    revenue=Decimal("200.00"),
                ),
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        await confirm_import(
            session,
            preview.batch.id,
            ConfirmImportRequest(
                financial=preview.financial,
                segments=[],
                expenses=None,
                extractions=None,
            ),
        )
        report = (
            await session.execute(
                select(FinancialReport).where(
                    FinancialReport.code == code,
                    FinancialReport.report_period == period,
                )
            )
        ).scalar_one()

    assert report.revenue == Decimal("200.00")
    assert report.updated_at > old_updated_at


@pytest.mark.asyncio
async def test_confirm_import_refreshes_extraction_updated_at_and_preserves_null_fields():
    await init_db()
    code = "TSTXUP1"
    period = "2099年报"
    old_updated_at = datetime(2000, 1, 1, 0, 0, 0)

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                DELETE FROM annual_report_extractions
                WHERE code = :code
                AND report_period = :period
                """
            ),
            {"code": code, "period": period},
        )
        session.add(
            AnnualReportExtraction(
                code=code,
                report_period=period,
                operating_profit=Decimal("100.00"),
                rd_investment=Decimal("500.00"),
                source="seed",
                review_status="confirmed",
                updated_at=old_updated_at,
            )
        )
        await session.commit()

        preview = await create_manual_preview(
            session,
            ConfirmImportRequest(
                financial=ManualFinancialInput(code=code, report_period=period),
                segments=[],
                expenses=None,
                extractions=ReportExtractions(
                    operating_profit=Decimal("200.00"),
                    rd_investment=None,
                ),
            ),
        )
        await confirm_import(
            session,
            preview.batch.id,
            ConfirmImportRequest(
                financial=preview.financial,
                segments=[],
                expenses=None,
                extractions=preview.extractions,
            ),
        )
        extraction = (
            await session.execute(
                select(AnnualReportExtraction).where(
                    AnnualReportExtraction.code == code,
                    AnnualReportExtraction.report_period == period,
                )
            )
        ).scalar_one()

    assert extraction.operating_profit == Decimal("200.00")
    assert extraction.rd_investment == Decimal("500.00")
    assert extraction.updated_at > old_updated_at


def _confirmed_fact() -> ConfirmedFact:
    return ConfirmedFact(
        code="TSTUQ1",
        period="2025",
        fact_type="financial",
        metric_name="Revenue",
        metric_key="revenue",
        source_type="test",
    )
