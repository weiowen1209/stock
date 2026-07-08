import axios from 'axios'
import NProgress from 'nprogress'
import type {
  AnnualReportExtraction,
  ApiResponse,
  BaseDataImportResult,
  BaseDataStockUpsert,
  BusinessSegment,
  CandidateFact,
  ExpenseItem,
  ConfirmImportRequest,
  ConfirmImportResult,
  ConfirmedFact,
  DeepFundamentalAnalysis,
  EvidenceItem,
  FinancialReport,
  ImportBatch,
  ImportPreview,
  IndustryGroup,
  KLineItem,
  Quote,
  FieldSource,
  ReportExtractions,
  ReportDocument,
  ReportDocumentUploadResult,
  Stock,
  StockCategory,
  StockCategoryWrite,
  SyncProgress,
  SyncStatus,
  TechnicalIndicators,
  ValuationMetric
} from './types'

const DEFAULT_TIMEOUT = 15000
const SYNC_TIMEOUT = 10 * 60 * 1000

const client = axios.create({
  baseURL: '',
  timeout: DEFAULT_TIMEOUT
})

client.interceptors.request.use((config) => {
  NProgress.start()
  return config
})

client.interceptors.response.use(
  (response) => {
    NProgress.done()
    return response
  },
  (error) => {
    NProgress.done()
    return Promise.reject(error)
  }
)

