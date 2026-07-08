# 财报事实流水线实施计划

> **给执行型 agent 的要求：** 实施本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行。步骤使用 `- [ ]` 复选框语法，方便逐步勾选和复核。

**目标：** 完成财报数据平台阶段 1：证据库、候选事实库、正式事实库、导入确认防覆盖，以及按已确认 A 方向 UI 原型展示候选事实和证据。

**架构：** 在现有财报导入链路旁新增事实流水线。PDF 和手工导入继续返回现有预览结构，同时生成证据与候选事实；确认入库时写入正式事实库，并继续同步旧财务表、分部表和费用表，保证现有基本面页面不被打断。外部搜索、覆盖率评分和报告章节生成不在本计划内。

**技术栈：** FastAPI、SQLAlchemy Async ORM、SQLite、Pydantic v2、pytest、httpx ASGITransport、Vue 3、TypeScript、Element Plus、Vite。

---

## 范围边界

本计划只实现阶段 1：

1. 新增 `evidence_items`、`candidate_facts`、`confirmed_facts`。
2. 从现有 PDF/手工导入预览生成候选事实和证据。
3. 确认导入时生成正式事实。
4. 确认导入时避免 `None` 覆盖旧表已有值。
5. 导入工作台按已确认的 **A：研究流水线式** 原型展示候选事实、证据片段和覆盖风险。

后续单独出计划：

1. 外部搜索采集。
2. 经营质量、研发产能、资本动作、估值市场等强类型事实域扩展。
3. 数据覆盖率系统。
4. Markdown 深度报告章节生成。

## UI 原型门禁

已确认 UI 方向：**A：研究流水线式**。

开发前必须遵守：

1. 不直接做传统后台表格页。
2. 导入工作台采用三栏结构：左侧流程与文档资产库，中间候选事实复核队列，右侧证据与覆盖风险。
3. 风险项、低置信度项、冲突项必须明显标识。
4. 批量确认只允许高可信事实。
5. 空值不覆盖旧值的规则必须在确认区域或右侧风险区展示。
6. 后续如果改布局或核心交互，需要先更新 UI 原型并再次让用户确认。

已沉淀 UI 设计文档：

`docs/superpowers/specs/2026-07-08-import-workbench-ui-design.md`

## 文件职责

新增：

- `backend/fact_service.py`：负责候选事实、证据、正式事实的创建与查询。
- `tests/test_fact_pipeline.py`：覆盖建表、候选事实生成、API 查询、确认入库和防空值覆盖。

修改：

- `backend/models.py`：新增 `EvidenceItem`、`CandidateFact`、`ConfirmedFact`。
- `backend/schemas/importing.py`：新增证据、候选事实、正式事实读模型，并扩展导入预览与确认结果。
- `backend/import_service.py`：在解析、手工预览和确认入库中接入事实流水线，并保护旧表已有值。
- `backend/api/imports.py`：新增候选事实、证据、正式事实查询接口。
- `frontend/src/api/types.ts`：新增前端类型。
- `frontend/src/api/index.ts`：新增 API 方法。
- `frontend/src/views/ImportWorkbench.vue`：按 A 原型展示三栏式候选事实复核。
- `doc/pages/import-workbench.md`：更新页面契约。

### 任务 1：新增事实流水线数据模型

**文件：**

- 修改：`backend/models.py`
- 修改：`backend/schemas/importing.py`
- 测试：`tests/test_fact_pipeline.py`

- [ ] **步骤 1：写失败测试**

新建 `tests/test_fact_pipeline.py`：

```python
import pytest
from sqlalchemy import text

from backend.database import AsyncSessionLocal, init_db


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
```

- [ ] **步骤 2：确认测试失败**

运行：

```powershell
python -m pytest tests/test_fact_pipeline.py::test_init_db_creates_fact_pipeline_tables -q
```

预期：失败，因为三张表还不存在。

- [ ] **步骤 3：新增 SQLAlchemy 模型**

在 `backend/models.py` 的 `ReportParseResult` 后、`ImportBatch` 前加入：

