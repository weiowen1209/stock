<template>
  <el-table :data="stocks" height="520" class="stock-table" @row-click="(row: Stock) => emit('select', row.code)">
    <el-table-column prop="code" label="代码" width="92" />
    <el-table-column prop="name" label="名称" width="110" />
    <el-table-column label="产业链" min-width="150">
      <template #default="{ row }">
        <IndustryTag :value="row.industry_chain" />
      </template>
    </el-table-column>
    <el-table-column prop="industry_chain_detail" label="细分定位" min-width="220" />
    <el-table-column label="涨跌幅" width="110" sortable>
      <template #default="{ row }">
        <span :class="changeClass(quoteMap.get(row.code)?.change_pct)">
          {{ formatPercent(quoteMap.get(row.code)?.change_pct) }}
        </span>
      </template>
    </el-table-column>
    <el-table-column label="最新价" width="100">
      <template #default="{ row }">
        {{ quoteMap.get(row.code)?.price ?? '--' }}
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Quote, Stock } from '../api'
import IndustryTag from './IndustryTag.vue'

const props = defineProps<{
  stocks: Stock[]
  quotes: Quote[]
}>()

const emit = defineEmits<{
  select: [code: string]
}>()

const quoteMap = computed(() => new Map(props.quotes.map((item) => [item.code, item])))

function formatPercent(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  const numeric = Number(value)
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(2)}%`
}

function changeClass(value: string | number | null | undefined) {
  const numeric = Number(value ?? 0)
  return numeric > 0 ? 'up' : numeric < 0 ? 'down' : 'flat'
}
</script>

<style scoped>
.stock-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.92);
  --el-table-text-color: #dce8f6;
  --el-table-header-text-color: #8fb0d3;
  --el-table-border-color: rgba(148, 163, 184, 0.12);
  border-radius: 18px;
  overflow: hidden;
}

.up {
  color: #fb7185;
  font-weight: 700;
}

.down {
  color: #22c55e;
  font-weight: 700;
}

.flat {
  color: #94a3b8;
}
</style>
