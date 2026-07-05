<template>
  <section class="detail-grid">
    <aside class="profile-card">
      <p>个股档案</p>
      <h2>{{ stock?.name ?? '请选择股票' }}</h2>
      <strong>{{ stock?.code }}</strong>
      <IndustryTag v-if="stock" :value="stock.industry_chain" />
      <p class="desc">{{ stock?.industry_chain_detail ?? '暂无细分定位' }}</p>
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
      <MetricCard label="最新价" :value="quote?.price" :hint="formatPercent(quote?.change_pct)" />
      <MetricCard label="换手率" :value="formatPercent(quote?.turnover_rate)" hint="实时行情" />
      <MetricCard label="成交额" :value="formatMoney(quote?.turnover)" hint="市场活跃度" />
      <MetricCard label="总市值" :value="formatMoney(quote?.market_cap)" hint="规模参考" />
    </div>
    <div class="chart-area">
      <KLineChart :title="stock ? `${stock.name} ${stock.code}` : 'K线图'" :items="store.kline" />
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
const stock = computed(() => store.currentStock)
const quote = computed(() => store.currentQuote)
const reportDocuments = ref<ReportDocument[]>([])
const parsedTags = computed(() => {
  if (!stock.value?.supply_chain_tags) return []
  try {
    return JSON.parse(stock.value.supply_chain_tags) as string[]
  } catch {
    return []
  }
})

watch(
  () => stock.value?.code,
  () => {
    void loadReportDocuments()
  },
  { immediate: true }
)

async function loadReportDocuments() {
  if (!stock.value?.code) {
    reportDocuments.value = []
    return
  }
  const response = await api.getReportDocuments({ code: stock.value.code })
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
  if (numeric >= 100000000) return `${(numeric / 100000000).toFixed(2)}亿`
  if (numeric >= 10000) return `${(numeric / 10000).toFixed(2)}万`
  return numeric.toFixed(2)
}
</script>

<style scoped>
.detail-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 22px;
}

.profile-card,
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

.chart-area {
  grid-column: 2;
}

@media (max-width: 1180px) {
  .detail-grid,
  .metrics {
    grid-template-columns: 1fr;
  }

  .chart-area {
    grid-column: auto;
  }
}
</style>