```python
class EvidenceItem(Base, TimestampMixin):
    __tablename__ = "evidence_items"
    __table_args__ = (
        Index("idx_evidence_code_topic", "code", "topic"),
        Index("idx_evidence_document", "document_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_title: Mapped[str] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    source_date: Mapped[date] = mapped_column(Date, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    document_id: Mapped[int] = mapped_column(Integer, nullable=True)
    batch_id: Mapped[int] = mapped_column(Integer, nullable=True)
    parse_job_id: Mapped[int] = mapped_column(Integer, nullable=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=True)
    company_name: Mapped[str] = mapped_column(String(100), nullable=True)
    topic: Mapped[str] = mapped_column(String(50), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    page_no: Mapped[int] = mapped_column(Integer, nullable=True)
    section_name: Mapped[str] = mapped_column(String(100), nullable=True)
    locator_json: Mapped[str] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    trust_level: Mapped[str] = mapped_column(String(1), default="A", nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    reviewer_note: Mapped[str] = mapped_column(Text, nullable=True)


class CandidateFact(Base, TimestampMixin):
    __tablename__ = "candidate_facts"
    __table_args__ = (
        Index("idx_candidate_batch", "batch_id"),
        Index("idx_candidate_code_period", "code", "period"),
        Index("idx_candidate_review_status", "review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    document_id: Mapped[int] = mapped_column(Integer, nullable=True)
    parse_job_id: Mapped[int] = mapped_column(Integer, nullable=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=True)
    fact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=True)
    metric_unit: Mapped[str] = mapped_column(String(30), nullable=True)
    dimension: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    dimension_value: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    evidence_id: Mapped[int] = mapped_column(Integer, nullable=True)
    evidence_ids_json: Mapped[str] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(1), default="A", nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    parser_version: Mapped[str] = mapped_column(String(30), nullable=True)
    existing_fact_id: Mapped[int] = mapped_column(Integer, nullable=True)
    conflict_group: Mapped[str] = mapped_column(String(100), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    reviewer_note: Mapped[str] = mapped_column(Text, nullable=True)


class ConfirmedFact(Base, TimestampMixin):
    __tablename__ = "confirmed_facts"
    __table_args__ = (
        UniqueConstraint(
            "code",
            "period",
            "fact_type",
            "metric_key",
            "dimension",
            "dimension_value",
            name="uq_confirmed_fact_identity",
        ),
        Index("idx_confirmed_code_period", "code", "period"),
        Index("idx_confirmed_fact_type", "fact_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=True)
    fact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=True)
    metric_unit: Mapped[str] = mapped_column(String(30), nullable=True)
    dimension: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    dimension_value: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    evidence_id: Mapped[int] = mapped_column(Integer, nullable=True)
    evidence_ids_json: Mapped[str] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(1), default="A", nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    candidate_fact_id: Mapped[int] = mapped_column(Integer, nullable=True)
    import_id: Mapped[int] = mapped_column(Integer, nullable=True)
```

说明：`dimension` 和 `dimension_value` 使用空字符串而不是 `NULL`，是为了让 SQLite 的唯一约束和 upsert 能稳定识别同一事实。

- [ ] **步骤 4：新增 Pydantic 读模型**

在 `backend/schemas/importing.py` 的 `ImportBatchRead` 后加入：

```python
class EvidenceItemRead(OrmModel):
    id: int
    source_type: str
    source_title: str | None = None
    source_url: str | None = None
    source_date: datetime | None = None
    collected_at: datetime
    document_id: int | None = None
    batch_id: int | None = None
    parse_job_id: int | None = None
    code: str | None = None
    company_name: str | None = None
    topic: str
    snippet: str
    page_no: int | None = None
    section_name: str | None = None
    locator_json: str | None = None
    confidence: Decimal | None = None
    trust_level: str
    review_status: str
    reviewer_note: str | None = None
    created_at: datetime
    updated_at: datetime


class CandidateFactRead(OrmModel):
    id: int
    batch_id: int
    document_id: int | None = None
    parse_job_id: int | None = None
    code: str
    company_name: str | None = None
    period: str
    period_type: str | None = None
    fact_type: str
    metric_name: str
    metric_key: str
    metric_value: Decimal | None = None
    metric_unit: str | None = None
    dimension: str = ""
    dimension_value: str = ""
    evidence_id: int | None = None
    evidence_ids_json: str | None = None
    source_type: str
    trust_level: str
    confidence: Decimal | None = None
    parser_version: str | None = None
    existing_fact_id: int | None = None
    conflict_group: str | None = None
    review_status: str
    reviewer_note: str | None = None
    created_at: datetime
    updated_at: datetime


class ConfirmedFactRead(OrmModel):
    id: int
    code: str
    company_name: str | None = None
    period: str
    period_type: str | None = None
    fact_type: str
    metric_name: str
    metric_key: str
    metric_value: Decimal | None = None
    metric_unit: str | None = None
    dimension: str = ""
    dimension_value: str = ""
    evidence_id: int | None = None
    evidence_ids_json: str | None = None
    source_type: str
    trust_level: str
    review_status: str
    candidate_fact_id: int | None = None
    import_id: int | None = None
    created_at: datetime
    updated_at: datetime
```

扩展 `ImportPreview`：

