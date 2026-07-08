<template>
  <section class="import-workbench-debug">
    <header class="import-workbench-debug__hero">
      <div>
        <span class="import-workbench-debug__eyebrow">Annual Report Intake</span>
        <h1>财报导入工作台</h1>
        <p>当前先恢复最安全的静态头部区域，不引入表单、表格、按钮交互和异步请求。</p>
      </div>
      <div class="import-workbench-debug__steps" aria-label="导入步骤">
        <div class="import-workbench-debug__step import-workbench-debug__step--active">
          <span>01</span>
          <strong>保存 PDF</strong>
          <small>文档资产化</small>
        </div>
        <div class="import-workbench-debug__step">
          <span>02</span>
          <strong>解析预览</strong>
          <small>结构化抽取</small>
        </div>
        <div class="import-workbench-debug__step">
          <span>03</span>
          <strong>确认入库</strong>
          <small>人工复核</small>
        </div>
      </div>
    </header>

    <section class="import-workbench-debug__layout">
      <div class="import-workbench-debug__left-rail">
        <article class="import-workbench-debug__upload-shell">
          <div class="import-workbench-debug__section-head">
            <span class="import-workbench-debug__kicker">上传入口</span>
            <h2>新增财报 PDF</h2>
            <p>当前先恢复最小真实上传闭环：可选择 PDF、填写补充信息并调用上传接口；暂不恢复拖拽上传和跨区域联动。</p>
          </div>

          <input
            ref="uploadInputRef"
            class="import-workbench-debug__file-input"
            type="file"
            accept="application/pdf,.pdf"
            @change="handleFileChange"
          />

          <button type="button" class="import-workbench-debug__dropzone import-workbench-debug__dropzone--button" @click="openFilePicker">
            <div class="import-workbench-debug__file-badge">PDF</div>
            <strong>{{ uploadFile ? uploadFile.name : '点击选择年报 / 半年报 PDF' }}</strong>
            <span>{{ uploadFile ? '已选择文件，下一步可直接提交解析。' : '当前先恢复点击选择文件，不启用拖拽行为。' }}</span>
          </button>

          <div class="import-workbench-debug__field-list">
            <input v-model="uploadForm.code" class="import-workbench-debug__field import-workbench-debug__field--input" placeholder="股票代码，可选" />
            <input v-model="uploadForm.reportPeriod" class="import-workbench-debug__field import-workbench-debug__field--input" placeholder="报告期，可选，如 2025 年报" />
            <input v-model="uploadForm.sourceSite" class="import-workbench-debug__field import-workbench-debug__field--input" placeholder="来源网站，可选" />
          </div>

          <button type="button" class="import-workbench-debug__button-shell import-workbench-debug__button-shell--button" :disabled="uploadSubmitting" @click="handleUploadSubmit">
            {{ uploadSubmitting ? '上传并解析中...' : '保存 PDF 并解析' }}
          </button>

          <div v-if="uploadSummary" class="import-workbench-debug__upload-result">
            <strong>{{ uploadSummary.duplicate ? '已复用现有 PDF 解析结果' : '上传完成' }}</strong>
            <span>文件：{{ uploadSummary.filename }}</span>
            <span>股票：{{ uploadSummary.code }}</span>
            <span>报告期：{{ uploadSummary.reportPeriod }}</span>
            <span>状态：{{ uploadSummary.status }}</span>
            <span>批次：#{{ uploadSummary.batchId }}</span>
          </div>
        </article>

        <article class="import-workbench-debug__manual-shell">
          <div class="import-workbench-debug__section-head">
            <span class="import-workbench-debug__kicker">人工修正</span>
            <h2>核心指标补录</h2>
            <p>当前只恢复手工补录卡片的静态外壳，不接入表单绑定、按钮事件和预览请求。</p>
          </div>

          <div class="import-workbench-debug__manual-grid">
            <div class="import-workbench-debug__field">股票代码</div>
            <div class="import-workbench-debug__field">报告期</div>
            <div class="import-workbench-debug__field">报告日期，如 2025-12-31</div>
            <div class="import-workbench-debug__field">营业收入</div>
            <div class="import-workbench-debug__field">净利润</div>
            <div class="import-workbench-debug__field">毛利率</div>
            <div class="import-workbench-debug__field">ROE</div>
            <div class="import-workbench-debug__field">研发费用率</div>
          </div>

          <div class="import-workbench-debug__button-shell import-workbench-debug__button-shell--secondary">生成手工预览</div>
        </article>
      </div>

      <div class="import-workbench-debug__stage">
        <article class="import-workbench-debug__library-shell">
          <div class="import-workbench-debug__section-head">
            <span class="import-workbench-debug__kicker">文档资产库</span>
            <h2>已入库 PDF 列表</h2>
            <p>当前已恢复真实数据加载和基础筛选，只展示列表结果；暂不接入点击预览、重解析、原文打开等高风险联动。</p>
          </div>

          <div class="import-workbench-debug__library-toolbar">
            <button
              type="button"
              class="import-workbench-debug__toolbar-pill import-workbench-debug__toolbar-pill--button"
              :class="{ 'import-workbench-debug__toolbar-pill--active': documentFilter === 'all' }"
              @click="documentFilter = 'all'"
            >
              全部文档
            </button>
            <button
              type="button"
              class="import-workbench-debug__toolbar-pill import-workbench-debug__toolbar-pill--button"
              :class="{ 'import-workbench-debug__toolbar-pill--active': documentFilter === 'recent' }"
              @click="documentFilter = 'recent'"
            >
              最近上传
            </button>
            <input
              v-model="documentKeyword"
              class="import-workbench-debug__toolbar-search import-workbench-debug__toolbar-search--input"
              placeholder="按股票代码 / 文件名 / 报告期搜索"
            />
          </div>

          <div v-if="documentsLoading" class="import-workbench-debug__table-empty">正在加载文档资产库...</div>
          <div v-else-if="filteredDocuments.length === 0" class="import-workbench-debug__table-empty">当前没有匹配的 PDF 文档记录。</div>
          <div v-else class="import-workbench-debug__table-shell" role="table" aria-label="文档资产库表格">
            <div class="import-workbench-debug__table-row import-workbench-debug__table-row--head" role="row">
              <div>文档</div>
              <div>报告期</div>
              <div>状态</div>
              <div>更新时间</div>
              <div>操作</div>
            </div>
            <div
              v-for="document in filteredDocuments"
              :key="document.id"
              class="import-workbench-debug__table-row"
              :class="{ 'import-workbench-debug__table-row--active': selectedDocumentId === document.id }"
              role="row"
            >
              <div>
                <strong>{{ document.original_filename }}</strong>
                <span>{{ document.code || '未识别代码' }} · {{ document.source_site || '来源未记录' }}</span>
              </div>
              <div>{{ document.report_period || '未识别' }}</div>
              <div><em :class="documentStatusClass(document.status)">{{ formatDocumentStatus(document.status) }}</em></div>
              <div>{{ formatDateTime(document.updated_at) }}</div>
              <div>
                <button type="button" class="import-workbench-debug__link-button" @click="loadPreview(document.id)">查看预览</button>
              </div>
            </div>
          </div>
        </article>

        <article class="import-workbench-debug__preview-shell">
          <div class="import-workbench-debug__section-head">
            <span class="import-workbench-debug__kicker">解析预览区</span>
            <h2>结构化抽取结果</h2>
            <p>当前已恢复预览编辑态和确认导入：支持在预览区修正核心字段并提交确认，字段来源仍保持只读展示，不接入抽屉。</p>
          </div>

          <div v-if="previewLoading" class="import-workbench-debug__table-empty">正在加载解析预览...</div>
          <div v-else-if="!selectedPreview" class="import-workbench-debug__table-empty">请选择一份文档以查看解析预览。</div>
          <template v-else>
            <div class="import-workbench-debug__preview-summary">
              <div v-for="metric in previewMetrics" :key="metric.label" class="import-workbench-debug__metric-shell">
                <small>{{ metric.label }}</small>
                <strong>{{ metric.value }}</strong>
                <span>只读展示真实解析结果，不开放编辑。</span>
              </div>
            </div>

            <div class="import-workbench-debug__preview-grid">
              <div class="import-workbench-debug__preview-form-shell">
                <div class="import-workbench-debug__preview-headline">
                  <strong>财务字段核对</strong>
                  <span>当前支持直接修正核心字段，并将修正值用于确认导入</span>
                </div>
                <div class="import-workbench-debug__preview-fields">
                  <label v-for="field in previewFields" :key="field.key" class="import-workbench-debug__edit-field">
                    <span class="import-workbench-debug__edit-label">{{ field.label }}</span>
                    <input
                      v-model="editableFinancial[field.key]"
                      class="import-workbench-debug__field import-workbench-debug__field--input"
                      :placeholder="field.label"
                    />
                    <small class="import-workbench-debug__edit-hint">当前值：{{ formatMetricValue(field.value, field.mode) }}</small>
                  </label>
                </div>
                <div class="import-workbench-debug__button-row">
                  <button type="button" class="import-workbench-debug__button-shell import-workbench-debug__button-shell--ghost import-workbench-debug__button-shell--button" @click="syncEditableFinancial(selectedPreview)">重置为解析结果</button>
                  <button
                    type="button"
                    class="import-workbench-debug__button-shell import-workbench-debug__button-shell--button"
                    :disabled="confirmSubmitting"
                    @click="handleConfirmImport"
                  >
                    {{ confirmSubmitting ? '确认导入中...' : '确认导入' }}
                  </button>
                </div>
              </div>

              <div class="import-workbench-debug__preview-notes-shell">
                <div class="import-workbench-debug__preview-headline">
                  <strong>字段来源说明</strong>
                  <span>当前只读展示字段来源摘要，不打开抽屉、不联动原文预览</span>
                </div>
                <div v-if="previewSources.length > 0" class="import-workbench-debug__source-list">
                  <div v-for="source in previewSources" :key="source.key" class="import-workbench-debug__source-item">
                    <strong>{{ source.label }}</strong>
                    <span>{{ source.detail || '暂无来源说明' }}</span>
                  </div>
                </div>
                <div v-else class="import-workbench-debug__table-empty">当前预览没有可展示的字段来源说明。</div>
              </div>
            </div>
          </template>
        </article>

        <div class="import-workbench-debug__card">
          <h2>导入财报页调试中</h2>
          <p>当前组件采用“静态外壳逐块恢复”方式验证风险区，避免一次性回挂真实表格和预览逻辑。</p>
          <p>当前页面收口目标已明确为上传区、文档资产库、解析预览区三块闭环，不再恢复导入批次区。</p>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type ConfirmImportRequest, type ImportPreview, type ReportDocument, type ReportDocumentUploadResult } from '../api'