async function request<T>(url: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> {
  const response = await client.get<ApiResponse<T>>(url, { params })
  if (response.data.error) {
    throw new Error(response.data.error.message)
  }
  return response.data
}

export const api = {
  getBaseDataStocks(params?: { include_inactive?: boolean }) {
    return request<Stock[]>('/api/base-data/stocks', params)
  },
  async importBaseDataExcel(file: File, mode: 'replace' | 'append' = 'replace') {
    const formData = new FormData()
    formData.append('file', file)
    const response = await client.post<ApiResponse<BaseDataImportResult>>('/api/base-data/stocks/import-excel', formData, { params: { mode } })
    return response.data
  },
  async upsertBaseDataStock(payload: BaseDataStockUpsert) {
    const response = await client.post<ApiResponse<Stock>>('/api/base-data/stocks', payload)
    return response.data
  },
  async deleteBaseDataStock(code: string) {
    await client.delete(`/api/base-data/stocks/${code}`)
  },
  async downloadBaseDataTemplate() {
    const response = await client.get<Blob>('/api/base-data/stocks/template', { responseType: 'blob' })
    return response.data
  },
  getStockCategories() {
    return request<StockCategory[]>('/api/base-data/categories')
  },
  async createStockCategory(payload: StockCategoryWrite) {
    const response = await client.post<ApiResponse<StockCategory>>('/api/base-data/categories', payload)
    return response.data
  },
  async updateStockCategory(id: number, payload: StockCategoryWrite) {
    const response = await client.put<ApiResponse<StockCategory>>(`/api/base-data/categories/${id}`, payload)
    return response.data
  },
  async deleteStockCategory(id: number) {
    await client.delete(`/api/base-data/categories/${id}`)
  },
  getStocks(params?: { industry_chain?: string; keyword?: string }) {
    return request<Stock[]>('/api/stocks', params)
  },
  getStocksByIndustry() {
    return request<IndustryGroup[]>('/api/stocks/by-industry')
  },
  getQuotes(codes?: string[]) {
    return request<Quote[]>('/api/quotes', codes?.length ? { codes } : undefined)
  },
  getKline(code: string, period = 'day') {
    return request<KLineItem[]>(`/api/kline/${code}`, { period })
  },
  getSyncStatus() {
    return request<SyncStatus>('/api/sync/status')
  },
  getFinancialReports(code: string) {
    return request<FinancialReport[]>(`/api/fundamentals/${code}`)
  },
  getBusinessSegments(code: string) {
    return request<BusinessSegment[]>(`/api/fundamentals/${code}/segments`)
  },
  getExpenses(code: string) {
    return request<ExpenseItem[]>(`/api/fundamentals/${code}/expenses`)
  },
  getValuation(code: string) {
    return request<ValuationMetric[]>(`/api/valuation/${code}`)
  },
  getDeepFundamentalAnalysis(code: string) {
    return request<DeepFundamentalAnalysis>(`/api/fundamentals/${code}/deep-analysis`)
  },
  getAnnualReportExtractions(code: string) {
    return request<AnnualReportExtraction[]>(`/api/fundamentals/${code}/extractions`)
  },
  getTechnical(code: string, period = 'day') {
    return request<TechnicalIndicators>(`/api/technical/${code}`, { period })
  },
  async triggerSync(codes?: string[], startDate?: string, forceFull?: boolean) {
    const response = await client.post(
      '/api/sync/trigger',
      {
        codes,
        include_quotes: true,
        include_kline: true,
        periods: ['day', 'week', 'month'],
        start_date: startDate ?? '2022-01-01',
        force_full: forceFull ?? false
      },
      { timeout: SYNC_TIMEOUT }
    )
    return response.data
  },
  async uploadImport(file: File, code?: string, reportPeriod?: string) {
    const formData = new FormData()
    formData.append('file', file)
    if (code) formData.append('code', code)
    if (reportPeriod) formData.append('report_period', reportPeriod)
    const response = await client.post<ApiResponse<ImportPreview>>('/api/imports/upload', formData)
    return response.data
  },
  async uploadReportDocument(file: File, code?: string, reportPeriod?: string, sourceSite?: string) {
    const formData = new FormData()
    formData.append('file', file)
    if (code) formData.append('code', code)
    if (reportPeriod) formData.append('report_period', reportPeriod)
    if (sourceSite) formData.append('source_site', sourceSite)
    const response = await client.post<ApiResponse<ReportDocumentUploadResult>>('/api/imports/documents/upload', formData)
    return response.data
  },
  getReportDocuments(params?: { code?: string }) {
    return request<ReportDocument[]>('/api/imports/documents', params)
  },
  getReportDocumentPreview(documentId: number) {
    return request<ImportPreview>(`/api/imports/documents/${documentId}/preview`)
  },
  async reparseReportDocument(documentId: number) {
    const response = await client.post<ApiResponse<ImportPreview>>(`/api/imports/documents/${documentId}/parse`)
    return response.data
  },
  async createManualImport(payload: ConfirmImportRequest) {
    const response = await client.post<ApiResponse<ImportPreview>>('/api/imports/manual', payload)
    return response.data
  },
  async confirmImport(batchId: number, payload: ConfirmImportRequest) {
    const response = await client.post<ApiResponse<ConfirmImportResult>>(`/api/imports/${batchId}/confirm`, payload)
    return response.data
  },
  getCandidateFacts(params?: { batch_id?: number }) {
    return request<CandidateFact[]>('/api/imports/candidate-facts', params)
  },
  getEvidenceItems(params?: { batch_id?: number; code?: string }) {
    return request<EvidenceItem[]>('/api/imports/evidence', params)
  },
  getConfirmedFacts(params?: { code?: string; period?: string }) {
    return request<ConfirmedFact[]>('/api/imports/confirmed-facts', params)
  },
  getImportBatches() {
    return request<ImportBatch[]>('/api/imports')
  }
}

export type {
  AnnualReportExtraction,
  BaseDataImportResult,
  BaseDataStockUpsert,
  BusinessSegment,
  CandidateFact,
  ConfirmImportRequest,
  ConfirmImportResult,
  ConfirmedFact,
  DeepFundamentalAnalysis,
  EvidenceItem,
  ExpenseItem,
  FinancialReport,
  ImportBatch,
  ImportPreview,
  IndustryGroup,
  KLineItem,
  Quote,
  FieldSource,
  ReportExtractions,
  ReportDocument,
  ReportDocumentUploadResult,
  Stock,
  StockCategory,
  StockCategoryWrite,
  SyncProgress,
  SyncStatus,
  TechnicalIndicators,
  ValuationMetric
}
