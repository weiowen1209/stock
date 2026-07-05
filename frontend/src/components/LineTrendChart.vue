<template>
  <section class="trend-card">
    <div class="chart-title">
      <p>{{ eyebrow }}</p>
      <strong>{{ title }}</strong>
    </div>
    <v-chart v-if="series.length" class="trend-chart" :option="option" autoresize />
    <div v-else class="empty">暂无数据</div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps<{
  title: string
  eyebrow: string
  labels: string[]
  chartType?: 'default' | 'macd' | 'rsi'
  series: Array<{ name: string; data: Array<number | null>; type?: 'line' | 'bar' }>
}>()

const option = computed(() => {
  const isMacd = props.chartType === 'macd'
  const isRsi = props.chartType === 'rsi'
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { top: 4, right: 8, textStyle: { color: '#91a9c4' } },
    grid: { left: 44, right: 18, top: 58, bottom: 36 },
    xAxis: { type: 'category', data: props.labels, axisLabel: { color: '#7f93ad' }, axisLine: { lineStyle: { color: '#2d4058' } } },
    yAxis: {
      type: 'value',
      min: isRsi ? 0 : undefined,
      max: isRsi ? 100 : undefined,
      axisLabel: { color: '#7f93ad' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }
    },
    series: props.series.map((item, index) => ({
      name: item.name,
      type: item.type ?? 'line',
      data: item.data,
      smooth: !isMacd,
      symbol: 'none',
      symbolSize: 6,
      barWidth: isMacd && item.type === 'bar' ? '58%' : undefined,
      itemStyle: {
        color: isMacd && item.type === 'bar'
          ? (params: { value: number | null }) => Number(params.value ?? 0) >= 0 ? '#ef4444' : '#22c55e'
          : chartColor(item.name, index)
      },
      lineStyle: item.type === 'bar' ? undefined : { width: 1.2, color: chartColor(item.name, index) },
      areaStyle: undefined,
      markLine: isRsi && index === 0 ? {
        silent: true,
        symbol: 'none',
        lineStyle: { color: 'rgba(148, 163, 184, 0.36)', type: 'dashed' },
        label: { color: '#91a9c4' },
        data: [{ yAxis: 20, name: '20' }, { yAxis: 50, name: '50' }, { yAxis: 80, name: '80' }]
      } : undefined
    }))
  }
})

function chartColor(name: string, index: number) {
  const namedColors: Record<string, string> = {
    DIF: '#facc15',
    DEA: '#a78bfa',
    RSI6: '#facc15'
  }
  return namedColors[name] ?? ['#7dd3fc', '#2dd4bf', '#f59e0b', '#fb7185'][index % 4]
}
</script>

<style scoped>
.trend-card {
  min-height: 300px;
  padding: 20px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 24px;
  background: rgba(7, 12, 23, 0.72);
}

.chart-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
}

p {
  margin: 0;
  color: #7f93ad;
  font-size: 12px;
}

strong {
  color: #f8fbff;
  font-size: 20px;
}

.trend-chart {
  height: 260px;
}

.empty {
  display: grid;
  height: 240px;
  place-items: center;
  color: #7f93ad;
}
</style>
