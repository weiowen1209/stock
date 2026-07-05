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


class ImportPreview(BaseModel):
    batch: ImportBatchRead
    financial: ManualFinancialInput
    segments: list[SegmentInput] = []
    expenses: ExpenseInput | None = None
    confidence: Decimal
    warnings: list[str] = []
    field_sources: dict[str, dict[str, str | None]] = {}
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


class ConfirmImportResult(BaseModel):
    batch: ImportBatchRead
    financial_records: int
    segment_records: int
    expense_records: int
