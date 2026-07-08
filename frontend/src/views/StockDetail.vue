<template>
  <section class="detail-grid">
    <aside class="profile-card">
      <p>个股档案</p>
      <h2>{{ store.currentStock?.name ?? '请选择股票' }}</h2>
      <strong>{{ store.currentStock?.code }}</strong>
      <IndustryTag v-if="store.currentStock" :value="store.currentStock.industry_chain" />
      <p class="desc">{{ store.currentStock?.industry_chain_detail ?? '暂无细分定位' }}</p>
      <div class="tags">
        <span v-for="tag in parsedTags" :key="tag">{{ tag }}</span>
      </div>
      <div class="report-docs">
        <div class="doc-head">
          <strong>财报原文</strong>
          <button type="button" @click="loadReportDocuments">刷新</button>
        </div>
        <div v-if="reportDocuments.length" class="doc-list">
          <button v-for="doc in reportDocuments" :key="doc.id" type="button" @click="openDocument(doc.id)">
            {{ doc.report_period ?? '未识别报告期' }} · {{ doc.original_filename }}
          </button>
        </div>
        <p v-else class="doc-empty">暂无已保存PDF</p>
      </div>
    </aside>
    <div class="metrics">
      <MetricCard label="最新价" :value="store.currentQuote?.price" :hint="formatPercent(store.currentQuote?.change_pct)" />
      <MetricCard label="换手率" :value="formatPercent(store.currentQuote?.turnover_rate)" hint="实时行情" />
      <MetricCard label="成交额" :value="formatMoney(store.currentQuote?.turnover)" hint="市场活跃度" />
      <MetricCard label="总市值" :value="formatMoney(store.currentQuote?.market_cap)" hint="规模参考" />
    </div>
    <section class="deep-card">
      <div class="section-title">
        <p>Annual report data</p>
        <h3>年报深度字段</h3>
        <span>{{ latestExtraction?.report_period ?? '暂无确认字段' }}</span>
      </div>
      <div v-if="latestExtraction" class="deep-grid">
        <div v-for="item in deepFieldItems" :key="item.label" class="deep-item">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.hint }}</small>
        </div>
      </div>
      <div v-if="latestExtraction && noteItems.length" class="note-list">
        <div v-for="item in noteItems" :key="item.label">
          <strong>{{ item.label }}</strong>
          <p>{{ item.value }}</p>
        </div>
      </div>
      <p v-if="!latestExtraction" class="doc-empty">暂无已确认年报深度字段，请先在导入财报页确认入库。</p>
    </section>
    <div class="chart-area">
      <KLineChart :title="store.currentStock ? `${store.currentStock.name} ${store.currentStock.code}` : 'K线图'" :items="store.kline" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api, type ReportDocument } from '../api'
import IndustryTag from '../components/IndustryTag.vue'
import KLineChart from '../components/KLineChart.vue'
import MetricCard from '../components/MetricCard.vue'
import { useStockStore } from '../stores/stockStore'

const store = useStockStore()
const reportDocuments = ref<ReportDocument[]>([])
const latestExtraction = computed(() => {
  const rows = store.annualReportExtractions ?? []
  return rows.length ? rows[rows.length - 1] : null
})
const deepFieldItems = computed(() => {
  const item = latestExtraction.value
  if (!item) return []
  return [
    { label: '营业利润', value: formatMoney(item.operating_profit), hint: '利润主线' },
    { label: '扣非净利', value: formatMoney(item.non_recurring_net_profit), hint: '经营含金量' },
    { label: '投资收益', value: formatMoney(item.investment_income), hint: '非经营影响' },
    { label: '资产减值', value: formatMoney(item.asset_impairment_loss), hint: '存货/资产风险' },
    { label: '销售收现', value: formatMoney(item.cash_received_from_sales), hint: '回款验证' },
    { label: '存货', value: formatMoney(item.inventory_total), hint: '经营质量' },
    { label: '资本公积', value: formatMoney(item.capital_reserve), hint: '股本扩张潜力' },
    { label: '股本', value: formatMoney(item.total_share_capital), hint: '股本基础' },
    { label: '研发投入', value: formatMoney(item.rd_investment), hint: formatPercentPlain(item.rd_investment_ratio) },
    { label: '专利数量', value: formatCount(item.patent_count), hint: `发明 ${formatCount(item.invention_patent_count)}` },
    { label: '在建工程', value: formatMoney(item.construction_in_progress), hint: '产能建设' }
  ]
})
const noteItems = computed(() => {
  const notes = latestExtraction.value?.notes ?? {}
  const labels: Record<string, string> = {
    standards: '国家标准',
    core_technology: '核心技术',
    private_placement: '定向增发',
    fundraising: '募集资金',
    capacity_project: '产能项目',
    planetary_roller_screw: '行星滚柱丝杠'
  }
  return Object.entries(notes)
    .filter(([, value]) => Boolean(value))
    .map(([key, value]) => ({ label: labels[key] ?? key, value }))
})
const parsedTags = computed(() => {
  const tags = store.currentStock?.supply_chain_tags
  if (!tags) return []
  try {
    return JSON.parse(tags) as string[]
  } catch {
    return []
  }
})