```python
class ImportPreview(BaseModel):
    batch: ImportBatchRead
    financial: ManualFinancialInput
    segments: list[SegmentInput] = []
    expenses: ExpenseInput | None = None
    confidence: Decimal
    warnings: list[str] = []
    field_sources: dict[str, dict[str, str | None]] = {}
    extractions: ReportExtractions | None = None
    document: ReportDocumentRead | None = None
    parse_job: ReportParseJobRead | None = None
    is_duplicate: bool = False
    candidate_facts: list[CandidateFactRead] = []
```

扩展 `ConfirmImportResult`：

```python
class ConfirmImportResult(BaseModel):
    batch: ImportBatchRead
    financial_records: int
    segment_records: int
    expense_records: int
    extraction_records: int
    candidate_records: int = 0
    confirmed_fact_records: int = 0
```

- [ ] **步骤 5：运行测试**

运行：

```powershell
python -m pytest tests/test_fact_pipeline.py::test_init_db_creates_fact_pipeline_tables tests/test_pdf_financial_parser.py -q
```

预期：通过。

- [ ] **步骤 6：提交**

运行：

```powershell
git add -- backend/models.py backend/schemas/importing.py tests/test_fact_pipeline.py
git commit -m "feat: add fact pipeline data models"
```

预期：只提交上述文件。

### 任务 2：从导入预览生成候选事实和证据

**文件：**

- 新增：`backend/fact_service.py`
- 修改：`tests/test_fact_pipeline.py`

- [ ] **步骤 1：写失败测试**

追加到 `tests/test_fact_pipeline.py`：

```python
from decimal import Decimal

from backend.fact_service import create_candidate_facts_for_import, list_candidate_facts
from backend.models import ImportBatch
from backend.schemas.importing import ManualFinancialInput


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

    assert created_count == 1
    assert len(facts) == 1
    assert facts[0].metric_key == "revenue"
    assert facts[0].metric_name == "营业收入"
    assert facts[0].metric_value == Decimal("570714025.2600")
    assert facts[0].metric_unit == "元"
    assert facts[0].source_type == "annual_report"
    assert facts[0].trust_level == "A"
    assert facts[0].dimension == ""
    assert facts[0].dimension_value == ""
    assert facts[0].evidence_id is not None
```

- [ ] **步骤 2：确认测试失败**

运行：

```powershell
python -m pytest tests/test_fact_pipeline.py::test_create_candidate_facts_for_import_links_evidence -q
```

预期：失败，提示 `backend.fact_service` 不存在。

- [ ] **步骤 3：新增 `backend/fact_service.py`**

创建文件：

