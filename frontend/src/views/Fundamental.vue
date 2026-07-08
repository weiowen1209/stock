<template>
  <section class="fundamental-grid">
    <div class="stock-header">
      <div class="stock-identity">
        <h2>{{ store.currentStock?.name ?? '未选择股票' }}</h2>
        <span class="stock-code">{{ store.currentCode || '--' }}</span>
        <div v-if="store.currentStock?.industry_chain" class="stock-industry">{{ store.currentStock.industry_chain }}</div>
      </div>

      <div class="stock-search">
        <div class="search-box">
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="输入股票代码或名称模糊搜索"
            @focus="showDropdown = true"
            @blur="hideDropdownLater"
          />
          <div v-if="showDropdown && searchResults.length" class="search-dropdown">
            <div
              v-for="item in searchResults"
              :key="item.code"
              class="dropdown-item"
              @mousedown.prevent="selectSearchedStock(item.code)"
            >
              <strong>{{ item.name }}</strong>
              <span>{{ item.code }}</span>
              <small v-if="item.industry_chain">{{ item.industry_chain }}</small>
            </div>
          </div>
          <div v-else-if="showDropdown && searchKeyword && !searchResults.length" class="search-dropdown">
            <div class="dropdown-empty">未找到匹配的股票</div>
          </div>
        </div>

        <div v-if="store.currentQuote" class="stock-price">
          <strong :class="priceUp ? 'price-up' : 'price-down'">{{ formatPrice(store.currentQuote?.price) }}</strong>
          <span :class="priceUp ? 'price-up' : 'price-down'">{{ formatChangePct(store.currentQuote?.change_pct) }}</span>
        </div>
      </div>
    </div>

    <div class="metrics">
      <MetricCard label="综合评分" :value="formatScore(deep?.overall_score)" :hint="deep?.report_period ?? '深度分析'" />
      <MetricCard label="增长潜力" :value="formatScore(deep?.growth_potential_score)" hint="空间×能力×质量" />
      <MetricCard label="财务质量" :value="formatScore(deep?.quality_score)" hint="利润与现金流" />
      <MetricCard label="估值性价比" :value="formatScore(deep?.valuation_score)" hint="分位越低越高" />
    </div>

    <article class="insight-panel thesis-panel">
      <div>
        <p class="eyebrow">Research thesis</p>
        <h3>{{ deep?.ai_insight.conclusion ?? '暂无深度分析结论' }}</h3>
        <p class="thesis-text">按“产业逻辑 → 业务结构 → 毛利贡献 → 净利润影响因素 → 现金流验证 → 资产扩张 → 技术产能 → 估值风险”的顺序阅读。</p>
      </div>
      <div class="insight-columns">
        <div>
          <strong>增长亮点</strong>
          <span v-for="item in deep?.ai_insight.positives ?? []" :key="item">{{ item }}</span>
        </div>
        <div>
          <strong>风险提示</strong>
          <span v-for="item in deep?.ai_insight.risks ?? []" :key="item">{{ item }}</span>
        </div>
        <div>
          <strong>跟踪指标</strong>
          <span v-for="item in deep?.ai_insight.watch_items ?? []" :key="item">{{ item }}</span>
        </div>
      </div>
    </article>

    <div class="analysis-panel">
      <div class="panel-header">
        <p class="eyebrow">Eight modules</p>
        <h3>基本面分析八模块</h3>
      </div>
      <div class="module-grid">
        <article v-for="item in deep?.analysis_modules ?? []" :key="item.title" class="module-card" :class="moduleClass(item.status)">
          <span>{{ item.title }}</span>
          <p>{{ item.summary }}</p>
          <ul>
            <li v-for="point in item.key_points" :key="point">{{ point }}</li>
          </ul>
        </article>
      </div>
    </div>

    <div class="analysis-panel">
      <div class="panel-header">
        <p class="eyebrow">Profit attribution</p>
        <h3>净利润影响因素排序</h3>
      </div>
      <div class="impact-list">
        <div v-for="factor in deep?.impact_factors ?? []" :key="`${factor.category}-${factor.name}`" class="impact-row">
          <div>
            <strong>{{ factor.name }}</strong>
            <span>{{ factor.category }} · {{ factor.explanation }}</span>
          </div>
          <b :class="impactClass(factor.direction)">{{ formatMoney(factor.impact) }}</b>
        </div>
      </div>
    </div>

    <div class="analysis-panel">
      <div class="panel-header">
        <p class="eyebrow">Segment contribution</p>
        <h3>业务贡献拆解</h3>
      </div>
      <div class="segment-table">
        <div class="segment-head">
          <span>口径/分部</span>
          <span>收入</span>
          <span>毛利</span>
          <span>毛利率</span>
          <span>毛利占比</span>
          <span>角色</span>
        </div>
        <div v-for="item in deep?.segment_contribution ?? []" :key="`${item.segment_type}-${item.segment_name}`" class="segment-row">
          <span><em>{{ segmentTypeText(item.segment_type) }}</em>{{ item.segment_name }}</span>
          <span>{{ formatMoney(item.revenue) }}</span>
          <span>{{ formatMoney(item.gross_profit) }}</span>
          <span>{{ formatPercent(item.gross_margin) }}</span>
          <span>{{ formatPercent(item.gross_profit_share) }}</span>
          <span>{{ item.role }}</span>
        </div>
      </div>
    </div>

    <div class="analysis-panel">
      <div class="panel-header">
        <p class="eyebrow">Watch signals</p>
        <h3>关键跟踪信号</h3>
      </div>
      <div class="watch-grid">
        <div v-for="item in deep?.watch_signals ?? []" :key="item.name" class="watch-card">
          <span>{{ item.name }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.judgement }} · 来源：{{ item.source }}</small>
        </div>
      </div>
    </div>

    <div class="analysis-panel">
      <div class="panel-header">
        <p class="eyebrow">Score factors</p>
        <h3>质量评分拆解</h3>
      </div>
      <div class="factor-list">
        <div v-for="factor in deep?.score_factors ?? []" :key="factor.name" class="factor-row">
          <div>
            <strong>{{ factor.benchmark }} <em>{{ factor.level }}</em></strong>
            <span>{{ factor.comment }} · 权重 {{ formatWeight(factor.weight) }} · {{ directionText(factor.direction) }}</span>
          </div>
          <div class="score-track"><i :class="scoreClass(factor.score)" :style="{ width: `${factor.score}%` }"></i></div>
          <b :class="scoreClass(factor.score)">{{ formatScore(factor.score) }}</b>
        </div>
      </div>
    </div>

    <LineTrendChart
      title="收入、利润与现金流验证"
      eyebrow="Growth quality"
      :labels="deep?.trend_breakdown.map((item) => item.report_period) ?? []"
      :series="[
        { name: '营收同比', data: deep?.trend_breakdown.map((item) => item.revenue_yoy) ?? [] },
        { name: '净利同比', data: deep?.trend_breakdown.map((item) => item.net_profit_yoy) ?? [] },
        { name: '现金流匹配', data: deep?.trend_breakdown.map((item) => percentRatio(item.cash_flow_match)) ?? [] }
      ]"
    />

    <LineTrendChart
      title="杜邦分析"
      eyebrow="Dupont analysis"
      :labels="deep?.dupont.map((item) => item.report_period) ?? []"
      :series="[
        { name: '披露ROE', data: deep?.dupont.map((item) => item.roe) ?? [] },
        { name: '估算ROE', data: deep?.dupont.map((item) => item.roe_estimated) ?? [] },
        { name: '净利率', data: deep?.dupont.map((item) => percentRatio(item.net_margin)) ?? [] },
        { name: '资产周转率', data: deep?.dupont.map((item) => item.asset_turnover) ?? [] },
        { name: '权益乘数', data: deep?.dupont.map((item) => item.equity_multiplier) ?? [] }
      ]"
    />

    <div class="analysis-panel compact-panel">
      <div v-for="item in deep?.dupont ?? []" :key="item.report_period" class="dupont-note">
        <strong>{{ item.report_period }} · 主驱动：{{ item.primary_driver }}</strong>
        <span>{{ item.interpretation }}</span>
      </div>
    </div>

    <div class="analysis-panel">
      <div class="panel-header">
        <p class="eyebrow">Valuation percentile</p>
        <h3>市场定位与估值分位</h3>
      </div>
      <div class="comparison-grid">
        <div v-for="item in deep?.valuation_percentiles ?? []" :key="item.metric" class="comparison-card">
          <span>{{ item.metric }} · {{ item.label }}</span>
          <strong>{{ formatNumber(item.current) }}</strong>
          <small>{{ item.comment }}</small>
          <small>样本 {{ item.sample_size }} · 回归中枢空间 {{ formatPercent(item.upside_room) }}</small>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import LineTrendChart from '../components/LineTrendChart.vue'