const uploadFile = ref<File | null>(null)
const uploadInputRef = ref<HTMLInputElement | null>(null)
const uploadSubmitting = ref(false)
const uploadResult = ref<ReportDocumentUploadResult | null>(null)
const documentsLoading = ref(false)
const documentKeyword = ref('')
const documentFilter = ref<'all' | 'recent'>('all')
const documents = ref<ReportDocument[]>([])
const previewLoading = ref(false)
const confirmSubmitting = ref(false)
const selectedDocumentId = ref<number | null>(null)
const selectedPreview = ref<ImportPreview | null>(null)

type EditableFinancialKey =
  | 'code'
  | 'report_period'
  | 'report_date'
  | 'revenue'
  | 'gross_profit'
  | 'gross_margin'
  | 'net_profit'
  | 'operating_cash_flow'
  | 'total_assets'
  | 'net_assets'
  | 'eps'
  | 'roe'
  | 'rd_ratio'

type MetricMode = 'currency' | 'percent' | 'plain'

const editableFinancial = reactive<Record<EditableFinancialKey, string>>({
  code: '',
  report_period: '',
  report_date: '',
  revenue: '',
  gross_profit: '',
  gross_margin: '',
  net_profit: '',
  operating_cash_flow: '',
  total_assets: '',
  net_assets: '',
  eps: '',
  roe: '',
  rd_ratio: ''
})

