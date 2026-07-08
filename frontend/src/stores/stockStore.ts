import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  api,
  type AnnualReportExtraction,
  type BusinessSegment,
  type DeepFundamentalAnalysis,
  type ExpenseItem,
  type FinancialReport,
  type IndustryGroup,
  type KLineItem,
  type Quote,
  type Stock,
  type SyncStatus,
  type TechnicalIndicators,
  type ValuationMetric
} from '../api'

export const useStockStore = defineStore('stock', () => {
  const stocks = ref<Stock[]>([])
  const groups = ref<IndustryGroup[]>([])
  const quotes = ref<Quote[]>([])
  const kline = ref<KLineItem[]>([])
  const syncStatus = ref<SyncStatus | null>(null)
  const financialReports = ref<FinancialReport[]>([])
  const businessSegments = ref<BusinessSegment[]>([])
  const expenses = ref<ExpenseItem[]>([])
  const valuation = ref<ValuationMetric[]>([])
  const annualReportExtractions = ref<AnnualReportExtraction[]>([])
  const deepFundamental = ref<DeepFundamentalAnalysis | null>(null)
  const technical = ref<TechnicalIndicators | null>(null)
  const klinePeriod = ref<'day' | 'week' | 'month'>('day')
  const currentCode = ref<string>('')
  const selectedIndustry = ref<string>('全部')
  const selectedSubIndustry = ref<string>('全部')
  const selectedSub2Industry = ref<string>('全部')
  const loading = ref(false)
  const syncing = ref(false)
  const error = ref<string | null>(null)

  const currentStock = computed(() => stocks.value.find((item) => item.code === currentCode.value) ?? null)
  const currentQuote = computed(() => quotes.value.find((item) => item.code === currentCode.value) ?? null)
  const industries = computed(() => ['全部', ...groups.value.map((item) => item.industry_chain)])
  const subIndustries = computed(() => {
    const values = stocks.value
      .filter((item) => selectedIndustry.value === '全部' || item.industry_chain === selectedIndustry.value)
      .map((item) => splitIndustryDetail(item.industry_chain_detail)[0])
      .filter((item): item is string => Boolean(item))
    return ['全部', ...Array.from(new Set(values))]
  })
  const sub2Industries = computed(() => {
    const values = stocks.value
      .filter((item) => {
        if (selectedIndustry.value !== '全部' && item.industry_chain !== selectedIndustry.value) return false
        const [level2] = splitIndustryDetail(item.industry_chain_detail)
        if (selectedSubIndustry.value === '全部') return true
        return level2 === selectedSubIndustry.value
      })
      .map((item) => splitIndustryDetail(item.industry_chain_detail)[1])
      .filter((item): item is string => Boolean(item))
    return ['全部', ...Array.from(new Set(values))]
  })
  const filteredStocks = computed(() => {
    return stocks.value.filter((item) => {
      const [level2, level3] = splitIndustryDetail(item.industry_chain_detail)
      const matchIndustry = selectedIndustry.value === '全部' || item.industry_chain === selectedIndustry.value
      const matchSubIndustry = selectedSubIndustry.value === '全部' || level2 === selectedSubIndustry.value
      const matchSub2Industry = selectedSub2Industry.value === '全部' || level3 === selectedSub2Industry.value
      return matchIndustry && matchSubIndustry && matchSub2Industry
    })
  })

  function setSelectedIndustry(industry: string) {
    selectedIndustry.value = industry
    selectedSubIndustry.value = '全部'
    selectedSub2Industry.value = '全部'
  }

  function setSelectedSubIndustry(subIndustry: string) {
    selectedSubIndustry.value = subIndustry
    selectedSub2Industry.value = '全部'
  }

  function setSelectedSub2Industry(sub2Industry: string) {
    selectedSub2Industry.value = sub2Industry
  }

  function splitIndustryDetail(detail: string | null | undefined) {
    return (detail ?? '').split('/').map((item) => item.trim()).filter(Boolean)
  }

  async function loadInitialData() {
    loading.value = true
    error.value = null
    try {
      const [stockResponse, groupResponse, quoteResponse, statusResponse] = await Promise.all([
        api.getStocks(),
        api.getStocksByIndustry(),
        api.getQuotes(),
        api.getSyncStatus()
      ])
      stocks.value = stockResponse.data ?? []
      groups.value = groupResponse.data ?? []
      quotes.value = quoteResponse.data ?? []
      syncStatus.value = statusResponse.data
      if (!currentCode.value && stocks.value.length) {
        currentCode.value = stocks.value[0].code
      }
      if (currentCode.value) {
        await loadStockAnalysis(currentCode.value)
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function selectStock(code: string) {
    currentCode.value = code
    await loadStockAnalysis(code)
  }

  async function loadStockAnalysis(code: string) {
    await Promise.all([loadKline(code), loadFundamentals(code), loadTechnical(code)])
  }

  async function loadKline(code: string, period = klinePeriod.value) {
    try {
      const response = await api.getKline(code, period)
      kline.value = response.data ?? []
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'K线加载失败'
      kline.value = []
    }
  }

  async function loadFundamentals(code: string) {
    try {
      const [reports, segments, expenseRows, valuationRows, deepAnalysis, extractionRows] = await Promise.all([
        api.getFinancialReports(code),
        api.getBusinessSegments(code),
        api.getExpenses(code),
        api.getValuation(code),
        api.getDeepFundamentalAnalysis(code),
        api.getAnnualReportExtractions(code)
      ])
      financialReports.value = reports.data ?? []
      businessSegments.value = segments.data ?? []
      expenses.value = expenseRows.data ?? []
      valuation.value = valuationRows.data ?? []
      deepFundamental.value = deepAnalysis.data
      annualReportExtractions.value = extractionRows.data ?? []
    } catch (err) {
      error.value = err instanceof Error ? err.message : '基本面加载失败'
      financialReports.value = []
      businessSegments.value = []
      expenses.value = []
      valuation.value = []
      annualReportExtractions.value = []
      deepFundamental.value = null
    }
  }

  async function loadTechnical(code: string, period = klinePeriod.value) {
    try {
      const response = await api.getTechnical(code, period)
      technical.value = response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : '技术指标加载失败'
      technical.value = null
    }
  }

  async function setKlinePeriod(period: 'day' | 'week' | 'month') {
    if (klinePeriod.value === period) return
    klinePeriod.value = period
    if (!currentCode.value) return
    await Promise.all([loadKline(currentCode.value, period), loadTechnical(currentCode.value, period)])
  }

  async function refreshAfterSync() {
    const [quoteResponse, statusResponse] = await Promise.all([
      api.getQuotes(stocks.value.map((item) => item.code)),
      api.getSyncStatus()
    ])
    quotes.value = quoteResponse.data ?? []
    syncStatus.value = statusResponse.data
    if (currentCode.value) {
      await loadStockAnalysis(currentCode.value)
    }
  }

  async function syncStockByCode(code: string, forceFull = false) {
    if (!code) return
    currentCode.value = code
    syncing.value = true
    error.value = null
    try {
      await api.triggerSync([code], undefined, forceFull)
      await refreshAfterSync()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '同步失败'
    } finally {
      syncing.value = false
    }
  }

  async function syncStocksByCodes(codes: string[], forceFull = false) {
    if (!codes.length) return
    currentCode.value = codes[0]
    syncing.value = true
    error.value = null
    try {
      await api.triggerSync(codes, undefined, forceFull)
      await refreshAfterSync()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '批量同步失败'
    } finally {
      syncing.value = false
    }
  }

  async function syncAllStocks() {
    syncing.value = true
    error.value = null
    try {
      await api.triggerSync()
      await refreshAfterSync()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '同步全部股票失败'
    } finally {
      syncing.value = false
    }
  }

  return {
    stocks,
    groups,
    quotes,
    kline,
    syncStatus,
    financialReports,
    businessSegments,
    expenses,
    valuation,
    annualReportExtractions,
    deepFundamental,
    technical,
    klinePeriod,
    currentCode,
    selectedIndustry,
    selectedSubIndustry,
    selectedSub2Industry,
    loading,
    syncing,
    error,
    currentStock,
    currentQuote,
    industries,
    subIndustries,
    sub2Industries,
    filteredStocks,
    setSelectedIndustry,
    setSelectedSubIndustry,
    setSelectedSub2Industry,
    loadInitialData,
    selectStock,
    setKlinePeriod,
    syncStockByCode,
    syncStocksByCodes,
    syncAllStocks
  }
})
