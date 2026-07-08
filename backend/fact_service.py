import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import asc, case, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import CandidateFact, ConfirmedFact, EvidenceItem, ImportBatch
from backend.schemas.importing import ExpenseInput, ManualFinancialInput, ReportExtractions, SegmentInput


FINANCIAL_FIELD_LABELS = {
    "revenue": ("营业收入", "financial", "元"),
    "gross_profit": ("毛利", "financial", "元"),
    "gross_margin": ("毛利率", "financial", "%"),
    "net_profit": ("归母净利润", "financial", "元"),
    "operating_cash_flow": ("经营现金流净额", "financial", "元"),
    "total_assets": ("总资产", "financial", "元"),
    "net_assets": ("净资产", "financial", "元"),
    "eps": ("基本每股收益", "financial", "元/股"),
    "roe": ("ROE", "financial", "%"),
    "rd_ratio": ("研发费用率", "financial", "%"),
}

EXPENSE_FIELD_LABELS = {
    "selling_expense": ("销售费用", "profit_impact", "元"),
    "admin_expense": ("管理费用", "profit_impact", "元"),
    "rd_expense": ("研发费用", "profit_impact", "元"),
    "finance_expense": ("财务费用", "profit_impact", "元"),
}

EXTRACTION_FIELD_LABELS = {
    "operating_profit": ("营业利润", "profit_impact", "元"),
    "total_profit": ("利润总额", "profit_impact", "元"),
    "non_recurring_net_profit": ("扣非净利润", "profit_impact", "元"),
    "income_tax_expense": ("所得税费用", "profit_impact", "元"),
    "minority_interest": ("少数股东损益", "profit_impact", "元"),
    "other_income": ("其他收益", "profit_impact", "元"),
    "investment_income": ("投资收益", "profit_impact", "元"),
    "fair_value_change_income": ("公允价值变动收益", "profit_impact", "元"),
    "credit_impairment_loss": ("信用减值损失", "profit_impact", "元"),
    "asset_impairment_loss": ("资产减值损失", "profit_impact", "元"),
    "asset_disposal_income": ("资产处置收益", "profit_impact", "元"),
    "cash_received_from_sales": ("销售商品、提供劳务收到的现金", "operation", "元"),
    "cash_received_other_operating": ("收到其他与经营活动有关的现金", "operation", "元"),
    "inventory_total": ("存货", "operation", "元"),
    "inventory_impairment": ("存货跌价准备", "operation", "元"),
    "capital_reserve": ("资本公积", "capital", "元"),
    "total_share_capital": ("总股本", "capital", "元"),
    "rd_investment": ("研发投入", "rd", "元"),
    "rd_investment_ratio": ("研发投入占营业收入比例", "rd", "%"),
    "patent_count": ("专利数量", "rd", "项"),
    "invention_patent_count": ("发明专利数量", "rd", "项"),
    "construction_in_progress": ("在建工程", "capacity", "元"),
}

SEGMENT_FIELD_LABELS = {
    "revenue": ("segment_revenue", "分部收入", "segment", "元"),
    "cost": ("segment_cost", "分部成本", "segment", "元"),
    "gross_profit": ("segment_gross_profit", "分部毛利", "segment", "元"),
    "gross_margin": ("segment_gross_margin", "分部毛利率", "segment", "%"),
    "revenue_yoy": ("segment_revenue_yoy", "分部收入同比", "segment", "%"),
}


@dataclass(frozen=True)
class FactMetric:
    metric_key: str
    metric_name: str
    fact_type: str
    value: Decimal
    unit: str | None
    dimension: str = ""
    dimension_value: str = ""