import MetricCard from '../components/MetricCard.vue'
import { useStockStore } from '../stores/stockStore'

const store = useStockStore()
const deep = computed(() => store.deepFundamental ?? null)
const priceUp = computed(() => {
  if (!store.currentQuote) return true
  return Number(store.currentQuote.change_pct ?? 0) >= 0
})

const searchKeyword = ref('')
const showDropdown = ref(false)

const searchResults = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return []
  return store.stocks
    .filter(
      (item) =>
        item.is_active &&
        (item.code.toLowerCase().includes(keyword) || item.name.toLowerCase().includes(keyword))
    )
    .slice(0, 10)
})

function selectSearchedStock(code: string) {
  searchKeyword.value = ''
  showDropdown.value = false
  store.selectStock(code)
}

function hideDropdownLater() {
  setTimeout(() => {
    showDropdown.value = false
  }, 200)
}

function percentRatio(value: number | null | undefined) {
  if (value === null || value === undefined) return null
  return Number((value * 100).toFixed(2))
}

function formatScore(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return Number(value).toFixed(0)
}

function formatWeight(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return `${(Number(value) * 100).toFixed(0)}%`
}

function formatNumber(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return Number(value).toFixed(2)
}

function formatPercent(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return `${Number(value).toFixed(2)}%`
}

