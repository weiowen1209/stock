<template>
  <section class="status-panel">
    <div class="status-title">
      <p>股票数据状态</p>
      <strong>{{ healthLabel }}</strong>
      <small>{{ healthHint }}</small>
    </div>

    <div class="metric-grid">
      <div v-for="metric in metrics" :key="metric.label" class="metric-card" :class="metric.tone">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.hint }}</small>
      </div>
    </div>

    <el-button type="primary" :loading="syncing" @click="$emit('sync-all')">同步全部股票池</el-button>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SyncProgress, SyncStatus } from '../api'

const props = defineProps<{
  status: SyncStatus | null
  progress: SyncProgress | null
  syncing: boolean
}>()

defineEmits<{
  'sync-all': []
}>()

const coverage = computed(() => props.status?.coverage ?? null)
const stockCount = computed(() => coverage.value?.stock_pool_count ?? 0)
const quoteCount = computed(() => coverage.value?.quote_count ?? 0)
const klineCount = computed(() => coverage.value?.kline_count ?? 0)
const missingQuotes = computed(() => coverage.value?.missing_quotes_count ?? props.status?.missing_quotes.length ?? 0)
const missingKline = computed(() => coverage.value?.missing_kline_count ?? props.status?.missing_kline.length ?? 0)
const missingTotal = computed(() => coverage.value?.missing_total ?? missingQuotes.value + missingKline.value)
const currentProgress = computed(() => props.progress ?? props.status?.progress ?? null)
const syncSummary = computed(() => {
  const total = currentProgress.value?.total ?? 0
  if (!props.syncing || !total) return null
  return `${currentProgress.value?.current ?? 0}/${total}，${currentProgress.value?.message ?? '同步中'}`
})
const quoteCoverageText = computed(() => formatCoverage(quoteCount.value, stockCount.value))
const klineCoverageText = computed(() => formatCoverage(klineCount.value, stockCount.value))
const quoteUpdatedAtText = computed(() => formatDateTime(coverage.value?.quote_source_updated_at ?? coverage.value?.quote_updated_at))
const klineRangeText = computed(() => {
  const start = formatDate(coverage.value?.kline_start_date)
  const end = formatDate(coverage.value?.kline_end_date)
  if (start === '-' || end === '-') return '-'
  return `${start} 至 ${end}`
})
const healthLabel = computed(() => {
  if (!stockCount.value) return '暂无股票池数据'
  if (missingTotal.value === 0) return '数据覆盖完整'
  return `仍缺失 ${missingTotal.value} 项`
})
const healthHint = computed(() => syncSummary.value ?? '看股票池覆盖、行情更新时间和K线时间范围')
const metrics = computed(() => [
  {
    label: '股票数量',
    value: stockCount.value ? `${stockCount.value} 只` : '-',
    hint: `行情覆盖 ${quoteCoverageText.value}`,
    tone: 'primary'
  },
  {
    label: '行情数据截止',
    value: quoteUpdatedAtText.value,
    hint: `覆盖 ${quoteCoverageText.value}`,
    tone: missingQuotes.value ? 'warning' : 'success'
  },
  {
    label: 'K线数据范围',
    value: klineRangeText.value,
    hint: `覆盖 ${klineCoverageText.value}，${coverage.value?.kline_period_count ?? 0} 个周期`,
    tone: missingKline.value ? 'warning' : 'success'
  },
  {
    label: '缺失数据',
    value: `${missingTotal.value} 项`,
    hint: `行情 ${missingQuotes.value}，K线 ${missingKline.value}`,
    tone: missingTotal.value ? 'danger' : 'success'
  }
])

function formatCoverage(count: number, total: number) {
  if (!total) return '-'
  return `${count}/${total}`
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  return value.slice(0, 10)
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return formatDate(value)
  return date.toLocaleDateString()
}
</script>

<style scoped>
.status-panel {
  display: grid;
  grid-template-columns: minmax(190px, 0.65fr) minmax(620px, 1.8fr) auto;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border: 1px solid rgba(45, 212, 191, 0.22);
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.14), rgba(15, 23, 42, 0.76));
}

.status-title p {
  margin: 0 0 6px;
  color: #86a6c4;
  font-size: 12px;
}

.status-title strong {
  display: block;
  color: #f8fbff;
  font-size: 18px;
  line-height: 1.35;
}

.status-title small {
  display: block;
  margin-top: 6px;
  color: #8ba2bd;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  min-height: 76px;
  padding: 10px 12px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.42);
}

.metric-card span,
.metric-card small {
  display: block;
  color: #8ba2bd;
  font-size: 12px;
}

.metric-card strong {
  display: block;
  margin: 7px 0 5px;
  color: #f8fbff;
  font-size: 16px;
  line-height: 1.25;
}

.metric-card.success strong {
  color: #5eead4;
}

.metric-card.warning strong {
  color: #fbbf24;
}

.metric-card.danger strong {
  color: #fb7185;
}

@media (max-width: 1180px) {
  .status-panel,
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