```python
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import asc, select
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
    await _clear_pending_candidates(session, batch.id)
    count = 0
    for metric in _iter_import_metrics(financial, segments, expenses, extractions):
        evidence = await _create_evidence(session, batch, financial, metric, field_sources, confidence)
        session.add(
            CandidateFact(
                batch_id=batch.id,
                document_id=batch.document_id,
                parse_job_id=batch.parse_job_id,
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
                evidence_id=evidence.id if evidence else None,
                evidence_ids_json=json.dumps([evidence.id], ensure_ascii=False) if evidence else None,
                source_type=_source_type(batch),
                trust_level="A",
                confidence=confidence,
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
    if code:
        stmt = stmt.where(EvidenceItem.code == code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_confirmed_facts(
    session: AsyncSession,
    code: str | None = None,
    period: str | None = None,
) -> list[ConfirmedFact]:
    stmt = select(ConfirmedFact).order_by(asc(ConfirmedFact.id))
    if code:
        stmt = stmt.where(ConfirmedFact.code == code)
    if period:
        stmt = stmt.where(ConfirmedFact.period == period)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _clear_pending_candidates(session: AsyncSession, batch_id: int) -> None:
    result = await session.execute(
        select(CandidateFact).where(
            CandidateFact.batch_id == batch_id,
            CandidateFact.review_status == "pending",
        )
    )
    for row in result.scalars().all():
        await session.delete(row)
    await session.flush()


async def _create_evidence(
    session: AsyncSession,
    batch: ImportBatch,
    financial: ManualFinancialInput,
    metric: FactMetric,
    field_sources: dict[str, dict[str, str | None]],
    confidence: Decimal,
) -> EvidenceItem:
    source = field_sources.get(metric.metric_key, {})
    snippet = source.get("line") or f"{metric.metric_name}: {metric.value}"
    evidence = EvidenceItem(
        source_type=_source_type(batch),
        source_title=batch.file_name,
        document_id=batch.document_id,
        batch_id=batch.id,
        parse_job_id=batch.parse_job_id,
        code=financial.code,
        topic=metric.fact_type,
        snippet=snippet,
        section_name=source.get("section"),
        locator_json=json.dumps(
            {
                "metric_key": metric.metric_key,
                "label": source.get("label"),
                "dimension": metric.dimension,
                "dimension_value": metric.dimension_value,
            },
            ensure_ascii=False,
        ),
        confidence=_decimal_or(source.get("confidence"), confidence),
        trust_level="A",
        review_status="pending",
    )
    session.add(evidence)
    await session.flush()
    return evidence


def _iter_import_metrics(
    financial: ManualFinancialInput,
    segments: list[SegmentInput],
    expenses: ExpenseInput | None,
    extractions: ReportExtractions | None,
) -> list[FactMetric]:
    metrics: list[FactMetric] = []
    for key, (label, fact_type, unit) in FINANCIAL_FIELD_LABELS.items():
        value = getattr(financial, key)
        if value is not None:
            metrics.append(FactMetric(key, label, fact_type, value, unit))
    if expenses:
        for key, (label, fact_type, unit) in EXPENSE_FIELD_LABELS.items():
            value = getattr(expenses, key)
            if value is not None:
                metrics.append(FactMetric(key, label, fact_type, value, unit))
    if extractions:
        values = extractions.model_dump()
        values.pop("notes", None)
        for key, (label, fact_type, unit) in EXTRACTION_FIELD_LABELS.items():
            value = values.get(key)
            if value is not None:
                metrics.append(FactMetric(key, label, fact_type, value, unit))
    for item in segments:
        for metric_key, metric_name, value, unit in (
            ("segment_revenue", "分部收入", item.revenue, "元"),
            ("segment_cost", "分部成本", item.cost, "元"),
            ("segment_gross_profit", "分部毛利", item.gross_profit, "元"),
            ("segment_gross_margin", "分部毛利率", item.gross_margin, "%"),
            ("segment_revenue_yoy", "分部收入同比", item.revenue_yoy, "%"),
        ):
            if value is not None:
                metrics.append(
                    FactMetric(
                        metric_key=metric_key,
                        metric_name=metric_name,
                        fact_type="segment",
                        value=value,
                        unit=unit,
                        dimension=item.segment_type,
                        dimension_value=item.segment_name,
                    )
                )
    return metrics


def _source_type(batch: ImportBatch) -> str:
    return "manual_note" if batch.import_type == "manual" else "annual_report"


def _period_type(period: str) -> str | None:
    if "年报" in period or "年度" in period:
        return "annual"
    if "半年" in period or "中报" in period:
        return "semi_annual"
    if "季" in period:
        return "quarter"
    return None


def _decimal_or(value: str | None, fallback: Decimal) -> Decimal:
    if value is None:
        return fallback
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return fallback
```

- [ ] **步骤 4：运行测试**

运行：

```powershell
python -m pytest tests/test_fact_pipeline.py::test_create_candidate_facts_for_import_links_evidence -q
```

预期：通过。

- [ ] **步骤 5：提交**

运行：

```powershell
git add -- backend/fact_service.py tests/test_fact_pipeline.py
git commit -m "feat: create import candidate facts"
```

预期：只提交上述文件。

### 任务 3：把候选事实接入导入预览和 API

**文件：**

- 修改：`backend/import_service.py`
- 修改：`backend/api/imports.py`
- 修改：`tests/test_fact_pipeline.py`

- [ ] **步骤 1：写失败 API 测试**

追加到 `tests/test_fact_pipeline.py`：

```python
from httpx import ASGITransport, AsyncClient

from backend.main import app


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

    assert any(item["metric_key"] == "revenue" for item in preview["candidate_facts"])
    assert listed.status_code == 200
    assert any(item["metric_key"] == "revenue" for item in listed.json()["data"])
```

- [ ] **步骤 2：确认测试失败**

运行：

```powershell
python -m pytest tests/test_fact_pipeline.py::test_upload_preview_returns_candidate_facts_and_list_endpoint -q
```

预期：失败，因为预览还没有 `candidate_facts` 或接口返回 404。

- [ ] **步骤 3：修改 `backend/import_service.py`**

加入导入：

```python
from backend.fact_service import create_candidate_facts_for_import, list_candidate_facts
```

在 `parse_report_document` 中，`await session.refresh(batch)` 之后、返回 `ImportPreview` 之前加入：

```python
    await create_candidate_facts_for_import(
        session=session,
        batch=batch,
        financial=financial,
        segments=segments,
        expenses=expenses,
        extractions=parsed.extractions,
        field_sources=parsed.field_sources,
        confidence=confidence,
        parser_version=job.parser_version,
    )
    candidate_facts = await list_candidate_facts(session, batch_id=batch.id)
```

返回 `ImportPreview` 时增加：

```python
        candidate_facts=candidate_facts,
```

在 `create_manual_preview` 中，`await session.refresh(batch)` 之后加入：

```python
    await create_candidate_facts_for_import(
        session=session,
        batch=batch,
        financial=payload.financial,
        segments=payload.segments,
        expenses=payload.expenses,
        extractions=payload.extractions,
        field_sources={},
        confidence=Decimal("1.00"),
        parser_version="manual-v1",
    )
    candidate_facts = await list_candidate_facts(session, batch_id=batch.id)
```

