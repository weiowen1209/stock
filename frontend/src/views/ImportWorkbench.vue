<template>
  <section class="report-workbench">
    <header class="hero-panel">
      <div class="hero-copy">
        <span class="eyebrow">Annual Report Intake</span>
        <h1>财报导入工作台</h1>
        <p>把 PDF 先沉淀成可复用文档资产，再抽取三表、费用结构和业务分部，最后人工确认入库。</p>
      </div>
      <div class="hero-steps" aria-label="导入步骤">
        <div class="step active">
          <span>01</span>
          <strong>保存PDF</strong>
          <small>hash 去重</small>
        </div>
        <div class="step">
          <span>02</span>
          <strong>解析预览</strong>
          <small>三表 + 分部</small>
        </div>
        <div class="step">
          <span>03</span>
          <strong>确认入库</strong>
          <small>可追溯来源</small>
        </div>
      </div>
    </header>

    <div class="workspace-layout">
      <aside class="left-rail">
        <article class="panel upload-panel">
          <div class="panel-title">
            <span class="kicker">上传入口</span>
            <h2>新增财报 PDF</h2>
            <p>适合第一次导入某份公告；相同文件会自动复用，不重复保存。</p>
          </div>

          <el-upload
            class="pdf-dropzone"
            drag
            :auto-upload="false"
            :show-file-list="true"
            :on-change="handleFileChange"
            accept=".pdf,.txt,.csv"
          >
            <div class="upload-icon">PDF</div>
            <div class="el-upload__text">拖入年报 / 半年报 PDF，或点击选择</div>
            <template #tip>
              <div class="upload-tip">建议文件名包含股票代码和报告期，例如 688017_绿的谐波_2025年报.pdf</div>
            </template>
          </el-upload>

          <div class="compact-form">
            <el-input v-model="uploadCode" clearable placeholder="股票代码，可选" />
            <el-input v-model="uploadPeriod" clearable placeholder="报告期，可选，如2025年报" />
            <el-input v-model="sourceSite" clearable placeholder="来源网站，可选" />
          </div>

          <el-button class="primary-action" type="primary" :loading="loading" @click="uploadDocument">
            保存 PDF 并解析
          </el-button>
        </article>

        <article class="panel manual-panel">
          <div class="panel-title compact">
            <span class="kicker">人工修正</span>
            <h2>核心指标补录</h2>
            <p>用于 PDF 识别失败、补关键字段或快速生成一条确认预览。</p>
          </div>

          <el-form label-position="top" class="manual-form">
            <el-form-item label="股票代码"><el-input v-model="manual.financial.code" /></el-form-item>
            <el-form-item label="报告期"><el-input v-model="manual.financial.report_period" /></el-form-item>
            <el-form-item label="报告日期"><el-input v-model="manual.financial.report_date" placeholder="2025-12-31" /></el-form-item>
            <el-form-item label="营业收入"><el-input v-model="manual.financial.revenue" /></el-form-item>
            <el-form-item label="净利润"><el-input v-model="manual.financial.net_profit" /></el-form-item>
            <el-form-item label="毛利率"><el-input v-model="manual.financial.gross_margin" /></el-form-item>
            <el-form-item label="ROE"><el-input v-model="manual.financial.roe" /></el-form-item>
            <el-form-item label="研发费用率"><el-input v-model="manual.financial.rd_ratio" /></el-form-item>
          </el-form>

          <el-button :loading="loading" @click="previewManual">生成手工预览</el-button>
        </article>
      </aside>

      <main class="main-stage">
        <article class="panel documents-panel">
          <div class="panel-toolbar">
            <div class="panel-title compact">
              <span class="kicker">文档资产库</span>
              <h2>已保存财报</h2>
            </div>
            <div class="toolbar-actions">
              <el-input v-model="documentCode" clearable placeholder="股票代码" @keyup.enter="loadDocuments" />
              <el-button @click="loadDocuments">刷新</el-button>
            </div>
          </div>

          <el-table
            class="document-table"
            :data="documents"
            height="360"
            :row-class-name="documentRowClassName"
            empty-text="暂无已保存财报，先上传一份 PDF"
            @row-click="loadDocumentPreview"
          >
            <el-table-column label="财报" min-width="280" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="doc-cell">
                  <strong>{{ row.original_filename }}</strong>
                  <span>#{{ row.id }} · {{ formatFileSize(row.file_size) }} · {{ row.page_count ?? '--' }}页</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="股票 / 期间" width="150">
              <template #default="{ row }">
                <div class="stacked-cell">
                  <strong>{{ row.code ?? '--' }}</strong>
                  <span>{{ row.report_period ?? '--' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <span :class="['status-pill', row.status]">{{ statusLabel(row.status) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="来源" width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.source_site || '本地上传' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click.stop="openDocument(row.id)">打开PDF</el-button>
                <el-button link type="primary" @click.stop="reparseDocument(row.id)">重解析</el-button>
              </template>
            </el-table-column>
          </el-table>
        </article>

        <section class="review-grid">
          <article class="panel preview-panel">
            <div class="panel-toolbar">
              <div class="panel-title compact">
                <span class="kicker">解析预览</span>
                <h2>{{ preview ? `批次 #${preview.batch.id}` : '等待选择文档' }}</h2>
              </div>
              <div v-if="preview" class="preview-tools">
                <span class="confidence-ring">{{ Number(preview.confidence).toFixed(2) }}</span>
                <el-button @click="sourceDrawerVisible = true">字段来源</el-button>
                <el-button v-if="preview.document" @click="openDocument(preview.document.id)">查看原文</el-button>
              </div>
            </div>

            <el-alert v-if="preview?.is_duplicate" class="notice" type="success" title="已复用相同 PDF，未重复保存文件。" show-icon />
            <el-alert v-for="warning in preview?.warnings" :key="warning" class="notice" type="warning" :title="warning" show-icon />

            <template v-if="preview">
              <div class="metric-grid">
                <div class="metric-card emphasis">
                  <span>营业收入</span>
                  <strong>{{ formatMoney(editableFinancial.revenue) }}</strong>
                </div>
                <div class="metric-card profit">
                  <span>归母净利润</span>
                  <strong>{{ formatMoney(editableFinancial.net_profit) }}</strong>
                </div>
                <div class="metric-card">
                  <span>毛利率</span>
                  <strong>{{ formatPercent(editableFinancial.gross_margin) }}</strong>
                </div>
                <div class="metric-card">
                  <span>研发费用率</span>
                  <strong>{{ formatPercent(editableFinancial.rd_ratio) }}</strong>
                </div>
                <div class="metric-card">
                  <span>经营现金流</span>
                  <strong>{{ formatMoney(editableFinancial.operating_cash_flow) }}</strong>
                </div>
                <div class="metric-card">
                  <span>总资产</span>
                  <strong>{{ formatMoney(editableFinancial.total_assets) }}</strong>
                </div>
              </div>

              <div class="edit-panel">
                <div class="section-head">
                  <strong>确认前可编辑字段</strong>
                  <span>修改后再确认入库，不影响原始PDF</span>
                </div>
                <el-form label-position="top" class="edit-form">
                  <el-form-item label="股票代码"><el-input v-model="editableFinancial.code" /></el-form-item>
                  <el-form-item label="报告期"><el-input v-model="editableFinancial.report_period" /></el-form-item>
                  <el-form-item label="报告日期"><el-input v-model="editableFinancial.report_date" /></el-form-item>
                  <el-form-item label="营业收入"><el-input v-model="editableFinancial.revenue" /></el-form-item>
                  <el-form-item label="毛利"><el-input v-model="editableFinancial.gross_profit" /></el-form-item>
                  <el-form-item label="毛利率"><el-input v-model="editableFinancial.gross_margin" /></el-form-item>
                  <el-form-item label="归母净利润"><el-input v-model="editableFinancial.net_profit" /></el-form-item>
                  <el-form-item label="经营现金流"><el-input v-model="editableFinancial.operating_cash_flow" /></el-form-item>
                  <el-form-item label="总资产"><el-input v-model="editableFinancial.total_assets" /></el-form-item>
                  <el-form-item label="净资产"><el-input v-model="editableFinancial.net_assets" /></el-form-item>
                  <el-form-item label="EPS"><el-input v-model="editableFinancial.eps" /></el-form-item>
                  <el-form-item label="ROE"><el-input v-model="editableFinancial.roe" /></el-form-item>
                  <el-form-item label="研发费用率"><el-input v-model="editableFinancial.rd_ratio" /></el-form-item>
                </el-form>
              </div>

              <div class="preview-meta">
                <span>股票：{{ preview.financial.code }}</span>
                <span>报告期：{{ preview.financial.report_period }}</span>
                <span>解析器：{{ preview.parse_job?.parser_version ?? '--' }}</span>
                <span>文档ID：{{ preview.document?.id ?? '--' }}</span>
              </div>

              <div v-if="preview.segments.length" class="segment-panel">
                <div class="section-head">
                  <strong>业务分部</strong>
                  <span>{{ preview.segments.length }} 条</span>
                </div>
                <div class="segment-list">
                  <span v-for="item in preview.segments" :key="`${item.segment_type}-${item.segment_name}`">
                    {{ segmentTypeLabel(item.segment_type) }} · {{ item.segment_name }} · {{ formatMoney(item.revenue) }}
                  </span>
                </div>
              </div>

              <el-button class="confirm-action" type="primary" :loading="loading" @click="confirmCurrent">确认入库</el-button>
            </template>

            <el-empty v-else description="上传 PDF 或点击文档库中的财报，右侧会生成可确认预览" />
          </article>

          <article class="panel batches-panel">
            <div class="panel-toolbar">
              <div class="panel-title compact">
                <span class="kicker">确认链路</span>
                <h2>导入批次</h2>
              </div>
              <el-button @click="loadBatches">刷新</el-button>
            </div>

            <el-table :data="batches" height="360" empty-text="暂无导入批次">
              <el-table-column prop="id" label="ID" width="70" />
              <el-table-column label="状态" width="105">
                <template #default="{ row }">
                  <span :class="['status-pill', row.status]">{{ statusLabel(row.status) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="对象" min-width="150">
                <template #default="{ row }">
                  <div class="stacked-cell">
                    <strong>{{ row.code ?? '--' }}</strong>
                    <span>{{ row.report_period ?? '--' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="document_id" label="文档ID" width="90" />
              <el-table-column prop="created_at" label="创建时间" min-width="170" />
            </el-table>
          </article>
        </section>
      </main>
    </div>
    <el-drawer v-model="sourceDrawerVisible" size="46%" title="字段来源核对" append-to-body>
      <div class="source-drawer">
        <p>这里展示解析器命中的字段标签、表区、单位和原文行。发现误识别时，可回到预览区直接修正字段后再确认入库。</p>
        <el-table :data="fieldSourceRows" height="calc(100vh - 190px)" empty-text="当前预览没有字段来源信息">
          <el-table-column prop="fieldLabel" label="字段" width="120" />
          <el-table-column prop="sectionLabel" label="表区" width="100" />
          <el-table-column prop="source.label" label="命中标签" width="160" show-overflow-tooltip />
          <el-table-column label="数值" width="130">
            <template #default="{ row }">{{ row.source.value ?? '--' }}</template>
          </el-table-column>
          <el-table-column label="置信度" width="100">
            <template #default="{ row }">{{ formatPercentFromRatio(row.source.confidence) }}</template>
          </el-table-column>
          <el-table-column prop="source.unit" label="单位" width="90" />
          <el-table-column prop="source.line" label="原文行" min-width="280" show-overflow-tooltip />
        </el-table>
      </div>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import type { UploadFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { api, type ConfirmImportRequest, type FieldSource, type ImportBatch, type ImportPreview, type ReportDocument } from '../api'

const loading = ref(false)
const selectedFile = ref<File | null>(null)
const uploadCode = ref('')
const uploadPeriod = ref('')
const sourceSite = ref('')
const documentCode = ref('')
const preview = ref<ImportPreview | null>(null)
const batches = ref<ImportBatch[]>([])
const documents = ref<ReportDocument[]>([])
const sourceDrawerVisible = ref(false)
const editableFinancial = reactive<ConfirmImportRequest['financial']>(createEmptyFinancial())

const selectedDocumentId = computed(() => preview.value?.document?.id ?? null)
const fieldSourceRows = computed(() => buildFieldSourceRows(preview.value?.field_sources ?? {}))

const manual = reactive<ConfirmImportRequest>({
  financial: {
    ...createEmptyFinancial(),
    code: '688017',
    report_period: '2025年报',
    report_date: '2025-12-31'
  },
  segments: [],
  expenses: null
})

function createEmptyFinancial(): ConfirmImportRequest['financial'] {
  return {
    code: '',
    report_period: '',
    report_date: null,
    revenue: null,
    gross_profit: null,
    gross_margin: null,
    net_profit: null,
    operating_cash_flow: null,
    total_assets: null,
    net_assets: null,
    eps: null,
    roe: null,
    rd_ratio: null
  }
}

function syncEditableFinancial(nextPreview: ImportPreview | null) {
  Object.assign(editableFinancial, nextPreview?.financial ?? createEmptyFinancial())
}

watch(preview, syncEditableFinancial, { immediate: true })

function handleFileChange(file: UploadFile) {
  selectedFile.value = file.raw ?? null
  if (selectedFile.value) {
    ElMessage.success('PDF文件已选择')
  }
}

async function uploadDocument() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  loading.value = true
  try {
    const response = await api.uploadReportDocument(selectedFile.value, uploadCode.value, uploadPeriod.value, sourceSite.value)
    if (!response.data) return
    preview.value = response.data.preview
    ElMessage.success(response.data.is_duplicate ? '已复用相同PDF并生成预览' : 'PDF已保存并生成预览')
    await Promise.all([loadDocuments(), loadBatches()])
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '保存并解析失败')
  } finally {
    loading.value = false
  }
}

async function previewManual() {
  loading.value = true
  try {
    const response = await api.createManualImport(manual)
    preview.value = response.data
    ElMessage.success('预览已生成')
    await loadBatches()
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '生成预览失败')
  } finally {
    loading.value = false
  }
}

async function loadDocumentPreview(row: ReportDocument) {
  try {
    const response = await api.getReportDocumentPreview(row.id)
    preview.value = response.data
  } catch (err) {
    ElMessage.warning(err instanceof Error ? err.message : '该文档暂无解析预览')
  }
}

async function reparseDocument(documentId: number) {
  loading.value = true
  try {
    const response = await api.reparseReportDocument(documentId)
    preview.value = response.data
    ElMessage.success('已基于保存的PDF重新解析')
    await Promise.all([loadDocuments(), loadBatches()])
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '重新解析失败')
  } finally {
    loading.value = false
  }
}

function openDocument(documentId: number) {
  window.open(`/api/imports/documents/${documentId}/file`, '_blank')
}

async function confirmCurrent() {
  if (!preview.value) return
  loading.value = true
  try {
    await api.confirmImport(preview.value.batch.id, {
      financial: { ...editableFinancial },
      segments: preview.value.segments,
      expenses: preview.value.expenses
    })
    ElMessage.success('导入已确认入库')
    await Promise.all([loadDocuments(), loadBatches()])
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '确认入库失败')
  } finally {
    loading.value = false
  }
}

async function loadBatches() {
  try {
    const response = await api.getImportBatches()
    batches.value = response.data ?? []
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '导入批次加载失败')
  }
}

async function loadDocuments() {
  try {
    const response = await api.getReportDocuments(documentCode.value ? { code: documentCode.value } : undefined)
    documents.value = response.data ?? []
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '财报文档加载失败')
  }
}

function buildFieldSourceRows(sources: Record<string, FieldSource>) {
  return Object.entries(sources).map(([field, source]) => ({
    field,
    fieldLabel: fieldLabel(field),
    sectionLabel: sectionLabel(source.section),
    source
  }))
}

function documentRowClassName({ row }: { row: ReportDocument }) {
  return row.id === selectedDocumentId.value ? 'is-selected-document' : ''
}

function formatFileSize(value: number | null | undefined) {
  if (!value) return '--'
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`
  return `${(value / 1024).toFixed(1)} KB`
}

function formatMoney(value: string | number | null | undefined) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '--'
  if (Math.abs(numberValue) >= 100000000) return `¥${(numberValue / 100000000).toFixed(2)}亿`
  if (Math.abs(numberValue) >= 10000) return `¥${(numberValue / 10000).toFixed(2)}万`
  return `¥${numberValue.toLocaleString('zh-CN')}`
}

function formatPercent(value: string | number | null | undefined) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '--'
  return `${numberValue.toFixed(2)}%`
}

function formatPercentFromRatio(value: string | number | null | undefined) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '--'
  return `${(numberValue * 100).toFixed(0)}%`
}

function statusLabel(status: string | null | undefined) {
  const labels: Record<string, string> = {
    uploaded: '已保存',
    parsed: '已解析',
    confirmed: '已入库',
    failed: '失败',
    pending: '等待中'
  }
  return labels[status ?? ''] ?? status ?? '--'
}

function fieldLabel(field: string) {
  const labels: Record<string, string> = {
    revenue: '营业收入',
    operating_cost: '营业成本',
    gross_profit: '毛利',
    net_profit: '归母净利润',
    operating_cash_flow: '经营现金流',
    total_assets: '总资产',
    net_assets: '净资产',
    eps: 'EPS',
    roe: 'ROE',
    selling_expense: '销售费用',
    admin_expense: '管理费用',
    rd_expense: '研发费用',
    finance_expense: '财务费用'
  }
  return labels[field] ?? field
}

function sectionLabel(section: string | null | undefined) {
  const labels: Record<string, string> = {
    income: '利润表',
    balance: '资产负债表',
    cashflow: '现金流量表',
    all: '全文'
  }
  return labels[section ?? ''] ?? section ?? '--'
}

function segmentTypeLabel(type: string) {
  const labels: Record<string, string> = {
    industry: '行业',
    product: '产品',
    region: '地区',
    sales_mode: '模式'
  }
  return labels[type] ?? type
}

onMounted(() => {
  void loadBatches()
  void loadDocuments()
})
</script>

<style scoped>
.report-workbench {
  --ink: #18212f;
  --muted: #718096;
  --line: #dbe4ef;
  --paper: #fffaf2;
  --panel: rgba(255, 255, 255, 0.86);
  --blue: #2356d7;
  --blue-soft: #e7efff;
  --gold: #b98224;
  --red: #d94841;
  --green: #20935b;
  min-height: calc(100vh - 112px);
  padding: 4px;
  color: var(--ink);
}

.hero-panel {
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 28px;
  margin-bottom: 18px;
  padding: 30px;
  border: 1px solid rgba(35, 86, 215, 0.14);
  border-radius: 30px;
  background:
    linear-gradient(135deg, rgba(255, 250, 242, 0.96), rgba(237, 244, 255, 0.96)),
    radial-gradient(circle at 16% 12%, rgba(217, 72, 65, 0.16), transparent 28%),
    radial-gradient(circle at 88% 18%, rgba(35, 86, 215, 0.18), transparent 30%);
  box-shadow: 0 24px 70px rgba(30, 48, 90, 0.12);
}

.hero-panel::after {
  position: absolute;
  right: -42px;
  bottom: -62px;
  width: 240px;
  height: 240px;
  border: 1px solid rgba(35, 86, 215, 0.16);
  border-radius: 50%;
  content: '';
}

.hero-copy,
.hero-steps {
  position: relative;
  z-index: 1;
}

.eyebrow,
.kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--gold);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.11em;
  text-transform: uppercase;
}

.hero-copy h1,
.panel-title h2 {
  margin: 8px 0 10px;
  color: var(--ink);
  font-family: 'Microsoft YaHei UI', 'Noto Serif SC', serif;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.hero-copy h1 {
  font-size: clamp(34px, 5vw, 58px);
  line-height: 1.02;
}

.hero-copy p,
.panel-title p {
  margin: 0;
  color: var(--muted);
  line-height: 1.8;
}

.hero-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-self: end;
}

.step {
  min-height: 118px;
  padding: 18px;
  border: 1px solid rgba(24, 33, 47, 0.09);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.9);
}

.step span {
  display: block;
  margin-bottom: 18px;
  color: rgba(35, 86, 215, 0.38);
  font-size: 26px;
  font-weight: 900;
}

.step strong,
.step small {
  display: block;
}

.step strong {
  margin-bottom: 4px;
  color: var(--ink);
}

.step small {
  color: var(--muted);
}

.step.active {
  color: white;
  background: linear-gradient(145deg, #2356d7, #183b98);
}

.step.active span,
.step.active strong,
.step.active small {
  color: white;
}

.workspace-layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 18px;
}

.left-rail,
.main-stage,
.review-grid {
  display: grid;
  gap: 18px;
}

.review-grid {
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
}

.panel {
  padding: 22px;
  border: 1px solid rgba(24, 33, 47, 0.08);
  border-radius: 26px;
  background: var(--panel);
  box-shadow: 0 18px 60px rgba(30, 48, 90, 0.1);
  backdrop-filter: blur(14px);
}

.panel-title.compact h2 {
  margin-bottom: 0;
  font-size: 24px;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.toolbar-actions,
.preview-tools {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-actions .el-input {
  width: 150px;
}

.upload-panel {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(255, 250, 242, 0.9)),
    repeating-linear-gradient(135deg, rgba(35, 86, 215, 0.05) 0 1px, transparent 1px 12px);
}

.pdf-dropzone {
  margin: 18px 0 14px;
}

.pdf-dropzone :deep(.el-upload-dragger) {
  padding: 28px 18px;
  border: 1.5px dashed rgba(35, 86, 215, 0.38);
  border-radius: 24px;
  background: rgba(231, 239, 255, 0.52);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.pdf-dropzone :deep(.el-upload-dragger:hover) {
  border-color: var(--blue);
  box-shadow: 0 18px 40px rgba(35, 86, 215, 0.16);
  transform: translateY(-2px);
}

.upload-icon {
  display: grid;
  place-items: center;
  width: 72px;
  height: 86px;
  margin: 0 auto 14px;
  border-radius: 12px 12px 20px 20px;
  color: white;
  background: linear-gradient(160deg, var(--red), #f08a5b);
  font-weight: 900;
  letter-spacing: 0.08em;
  box-shadow: 0 16px 30px rgba(217, 72, 65, 0.24);
}

.upload-tip {
  color: var(--muted);
  font-size: 12px;
}

.compact-form,
.manual-form {
  display: grid;
  gap: 12px;
}

.primary-action,
.confirm-action {
  width: 100%;
  margin-top: 14px;
  min-height: 44px;
  font-weight: 800;
}

.manual-form,
.edit-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 16px;
}

.edit-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.manual-form :deep(.el-form-item),
.edit-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.document-table :deep(.el-table__row) {
  cursor: pointer;
}

.document-table :deep(.is-selected-document td) {
  background: #fff4df !important;
}

.doc-cell,
.stacked-cell {
  display: grid;
  gap: 4px;
}

.doc-cell strong,
.stacked-cell strong {
  color: var(--ink);
  font-weight: 800;
}

.doc-cell span,
.stacked-cell span {
  color: var(--muted);
  font-size: 12px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  color: #49606f;
  background: #edf2f7;
  font-size: 12px;
  font-weight: 800;
}

.status-pill.parsed,
.status-pill.uploaded {
  color: #1852bd;
  background: var(--blue-soft);
}

.status-pill.confirmed {
  color: var(--green);
  background: #e9f8ef;
}

.status-pill.failed {
  color: var(--red);
  background: #fff0ee;
}

.notice {
  margin-bottom: 10px;
}

.confidence-ring {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border: 7px solid #dbeafe;
  border-top-color: var(--blue);
  border-radius: 50%;
  color: var(--blue);
  font-size: 13px;
  font-weight: 900;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  min-height: 104px;
  padding: 16px;
  border: 1px solid rgba(24, 33, 47, 0.07);
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
}

.metric-card span,
.preview-meta span,
.section-head span {
  color: var(--muted);
  font-size: 12px;
}

.metric-card strong {
  display: block;
  margin-top: 14px;
  color: var(--ink);
  font-size: 22px;
  line-height: 1.1;
}

.metric-card.emphasis {
  background: linear-gradient(145deg, #1f4fc8, #12327f);
}

.metric-card.profit {
  background: linear-gradient(145deg, #cf443d, #8f2628);
}

.metric-card.emphasis span,
.metric-card.emphasis strong,
.metric-card.profit span,
.metric-card.profit strong {
  color: white;
}

.preview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0;
}

.preview-meta span {
  padding: 7px 10px;
  border-radius: 999px;
  background: #f4f7fb;
}

.edit-panel,
.segment-panel {
  padding: 16px;
  border-radius: 20px;
}

.edit-panel {
  margin-top: 16px;
  background: linear-gradient(180deg, #ffffff, #f2f6ff);
  border: 1px solid rgba(35, 86, 215, 0.1);
}

.segment-panel {
  background: #fbf7ef;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.segment-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.segment-list span {
  display: inline-flex;
  padding: 7px 10px;
  border: 1px solid rgba(185, 130, 36, 0.18);
  border-radius: 999px;
  color: #7a5319;
  background: rgba(255, 255, 255, 0.75);
  font-size: 12px;
}

.source-drawer p {
  margin: 0 0 16px;
  color: var(--muted);
  line-height: 1.8;
}

:deep(.el-drawer__header) {
  margin-bottom: 10px;
  color: var(--ink);
  font-weight: 900;
}

:deep(.el-button--primary) {
  --el-button-bg-color: var(--blue);
  --el-button-border-color: var(--blue);
  --el-button-hover-bg-color: #1745bd;
  --el-button-hover-border-color: #1745bd;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  border-radius: 14px;
  box-shadow: 0 0 0 1px rgba(24, 33, 47, 0.08) inset;
}

:deep(.el-table) {
  border-radius: 18px;
  overflow: hidden;
}

@media (max-width: 1280px) {
  .workspace-layout,
  .review-grid {
    grid-template-columns: 1fr;
  }

  .left-rail {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 900px) {
  .hero-panel,
  .hero-steps,
  .left-rail,
  .metric-grid,
  .manual-form,
  .edit-form {
    grid-template-columns: 1fr;
  }

  .panel-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-actions {
    width: 100%;
  }

  .toolbar-actions .el-input {
    flex: 1;
    width: auto;
  }
}
</style>