const uploadForm = reactive({
  code: '',
  reportPeriod: '',
  sourceSite: ''
})

const uploadSummary = computed(() => {
  if (!uploadResult.value) return null
  const { document, is_duplicate, preview } = uploadResult.value
  return {
    filename: document.original_filename,
    status: document.status,
    duplicate: is_duplicate,
    batchId: preview.batch.id,
    reportPeriod: document.report_period || uploadForm.reportPeriod || '未识别',
    code: document.code || uploadForm.code || '未识别'
  }
})

const filteredDocuments = computed(() => {
  const keyword = documentKeyword.value.trim().toLowerCase()
  let list = [...documents.value]

  if (documentFilter.value === 'recent') {
    list.sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)))
    list = list.slice(0, 8)
  }

  if (!keyword) return list

  return list.filter((item) => {
    const haystack = [item.code, item.report_period, item.original_filename, item.source_site]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return haystack.includes(keyword)
  })
})

const previewMetrics = computed(() => {
  const financial = selectedPreview.value?.financial
  if (!financial) return []
  return [
    { label: '营业收入', value: formatMetricValue(financial.revenue, 'currency') },
    { label: '归母净利润', value: formatMetricValue(financial.net_profit, 'currency') },
    { label: '毛利率', value: formatMetricValue(financial.gross_margin, 'percent') }
  ]
})