返回 `ImportPreview` 时使用：

```python
        extractions=payload.extractions,
        candidate_facts=candidate_facts,
```

在 `get_latest_document_preview` 返回前加入：

```python
    candidate_facts = await list_candidate_facts(session, batch_id=batch.id)
```

返回 `ImportPreview` 时增加：

```python
        candidate_facts=candidate_facts,
```

- [ ] **步骤 4：修改 `backend/api/imports.py`**

加入导入：

```python
from backend.fact_service import list_candidate_facts, list_confirmed_facts, list_evidence_items
```

在 schema import 列表中加入：

```python
    CandidateFactRead,
    ConfirmedFactRead,
    EvidenceItemRead,
```

在 `@router.get("/{batch_id}", response_model=ApiResponse[ImportBatchRead])` 之前加入：

```python
@router.get("/candidate-facts", response_model=ApiResponse[list[CandidateFactRead]])
async def read_candidate_facts(
    batch_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[CandidateFactRead]]:
    rows = await list_candidate_facts(session, batch_id=batch_id)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="candidate_facts", updated_at=updated_at, stale=not rows))


@router.get("/evidence", response_model=ApiResponse[list[EvidenceItemRead]])
async def read_evidence_items(
    batch_id: int | None = None,
    code: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[EvidenceItemRead]]:
    rows = await list_evidence_items(session, batch_id=batch_id, code=code)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="evidence", updated_at=updated_at, stale=not rows))


@router.get("/confirmed-facts", response_model=ApiResponse[list[ConfirmedFactRead]])
async def read_confirmed_facts(
    code: str | None = None,
    period: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[ConfirmedFactRead]]:
    rows = await list_confirmed_facts(session, code=code, period=period)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="confirmed_facts", updated_at=updated_at, stale=not rows))
```

- [ ] **步骤 5：运行测试**

运行：

```powershell
python -m pytest tests/test_fact_pipeline.py::test_upload_preview_returns_candidate_facts_and_list_endpoint tests/test_import_preview_sources.py -q
```

预期：通过。

- [ ] **步骤 6：提交**

运行：

```powershell
git add -- backend/import_service.py backend/api/imports.py tests/test_fact_pipeline.py
git commit -m "feat: expose import candidate facts"
```

预期：只提交上述文件。

### 任务 4：确认入库生成正式事实并防止空值覆盖

**文件：**

- 修改：`backend/fact_service.py`
- 修改：`backend/import_service.py`
- 修改：`tests/test_fact_pipeline.py`

- [ ] **步骤 1：写失败测试**

追加到 `tests/test_fact_pipeline.py`：

```python
from sqlalchemy import select

from backend.import_service import confirm_import, create_manual_preview
from backend.models import ConfirmedFact, FinancialReport
from backend.schemas.importing import ConfirmImportRequest


@pytest.mark.asyncio
async def test_confirm_import_materializes_confirmed_facts():
    await init_db()

    async with AsyncSessionLocal() as session:
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
    assert {row.metric_key for row in rows} == {"revenue", "net_profit"}
    assert all(row.review_status == "confirmed" for row in rows)


@pytest.mark.asyncio
async def test_confirm_import_does_not_overwrite_legacy_values_with_nulls():
    await init_db()

    async with AsyncSessionLocal() as session:
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
```

- [ ] **步骤 2：确认测试失败**

运行：

```powershell
python -m pytest tests/test_fact_pipeline.py::test_confirm_import_materializes_confirmed_facts tests/test_fact_pipeline.py::test_confirm_import_does_not_overwrite_legacy_values_with_nulls -q
```

预期：失败，因为尚未生成正式事实，且旧表可能被 `None` 覆盖。

- [ ] **步骤 3：在 `backend/fact_service.py` 加入确认函数**

在 `list_confirmed_facts` 后加入：

