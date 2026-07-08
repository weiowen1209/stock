<template>
  <section class="chart-shell">
    <div class="chart-head">
      <div>
        <p>K线走势</p>
        <strong>{{ title }}</strong>
      </div>
      <div class="chart-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          size="small"
          :clearable="false"
        />
        <el-segmented :model-value="period" :options="periodOptions" size="small" @change="handlePeriodChange" />
        <SourceBadge :source="latestSource" :updated-at="latestUpdatedAt" :stale="!items.length" />
      </div>
    </div>
    <v-chart v-if="filteredItems.length" class="chart" :option="option" autoresize />
    <div v-else class="empty-chart">{{ items.length ? '当前日期范围暂无K线数据' : '暂无K线数据，请先发起股票同步' }}</div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart, BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent, LegendComponent } from 'echarts/components'
import type { KLineItem, TechnicalIndicators } from '../api'
import SourceBadge from './SourceBadge.vue'

use([CanvasRenderer, CandlestickChart, BarChart, LineChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent])

const props = withDefaults(defineProps<{
  title: string
  items: KLineItem[]
  period?: 'day' | 'week' | 'month'
  technical?: TechnicalIndicators | null
}>(), {
  period: 'day'
})

const emit = defineEmits<{
  (event: 'period-change', period: 'day' | 'week' | 'month'): void
  (event: 'date-range-change', range: [string, string]): void
}>()

const periodOptions = [
  { label: '日线', value: 'day' },
  { label: '周线', value: 'week' },
  { label: '月线', value: 'month' }
]
const dateRange = ref<[string, string]>(defaultHalfYearRange())

function defaultHalfYearRange(): [string, string] {
  const end = new Date()
  const start = new Date(end)
  start.setMonth(start.getMonth() - 6)
  return [formatDate(start), formatDate(end)]
}

function formatDate(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function handlePeriodChange(value: string | number | boolean) {
  emit('period-change', value as 'day' | 'week' | 'month')
}

const latestSource = computed(() => props.items[props.items.length - 1]?.source ?? 'sqlite')
const latestUpdatedAt = computed(() => props.items[props.items.length - 1]?.updated_at ?? null)
const filteredItems = computed(() => {
  const [start, end] = dateRange.value
  return props.items.filter((item) => item.date >= start && item.date <= end)
})
const filteredIndexes = computed(() => {
  const [start, end] = dateRange.value
  return (props.technical?.dates ?? [])
    .map((date, index) => ({ date, index }))
    .filter((item) => item.date >= start && item.date <= end)
    .map((item) => item.index)
})
const technicalSeries = computed(() => {
  const technical = props.technical
  if (!technical) return []
  return [
    { name: '收盘价', data: technical.close, color: '#7dd3fc' },
    { name: 'MA5', data: technical.ma5, color: '#2dd4bf' },
    { name: 'MA10', data: technical.ma10, color: '#f59e0b' },
    { name: 'MA20', data: technical.ma20, color: '#fb7185' }
  ].map((series) => ({
    ...series,
    data: filteredIndexes.value.map((index) => series.data[index] ?? null)
  }))
})

watch(
  dateRange,
  (range) => {
    emit('date-range-change', range)
  },
  { immediate: true }
)

watch(
  () => [props.period, props.items[0]?.date, props.items[props.items.length - 1]?.date] as const,
  () => {
    if (props.period !== 'day') return
    dateRange.value = defaultHalfYearRange()
  }
)

const option = computed(() => {
  const dates = filteredItems.value.map((item) => item.date)
  const candles = filteredItems.value.map((item) => [item.open, item.close, item.low, item.high].map((value) => Number(value ?? 0)))
  const volumes = filteredItems.value.map((item) => item.volume ?? 0)
  return {
    backgroundColor: 'transparent',
    animation: true,
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { top: 6, textStyle: { color: '#91a9c4' }, data: ['K线', ...technicalSeries.value.map((item) => item.name), '成交量'] },
    grid: [
      { left: 48, right: 22, top: 48, height: 250 },
      { left: 48, right: 22, top: 328, height: 88 }
    ],
    xAxis: [
      { type: 'category', data: dates, boundaryGap: true, axisLine: { lineStyle: { color: '#30465f' } }, axisLabel: { color: '#7791ad' } },
      { type: 'category', gridIndex: 1, data: dates, axisLine: { lineStyle: { color: '#30465f' } }, axisLabel: { show: false } }
    ],
    yAxis: [
      { scale: true, axisLine: { lineStyle: { color: '#30465f' } }, splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }, axisLabel: { color: '#7791ad' } },
      { gridIndex: 1, axisLabel: { color: '#7791ad' }, splitLine: { show: false } }
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] }, { type: 'slider', xAxisIndex: [0, 1], bottom: 0, height: 18 }],
    series: [
      { name: 'K线', type: 'candlestick', data: candles, itemStyle: { color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' } },
      ...technicalSeries.value.map((item) => ({
        name: item.name,
        type: 'line',
        data: item.data,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: item.name === '收盘价' ? 1.5 : 1.2, color: item.color },
        itemStyle: { color: item.color }
      })),
      { name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volumes, itemStyle: { color: 'rgba(56, 189, 248, 0.46)' } }
    ]
  }
})
</script>

<style scoped>
.chart-shell {
  min-height: 520px;
  padding: 22px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 26px;
  background: rgba(7, 12, 23, 0.72);
}

.chart-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.chart-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.chart-actions :deep(.el-date-editor) {
  width: 260px;
}

p {
  margin: 0 0 6px;
  color: #7f93ad;
}

strong {
  color: #f8fbff;
  font-size: 24px;
}

.chart {
  height: 440px;
}

.empty-chart {
  display: grid;
  height: 420px;
  place-items: center;
  border: 1px dashed rgba(148, 163, 184, 0.2);
  border-radius: 20px;
  color: #7f93ad;
}
</style>
