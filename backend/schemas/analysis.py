from datetime import date
from decimal import Decimal

from backend.schemas.common import OrmModel


class FinancialReportRead(OrmModel):
    code: str
    report_period: str
    report_date: date | None = None
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
    source: str | None = None
    review_status: str


class BusinessSegmentRead(OrmModel):
    report_period: str
    segment_type: str
    segment_name: str
    revenue: Decimal | None = None
    cost: Decimal | None = None
    gross_profit: Decimal | None = None
    gross_margin: Decimal | None = None
    revenue_yoy: Decimal | None = None
    source: str | None = None
    review_status: str


class ExpenseItemRead(OrmModel):
    report_period: str
    selling_expense: Decimal | None = None
    admin_expense: Decimal | None = None
    rd_expense: Decimal | None = None
    finance_expense: Decimal | None = None
    source: str | None = None


class AnnualReportExtractionRead(OrmModel):
    code: str
    report_period: str
    document_id: int | None = None
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
    source: str | None = None
    review_status: str


class ValuationRead(OrmModel):
    date: date
    pe: Decimal | None = None
    pb: Decimal | None = None
    peg: Decimal | None = None
    market_cap: Decimal | None = None
    source: str | None = None


class ScoreFactor(OrmModel):
    name: str
    score: float
    weight: float
    value: float | None = None
    benchmark: str
    comment: str
    level: str
    direction: str


class TrendBreakdownItem(OrmModel):
    report_period: str
    revenue_yoy: float | None = None
    revenue_qoq: float | None = None
    net_profit_yoy: float | None = None
    net_profit_qoq: float | None = None
    gross_margin_change: float | None = None
    cash_flow_match: float | None = None
    revenue_growth_contribution: float | None = None
    net_profit_growth_contribution: float | None = None
    signal: str


class DupontAnalysis(OrmModel):
    report_period: str
    roe: float | None = None
    net_margin: float | None = None
    asset_turnover: float | None = None
    equity_multiplier: float | None = None
    roe_estimated: float | None = None
    primary_driver: str
    interpretation: str


class PeerComparisonItem(OrmModel):
    metric: str
    company_value: float | None = None
    peer_median: float | None = None
    percentile: float | None = None
    conclusion: str


class ValuationPercentile(OrmModel):
    metric: str
    current: float | None = None
    percentile: float | None = None
    label: str
    comment: str
    sample_size: int
    upside_room: float | None = None


class AiInsight(OrmModel):
    conclusion: str
    positives: list[str]
    risks: list[str]
    watch_items: list[str]


class FundamentalModule(OrmModel):
    title: str
    summary: str
    key_points: list[str]
    status: str = "neutral"


class ImpactFactor(OrmModel):
    name: str
    category: str
    impact: float | None = None
    direction: str
    explanation: str


class SegmentContributionItem(OrmModel):
    report_period: str
    segment_type: str
    segment_name: str
    revenue: float | None = None
    gross_profit: float | None = None
    gross_margin: float | None = None
    revenue_yoy: float | None = None
    gross_profit_share: float | None = None
    role: str


class WatchSignal(OrmModel):
    name: str
    value: str
    judgement: str
    source: str


class DeepFundamentalAnalysis(OrmModel):
    code: str
    report_period: str | None = None
    overall_score: float
    growth_potential_score: float
    quality_score: float
    valuation_score: float
    score_factors: list[ScoreFactor]
    trend_breakdown: list[TrendBreakdownItem]
    dupont: list[DupontAnalysis]
    peer_comparison: list[PeerComparisonItem]
    valuation_percentiles: list[ValuationPercentile]
    ai_insight: AiInsight
    analysis_modules: list[FundamentalModule] = []
    impact_factors: list[ImpactFactor] = []
    segment_contribution: list[SegmentContributionItem] = []
    watch_signals: list[WatchSignal] = []


class TechnicalIndicators(OrmModel):
    code: str
    period: str
    dates: list[date]
    close: list[float]
    ma5: list[float | None]
    ma10: list[float | None]
    ma20: list[float | None]
    macd: list[float | None]
    signal: list[float | None]
    histogram: list[float | None]
    rsi6: list[float | None]