```python
async def confirm_facts_for_import(
    session: AsyncSession,
    batch: ImportBatch,
    financial: ManualFinancialInput,
    segments: list[SegmentInput],
    expenses: ExpenseInput | None,
    extractions: ReportExtractions | None,
) -> int:
    candidates = await list_candidate_facts(session, batch_id=batch.id)
    candidate_by_identity = {
        _identity(item.metric_key, item.dimension, item.dimension_value): item for item in candidates
    }
    confirmed_count = 0
    expected_identities: set[tuple[str, str, str]] = set()

    for metric in _iter_import_metrics(financial, segments, expenses, extractions):
        identity = _identity(metric.metric_key, metric.dimension, metric.dimension_value)
        expected_identities.add(identity)
        candidate = candidate_by_identity.get(identity)
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
            evidence_id=candidate.evidence_id if candidate else None,
            evidence_ids_json=candidate.evidence_ids_json if candidate else None,
            source_type=_source_type(batch),
            trust_level="A",
            review_status="confirmed",
            candidate_fact_id=candidate.id if candidate else None,
            import_id=batch.id,
        )
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=["code", "period", "fact_type", "metric_key", "dimension", "dimension_value"],
                set_={
                    "metric_name": stmt.excluded.metric_name,
                    "metric_value": stmt.excluded.metric_value,
                    "metric_unit": stmt.excluded.metric_unit,
                    "evidence_id": stmt.excluded.evidence_id,
                    "evidence_ids_json": stmt.excluded.evidence_ids_json,
                    "source_type": stmt.excluded.source_type,
                    "trust_level": stmt.excluded.trust_level,
                    "review_status": stmt.excluded.review_status,
                    "candidate_fact_id": stmt.excluded.candidate_fact_id,
                    "import_id": stmt.excluded.import_id,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
        )
        if candidate:
            candidate.review_status = "confirmed"
        confirmed_count += 1

    for candidate in candidates:
        if _identity(candidate.metric_key, candidate.dimension, candidate.dimension_value) not in expected_identities:
            candidate.review_status = "rejected"

    await session.flush()
    return confirmed_count


def _identity(metric_key: str, dimension: str, dimension_value: str) -> tuple[str, str, str]:
    return (metric_key, dimension or "", dimension_value or "")
```

- [ ] **步骤 4：在 `backend/import_service.py` 接入确认函数**

加入导入：

```python
from sqlalchemy import case
from backend.fact_service import confirm_facts_for_import
```

在 `confirm_import` 的 `_upsert_extractions` 调用后加入：

```python
    confirmed_fact_records = await confirm_facts_for_import(
        session=session,
        batch=batch,
        financial=payload.financial,
        segments=payload.segments,
        expenses=payload.expenses,
        extractions=payload.extractions,
    )
```

返回结果改为：

```python
    return ConfirmImportResult(
        batch=batch,
        financial_records=financial_records,
        segment_records=segment_records,
        expense_records=expense_records,
        extraction_records=extraction_records,
        candidate_records=len(await list_candidate_facts(session, batch_id=batch.id)),
        confirmed_fact_records=confirmed_fact_records,
    )
```

- [ ] **步骤 5：保护旧表不被空值覆盖**

在 `backend/import_service.py` 的 `_upsert_financial` 前加入：

```python
def _preserve_existing_on_null(model, stmt, fields: list[str]) -> dict[str, object]:
    return {
        field: case(
            (getattr(stmt.excluded, field).is_not(None), getattr(stmt.excluded, field)),
            else_=getattr(model, field),
        )
        for field in fields
    }
```

在 `_upsert_financial` 中替换 `update_fields`：

```python
    nullable_fields = [
        "report_date",
        "revenue",
        "gross_profit",
        "gross_margin",
        "net_profit",
        "operating_cash_flow",
        "total_assets",
        "net_assets",
        "eps",
        "roe",
        "rd_ratio",
    ]
    update_fields = _preserve_existing_on_null(FinancialReport, stmt, nullable_fields)
    update_fields.update({
        "source": stmt.excluded.source,
        "import_id": stmt.excluded.import_id,
        "review_status": stmt.excluded.review_status,
        "updated_at": stmt.excluded.updated_at,
    })
```

同样把 `_upsert_segments`、`_upsert_expenses`、`_upsert_extractions` 的数值字段更新改为 `_preserve_existing_on_null`，元数据字段继续直接更新。

- [ ] **步骤 6：运行测试**

运行：

```powershell
python -m pytest tests/test_fact_pipeline.py tests/test_import_preview_sources.py tests/test_pdf_financial_parser.py tests/test_stage6.py -q
```

预期：通过。

- [ ] **步骤 7：提交**

运行：

```powershell
git add -- backend/fact_service.py backend/import_service.py tests/test_fact_pipeline.py
git commit -m "feat: confirm facts without null overwrites"
```

预期：只提交上述文件。

### 任务 5：按 A 原型改造导入工作台

**文件：**

- 修改：`frontend/src/api/types.ts`
- 修改：`frontend/src/api/index.ts`
- 修改：`frontend/src/views/ImportWorkbench.vue`

- [ ] **步骤 1：新增前端类型**

在 `frontend/src/api/types.ts` 的 `ImportPreview` 前加入：

