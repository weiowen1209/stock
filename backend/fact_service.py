import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import asc, select
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

    await _delete_pending_candidate_facts(session, batch.id)
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


async def list_evidence_items(session: AsyncSession, batch_id: int | None = None) -> list[EvidenceItem]:
    stmt = select(EvidenceItem).order_by(asc(EvidenceItem.id))
    if batch_id is not None:
        stmt = stmt.where(EvidenceItem.batch_id == batch_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_confirmed_facts(session: AsyncSession, code: str | None = None) -> list[ConfirmedFact]:
    stmt = select(ConfirmedFact).order_by(asc(ConfirmedFact.id))
    if code is not None:
        stmt = stmt.where(ConfirmedFact.code == code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _delete_pending_candidate_facts(session: AsyncSession, batch_id: int) -> None:
    result = await session.execute(
        select(CandidateFact).where(
            CandidateFact.batch_id == batch_id,
            CandidateFact.review_status == "pending",
        )
    )
    for item in result.scalars().all():
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
