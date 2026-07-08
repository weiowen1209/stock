import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.database import AsyncSessionLocal, init_db
from backend.models import CandidateFact, ConfirmedFact
from backend.schemas.importing import EvidenceItemRead


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


def _confirmed_fact() -> ConfirmedFact:
    return ConfirmedFact(
        code="TSTUQ1",
        period="2025",
        fact_type="financial",
        metric_name="Revenue",
        metric_key="revenue",
        source_type="test",
    )