watch(
  () => store.currentStock?.code,
  () => {
    void loadReportDocuments()
  },
  { immediate: true }
)

async function loadReportDocuments() {
  const code = store.currentStock?.code
  if (!code) {
    reportDocuments.value = []
    return
  }
  const response = await api.getReportDocuments({ code })
  reportDocuments.value = response.data ?? []
}

function openDocument(documentId: number) {
  window.open(`/api/imports/documents/${documentId}/file`, '_blank')
}

function formatPercent(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  const numeric = Number(value)
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(2)}%`
}

function formatMoney(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  const numeric = Number(value)
  const absValue = Math.abs(numeric)
  const sign = numeric < 0 ? '-' : ''
  if (absValue >= 100000000) return `${sign}${(absValue / 100000000).toFixed(2)}亿`
  if (absValue >= 10000) return `${sign}${(absValue / 10000).toFixed(2)}万`
  return numeric.toFixed(2)
}

function formatPercentPlain(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return `${Number(value).toFixed(2)}%`
}

function formatCount(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return `${Number(value).toFixed(0)}项`
}
</script>

<style scoped>
.detail-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 22px;
}

.profile-card,
.deep-card,
.chart-area {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 28px;
  background: rgba(7, 12, 23, 0.72);
}

.profile-card {
  min-height: 460px;
  padding: 28px;
}

p {
  margin: 0 0 10px;
  color: #7f93ad;
}

h2 {
  margin: 0 0 8px;
  color: #f8fbff;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 42px;
}

.profile-card > strong {
  display: block;
  margin-bottom: 20px;
  color: #7dd3fc;
  font-size: 20px;
}

.desc {
  margin-top: 24px;
  line-height: 1.7;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 24px;
}

.tags span {
  padding: 7px 10px;
  border-radius: 999px;
  color: #c4d7ef;
  background: rgba(148, 163, 184, 0.12);
}

.report-docs {
  margin-top: 28px;
  padding-top: 22px;
  border-top: 1px solid rgba(148, 163, 184, 0.14);
}

.doc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #d8e6f5;
}

.doc-head button,
.doc-list button {
  border: 0;
  color: #7dd3fc;
  background: transparent;
  cursor: pointer;
}

.doc-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.doc-list button {
  padding: 10px 12px;
  border-radius: 12px;
  text-align: left;
  background: rgba(125, 211, 252, 0.08);
}

.doc-empty {
  margin-top: 14px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.deep-card {
  grid-column: 2;
  padding: 24px;
}

.section-title {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 18px;
}

.section-title p,
.section-title h3 {
  margin: 0;
}

.section-title h3 {
  color: #f8fbff;
  font-size: 22px;
}

.section-title span {
  margin-left: auto;
  color: #7dd3fc;
}

.deep-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.deep-item,
.note-list div {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(125, 211, 252, 0.07);
}

.deep-item span,
.deep-item small,
.note-list p {
  color: #7f93ad;
}

.deep-item strong,
.note-list strong {
  color: #f8fbff;
}

.note-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.note-list p {
  margin: 0;
  line-height: 1.7;
}

.chart-area {
  grid-column: 2;
}

@media (max-width: 1180px) {
  .detail-grid,
  .metrics {
    grid-template-columns: 1fr;
  }

  .deep-card,
  .chart-area {
    grid-column: auto;
  }

  .deep-grid,
  .note-list {
    grid-template-columns: 1fr;
  }
}
</style>
