export interface ResponseMeta {
  source: string
  updated_at: string | null
  stale: boolean
}

export interface ApiError {
  code: string
  message: string
  detail?: unknown
}

export interface ApiResponse<T> {
  data: T | null
  meta: ResponseMeta
  error: ApiError | null
}

export interface Stock {
  code: string
  name: string
  exchange: string
  industry_chain: string
  industry_chain_detail: string | null
  core_products: string | null
  supply_chain_tags: string | null
  list_date: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface IndustryGroup {
  industry_chain: string
  stocks: Stock[]
}

export interface Quote {
  code: string
  price: string | number | null
  change_pct: string | number | null
  turnover_rate: string | number | null
  volume: number | null
  turnover: string | number | null
  market_cap: string | number | null
  source: string | null
  source_updated_at: string | null
  updated_at: string
}

export interface KLineItem {
  code: string
  period: string
  date: string
  open: string | number | null
  close: string | number | null
  high: string | number | null
  low: string | number | null
  volume: number | null
  turnover: string | number | null
  change_pct: string | number | null
  source: string | null
  updated_at: string
}

export interface SyncProgress {
  stage: string
  message: string
  provider: string | null
  code: string | null
  percent: number
  current: number
  total: number
  updated_at: string
}

export interface ProviderHealth {
  provider: string
  status: string
  consecutive_failures: number
  last_success_at: string | null
  last_failure_at: string | null
  next_probe_at: string | null
  error_message: string | null
}

export interface SyncCoverage {
  stock_pool_count: number
  quote_count: number
  kline_count: number
  missing_quotes_count: number
  missing_kline_count: number
  missing_total: number
  quote_updated_at: string | null
  quote_source_updated_at: string | null
  kline_start_date: string | null
  kline_end_date: string | null
  kline_period_count: number
}

export interface BaseDataImportResult {
  row_count: number
  parsed_count: number
  inserted_count: number
  updated_count: number
  disabled_count: number
  skipped_count: number
  active_count: number
  skipped_examples: Array<{ item: string; reason: string }>
}

export interface BaseDataStockUpsert {
  industry_chain: string
  industry_chain_detail_level2: string
  industry_chain_detail_level3: string
  name: string
  code: string | number
}

export interface StockCategory {
  id: number
  industry_chain: string
  level2: string
  level3: string
}

export interface StockCategoryWrite {
  industry_chain: string
  level2: string
  level3: string
}

export interface SyncStatus {
  latest_logs: Array<{
    task_type: string
    status: string
    records_count: number
    detail: string | null
    created_at: string | null
  }>
  missing_quotes: string[]
  missing_kline: string[]
  providers: ProviderHealth[]
  progress: SyncProgress
  coverage: SyncCoverage
}

export interface FinancialReport {
  code: string
  report_period: string
  report_date: string | null
  revenue: string | number | null
  gross_profit: string | number | null
  gross_margin: string | number | null
  net_profit: string | number | null
  operating_cash_flow: string | number | null
  total_assets: string | number | null
  net_assets: string | number | null
  eps: string | number | null
  roe: string | number | null
  rd_ratio: string | number | null
  source: string | null
  review_status: string
}

export interface BusinessSegment {
  report_period: string
  segment_type: string
  segment_name: string
  revenue: string | number | null
  cost: string | number | null
  gross_profit: string | number | null
  gross_margin: string | number | null
  revenue_yoy: string | number | null
  source: string | null
  review_status: string
}

export interface ExpenseItem {
  report_period: string
  selling_expense: string | number | null
  admin_expense: string | number | null
  rd_expense: string | number | null
  finance_expense: string | number | null
  source: string | null
}

export interface ValuationMetric {
  date: string
  pe: string | number | null
  pb: string | number | null
  peg: string | number | null
  market_cap: string | number | null
  source: string | null
}

export interface AnnualReportExtraction {
  code: string
  report_period: string
  document_id: number | null
  operating_profit: string | number | null
  total_profit: string | number | null
  non_recurring_net_profit: string | number | null
  income_tax_expense: string | number | null
  minority_interest: string | number | null
  other_income: string | number | null
  investment_income: string | number | null
  fair_value_change_income: string | number | null
  credit_impairment_loss: string | number | null
  asset_impairment_loss: string | number | null
  asset_disposal_income: string | number | null
  cash_received_from_sales: string | number | null
  cash_received_other_operating: string | number | null
  inventory_total: string | number | null
  inventory_impairment: string | number | null
  capital_reserve: string | number | null
  total_share_capital: string | number | null
  rd_investment: string | number | null
  rd_investment_ratio: string | number | null
  patent_count: string | number | null
  invention_patent_count: string | number | null
  construction_in_progress: string | number | null
  notes: Record<string, string>
  source: string | null
  review_status: string
}

export interface ScoreFactor {
  name: string
  score: number
  weight: number
  value: number | null
  benchmark: string
  comment: string
  level: string
  direction: string
}

export interface TrendBreakdownItem {
  report_period: string
  revenue_yoy: number | null
  revenue_qoq: number | null
  net_profit_yoy: number | null
  net_profit_qoq: number | null
  gross_margin_change: number | null
  cash_flow_match: number | null
  revenue_growth_contribution: number | null
  net_profit_growth_contribution: number | null
  signal: string
}

export interface DupontAnalysis {
  report_period: string
  roe: number | null
  net_margin: number | null
  asset_turnover: number | null
  equity_multiplier: number | null
  roe_estimated: number | null
  primary_driver: string
  interpretation: string
}

export interface PeerComparisonItem {
  metric: string
  company_value: number | null
  peer_median: number | null
  percentile: number | null
  conclusion: string
}

export interface ValuationPercentile {
  metric: string
  current: number | null
  percentile: number | null
  label: string
  comment: string
  sample_size: number
  upside_room: number | null
}

export interface AiInsight {
  conclusion: string
  positives: string[]
  risks: string[]
  watch_items: string[]
}

export interface FundamentalModule {
  title: string
  summary: string
  key_points: string[]
  status: string
}

export interface ImpactFactor {
  name: string
  category: string
  impact: number | null
  direction: string
  explanation: string
}

export interface SegmentContributionItem {
  report_period: string
  segment_type: string
  segment_name: string
  revenue: number | null
  gross_profit: number | null
  gross_margin: number | null
  revenue_yoy: number | null
  gross_profit_share: number | null
  role: string
}

export interface WatchSignal {
  name: string
  value: string
  judgement: string
  source: string
}

export interface DeepFundamentalAnalysis {
  code: string
  report_period: string | null
  overall_score: number
  growth_potential_score: number
  quality_score: number
  valuation_score: number
  score_factors: ScoreFactor[]
  trend_breakdown: TrendBreakdownItem[]
  dupont: DupontAnalysis[]
  peer_comparison: PeerComparisonItem[]
  valuation_percentiles: ValuationPercentile[]
  ai_insight: AiInsight
  analysis_modules: FundamentalModule[]
  impact_factors: ImpactFactor[]
  segment_contribution: SegmentContributionItem[]
  watch_signals: WatchSignal[]
}

export interface TechnicalIndicators {
  code: string
  period: string
  dates: string[]
  close: number[]
  ma5: Array<number | null>
  ma10: Array<number | null>
  ma20: Array<number | null>
  macd: Array<number | null>
  signal: Array<number | null>
  histogram: Array<number | null>
  rsi6: Array<number | null>
}

export interface ReportDocument {
  id: number
  code: string | null
  report_period: string | null
  report_type: string | null
  original_filename: string
  stored_filename: string
  file_hash: string
  file_size: number
  mime_type: string | null
  page_count: number | null
  source_site: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface ReportParseJob {
  id: number
  document_id: number
  parser_version: string
  status: string
  confidence: string | number | null
  warnings: string | null
  error_detail: string | null
  started_at: string
  finished_at: string | null
}

export interface ImportBatch {
  id: number
  import_type: string
  file_name: string | null
  code: string | null
  report_period: string | null
  status: string
  summary: string | null
  error_detail: string | null
  document_id: number | null
  parse_job_id: number | null
  created_at: string
  confirmed_at: string | null
}

export interface ManualFinancialInput {
  code: string
  report_period: string
  report_date: string | null
  revenue: string | number | null
  gross_profit: string | number | null
  gross_margin: string | number | null
  net_profit: string | number | null
  operating_cash_flow: string | number | null
  total_assets: string | number | null
  net_assets: string | number | null
  eps: string | number | null
  roe: string | number | null
  rd_ratio: string | number | null
}

export interface SegmentInput {
  segment_type: string
  segment_name: string
  revenue: string | number | null
  cost: string | number | null
  gross_profit: string | number | null
  gross_margin: string | number | null
  revenue_yoy: string | number | null
}

export interface ExpenseInput {
  selling_expense: string | number | null
  admin_expense: string | number | null
  rd_expense: string | number | null
  finance_expense: string | number | null
}

export interface FieldSource {
  value?: string
  label?: string
  section?: string
  confidence?: string
  unit?: string
  line?: string
}

export interface ReportExtractions {
  operating_profit: string | number | null
  total_profit: string | number | null
  non_recurring_net_profit: string | number | null
  income_tax_expense: string | number | null
  minority_interest: string | number | null
  other_income: string | number | null
  investment_income: string | number | null
  fair_value_change_income: string | number | null
  credit_impairment_loss: string | number | null
  asset_impairment_loss: string | number | null
  asset_disposal_income: string | number | null
  cash_received_from_sales: string | number | null
  cash_received_other_operating: string | number | null
  inventory_total: string | number | null
  inventory_impairment: string | number | null
  capital_reserve: string | number | null
  total_share_capital: string | number | null
  rd_investment: string | number | null
  rd_investment_ratio: string | number | null
  patent_count: string | number | null
  invention_patent_count: string | number | null
  construction_in_progress: string | number | null
  notes: Record<string, string>
}

export interface ImportPreview {
  batch: ImportBatch
  financial: ManualFinancialInput
  segments: SegmentInput[]
  expenses: ExpenseInput | null
  confidence: string | number
  warnings: string[]
  field_sources: Record<string, FieldSource>
  extractions: ReportExtractions | null
  document: ReportDocument | null
  parse_job: ReportParseJob | null
  is_duplicate: boolean
}

export interface ReportDocumentUploadResult {
  document: ReportDocument
  preview: ImportPreview
  is_duplicate: boolean
}

export interface ConfirmImportRequest {
  financial: ManualFinancialInput
  segments: SegmentInput[]
  expenses: ExpenseInput | null
  extractions: ReportExtractions | null
}

export interface ConfirmImportResult {
  batch: ImportBatch
  financial_records: number
  segment_records: number
  expense_records: number
  extraction_records: number
}
