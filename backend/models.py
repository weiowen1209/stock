from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


nullable = True


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    industry_chain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    industry_chain_detail: Mapped[str] = mapped_column(String(100), nullable=True)
    core_products: Mapped[str] = mapped_column(Text, nullable=True)
    supply_chain_tags: Mapped[str] = mapped_column(Text, nullable=True)
    list_date: Mapped[date] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StockCategory(Base, TimestampMixin):
    __tablename__ = "stock_categories"
    __table_args__ = (
        UniqueConstraint("industry_chain", "level2", "level3", name="uq_stock_category_levels"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry_chain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    level2: Mapped[str] = mapped_column(String(50), nullable=False)
    level3: Mapped[str] = mapped_column(String(50), nullable=False)


class KLineData(Base):
    __tablename__ = "kline_data"
    __table_args__ = (
        UniqueConstraint("code", "period", "date", name="uq_kline_code_period_date"),
        Index("idx_kline_code_period_date", "code", "period", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    volume: Mapped[int] = mapped_column(Integer, nullable=True)
    turnover: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    change_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class RealtimeQuote(Base):
    __tablename__ = "realtime_quotes"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    change_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    turnover_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    volume: Mapped[int] = mapped_column(Integer, nullable=True)
    turnover: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    market_cap: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=True)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class FinancialReport(Base):
    __tablename__ = "financial_reports"
    __table_args__ = (UniqueConstraint("code", "report_period", name="uq_financial_code_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    report_period: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=True)
    revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    gross_margin: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    operating_cash_flow: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    net_assets: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    eps: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=True)
    roe: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    rd_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=True)
    import_id: Mapped[int] = mapped_column(Integer, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class BusinessSegment(Base):
    __tablename__ = "business_segments"
    __table_args__ = (
        UniqueConstraint(
            "code", "report_period", "segment_type", "segment_name", name="uq_segment_identity"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    report_period: Mapped[str] = mapped_column(String(20), nullable=False)
    segment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    segment_name: Mapped[str] = mapped_column(String(100), nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    gross_margin: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    revenue_yoy: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=True)
    import_id: Mapped[int] = mapped_column(Integer, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)


class ExpenseItem(Base):
    __tablename__ = "expense_items"
    __table_args__ = (UniqueConstraint("code", "report_period", name="uq_expense_code_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    report_period: Mapped[str] = mapped_column(String(20), nullable=False)
    selling_expense: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    admin_expense: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    rd_expense: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    finance_expense: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=True)
    import_id: Mapped[int] = mapped_column(Integer, nullable=True)


class AnnualReportExtraction(Base):
    __tablename__ = "annual_report_extractions"
    __table_args__ = (UniqueConstraint("code", "report_period", name="uq_extraction_code_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    report_period: Mapped[str] = mapped_column(String(20), nullable=False)
    document_id: Mapped[int] = mapped_column(Integer, nullable=True)
    import_id: Mapped[int] = mapped_column(Integer, nullable=True)
    operating_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    total_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    non_recurring_net_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    income_tax_expense: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    minority_interest: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    other_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    investment_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    fair_value_change_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    credit_impairment_loss: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    asset_impairment_loss: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    asset_disposal_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    cash_received_from_sales: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    cash_received_other_operating: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    inventory_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    inventory_impairment: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    capital_reserve: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    total_share_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    rd_investment: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    rd_investment_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    patent_count: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    invention_patent_count: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    construction_in_progress: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    notes_json: Mapped[str] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ValuationMetric(Base):
    __tablename__ = "valuation_metrics"
    __table_args__ = (UniqueConstraint("code", "date", name="uq_valuation_code_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    pe: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    pb: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    peg: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    market_cap: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=True)


class IndustryIndex(Base):
    __tablename__ = "industry_index"
    __table_args__ = (UniqueConstraint("index_code", "date", name="uq_index_code_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_code: Mapped[str] = mapped_column(String(20), nullable=False)
    index_name: Mapped[str] = mapped_column(String(50), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    change_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=True)


class ReportDocument(Base, TimestampMixin):
    __tablename__ = "report_documents"
    __table_args__ = (UniqueConstraint("file_hash", name="uq_report_document_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=True)
    report_period: Mapped[str] = mapped_column(String(20), nullable=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    source_site: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="stored", nullable=False)


class ReportParseJob(Base):
    __tablename__ = "report_parse_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    warnings: Mapped[str] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ReportParseResult(Base):
    __tablename__ = "report_parse_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    financial_json: Mapped[str] = mapped_column(Text, nullable=False)
    segments_json: Mapped[str] = mapped_column(Text, nullable=False)
    expenses_json: Mapped[str] = mapped_column(Text, nullable=True)
    field_sources_json: Mapped[str] = mapped_column(Text, nullable=True)
    extractions_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=True)
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=True)
    report_period: Mapped[str] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str] = mapped_column(Text, nullable=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=True)
    parse_job_id: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ProviderHealth(Base):
    __tablename__ = "provider_health"

    provider: Mapped[str] = mapped_column(String(30), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_success_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_failure_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    next_probe_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