async def create_candidate_facts_for_import(
    session: AsyncSession,
    batch: ImportBatch,
    financial: ManualFinancialInput,
    segments: list[SegmentInput],
    expenses: ExpenseInput | None,
    extractions: ReportExtractions | None,
    field_sources: dict[str, dict[str, str | None]],
    confidence: Decimal,
    parser_version: str | None,
) -> int:
    if batch.id is None:
        await session.flush()

    await _clear_pending_candidates(session, batch.id)
    source_type = _source_type(batch)
    period_type = _period_type(financial.report_period or batch.report_period)
    count = 0

    for metric in _build_metrics(financial, segments, expenses, extractions):
        field_source = field_sources.get(metric.metric_key, {})
        metric_confidence = _confidence_from_source(field_source, confidence)
        evidence = EvidenceItem(
            source_type=source_type,
            source_title=batch.file_name,
            document_id=batch.document_id,
            batch_id=batch.id,
            parse_job_id=batch.parse_job_id,
            code=financial.code,
            topic=metric.fact_type,
            snippet=_evidence_snippet(metric, field_source),
            section_name=field_source.get("section"),
            locator_json=json.dumps(
                {
                    "metric_key": metric.metric_key,
                    "dimension": metric.dimension,
                    "dimension_value": metric.dimension_value,
                    "parser_version": parser_version,
                },
                ensure_ascii=False,
            ),
            confidence=metric_confidence,
            trust_level="A",
            review_status="pending",
        )
        session.add(evidence)
        await session.flush()

        session.add(
            CandidateFact(
                batch_id=batch.id,
                document_id=batch.document_id,
                parse_job_id=batch.parse_job_id,
                code=financial.code,
                period=financial.report_period,
                period_type=period_type,
                fact_type=metric.fact_type,
                metric_name=metric.metric_name,
                metric_key=metric.metric_key,
                metric_value=metric.value,
                metric_unit=metric.unit,
                dimension=metric.dimension,
                dimension_value=metric.dimension_value,
                evidence_id=evidence.id,
                evidence_ids_json=json.dumps([evidence.id]),
                source_type=source_type,
                trust_level="A",
                confidence=metric_confidence,
                parser_version=parser_version,
                review_status="pending",
            )
        )
        count += 1

    await session.flush()
    return count