function formatMoney(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  const numeric = Number(value)
  const absValue = Math.abs(numeric)
  const sign = numeric < 0 ? '-' : ''
  if (absValue >= 100000000) return `${sign}${(absValue / 100000000).toFixed(2)}亿`
  if (absValue >= 10000) return `${sign}${(absValue / 10000).toFixed(2)}万`
  return numeric.toFixed(0)
}

function formatPrice(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return Number(value).toFixed(2)
}

function formatChangePct(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  const num = Number(value)
  return num >= 0 ? `+${num.toFixed(2)}%` : `${num.toFixed(2)}%`
}

function scoreClass(value: string | number | null | undefined) {
  const score = Number(value ?? 0)
  if (score >= 80) return 'score-strong'
  if (score >= 65) return 'score-good'
  if (score >= 50) return 'score-neutral'
  return 'score-weak'
}

function impactClass(value: string) {
  if (value === 'positive') return 'impact-positive'
  if (value === 'negative') return 'impact-negative'
  return 'impact-neutral'
}

function moduleClass(value: string) {
  return {
    positive: 'module-positive',
    warning: 'module-warning',
    negative: 'module-negative'
  }[value] ?? 'module-neutral'
}

function directionText(value: string) {
  const labels: Record<string, string> = {
    higher_better: '越高越好',
    lower_better: '越低越好',
    lower_moderate_better: '适度更好'
  }
  return labels[value] ?? '综合判断'
}

function segmentTypeText(value: string) {
  const labels: Record<string, string> = {
    product: '产品',
    industry: '行业',
    region: '地区',
    sales_mode: '销售'
  }
  return labels[value] ?? value
}
</script>

<style scoped>
.fundamental-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}

.stock-header {
  grid-column: 1 / -1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 20px 24px;
  background: var(--card-bg);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}

.stock-identity {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.stock-identity h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
}

.stock-code,
.stock-industry {
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 13px;
}

.stock-code {
  background: rgba(148, 163, 184, 0.12);
  color: var(--muted);
}

.stock-industry {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent, #6366f1);
}

.stock-search {
  display: flex;
  align-items: center;
  gap: 24px;
}

.search-box {
  position: relative;
  min-width: 280px;
}

.search-box input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px;
  font-size: 14px;
  background: var(--card-bg);
  color: var(--text);
  outline: none;
  transition: border-color 0.2s;
}

