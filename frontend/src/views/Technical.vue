<template>
  <section class="technical-grid">
    <KLineChart
      :title="store.currentStock ? `${store.currentStock.name} 技术走势` : '技术走势'"
      :items="store.kline"
      :period="store.klinePeriod"
      :technical="store.technical"
      @period-change="store.setKlinePeriod"
      @date-range-change="dateRange = $event"
    />
    <LineTrendChart
      title="MACD"
      eyebrow="DIF / DEA / MACD"
      chart-type="macd"
      :labels="filteredTechnicalDates"
      :series="[
        { name: 'MACD柱', type: 'bar', data: filteredTechnicalSeries('histogram') },
        { name: 'DIF', data: filteredTechnicalSeries('macd') },
        { name: 'DEA', data: filteredTechnicalSeries('signal') }
      ]"
    />
    <LineTrendChart
      title="RSI6"
      eyebrow="Relative strength index"
      chart-type="rsi"
      :labels="filteredTechnicalDates"
      :series="[{ name: 'RSI6', data: filteredTechnicalSeries('rsi6') }]"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import KLineChart from '../components/KLineChart.vue'
import LineTrendChart from '../components/LineTrendChart.vue'
import { useStockStore } from '../stores/stockStore'
import type { TechnicalIndicators } from '../api'

const store = useStockStore()
const dateRange = ref<[string, string] | null>(null)
const filteredTechnicalIndexes = computed(() => {
  const dates = store.technical?.dates ?? []
  if (!dateRange.value) return dates.map((_, index) => index)
  const [start, end] = dateRange.value
  return dates
    .map((date, index) => ({ date, index }))
    .filter((item) => item.date >= start && item.date <= end)
    .map((item) => item.index)
})
const filteredTechnicalDates = computed(() => {
  const dates = store.technical?.dates ?? []
  return filteredTechnicalIndexes.value.map((index) => dates[index])
})

function filteredTechnicalSeries(key: keyof Pick<TechnicalIndicators, 'macd' | 'signal' | 'histogram' | 'rsi6'>) {
  const values = store.technical?.[key] ?? []
  return filteredTechnicalIndexes.value.map((index) => values[index] ?? null)
}
</script>

<style scoped>
.technical-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
}

.technical-grid > * {
  grid-column: 1 / -1;
}

@media (max-width: 1100px) {
  .technical-grid {
    grid-template-columns: 1fr;
  }
}
</style>
