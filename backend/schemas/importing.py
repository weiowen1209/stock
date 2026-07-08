from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from backend.schemas.common import OrmModel


class ReportDocumentRead(OrmModel):
    id: int
    code: str | None = None
    report_period: str | None = None
    report_type: str | None = None
    original_filename: str
    stored_filename: str
    file_hash: str
    file_size: int
    mime_type: str | None = None
    page_count: int | None = None
    source_site: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class ReportParseJobRead(OrmModel):
    id: int
    document_id: int
    parser_version: str
    status: str
    confidence: Decimal | None = None
    warnings: str | None = None
    error_detail: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class ImportBatchRead(OrmModel):
    id: int
    import_type: str
    file_name: str | None = None
    code: str | None = None
    report_period: str | None = None
    status: str
    summary: str | None = None
    error_detail: str | None = None
    document_id: int | None = None
    parse_job_id: int | None = None
    created_at: datetime
    confirmed_at: datetime | None = None


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


class ManualFinancialInput(BaseModel):
    code: str
    report_period: str
    report_date: str | None = None
    revenue: Decimal | None = None
    gross_profit: Decimal | None = None
    gross_margin: Decimal | None = None
    net_profit: Decimal | None = None
    operating_cash_flow: Decimal | None = None
    total_assets: Decimal | None = None
    net_assets: Decimal | None = None
    eps: Decimal | None = None
    roe: Decimal | None = None
    rd_ratio: Decimal | None = None


class SegmentInput(BaseModel):
    segment_type: str = "product"
    segment_name: str
    revenue: Decimal | None = None
    cost: Decimal | None = None
    gross_profit: Decimal | None = None
    gross_margin: Decimal | None = None
    revenue_yoy: Decimal | None = None


class ExpenseInput(BaseModel):
    selling_expense: Decimal | None = None
    admin_expense: Decimal | None = None
    rd_expense: Decimal | None = None
    finance_expense: Decimal | None = None


class ReportExtractions(BaseModel):
    operating_profit: Decimal | None = None
    total_profit: Decimal | None = None
    non_recurring_net_profit: Decimal | None = None
    income_tax_expense: Decimal | None = None
    minority_interest: Decimal | None = None
    other_income: Decimal | None = None
    investment_income: Decimal | None = None
    fair_value_change_income: Decimal | None = None
    credit_impairment_loss: Decimal | None = None
    asset_impairment_loss: Decimal | None = None
    asset_disposal_income: Decimal | None = None
    cash_received_from_sales: Decimal | None = None
    cash_received_other_operating: Decimal | None = None
    inventory_total: Decimal | None = None
    inventory_impairment: Decimal | None = None
    capital_reserve: Decimal | None = None
    total_share_capital: Decimal | None = None
    rd_investment: Decimal | None = None
    rd_investment_ratio: Decimal | None = None
    patent_count: Decimal | None = None
    invention_patent_count: Decimal | None = None
    construction_in_progress: Decimal | None = None
    notes: dict[str, str] = {}


class ImportPreview(BaseModel):
    batch: ImportBatchRead
    financial: ManualFinancialInput
    segments: list[SegmentInput] = []
    candidate_facts: list[CandidateFactRead] = []
    expenses: ExpenseInput | None = None
    confidence: Decimal
    warnings: list[str] = []
    field_sources: dict[str, dict[str, str | None]] = {}
    extractions: ReportExtractions | None = None
    document: ReportDocumentRead | None = None
    parse_job: ReportParseJobRead | None = None
    is_duplicate: bool = False


class ReportDocumentUploadResult(BaseModel):
    document: ReportDocumentRead
    preview: ImportPreview
    is_duplicate: bool


class ConfirmImportRequest(BaseModel):
    financial: ManualFinancialInput
    segments: list[SegmentInput] = []
    expenses: ExpenseInput | None = None
    extractions: ReportExtractions | None = None


class ConfirmImportResult(BaseModel):
    batch: ImportBatchRead
    financial_records: int
    segment_records: int
    expense_records: int
    extraction_records: int
    candidate_records: int = 0
    confirmed_fact_records: int = 0