const previewFields = computed<Array<{ key: EditableFinancialKey; label: string; value: string; mode: MetricMode }>>(() => [
  { key: 'code', label: '股票代码', value: editableFinancial.code, mode: 'plain' },
  { key: 'report_period', label: '报告期', value: editableFinancial.report_period, mode: 'plain' },
  { key: 'report_date', label: '报告日期', value: editableFinancial.report_date, mode: 'plain' },
  { key: 'operating_cash_flow', label: '经营现金流', value: editableFinancial.operating_cash_flow, mode: 'currency' },
  { key: 'net_assets', label: '净资产', value: editableFinancial.net_assets, mode: 'currency' },
  { key: 'rd_ratio', label: '研发费用率', value: editableFinancial.rd_ratio, mode: 'percent' }
])

const previewSources = computed(() => {
  const fieldSources = selectedPreview.value?.field_sources
  if (!fieldSources) return []
  return Object.entries(fieldSources)
    .slice(0, 6)
    .map(([key, source]) => ({
      key,
      label: source.label || key,
      detail: [source.section, source.label ? `命中“${source.label}”` : null, source.unit ? `单位：${source.unit}` : null, source.confidence ? `置信度：${source.confidence}` : null]
        .filter(Boolean)
        .join(' / ')
    }))
})

function resetEditableFinancial() {
  editableFinancial.code = ''
  editableFinancial.report_period = ''
  editableFinancial.report_date = ''
  editableFinancial.revenue = ''
  editableFinancial.gross_profit = ''
  editableFinancial.gross_margin = ''
  editableFinancial.net_profit = ''
  editableFinancial.operating_cash_flow = ''
  editableFinancial.total_assets = ''
  editableFinancial.net_assets = ''
  editableFinancial.eps = ''
  editableFinancial.roe = ''
  editableFinancial.rd_ratio = ''
}

function syncEditableFinancial(preview: ImportPreview | null) {
  if (!preview?.financial) {
    resetEditableFinancial()
    return
  }
  editableFinancial.code = preview.financial.code ?? ''
  editableFinancial.report_period = preview.financial.report_period ?? ''
  editableFinancial.report_date = preview.financial.report_date ?? ''
  editableFinancial.revenue = stringifyEditable(preview.financial.revenue)
  editableFinancial.gross_profit = stringifyEditable(preview.financial.gross_profit)
  editableFinancial.gross_margin = stringifyEditable(preview.financial.gross_margin)
  editableFinancial.net_profit = stringifyEditable(preview.financial.net_profit)
  editableFinancial.operating_cash_flow = stringifyEditable(preview.financial.operating_cash_flow)
  editableFinancial.total_assets = stringifyEditable(preview.financial.total_assets)
  editableFinancial.net_assets = stringifyEditable(preview.financial.net_assets)
  editableFinancial.eps = stringifyEditable(preview.financial.eps)
  editableFinancial.roe = stringifyEditable(preview.financial.roe)
  editableFinancial.rd_ratio = stringifyEditable(preview.financial.rd_ratio)
}

function stringifyEditable(value: string | number | null | undefined) {
  return value === null || value === undefined ? '' : String(value)
}

