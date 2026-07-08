<template>
  <el-dialog
    v-model="visibleModel"
    :title="dialogTitle"
    width="560px"
    :close-on-click-modal="!syncing"
    :close-on-press-escape="!syncing"
    class="sync-progress-dialog"
  >
    <div class="sync-header">
      <div>
        <p>正在同步</p>
        <strong>{{ stockLabel }}</strong>
      </div>
      <el-tag :type="stageType" effect="dark">{{ stageLabel }}</el-tag>
    </div>

    <el-progress
      class="main-progress"
      :percentage="progressPercent"
      :stroke-width="14"
      :status="progressStatus"
    />

    <div class="current-step" :class="{ failed: isFailed }">
      <span class="step-index">{{ currentStepIndex }}</span>
      <div>
        <strong>{{ currentMessage }}</strong>
        <small>{{ updatedAtText }}</small>
      </div>
    </div>

    <div class="meta-grid">
      <div>
        <span>数据源</span>
        <strong>{{ activeProvider || '等待连接' }}</strong>
      </div>
      <div>
        <span>股票代码</span>
        <strong>{{ activeCode || currentCode || '-' }}</strong>
      </div>
      <div>
        <span>同步数量</span>
        <strong>{{ countText }}</strong>
      </div>
      <div>
        <span>完成度</span>
        <strong>{{ progressPercent }}%</strong>
      </div>
    </div>

    <div class="compact-steps">
      <div
        v-for="(step, index) in steps"
        :key="step.title"
        class="compact-step"
        :class="{ active: index === activeStep, done: index < activeStep }"
      >
        <span>{{ index + 1 }}</span>
        <strong>{{ step.title }}</strong>
      </div>
    </div>

    <template #footer>
      <el-button :disabled="syncing" @click="visibleModel = false">
        {{ syncing ? '同步中，请稍候' : '关闭' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Stock, SyncProgress } from '../api'

const props = defineProps<{
  visible: boolean
  syncing: boolean
  progress: SyncProgress | null
  currentCode: string
  currentStock: Stock | null
  mode: 'current' | 'all'
  totalStocks: number
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const visibleModel = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value)
})

const dialogTitle = computed(() => (props.mode === 'all' ? '同步股票范围' : '同步当前股票'))
const progressPercent = computed(() => Math.max(0, Math.min(props.progress?.percent ?? 0, 100)))
const isFailed = computed(() => props.progress?.stage === 'failed')
const progressStatus = computed(() => (isFailed.value ? 'exception' : progressPercent.value === 100 ? 'success' : undefined))
const activeProvider = computed(() => props.progress?.provider ?? null)
const activeCode = computed(() => props.progress?.code ?? null)
const stockLabel = computed(() => {
  if (props.mode === 'all') return `全部股票池范围（${props.totalStocks} 只）`
  if (!props.currentStock) return props.currentCode || '未选择股票'
  return `${props.currentStock.name}（${props.currentStock.code}）`
})
const currentMessage = computed(() => props.progress?.message ?? '等待同步任务开始')
const countText = computed(() => {
  const current = props.progress?.current ?? 0
  const total = props.progress?.total ?? 0
  if (!total) return props.mode === 'all' ? `0/${props.totalStocks}` : '等待统计'
  return `${current}/${total}`
})
const updatedAtText = computed(() => {
  if (!props.progress?.updated_at) return '尚未收到进度'
  return `更新时间 ${new Date(props.progress.updated_at).toLocaleTimeString()}`
})

const activeStep = computed(() => {
  const stage = props.progress?.stage
  if (stage === 'quotes') return progressPercent.value < 42 ? 0 : 1
  if (stage === 'kline') return progressPercent.value < 90 ? 2 : 3
  if (stage === 'done' || stage === 'failed') return 3
  return props.syncing ? 0 : -1
})
const currentStepIndex = computed(() => `步骤 ${Math.max(activeStep.value + 1, 1)}`)
const stageLabel = computed(() => {
  if (isFailed.value) return '同步失败'
  if (!props.syncing && progressPercent.value === 100) return '已完成'
  if (props.progress?.stage === 'quotes') return '实时行情'
  if (props.progress?.stage === 'kline') return 'K线数据'
  if (props.progress?.stage === 'done') return '已完成'
  return props.syncing ? '准备中' : '等待同步'
})
const stageType = computed(() => (isFailed.value ? 'danger' : progressPercent.value === 100 ? 'success' : props.syncing ? 'warning' : 'info'))
const steps = computed(() => [
  { title: activeProvider.value ? `连接 ${activeProvider.value}` : '连接数据源' },
  { title: '同步行情' },
  { title: '同步K线' },
  { title: '写入并刷新' }
])
</script>

<style scoped>
.sync-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.sync-header p,
.meta-grid span,
.current-step small {
  margin: 0;
  color: #64748b;
  font-size: 12px;
}

.sync-header strong {
  display: block;
  margin-top: 2px;
  color: #0f172a;
  font-size: 16px;
}

.main-progress {
  margin-bottom: 12px;
}

.current-step {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px;
  border: 1px solid #bfdbfe;
  border-radius: 16px;
  background: #eff6ff;
}

  .current-step strong {
  display: block;
  color: #1e3a8a;
  font-size: 14px;
}

.current-step.failed {
  border-color: #fecaca;
  background: #fef2f2;
}

.current-step.failed strong {
  color: #b91c1c;
}

.current-step.failed .step-index {
  background: #dc2626;
}

.step-index {
  flex: 0 0 auto;
  padding: 5px 10px;
  border-radius: 999px;
  color: #fff;
  background: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 10px 0 12px;
}

.meta-grid div {
  padding: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #f8fafc;
}

.meta-grid strong {
  display: block;
  margin-top: 3px;
  color: #0f172a;
  font-size: 13px;
}

.compact-steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.compact-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  color: #64748b;
  background: #fff;
  font-size: 12px;
}

.compact-step span {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  color: #64748b;
  background: #e2e8f0;
  text-align: center;
  line-height: 18px;
  font-weight: 700;
}

.compact-step.active {
  border-color: #2563eb;
  color: #1d4ed8;
  background: #eff6ff;
}

.compact-step.done {
  border-color: #bbf7d0;
  color: #15803d;
  background: #f0fdf4;
}

.compact-step.active span,
.compact-step.done span {
  color: #fff;
  background: currentColor;
}

@media (max-width: 720px) {
  .meta-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
