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

    <article class="insight-panel">
      <div>
        <p class="eyebrow">AI interpretation</p>
        <h3>{{ deep?.ai_insight.conclusion ?? '暂无深度分析结论' }}</h3>
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
        <p class="eyebrow">Score factors</p>
        <h3>增长潜力评分拆解</h3>
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

    <div class="analysis-panel">
      <div class="panel-header">
        <p class="eyebrow">Growth signal</p>
        <h3>增长信号解读</h3>
      </div>
      <div class="signal-list">
        <div v-for="item in deep?.trend_breakdown ?? []" :key="item.report_period" class="signal-row">
          <strong>{{ item.report_period }}</strong>
          <span>{{ item.signal }}</span>
          <small>营收同比 {{ formatPercent(item.revenue_yoy) }} · 净利同比 {{ formatPercent(item.net_profit_yoy) }} · 现金流匹配 {{ formatRatio(item.cash_flow_match) }}</small>
        </div>
      </div>
    </div>

    <LineTrendChart
      title="同比/环比增长拆解"
      eyebrow="Growth breakdown"
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
        <p class="eyebrow">Peer comparison</p>
        <h3>行业对比</h3>
      </div>
      <div class="comparison-grid">
        <div v-for="item in deep?.peer_comparison ?? []" :key="item.metric" class="comparison-card">
          <span>{{ item.metric }}</span>
          <strong>{{ formatNumber(item.company_value) }}</strong>
          <small>{{ item.conclusion }} · 分位 {{ formatPercent(item.percentile) }}</small>
        </div>
      </div>
    </div>

    <div class="analysis-panel">
      <div class="panel-header">
        <p class="eyebrow">Valuation percentile</p>
        <h3>估值分位</h3>
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

    <LineTrendChart
      title="业务分部收入"
      eyebrow="Segment mix"
      :labels="segmentLabels"
      :series="[{ name: '收入', type: 'bar', data: store.businessSegments.map((item) => toNumber(item.revenue)) }]"
    />

    <LineTrendChart
      title="费用结构"
      eyebrow="Expense structure"
      :labels="expenseLabels"
      :series="expenseSeries"
    />

    <LineTrendChart
      title="估值指标"
      eyebrow="Valuation"
      :labels="store.valuation.map((item) => item.date)"
      :series="[
        { name: 'PE', data: store.valuation.map((item) => toNumber(item.pe)) },
        { name: 'PB', data: store.valuation.map((item) => toNumber(item.pb)) },
        { name: 'PEG', data: store.valuation.map((item) => toNumber(item.peg)) }
      ]"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import LineTrendChart from '../components/LineTrendChart.vue'
import MetricCard from '../components/MetricCard.vue'
import { useStockStore } from '../stores/stockStore'

const store = useStockStore()
const deep = computed(() => store.deepFundamental)
const latest = computed(() => store.financialReports[store.financialReports.length - 1])
const reportLabels = computed(() => store.financialReports.map((item) => item.report_period))
const segmentLabels = computed(() => store.businessSegments.map((item) => item.segment_name))
const expenseLabels = computed(() => store.expenses.map((item) => item.report_period))
const priceUp = computed(() => {
  if (!store.currentQuote) return true
  return Number(store.currentQuote.change_pct ?? 0) >= 0
})

// 股票模糊搜索
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
const expenseSeries = computed(() => [
  { name: '销售费用', data: store.expenses.map((item) => toNumber(item.selling_expense)) },
  { name: '管理费用', data: store.expenses.map((item) => toNumber(item.admin_expense)) },
  { name: '研发费用', data: store.expenses.map((item) => toNumber(item.rd_expense)) },
  { name: '财务费用', data: store.expenses.map((item) => toNumber(item.finance_expense)) }
])

function toNumber(value: string | number | null | undefined) {
  if (value === null || value === undefined) return null
  return Number(value)
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

function formatRatio(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '--'
  return `${Number(value).toFixed(2)}x`
}

function scoreClass(value: string | number | null | undefined) {
  const score = Number(value ?? 0)
  if (score >= 80) return 'score-strong'
  if (score >= 65) return 'score-good'
  if (score >= 50) return 'score-neutral'
  return 'score-weak'
}

function directionText(value: string) {
  const labels: Record<string, string> = {
    higher_better: '越高越好',
    lower_better: '越低越好',
    lower_moderate_better: '适度更好'
  }
  return labels[value] ?? '综合判断'
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
  if (numeric >= 100000000) return `${(numeric / 100000000).toFixed(2)}亿`
  if (numeric >= 10000) return `${(numeric / 10000).toFixed(2)}万`
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

.stock-identity h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
}

.stock-identity {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.stock-code {
  padding: 4px 10px;
  background: rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  font-size: 14px;
  color: var(--muted);
}

.stock-industry {
  padding: 4px 10px;
  background: rgba(99, 102, 241, 0.1);
  border-radius: 8px;
  font-size: 13px;
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
.signal-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 16px;
}

.insight-columns div,
.comparison-card,
.signal-row,
.dupont-note {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.04);
}

.insight-columns span,
.comparison-card small,
.factor-row span,
.signal-row small,
.dupont-note span {
  color: var(--muted);
  font-size: 13px;
}

.factor-list {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.factor-row {
  display: grid;
  grid-template-columns: 1.2fr 2fr 48px;
  align-items: center;
  gap: 14px;
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
  .signal-list,
  .compact-panel,
  .factor-row {
    grid-template-columns: 1fr;
  }
}
</style>