function toNullableNumber(value: string) {
  const trimmed = value.trim()
  if (!trimmed) return null
  const numeric = Number(trimmed.replace(/,/g, ''))
  return Number.isNaN(numeric) ? trimmed : numeric
}

function buildConfirmPayload(): ConfirmImportRequest | null {
  const preview = selectedPreview.value
  if (!preview) return null
  return {
    financial: {
      code: editableFinancial.code.trim(),
      report_period: editableFinancial.report_period.trim(),
      report_date: editableFinancial.report_date.trim() || null,
      revenue: toNullableNumber(editableFinancial.revenue),
      gross_profit: toNullableNumber(editableFinancial.gross_profit),
      gross_margin: toNullableNumber(editableFinancial.gross_margin),
      net_profit: toNullableNumber(editableFinancial.net_profit),
      operating_cash_flow: toNullableNumber(editableFinancial.operating_cash_flow),
      total_assets: toNullableNumber(editableFinancial.total_assets),
      net_assets: toNullableNumber(editableFinancial.net_assets),
      eps: toNullableNumber(editableFinancial.eps),
      roe: toNullableNumber(editableFinancial.roe),
      rd_ratio: toNullableNumber(editableFinancial.rd_ratio)
    },
    segments: preview.segments,
    expenses: preview.expenses,
    extractions: preview.extractions
  }
}

async function handleConfirmImport() {
  const preview = selectedPreview.value
  if (!preview) {
    ElMessage.warning('请先选择解析预览')
    return
  }
  const payload = buildConfirmPayload()
  if (!payload) {
    ElMessage.warning('当前没有可确认的预览数据')
    return
  }
  if (!payload.financial.code || !payload.financial.report_period) {
    ElMessage.warning('请先补全股票代码和报告期')
    return
  }

  confirmSubmitting.value = true
  try {
    const response = await api.confirmImport(preview.batch.id, payload)
    selectedPreview.value = {
      ...preview,
      financial: payload.financial,
      batch: response.data?.batch ?? preview.batch
    }
    await loadDocuments()
    ElMessage.success('确认导入完成')
  } catch (error) {
    const message = error instanceof Error ? error.message : '确认导入失败'
    ElMessage.error(message)
  } finally {
    confirmSubmitting.value = false
  }
}

watch(
  () => selectedPreview.value,
  (preview) => {
    syncEditableFinancial(preview)
  },
  { immediate: true }
)

