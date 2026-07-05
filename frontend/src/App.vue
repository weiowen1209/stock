<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <span class="eyebrow">Humanoid Robotics Equity Console</span>
        <h1>机器人产业分析仪表板</h1>
        <p>先以稳定MVP闭环展示股票池、产业链、行情与K线，再扩展基本面、同步和PDF能力。</p>
      </div>
      <div class="top-actions">
        <SourceBadge source="sqlite" :updated-at="store.currentStock?.updated_at" />
      </div>
    </header>

    <DataStatusPanel
      :status="store.syncStatus"
      :progress="dialogProgress"
      :syncing="store.syncing"
      @sync-all="handleSyncAllStocks"
    />

    <SyncProgressDialog
      v-model:visible="syncDialogVisible"
      :syncing="store.syncing"
      :progress="dialogProgress"
      :current-code="store.currentCode"
      :current-stock="store.currentStock"
      :mode="syncDialogMode"
      :total-stocks="store.stocks.length"
    />

    <el-alert v-if="store.error" class="error-alert" type="error" :title="store.error" show-icon />

    <el-tabs v-model="activeTab" class="dashboard-tabs">
      <el-tab-pane label="产业链总览" name="overview">
        <IndustryOverview />
      </el-tab-pane>
      <el-tab-pane label="基本面深度分析" name="fundamental">
        <Fundamental />
      </el-tab-pane>
      <el-tab-pane label="技术面分析" name="technical">
        <Technical />
      </el-tab-pane>
      <el-tab-pane label="个股深度档案" name="detail">
        <StockDetail />
      </el-tab-pane>
      <el-tab-pane label="股票池" name="base-data">
        <BaseData :syncing="store.syncing" @sync-stock="handleSyncStock" />
      </el-tab-pane>
      <el-tab-pane label="导入财报" name="import">
        <ImportWorkbench />
      </el-tab-pane>
    </el-tabs>

    <footer>仅供信息展示和研究辅助，不构成任何投资建议。</footer>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useSyncProgress } from './composables/useSyncProgress'
import DataStatusPanel from './components/DataStatusPanel.vue'
import SourceBadge from './components/SourceBadge.vue'
import SyncProgressDialog from './components/SyncProgressDialog.vue'
import BaseData from './views/BaseData.vue'
import Fundamental from './views/Fundamental.vue'
import ImportWorkbench from './views/ImportWorkbench.vue'
import IndustryOverview from './views/IndustryOverview.vue'
import StockDetail from './views/StockDetail.vue'
import Technical from './views/Technical.vue'
import { useStockStore } from './stores/stockStore'

const activeTab = ref('overview')
const syncDialogVisible = ref(false)
const syncDialogMode = ref<'current' | 'all'>('all')
const store = useStockStore()
const { progress, connected, connect } = useSyncProgress()
const fallbackProgress = computed(() => {
  if (progress.value) return progress.value
  if (!store.syncing) return null
  return {
    stage: 'connecting',
    message: connected.value ? '等待后端推送同步进度' : '正在连接同步进度通道',
    provider: null,
    code: null,
    percent: 0,
    current: 0,
    total: syncDialogMode.value === 'all' ? store.stocks.length : 1,
    updated_at: new Date().toISOString()
  }
})
const dialogProgress = computed(() => fallbackProgress.value ?? store.syncStatus?.progress ?? null)

async function handleSyncStock(code: string) {
  syncDialogMode.value = 'current'
  syncDialogVisible.value = true
  await store.syncStockByCode(code)
}

async function handleSyncAllStocks() {
  syncDialogMode.value = 'all'
  syncDialogVisible.value = true
  await store.syncAllStocks()
}

onMounted(() => {
  connect()
  store.loadInitialData()
})
</script>