async def list_candidate_facts(session: AsyncSession, batch_id: int | None = None) -> list[CandidateFact]:
    stmt = select(CandidateFact).order_by(asc(CandidateFact.id))
    if batch_id is not None:
        stmt = stmt.where(CandidateFact.batch_id == batch_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_evidence_items(
    session: AsyncSession,
    batch_id: int | None = None,
    code: str | None = None,
) -> list[EvidenceItem]:
    stmt = select(EvidenceItem).order_by(asc(EvidenceItem.id))
    if batch_id is not None:
        stmt = stmt.where(EvidenceItem.batch_id == batch_id)
    if code is not None:
        stmt = stmt.where(EvidenceItem.code == code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_confirmed_facts(
    session: AsyncSession,
    code: str | None = None,
    period: str | None = None,
) -> list[ConfirmedFact]:
    stmt = select(ConfirmedFact).order_by(asc(ConfirmedFact.id))
    if code is not None:
        stmt = stmt.where(ConfirmedFact.code == code)
    if period is not None:
        stmt = stmt.where(ConfirmedFact.period == period)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def confirm_facts_for_import(
    session: AsyncSession,
    batch: ImportBatch,
    financial: ManualFinancialInput,
    segments: list[SegmentInput],
    expenses: ExpenseInput | None,
    extractions: ReportExtractions | None,
) -> int:
    candidates = await list_candidate_facts(session, batch_id=batch.id)
    candidates_by_identity: dict[tuple[str, str, str], list[CandidateFact]] = {}
    for candidate in candidates:
        candidates_by_identity.setdefault(
            _identity(candidate.metric_key, candidate.dimension, candidate.dimension_value),
            [],
        ).append(candidate)

    metrics_by_identity = _dedupe_metrics_by_identity(_build_metrics(financial, segments, expenses, extractions))
    for candidate in candidates:
        candidate.review_status = "rejected"

    confirmed_count = 0

    for identity, metric in metrics_by_identity.items():
        identity_candidates = candidates_by_identity.get(identity, [])
        candidate = _first_exact_candidate(identity_candidates, metric)
        if candidate:
            candidate.review_status = "confirmed"
        existing_fact = await _get_confirmed_fact(session, financial.code, financial.report_period, metric)
        evidence_id = candidate.evidence_id if candidate else None
        evidence_ids_json = candidate.evidence_ids_json if candidate else None
        candidate_fact_id = candidate.id if candidate else None
        if candidate is None and (existing_fact is None or existing_fact.metric_value != metric.value):
            evidence = await _create_manual_evidence(session, batch, financial, metric)
            evidence_id = evidence.id
            evidence_ids_json = json.dumps([evidence.id])

        stmt = insert(ConfirmedFact).values(
            code=financial.code,
            period=financial.report_period,
            period_type=_period_type(financial.report_period),
            fact_type=metric.fact_type,
            metric_name=metric.metric_name,
            metric_key=metric.metric_key,
            metric_value=metric.value,
            metric_unit=metric.unit,
            dimension=metric.dimension,
            dimension_value=metric.dimension_value,
            evidence_id=evidence_id,
            evidence_ids_json=evidence_ids_json,
            source_type=_source_type(batch),
            trust_level="A",
            review_status="confirmed",
            candidate_fact_id=candidate_fact_id,
            import_id=batch.id,
        )
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=["code", "period", "fact_type", "metric_key", "dimension", "dimension_value"],
                set_={
                    "metric_name": stmt.excluded.metric_name,
                    "metric_value": stmt.excluded.metric_value,
                    "metric_unit": stmt.excluded.metric_unit,
                    "evidence_id": _preserve_provenance_on_same_value(stmt, "evidence_id"),
                    "evidence_ids_json": _preserve_provenance_on_same_value(stmt, "evidence_ids_json"),
                    "source_type": stmt.excluded.source_type,
                    "trust_level": stmt.excluded.trust_level,
                    "review_status": stmt.excluded.review_status,
                    "candidate_fact_id": _preserve_provenance_on_same_value(stmt, "candidate_fact_id"),
                    "import_id": stmt.excluded.import_id,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
        )
        confirmed_count += 1

    await session.flush()
    return confirmed_count


def _dedupe_metrics_by_identity(metrics: list[FactMetric]) -> dict[tuple[str, str, str], FactMetric]:
    metrics_by_identity: dict[tuple[str, str, str], FactMetric] = {}
    for metric in metrics:
        metrics_by_identity[_identity(metric.metric_key, metric.dimension, metric.dimension_value)] = metric
    return metrics_by_identity


def _first_exact_candidate(candidates: list[CandidateFact], metric: FactMetric) -> CandidateFact | None:
    for candidate in candidates:
        if candidate.metric_value == metric.value:
            return candidate
    return None


async def _get_confirmed_fact(
    session: AsyncSession,
    code: str,
    period: str,
    metric: FactMetric,
) -> ConfirmedFact | None:
    result = await session.execute(
        select(ConfirmedFact).where(
            ConfirmedFact.code == code,
            ConfirmedFact.period == period,
            ConfirmedFact.fact_type == metric.fact_type,
            ConfirmedFact.metric_key == metric.metric_key,
            ConfirmedFact.dimension == metric.dimension,
            ConfirmedFact.dimension_value == metric.dimension_value,
        )
    )
    return result.scalar_one_or_none()


async def _create_manual_evidence(
    session: AsyncSession,
    batch: ImportBatch,
    financial: ManualFinancialInput,
    metric: FactMetric,
) -> EvidenceItem:
    evidence = EvidenceItem(
        source_type="manual_note",
        source_title=batch.file_name,
        document_id=batch.document_id,
        batch_id=batch.id,
        parse_job_id=batch.parse_job_id,
        code=financial.code,
        topic=metric.fact_type,
        snippet=_evidence_snippet(metric, {}),
        locator_json=json.dumps(
            {
                "metric_key": metric.metric_key,
                "dimension": metric.dimension,
                "dimension_value": metric.dimension_value,
                "reason": "manual_confirm",
            },
            ensure_ascii=False,
        ),
        confidence=Decimal("1.00"),
        trust_level="A",
        review_status="confirmed",
    )
    session.add(evidence)
    await session.flush()
    return evidence


def _preserve_provenance_on_same_value(stmt, field: str):
    return case(
        (getattr(stmt.excluded, field).is_not(None), getattr(stmt.excluded, field)),
        (ConfirmedFact.metric_value == stmt.excluded.metric_value, getattr(ConfirmedFact, field)),
        else_=None,
    )


def _identity(metric_key: str, dimension: str, dimension_value: str) -> tuple[str, str, str]:
    return (metric_key, dimension or "", dimension_value or "")


async def _clear_pending_candidates(session: AsyncSession, batch_id: int) -> None:
    result = await session.execute(
        select(CandidateFact).where(
            CandidateFact.batch_id == batch_id,
            CandidateFact.review_status == "pending",
        )
    )
    pending_candidates = list(result.scalars().all())
    evidence_ids = [item.evidence_id for item in pending_candidates if item.evidence_id is not None]
    for item in pending_candidates:
        await session.delete(item)
    await session.flush()
    if not evidence_ids:
        return

    evidence_result = await session.execute(
        select(EvidenceItem).where(
            EvidenceItem.batch_id == batch_id,
            EvidenceItem.review_status == "pending",
            EvidenceItem.id.in_(evidence_ids),
        )
    )
    for item in evidence_result.scalars().all():
        await session.delete(item)
    await session.flush()


def _build_metrics(
    financial: ManualFinancialInput,
    segments: list[SegmentInput],
    expenses: ExpenseInput | None,
    extractions: ReportExtractions | None,
) -> list[FactMetric]:
    metrics: list[FactMetric] = []
    metrics.extend(_metrics_from_fields(financial, FINANCIAL_FIELD_LABELS))
    if expenses is not None:
        metrics.extend(_metrics_from_fields(expenses, EXPENSE_FIELD_LABELS))
    if extractions is not None:
        metrics.extend(_metrics_from_fields(extractions, EXTRACTION_FIELD_LABELS))
    for segment in segments:
        for field_name, (metric_key, metric_name, fact_type, unit) in SEGMENT_FIELD_LABELS.items():
            value = _decimal_value(getattr(segment, field_name))
            if value is None:
                continue
            metrics.append(
                FactMetric(
                    metric_key=metric_key,
                    metric_name=metric_name,
                    fact_type=fact_type,
                    value=value,
                    unit=unit,
                    dimension=segment.segment_type or "",
                    dimension_value=segment.segment_name,
                )
            )
    return metrics


def _metrics_from_fields(source: object, labels: dict[str, tuple[str, str, str]]) -> list[FactMetric]:
    metrics: list[FactMetric] = []
    for field_name, (metric_name, fact_type, unit) in labels.items():
        value = _decimal_value(getattr(source, field_name))
        if value is None:
            continue
        metrics.append(
            FactMetric(
                metric_key=field_name,
                metric_name=metric_name,
                fact_type=fact_type,
                value=value,
                unit=unit,
            )
        )
    return metrics


def _decimal_value(value: Decimal | int | float | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _confidence_from_source(field_source: dict[str, str | None], fallback: Decimal) -> Decimal:
    source_confidence = field_source.get("confidence")
    if source_confidence is None:
        return fallback
    try:
        return Decimal(str(source_confidence))
    except (InvalidOperation, ValueError):
        return fallback


def _evidence_snippet(metric: FactMetric, field_source: dict[str, str | None]) -> str:
    line = field_source.get("line")
    if line:
        return line
    if metric.dimension:
        return f"{metric.metric_name}[{metric.dimension}={metric.dimension_value}]: {metric.value}"
    return f"{metric.metric_name}: {metric.value}"


def _source_type(batch: ImportBatch) -> str:
    if batch.import_type == "manual":
        return "manual_note"
    return "annual_report"


def _period_type(report_period: str | None) -> str | None:
    if not report_period:
        return None
    if "半年" in report_period or "中报" in report_period:
        return "semi_annual"
    if "季" in report_period:
        return "quarter"
    if "年报" in report_period or "年度" in report_period:
        return "annual"
    return None