```ts
export interface EvidenceItem {
  id: number
  source_type: string
  source_title: string | null
  source_url: string | null
  source_date: string | null
  collected_at: string
  document_id: number | null
  batch_id: number | null
  parse_job_id: number | null
  code: string | null
  company_name: string | null
  topic: string
  snippet: string
  page_no: number | null
  section_name: string | null
  locator_json: string | null
  confidence: string | number | null
  trust_level: string
  review_status: string
  reviewer_note: string | null
  created_at: string
  updated_at: string
}

export interface CandidateFact {
  id: number
  batch_id: number
  document_id: number | null
  parse_job_id: number | null
  code: string
  company_name: string | null
  period: string
  period_type: string | null
  fact_type: string
  metric_name: string
  metric_key: string
  metric_value: string | number | null
  metric_unit: string | null
  dimension: string
  dimension_value: string
  evidence_id: number | null
  evidence_ids_json: string | null
  source_type: string
  trust_level: string
  confidence: string | number | null
  parser_version: string | null
  existing_fact_id: number | null
  conflict_group: string | null
  review_status: string
  reviewer_note: string | null
  created_at: string
  updated_at: string
}

export interface ConfirmedFact {
  id: number
  code: string
  company_name: string | null
  period: string
  period_type: string | null
  fact_type: string
  metric_name: string
  metric_key: string
  metric_value: string | number | null
  metric_unit: string | null
  dimension: string
  dimension_value: string
  evidence_id: number | null
  evidence_ids_json: string | null
  source_type: string
  trust_level: string
  review_status: string
  candidate_fact_id: number | null
  import_id: number | null
  created_at: string
  updated_at: string
}
```

扩展 `ImportPreview`：

```ts
  candidate_facts: CandidateFact[]
```

扩展 `ConfirmImportResult`：

```ts
  candidate_records: number
  confirmed_fact_records: number
```

- [ ] **步骤 2：新增 API 方法**

在 `frontend/src/api/index.ts` 的类型导入中加入：

```ts
  CandidateFact,
  ConfirmedFact,
  EvidenceItem,
```

新增方法：

```ts
  getCandidateFacts(params?: { batch_id?: number }) {
    return request<CandidateFact[]>('/api/imports/candidate-facts', params)
  },
  getEvidenceItems(params?: { batch_id?: number; code?: string }) {
    return request<EvidenceItem[]>('/api/imports/evidence', params)
  },
  getConfirmedFacts(params?: { code?: string; period?: string }) {
    return request<ConfirmedFact[]>('/api/imports/confirmed-facts', params)
  },
```

- [ ] **步骤 3：改造 `ImportWorkbench.vue` 状态**

新增类型导入：

```ts
import type { CandidateFact, EvidenceItem } from '@/api/types'
```

新增状态：

```ts
const candidateFacts = ref<CandidateFact[]>([])
const evidenceItems = ref<EvidenceItem[]>([])
const selectedCandidateId = ref<number | null>(null)
const factDomainFilter = ref('all')
```

新增计算属性：

```ts
const evidenceById = computed(() => {
  const map = new Map<number, EvidenceItem>()
  for (const item of evidenceItems.value) {
    map.set(item.id, item)
  }
  return map
})

const filteredCandidateFacts = computed(() => {
  if (factDomainFilter.value === 'all') return candidateFacts.value
  return candidateFacts.value.filter((fact) => fact.fact_type === factDomainFilter.value)
})

const selectedCandidate = computed(() => {
  return candidateFacts.value.find((fact) => fact.id === selectedCandidateId.value) ?? filteredCandidateFacts.value[0] ?? null
})

const selectedEvidence = computed(() => {
  const fact = selectedCandidate.value
  return fact?.evidence_id ? evidenceById.value.get(fact.evidence_id) ?? null : null
})
```

新增加载函数：

```ts
async function loadFactEvidence(batchId: number) {
  try {
    const [facts, evidence] = await Promise.all([
      api.getCandidateFacts({ batch_id: batchId }),
      api.getEvidenceItems({ batch_id: batchId })
    ])
    candidateFacts.value = facts.data ?? []
    evidenceItems.value = evidence.data ?? []
    selectedCandidateId.value = candidateFacts.value[0]?.id ?? null
  } catch (error) {
    candidateFacts.value = []
    evidenceItems.value = []
    selectedCandidateId.value = null
    const message = error instanceof Error ? error.message : '候选事实加载失败'
    ElMessage.warning(message)
  }
}
```

- [ ] **步骤 4：按 A 原型更新模板**

模板结构调整为：

```vue
<section class="import-workbench-debug">
  <header class="import-workbench-debug__hero">
    <h1>导入财报</h1>
  </header>
  <section class="import-workbench-debug__pipeline-layout">
    <aside class="import-workbench-debug__pipeline-rail">
      <!-- 流程导航 + 文档资产库 -->
    </aside>
    <main class="import-workbench-debug__fact-stage">
      <!-- 候选事实统计、筛选、复核队列 -->
    </main>
    <aside class="import-workbench-debug__evidence-panel">
      <!-- 当前事实证据、风险、覆盖旧值检查 -->
    </aside>
  </section>
</section>
```

