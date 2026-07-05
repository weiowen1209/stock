<template>
  <section class="overview-grid">
    <div class="panel hero-panel">
      <p>产业链雷达</p>
      <div class="filter-columns">
        <div class="filter-block">
          <span>一级分类</span>
          <div class="industry-pills">
            <button v-for="item in store.industries" :key="item" :class="{ active: store.selectedIndustry === item }" @click="store.setSelectedIndustry(item)">
              {{ item }}
            </button>
          </div>
        </div>
        <div class="filter-block">
          <span>二级分类</span>
          <div class="industry-pills compact">
            <button
              v-for="item in store.subIndustries"
              :key="item"
              :class="{ active: store.selectedSubIndustry === item }"
              @click="store.setSelectedSubIndustry(item)"
            >
              {{ item }}
            </button>
          </div>
        </div>
        <div class="filter-block">
          <span>三级分类</span>
          <div class="industry-pills compact">
            <button
              v-for="item in store.sub2Industries"
              :key="item"
              :class="{ active: store.selectedSub2Industry === item }"
              @click="store.setSelectedSub2Industry(item)"
            >
              {{ item }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="panel table-panel">
      <div class="panel-head">
        <div>
          <p>股票列表</p>
          <h3>{{ tableTitle }}</h3>
        </div>
        <SourceBadge source="sqlite" :updated-at="store.currentStock?.updated_at" />
      </div>
      <StockTable :stocks="store.filteredStocks" :quotes="store.quotes" @select="store.selectStock" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SourceBadge from '../components/SourceBadge.vue'
import StockTable from '../components/StockTable.vue'
import { useStockStore } from '../stores/stockStore'

const store = useStockStore()
const tableTitle = computed(() => {
  const parts = [store.selectedIndustry, store.selectedSubIndustry, store.selectedSub2Industry].filter((item) => item !== '全部')
  return parts.length ? parts.join(' / ') : '全部股票'
})
</script>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 22px;
}

.panel {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 28px;
  background: rgba(7, 12, 23, 0.72);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.28);
}

.hero-panel {
  padding: 24px 28px;
  background:
    radial-gradient(circle at 24% 10%, rgba(56, 189, 248, 0.24), transparent 34%),
    linear-gradient(140deg, rgba(15, 23, 42, 0.95), rgba(4, 10, 20, 0.9));
}

p {
  margin: 0 0 8px;
  color: #7f93ad;
  font-size: 13px;
}

h3 {
  margin: 0;
  color: #f8fbff;
}

.filter-columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.filter-block {
  min-width: 0;
}

.filter-block span {
  display: block;
  margin-bottom: 10px;
  color: #8fb0d3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.industry-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.industry-pills.compact {
  gap: 8px;
}

button {
  cursor: pointer;
  border: 1px solid rgba(125, 211, 252, 0.18);
  border-radius: 999px;
  padding: 9px 13px;
  color: #a7c5e6;
  background: rgba(15, 23, 42, 0.6);
}

.industry-pills.compact button {
  padding: 7px 11px;
  font-size: 12px;
}

button.active {
  color: #07131f;
  background: #7dd3fc;
  box-shadow: 0 0 24px rgba(125, 211, 252, 0.42);
}

.table-panel {
  padding: 20px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

@media (max-width: 1080px) {
  .filter-columns {
    grid-template-columns: 1fr;
  }
}
</style>