.search-box input:focus {
  border-color: var(--accent, #6366f1);
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  max-height: 320px;
  overflow-y: auto;
  background: var(--card-bg);
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
  z-index: 100;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.dropdown-item:hover {
  background: rgba(99, 102, 241, 0.08);
}

.dropdown-item strong {
  font-size: 14px;
  color: var(--text);
}

.dropdown-item span {
  font-size: 13px;
  color: var(--muted);
  font-family: monospace;
}

.dropdown-item small {
  margin-left: auto;
  font-size: 12px;
  color: var(--muted);
}

.dropdown-empty {
  padding: 16px 14px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

.stock-price {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.stock-price strong {
  font-size: 32px;
  font-weight: 700;
}

.stock-price span {
  font-size: 16px;
  font-weight: 500;
}

.price-up {
  color: #ef4444 !important;
}

.price-down {
  color: #22c55e !important;
}

.metrics,
.insight-panel,
.analysis-panel {
  grid-column: 1 / -1;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.insight-panel,
.analysis-panel {
  background: var(--card-bg);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}

.thesis-panel {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(99, 102, 241, 0.08)), var(--card-bg);
}

.thesis-text,
.module-card p,
.impact-row span,
.watch-card small,
.comparison-card small,
.factor-row span,
.dupont-note span {
  color: var(--muted);
  font-size: 13px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.insight-panel h3,
.analysis-panel h3 {
  margin: 0;
}

.insight-columns,
.comparison-grid,
.watch-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 16px;
}

.insight-columns div,
.comparison-card,
.watch-card,
.dupont-note {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.04);
}

.insight-columns span {
  color: var(--muted);
  font-size: 13px;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-top: 16px;
}

.module-card {
  display: grid;
  gap: 10px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.03);
}

.module-card span {
  font-weight: 700;
  color: var(--text);
}

.module-card p,
.module-card ul {
  margin: 0;
}

.module-card ul {
  display: grid;
  gap: 6px;
  padding-left: 18px;
  color: var(--muted);
  font-size: 13px;
}

.module-positive {
  border-color: rgba(239, 68, 68, 0.28);
  background: rgba(239, 68, 68, 0.05);
}

.module-warning {
  border-color: rgba(245, 158, 11, 0.28);
  background: rgba(245, 158, 11, 0.05);
}

.module-negative {
  border-color: rgba(34, 197, 94, 0.28);
  background: rgba(34, 197, 94, 0.05);
}

.impact-list,
.factor-list {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.impact-row,
.factor-row {
  display: grid;
  grid-template-columns: 1.5fr 2fr 90px;
  align-items: center;
  gap: 14px;
}

.impact-row {
  grid-template-columns: 1fr 120px;
  padding: 14px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.04);
}

.impact-row div {
  display: grid;
  gap: 6px;
}

.impact-row b {
  text-align: right;
}

.impact-positive {
  color: #dc2626;
}

.impact-negative {
  color: #16a34a;
}

.impact-neutral {
  color: #64748b;
}

.segment-table {
  display: grid;
  gap: 8px;
  margin-top: 16px;
  overflow-x: auto;
}

.segment-head,
.segment-row {
  display: grid;
  grid-template-columns: 1.5fr repeat(4, 0.8fr) 1.4fr;
  gap: 12px;
  align-items: center;
  min-width: 860px;
  padding: 12px 14px;
  border-radius: 12px;
}

.segment-head {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  background: rgba(148, 163, 184, 0.10);
}

.segment-row {
  background: rgba(15, 23, 42, 0.04);
  font-size: 13px;
}

.segment-row em {
  margin-right: 8px;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.10);
  color: var(--accent, #6366f1);
  font-style: normal;
}

.factor-row em {
  margin-left: 8px;
  color: var(--accent);
  font-size: 12px;
  font-style: normal;
}

.compact-panel {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.score-strong {
  color: #dc2626;
}

.score-good {
  color: #ea580c;
}

.score-neutral {
  color: #64748b;
}

.score-weak {
  color: #16a34a;
}

.score-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.2);
}

.score-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: currentColor;
}

@media (max-width: 1100px) {
  .fundamental-grid,
  .metrics,
  .insight-columns,
  .comparison-grid,
  .watch-grid,
  .module-grid,
  .compact-panel,
  .factor-row,
  .impact-row {
    grid-template-columns: 1fr;
  }

  .stock-header,
  .stock-search {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