候选事实行点击时设置：

```vue
@click="selectedCandidateId = fact.id"
```

右侧证据卡展示：

```vue
<strong>{{ selectedCandidate?.metric_name ?? '未选择候选事实' }}</strong>
<p>{{ selectedEvidence?.snippet ?? '暂无证据片段' }}</p>
<p>来源等级：{{ selectedCandidate?.trust_level ?? '--' }}</p>
<p>状态：{{ selectedCandidate?.review_status ?? '--' }}</p>
```

阶段 1 如果后端还没有逐条确认接口，前端按钮先只做展示和提示：

```ts
function showReviewActionHint(action: string) {
  ElMessage.info(`${action} 操作会在候选事实确认接口完成后接入`)
}
```

- [ ] **步骤 5：运行前端构建**

运行：

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

预期：构建通过，已有 Rolldown warning 可以保留。

- [ ] **步骤 6：提交**

运行：

```powershell
git add -- frontend/src/api/types.ts frontend/src/api/index.ts frontend/src/views/ImportWorkbench.vue
git commit -m "feat: show import candidate facts"
```

预期：只提交上述文件。

### 任务 6：更新文档并完整验证

**文件：**

- 修改：`doc/pages/import-workbench.md`
- 测试：后端与前端验证命令

- [ ] **步骤 1：更新页面契约**

在 `doc/pages/import-workbench.md` 中把页面目标更新为：

```markdown
导入工作台用于完成财报数据的半自动导入闭环。用户可以上传财报 PDF 生成解析预览，系统会同步生成字段来源、证据片段和候选事实；用户复核后确认入库，确认动作会写入正式事实库，并继续同步旧财务、业务分部和费用表以兼容现有页面。
```

在布局结构中加入：

```markdown
5. 候选事实与证据卡片：展示候选指标、来源等级、复核状态、覆盖风险和原文片段。
```

在数据依赖中加入：

```markdown
- `candidateFacts`：当前批次候选事实列表。
- `evidenceItems`：当前批次证据片段列表。
- `selectedCandidate`：当前选中的候选事实。
- `selectedEvidence`：当前候选事实对应的证据片段。
```

在修改规则中加入：

```markdown
- 修改候选事实或证据字段前，必须同步更新后端 `CandidateFactRead`、`EvidenceItemRead`、前端类型和本文件。
- 修改导入工作台布局前，必须先更新 UI 原型并获得确认。
```

- [ ] **步骤 2：运行后端验证**

运行：

```powershell
python -m pytest tests/test_fact_pipeline.py tests/test_import_preview_sources.py tests/test_pdf_financial_parser.py tests/test_stage6.py tests/test_stage7_delivery.py -q
```

预期：全部通过。

- [ ] **步骤 3：运行前端验证**

运行：

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

预期：构建通过。

- [ ] **步骤 4：检查最终变更**

运行：

```powershell
git status --short
git diff --stat
```

预期：本计划相关改动只包含计划列出的文件；其他预先存在的脏文件保持不动。

- [ ] **步骤 5：提交文档**

运行：

```powershell
git add -- doc/pages/import-workbench.md
git commit -m "docs: document import fact review flow"
```

预期：只提交文档文件。

## 最终验证清单

全部任务完成后运行：

```powershell
python -m pytest tests/test_fact_pipeline.py tests/test_import_preview_sources.py tests/test_pdf_financial_parser.py tests/test_stage6.py tests/test_stage7_delivery.py -q
Set-Location frontend
npm run build
Set-Location ..
```

验收结果：

1. `/api/imports/documents/upload` 返回 `preview.candidate_facts`。
2. `/api/imports/candidate-facts?batch_id=<id>` 返回候选事实。
3. `/api/imports/evidence?batch_id=<id>` 返回证据片段。
4. 确认导入后 `/api/imports/confirmed-facts?code=<code>&period=<period>` 返回正式事实。
5. 旧财务表已有值不会被新导入的 `None` 覆盖。
6. 导入工作台呈现 A 方向三栏式复核结构。
7. 现有基本面页面和个股档案继续可用。

## 自查记录

本计划覆盖阶段 1 的关键要求：

1. 证据库：任务 1、2、3、5。
2. 候选事实库：任务 1、2、3、5。
3. 正式事实库：任务 4。
4. 空值防覆盖：任务 4。
5. A 方向 UI 原型落地：任务 5。
6. 文档与验证：任务 6。

本计划刻意不覆盖：

1. 外部搜索采集。
2. 报告章节生成。
3. 覆盖率评分。
4. 完整强类型事实域扩展。

这些内容将在阶段 2、3、4 分别规划。