function formatMetricValue(value: string | number | null | undefined, mode: MetricMode) {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value)
  if (mode === 'percent') return `${numeric.toFixed(2)}%`
  if (mode === 'currency') return `¥${numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
  return numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function formatDocumentStatus(status: string) {
  const normalized = status.toLowerCase()
  if (normalized.includes('confirmed') || normalized.includes('imported')) return '已确认'
  if (normalized.includes('processing') || normalized.includes('parsing')) return '解析中'
  if (normalized.includes('failed') || normalized.includes('error')) return '失败'
  return '待复核'
}

function documentStatusClass(status: string) {
  const normalized = status.toLowerCase()
  if (normalized.includes('confirmed') || normalized.includes('imported')) {
    return 'import-workbench-debug__status-chip import-workbench-debug__status-chip--success'
  }
  if (normalized.includes('processing') || normalized.includes('parsing')) {
    return 'import-workbench-debug__status-chip import-workbench-debug__status-chip--warning'
  }
  if (normalized.includes('failed') || normalized.includes('error')) {
    return 'import-workbench-debug__status-chip import-workbench-debug__status-chip--danger'
  }
  return 'import-workbench-debug__status-chip'
}

function formatDateTime(value: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function openFilePicker() {
  uploadInputRef.value?.click()
}

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement | null
  const file = target?.files?.[0] ?? null
  uploadFile.value = file
  uploadResult.value = null
}

async function loadDocuments() {
  documentsLoading.value = true
  try {
    const response = await api.getReportDocuments()
    documents.value = response.data ?? []
  } catch (error) {
    const message = error instanceof Error ? error.message : '文档资产库加载失败'
    ElMessage.error(message)
  } finally {
    documentsLoading.value = false
  }
}

async function loadPreview(documentId: number) {
  selectedDocumentId.value = documentId
  previewLoading.value = true
  try {
    const response = await api.getReportDocumentPreview(documentId)
    selectedPreview.value = response.data
  } catch (error) {
    selectedPreview.value = null
    const message = error instanceof Error ? error.message : '解析预览加载失败'
    ElMessage.error(message)
  } finally {
    previewLoading.value = false
  }
}

async function handleUploadSubmit() {
  if (!uploadFile.value) {
    ElMessage.warning('请先选择 PDF 文件')
    return
  }

  uploadSubmitting.value = true
  try {
    const response = await api.uploadReportDocument(
      uploadFile.value,
      uploadForm.code.trim() || undefined,
      uploadForm.reportPeriod.trim() || undefined,
      uploadForm.sourceSite.trim() || undefined
    )
    if (!response.data) {
      throw new Error('上传接口未返回解析结果')
    }
    uploadResult.value = response.data
    selectedDocumentId.value = response.data.document.id
    selectedPreview.value = response.data.preview
    await loadDocuments()
    ElMessage.success(uploadResult.value.is_duplicate ? 'PDF 已存在，已返回最新解析结果' : 'PDF 上传并解析成功')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'PDF 上传失败'
    ElMessage.error(message)
  } finally {
    uploadSubmitting.value = false
  }
}

onMounted(async () => {
  await loadDocuments()
  if (documents.value.length > 0) {
    await loadPreview(documents.value[0].id)
  }
})
</script>

<style scoped>
.import-workbench-debug {
  min-height: 320px;
  padding: 24px;
}

.import-workbench-debug__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 20px;
  margin-bottom: 20px;
  padding: 24px;
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(255, 250, 242, 0.96), rgba(237, 244, 255, 0.96));
}

.import-workbench-debug__eyebrow {
  display: inline-flex;
  margin-bottom: 10px;
  color: #b98224;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.import-workbench-debug__hero h1 {
  margin: 0 0 10px;
  color: #18212f;
  font-size: 36px;
  line-height: 1.1;
}

.import-workbench-debug__hero p {
  margin: 0;
  color: #5b6b7f;
  line-height: 1.8;
}

.import-workbench-debug__steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-self: end;
}

.import-workbench-debug__step {
  min-height: 112px;
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.8);
}

.import-workbench-debug__step span,
.import-workbench-debug__step strong,
.import-workbench-debug__step small {
  display: block;
}

.import-workbench-debug__step span {
  margin-bottom: 16px;
  color: rgba(59, 130, 246, 0.4);
  font-size: 24px;
  font-weight: 900;
}

.import-workbench-debug__step strong {
  margin-bottom: 4px;
  color: #18212f;
}

.import-workbench-debug__step small {
  color: #5b6b7f;
}

.import-workbench-debug__step--active {
  background: linear-gradient(145deg, #2356d7, #183b98);
}

.import-workbench-debug__step--active span,
.import-workbench-debug__step--active strong,
.import-workbench-debug__step--active small {
  color: #ffffff;
}

.import-workbench-debug__layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 20px;
}

.import-workbench-debug__left-rail {
  display: grid;
  gap: 20px;
}

.import-workbench-debug__stage {
  display: grid;
  gap: 20px;
}

.import-workbench-debug__upload-shell,
.import-workbench-debug__manual-shell,
.import-workbench-debug__library-shell,
.import-workbench-debug__preview-shell,
.import-workbench-debug__card {
  padding: 24px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.88);
}

.import-workbench-debug__manual-shell,
.import-workbench-debug__library-shell,
.import-workbench-debug__preview-shell {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 250, 252, 0.92));
}

.import-workbench-debug__section-head h2,
.import-workbench-debug__card h2 {
  margin: 8px 0 12px;
  color: #18212f;
  font-size: 28px;
}

.import-workbench-debug__section-head p,
.import-workbench-debug__card p {
  margin: 0;
  color: #5b6b7f;
  line-height: 1.8;
}

.import-workbench-debug__manual-shell .import-workbench-debug__section-head p {
  margin-bottom: 18px;
}

.import-workbench-debug__kicker {
  display: inline-flex;
  color: #b98224;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.import-workbench-debug__file-input {
  display: none;
}

.import-workbench-debug__dropzone {
  width: 100%;
  margin: 20px 0 16px;
  padding: 24px 18px;
  border: 1.5px dashed rgba(59, 130, 246, 0.3);
  border-radius: 22px;
  background: rgba(231, 239, 255, 0.45);
  text-align: center;
}

.import-workbench-debug__dropzone--button {
  color: inherit;
  cursor: pointer;
}

.import-workbench-debug__dropzone strong,
.import-workbench-debug__dropzone span {
  display: block;
}

.import-workbench-debug__dropzone strong {
  margin-bottom: 6px;
  color: #18212f;
}

.import-workbench-debug__dropzone span {
  color: #5b6b7f;
  line-height: 1.7;
}

.import-workbench-debug__file-badge {
  display: grid;
  place-items: center;
  width: 68px;
  height: 82px;
  margin: 0 auto 14px;
  border-radius: 12px 12px 18px 18px;
  color: #ffffff;
  background: linear-gradient(160deg, #d94841, #f08a5b);
  font-weight: 900;
  letter-spacing: 0.08em;
}

.import-workbench-debug__field-list,
.import-workbench-debug__manual-grid {
  display: grid;
  gap: 10px;
}

.import-workbench-debug__manual-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.import-workbench-debug__field {
  min-height: 44px;
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 14px;
  color: #6b7a8c;
  background: rgba(255, 255, 255, 0.92);
}

.import-workbench-debug__field--input {
  width: 100%;
  font: inherit;
  outline: none;
}

.import-workbench-debug__field--input::placeholder {
  color: #94a3b8;
}

.import-workbench-debug__button-shell {
  margin-top: 16px;
  padding: 13px 16px;
  border-radius: 14px;
  color: #ffffff;
  background: linear-gradient(145deg, #2356d7, #183b98);
  text-align: center;
  font-weight: 800;
}

.import-workbench-debug__button-shell--button {
  width: 100%;
  border: none;
  cursor: pointer;
}

.import-workbench-debug__button-shell--button:disabled {
  opacity: 0.7;
  cursor: wait;
}

.import-workbench-debug__button-shell--secondary {
  margin-top: 18px;
  background: linear-gradient(145deg, #4b5563, #334155);
}

.import-workbench-debug__upload-result {
  display: grid;
  gap: 6px;
  margin-top: 16px;
  padding: 16px 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.96);
}

.import-workbench-debug__upload-result strong {
  color: #18212f;
}

.import-workbench-debug__upload-result span {
  color: #5b6b7f;
  line-height: 1.6;
}

.import-workbench-debug__library-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 20px 0 16px;
}

.import-workbench-debug__toolbar-pill,
.import-workbench-debug__toolbar-search {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  padding: 0 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 999px;
  color: #5b6b7f;
  background: rgba(255, 255, 255, 0.94);
}

.import-workbench-debug__toolbar-pill--button {
  cursor: pointer;
}

.import-workbench-debug__toolbar-pill--active {
  color: #ffffff;
  background: linear-gradient(145deg, #2356d7, #183b98);
}

.import-workbench-debug__toolbar-search {
  min-width: min(100%, 280px);
  color: #94a3b8;
}

.import-workbench-debug__toolbar-search--input {
  width: 100%;
  font: inherit;
  outline: none;
}

.import-workbench-debug__toolbar-search--input::placeholder {
  color: #94a3b8;
}

.import-workbench-debug__table-shell {
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
}

.import-workbench-debug__table-row {
  display: grid;
  grid-template-columns: minmax(220px, 2fr) 1fr 120px 160px 100px;
  gap: 12px;
  align-items: center;
  padding: 16px 18px;
  border-top: 1px solid rgba(226, 232, 240, 0.9);
}

.import-workbench-debug__table-row:first-child {
  border-top: none;
}

.import-workbench-debug__table-row--active {
  background: rgba(237, 244, 255, 0.8);
}

.import-workbench-debug__table-row--head {
  color: #475569;
  font-size: 13px;
  font-weight: 800;
  background: rgba(241, 245, 249, 0.88);
}

.import-workbench-debug__table-row strong,
.import-workbench-debug__table-row span,
.import-workbench-debug__link-action {
  display: block;
}

.import-workbench-debug__table-row strong {
  margin-bottom: 4px;
  color: #18212f;
}

.import-workbench-debug__table-row span {
  color: #6b7a8c;
  line-height: 1.6;
}

.import-workbench-debug__status-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 68px;
  padding: 6px 10px;
  border-radius: 999px;
  color: #9a6700;
  background: rgba(255, 244, 214, 0.95);
  font-style: normal;
  font-weight: 700;
}

.import-workbench-debug__status-chip--success {
  color: #0f766e;
  background: rgba(204, 251, 241, 0.95);
}

.import-workbench-debug__status-chip--warning {
  color: #1d4ed8;
  background: rgba(219, 234, 254, 0.95);
}

.import-workbench-debug__status-chip--danger {
  color: #b42318;
  background: rgba(254, 226, 226, 0.95);
}

.import-workbench-debug__link-action {
  color: #2356d7;
  font-weight: 700;
}

.import-workbench-debug__link-button {
  border: none;
  padding: 0;
  color: #2356d7;
  background: transparent;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.import-workbench-debug__table-empty {
  padding: 18px;
  border: 1px dashed rgba(148, 163, 184, 0.28);
  border-radius: 16px;
  color: #6b7a8c;
  background: rgba(255, 255, 255, 0.9);
}

.import-workbench-debug__preview-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 20px 0 16px;
}

.import-workbench-debug__metric-shell,
.import-workbench-debug__preview-form-shell,
.import-workbench-debug__preview-notes-shell {
  padding: 18px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
}

.import-workbench-debug__metric-shell small,
.import-workbench-debug__metric-shell strong,
.import-workbench-debug__metric-shell span {
  display: block;
}

.import-workbench-debug__metric-shell small {
  margin-bottom: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.import-workbench-debug__metric-shell strong {
  margin-bottom: 6px;
  color: #18212f;
  font-size: 24px;
}

.import-workbench-debug__metric-shell span {
  color: #6b7a8c;
  line-height: 1.6;
}

.import-workbench-debug__preview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 16px;
}

.import-workbench-debug__preview-headline {
  margin-bottom: 14px;
}

.import-workbench-debug__preview-headline strong,
.import-workbench-debug__preview-headline span {
  display: block;
}

.import-workbench-debug__preview-headline strong {
  margin-bottom: 6px;
  color: #18212f;
}

.import-workbench-debug__preview-headline span {
  color: #6b7a8c;
  line-height: 1.6;
}

.import-workbench-debug__preview-fields,
.import-workbench-debug__source-list {
  display: grid;
  gap: 10px;
}

.import-workbench-debug__edit-field {
  display: grid;
  gap: 6px;
}

.import-workbench-debug__edit-label {
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.import-workbench-debug__edit-hint {
  color: #94a3b8;
  line-height: 1.5;
}

.import-workbench-debug__button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
}

.import-workbench-debug__button-row .import-workbench-debug__button-shell {
  flex: 1 1 180px;
  margin-top: 0;
}

.import-workbench-debug__button-shell--ghost {
  color: #2356d7;
  background: rgba(219, 234, 254, 0.7);
}

.import-workbench-debug__button-shell--disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.import-workbench-debug__source-item {
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.9);
}

.import-workbench-debug__source-item strong,
.import-workbench-debug__source-item span {
  display: block;
}

.import-workbench-debug__source-item strong {
  margin-bottom: 6px;
  color: #18212f;
}

.import-workbench-debug__source-item span {
  color: #6b7a8c;
  line-height: 1.6;
}

.import-workbench-debug__card p + p {
  margin-top: 8px;
}

@media (max-width: 960px) {
  .import-workbench-debug__hero,
  .import-workbench-debug__steps,
  .import-workbench-debug__layout,
  .import-workbench-debug__table-row,
  .import-workbench-debug__preview-summary,
  .import-workbench-debug__preview-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .import-workbench-debug__manual-grid {
    grid-template-columns: 1fr;
  }

  .import-workbench-debug__library-toolbar {
    flex-direction: column;
  }

  .import-workbench-debug__toolbar-search {
    min-width: 0;
  }
}
</style>
