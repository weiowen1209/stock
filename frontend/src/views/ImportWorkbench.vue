<template>
  <section class="import-workbench-debug">
    <header class="import-workbench-debug__hero">
      <div>
        <span class="import-workbench-debug__eyebrow">Research Import Pipeline</span>
        <h1>财报导入研究流水线</h1>
        <p>把 PDF 资产、候选事实、证据链和覆盖风险放在同一个复核台里，先确认高可信事实，再进入正式财务数据。</p>
      </div>
      <div class="import-workbench-debug__steps" aria-label="导入步骤">
        <div class="import-workbench-debug__step import-workbench-debug__step--active">
          <span>01</span>
          <strong>资产入库</strong>
          <small>保存 PDF 与解析批次</small>
        </div>
        <div class="import-workbench-debug__step">
          <span>02</span>
          <strong>事实复核</strong>
          <small>筛出风险与低置信度项</small>
        </div>
        <div class="import-workbench-debug__step">
          <span>03</span>
          <strong>证据确认</strong>
          <small>空值不会覆盖旧值</small>
        </div>
      </div>
    </header>

    <section class="import-workbench-debug__pipeline-layout">
      <aside class="import-workbench-debug__pipeline-rail">
        <article class="import-workbench-debug__upload-shell">
          <div class="import-workbench-debug__section-head">
            <span class="import-workbench-debug__kicker">Intake</span>
            <h2>上传年报 PDF</h2>
            <p>保存文档后自动生成解析预览、候选事实和证据条目。</p>
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
            <span>{{ uploadFile ? '已选择文件，提交后进入候选事实复核。' : '支持补充股票代码、报告期与来源站点。' }}</span>
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

        <article class="import-workbench-debug__library-shell">
          <div class="import-workbench-debug__section-head">
            <span class="import-workbench-debug__kicker">Asset Library</span>
            <h2>文档资产库</h2>
            <p>选择 PDF 后，中间栏会载入对应批次的候选事实队列。</p>
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
              placeholder="搜索代码 / 文件 / 报告期"
            />
          </div>

          <div v-if="documentsLoading" class="import-workbench-debug__table-empty">正在加载文档资产库...</div>
          <div v-else-if="filteredDocuments.length === 0" class="import-workbench-debug__table-empty">当前没有匹配的 PDF 文档记录。</div>
          <div v-else class="import-workbench-debug__document-list" aria-label="文档资产库">
            <button
              v-for="document in filteredDocuments"
              :key="document.id"
              type="button"
              class="import-workbench-debug__document-card"
              :class="{ 'import-workbench-debug__document-card--active': selectedDocumentId === document.id }"
              @click="loadPreview(document.id)"
            >
              <span class="import-workbench-debug__document-meta">{{ document.code || '未识别代码' }} · {{ document.report_period || '未识别报告期' }}</span>
              <strong>{{ document.original_filename }}</strong>
              <span>{{ document.source_site || '来源未记录' }} · {{ formatDateTime(document.updated_at) }}</span>
              <em :class="documentStatusClass(document.status)">{{ formatDocumentStatus(document.status) }}</em>
            </button>
          </div>
        </article>
      </aside>

      <main class="import-workbench-debug__fact-stage">
        <article class="import-workbench-debug__fact-shell">
          <div class="import-workbench-debug__section-head import-workbench-debug__section-head--row">
            <div>
              <span class="import-workbench-debug__kicker">Candidate Facts</span>
              <h2>候选事实复核队列</h2>
              <p>优先处理冲突、低置信度和可能覆盖旧值的事实项。</p>
            </div>
            <button type="button" class="import-workbench-debug__batch-button" @click="showBulkConfirmHint">
              高可信批量确认 · {{ highTrustCandidateCount }}
            </button>
          </div>

          <div class="import-workbench-debug__fact-toolbar">
            <button
              type="button"
              class="import-workbench-debug__toolbar-pill import-workbench-debug__toolbar-pill--button"
              :class="{ 'import-workbench-debug__toolbar-pill--active': factDomainFilter === 'all' }"
              @click="factDomainFilter = 'all'"
            >
              全部类型
            </button>
            <button
              v-for="option in factDomainOptions"
              :key="option"
              type="button"
              class="import-workbench-debug__toolbar-pill import-workbench-debug__toolbar-pill--button"
              :class="{ 'import-workbench-debug__toolbar-pill--active': factDomainFilter === option }"
              @click="factDomainFilter = option"
            >
              {{ formatFactType(option) }}
            </button>
          </div>

          <div v-if="factEvidenceLoading" class="import-workbench-debug__table-empty">正在加载候选事实和证据链...</div>
          <div v-else-if="candidateFacts.length === 0" class="import-workbench-debug__empty-state">
            <strong>当前批次还没有候选事实</strong>
            <span>请先上传 PDF 或从左侧选择已解析文档。若解析批次较旧，可重新解析后再复核事实。</span>
          </div>
          <div v-else-if="filteredCandidateFacts.length === 0" class="import-workbench-debug__empty-state">
            <strong>当前筛选类型没有候选事实</strong>
            <span>切换到“全部类型”查看完整队列。</span>
          </div>
          <div v-else class="import-workbench-debug__fact-list">
            <button
              v-for="fact in filteredCandidateFacts"
              :key="fact.id"
              type="button"
              class="import-workbench-debug__fact-card"
              :class="[
                `import-workbench-debug__fact-card--${factRiskLevel(fact)}`,
                { 'import-workbench-debug__fact-card--active': selectedCandidate?.id === fact.id }
              ]"
              @click="selectedCandidateId = fact.id"
            >
              <div class="import-workbench-debug__fact-main">
                <span class="import-workbench-debug__risk-dot">{{ formatRiskLabel(factRiskLevel(fact)) }}</span>
                <strong>{{ fact.metric_name }}</strong>
                <small>{{ fact.metric_key }} · {{ fact.code }} · {{ fact.period }}</small>
              </div>
              <div class="import-workbench-debug__fact-value">
                <strong>{{ formatFactValue(fact) }}</strong>
                <span>{{ formatFactType(fact.fact_type) }}</span>
              </div>
              <div class="import-workbench-debug__fact-tags">
                <em :class="trustLevelClass(fact.trust_level)">Trust {{ fact.trust_level }}</em>
                <em :class="confidenceClass(fact.confidence)">{{ formatConfidence(fact.confidence) }}</em>
                <em>{{ formatReviewStatus(fact.review_status) }}</em>
                <em v-if="fact.conflict_group" class="import-workbench-debug__tag--danger">冲突</em>
              </div>
            </button>
          </div>

          <div class="import-workbench-debug__review-actions">
            <button type="button" @click="showReviewActionHint('确认')">逐条确认</button>
            <button type="button" @click="showReviewActionHint('修改')">修改事实</button>
            <button type="button" @click="showReviewActionHint('驳回')">驳回候选</button>
          </div>
        </article>

        <article class="import-workbench-debug__preview-shell">
          <div class="import-workbench-debug__section-head">
            <span class="import-workbench-debug__kicker">Structured Preview</span>
            <h2>财务字段核对与确认导入</h2>
            <p>保留现有预览编辑和确认导入能力。确认导入时，空值不会覆盖旧值。</p>
          </div>

          <div v-if="previewLoading" class="import-workbench-debug__table-empty">正在加载解析预览...</div>
          <div v-else-if="!selectedPreview" class="import-workbench-debug__table-empty">请选择一份文档以查看解析预览。</div>
          <template v-else>
            <div class="import-workbench-debug__preview-summary">
              <div v-for="metric in previewMetrics" :key="metric.label" class="import-workbench-debug__metric-shell">
                <small>{{ metric.label }}</small>
                <strong>{{ metric.value }}</strong>
                <span>来自当前解析预览</span>
              </div>
            </div>

            <div class="import-workbench-debug__preview-grid">
              <div class="import-workbench-debug__preview-form-shell">
                <div class="import-workbench-debug__preview-headline">
                  <strong>核心字段编辑</strong>
                  <span>修正值会用于确认导入；留空字段不会覆盖数据库旧值。</span>
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
                  <strong>字段来源摘要</strong>
                  <span>保留原解析字段来源，证据原文请查看右侧面板。</span>
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
      </main>

      <aside class="import-workbench-debug__evidence-panel">
        <article class="import-workbench-debug__evidence-shell">
          <div class="import-workbench-debug__section-head">
            <span class="import-workbench-debug__kicker">Evidence & Coverage</span>
            <h2>证据与覆盖风险</h2>
            <p>复核选中事实的原文片段、页码和覆盖判断。</p>
          </div>

          <div v-if="!selectedCandidate" class="import-workbench-debug__empty-state">
            <strong>尚未选择候选事实</strong>
            <span>从中间队列选择一条事实后，这里会展示证据链和覆盖风险。</span>
          </div>
          <template v-else>
            <div class="import-workbench-debug__selected-fact">
              <span>{{ formatFactType(selectedCandidate.fact_type) }}</span>
              <strong>{{ selectedCandidate.metric_name }}</strong>
              <small>{{ selectedCandidate.metric_key }} · {{ formatFactValue(selectedCandidate) }}</small>
            </div>

            <div class="import-workbench-debug__risk-board">
              <div
                v-for="risk in selectedRiskItems"
                :key="risk.title"
                class="import-workbench-debug__risk-item"
                :class="`import-workbench-debug__risk-item--${risk.level}`"
              >
                <strong>{{ risk.title }}</strong>
                <span>{{ risk.description }}</span>
              </div>
            </div>

            <div class="import-workbench-debug__coverage-rule">
              <strong>覆盖规则</strong>
              <span>空值不会覆盖旧值；只有确认后的非空事实才会参与正式入库或更新。</span>
            </div>

            <div class="import-workbench-debug__evidence-list">
              <div v-if="selectedEvidence.length === 0" class="import-workbench-debug__table-empty">当前事实没有匹配到证据片段。</div>
              <article v-for="evidence in selectedEvidence" :key="evidence.id" class="import-workbench-debug__evidence-card">
                <div class="import-workbench-debug__evidence-meta">
                  <span>{{ formatSourceType(evidence.source_type) }}</span>
                  <span>{{ evidence.page_no ? `第 ${evidence.page_no} 页` : '页码未记录' }}</span>
                  <span>{{ evidence.section_name || 'section 未记录' }}</span>
                </div>
                <p>{{ evidence.snippet }}</p>
                <footer>
                  <span>{{ evidence.source_title || evidence.topic }}</span>
                  <em :class="trustLevelClass(evidence.trust_level)">Trust {{ evidence.trust_level }}</em>
                </footer>
              </article>
            </div>
          </template>
        </article>
      </aside>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type CandidateFact, type ConfirmImportRequest, type EvidenceItem, type ImportPreview, type ReportDocument, type ReportDocumentUploadResult } from '../api'

const uploadFile = ref<File | null>(null)
const uploadInputRef = ref<HTMLInputElement | null>(null)
const uploadSubmitting = ref(false)
const uploadResult = ref<ReportDocumentUploadResult | null>(null)
const documentsLoading = ref(false)
const documentKeyword = ref('')
const documentFilter = ref<'all' | 'recent'>('all')
const documents = ref<ReportDocument[]>([])
const previewLoading = ref(false)
const factEvidenceLoading = ref(false)
const confirmSubmitting = ref(false)
const selectedDocumentId = ref<number | null>(null)
const selectedPreview = ref<ImportPreview | null>(null)
const candidateFacts = ref<CandidateFact[]>([])
const evidenceItems = ref<EvidenceItem[]>([])
const selectedCandidateId = ref<number | null>(null)
const factDomainFilter = ref('all')

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
type RiskLevel = 'stable' | 'watch' | 'danger'

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

const factDomainOptions = computed(() => {
  return Array.from(new Set(candidateFacts.value.map((fact) => fact.fact_type).filter(Boolean)))
})

const evidenceById = computed(() => {
  const map = new Map<number, EvidenceItem>()
  evidenceItems.value.forEach((item) => map.set(item.id, item))
  return map
})

const filteredCandidateFacts = computed(() => {
  if (factDomainFilter.value === 'all') return candidateFacts.value
  return candidateFacts.value.filter((fact) => fact.fact_type === factDomainFilter.value)
})

const selectedCandidate = computed(() => {
  const selected = candidateFacts.value.find((fact) => fact.id === selectedCandidateId.value)
  return selected ?? filteredCandidateFacts.value[0] ?? null
})

const selectedEvidence = computed(() => {
  const fact = selectedCandidate.value
  if (!fact) return []
  const evidenceIds = getEvidenceIds(fact)
  const directMatches = evidenceIds.map((id) => evidenceById.value.get(id)).filter((item): item is EvidenceItem => Boolean(item))
  if (directMatches.length > 0) return directMatches
  return evidenceItems.value.filter((item) => item.topic === fact.metric_key || item.topic === fact.metric_name)
})

const selectedRiskItems = computed(() => {
  const fact = selectedCandidate.value
  if (!fact) return []
  const items: Array<{ title: string; description: string; level: RiskLevel }> = []
  if (fact.conflict_group) {
    items.push({ title: '冲突项', description: `命中冲突组 ${fact.conflict_group}，需要人工比对证据。`, level: 'danger' })
  }
  if (isLowConfidence(fact)) {
    items.push({ title: '低置信度', description: `当前置信度 ${formatConfidence(fact.confidence)}，不应进入批量确认。`, level: 'danger' })
  }
  if (fact.existing_fact_id) {
    items.push({ title: '覆盖风险', description: `检测到既有事实 #${fact.existing_fact_id}，确认后会按非空值更新。`, level: 'watch' })
  }
  if (fact.metric_value === null || fact.metric_value === '') {
    items.push({ title: '空值保护', description: '该事实当前为空值，确认导入也不会覆盖数据库旧值。', level: 'watch' })
  }
  if (items.length === 0) {
    items.push({ title: '覆盖风险较低', description: '未发现冲突、低置信度或空值覆盖风险。', level: 'stable' })
  }
  return items
})

const highTrustCandidateCount = computed(() => candidateFacts.value.filter((fact) => isHighTrustFact(fact)).length)

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
    await Promise.all([loadDocuments(), loadFactEvidence(preview.batch.id)])
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

watch(
  filteredCandidateFacts,
  (facts) => {
    if (!facts.some((fact) => fact.id === selectedCandidateId.value)) {
      selectedCandidateId.value = facts[0]?.id ?? null
    }
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

function formatFactValue(fact: CandidateFact) {
  const value = fact.metric_value === null || fact.metric_value === '' ? '空值' : String(fact.metric_value)
  return fact.metric_unit ? `${value} ${fact.metric_unit}` : value
}

function formatFactType(type: string) {
  const labels: Record<string, string> = {
    financial: '财务指标',
    segment: '业务分部',
    expense: '费用明细',
    extraction: '年报扩展',
    manual: '人工补录'
  }
  return labels[type] ?? type
}

function formatReviewStatus(status: string) {
  const labels: Record<string, string> = {
    pending: '待复核',
    confirmed: '已确认',
    rejected: '已驳回',
    modified: '已修改'
  }
  return labels[status] ?? status
}

function formatSourceType(type: string) {
  const labels: Record<string, string> = {
    annual_report: '年报原文',
    manual_note: '人工备注',
    external: '外部来源'
  }
  return labels[type] ?? type
}

function formatConfidence(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '置信度 -'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return `置信度 ${value}`
  return `置信度 ${numeric.toFixed(0)}%`
}

function factRiskLevel(fact: CandidateFact): RiskLevel {
  if (fact.conflict_group || fact.review_status === 'rejected' || fact.metric_value === null || fact.metric_value === '') return 'danger'
  if (isLowConfidence(fact) || fact.existing_fact_id) return 'watch'
  return 'stable'
}

function formatRiskLabel(level: RiskLevel) {
  if (level === 'danger') return '高风险'
  if (level === 'watch') return '关注'
  return '可信'
}

function isLowConfidence(fact: CandidateFact) {
  const confidence = Number(fact.confidence)
  return fact.trust_level !== 'A' || Number.isNaN(confidence) || confidence < 80
}

function isHighTrustFact(fact: CandidateFact) {
  return fact.review_status === 'pending' && fact.trust_level === 'A' && !fact.conflict_group && Number(fact.confidence) >= 80 && fact.metric_value !== null && fact.metric_value !== ''
}

function trustLevelClass(level: string) {
  if (level === 'A') return 'import-workbench-debug__tag import-workbench-debug__tag--success'
  if (level === 'B') return 'import-workbench-debug__tag import-workbench-debug__tag--warning'
  return 'import-workbench-debug__tag import-workbench-debug__tag--danger'
}

function confidenceClass(value: string | number | null | undefined) {
  const numeric = Number(value)
  if (Number.isNaN(numeric) || numeric < 70) return 'import-workbench-debug__tag import-workbench-debug__tag--danger'
  if (numeric < 85) return 'import-workbench-debug__tag import-workbench-debug__tag--warning'
  return 'import-workbench-debug__tag import-workbench-debug__tag--success'
}

function showReviewActionHint(action: string) {
  ElMessage.info(`${action}接口完成后接入`)
}

function showBulkConfirmHint() {
  ElMessage.info('高可信事实批量确认会在逐条复核接口完成后接入')
}

function getEvidenceIds(fact: CandidateFact) {
  const ids = new Set<number>()
  if (fact.evidence_id) ids.add(fact.evidence_id)
  if (fact.evidence_ids_json) {
    try {
      const parsed = JSON.parse(fact.evidence_ids_json)
      if (Array.isArray(parsed)) {
        parsed.forEach((item) => {
          const id = Number(item)
          if (!Number.isNaN(id)) ids.add(id)
        })
      }
    } catch {
      fact.evidence_ids_json
        .split(',')
        .map((item) => Number(item.trim()))
        .filter((item) => !Number.isNaN(item))
        .forEach((item) => ids.add(item))
    }
  }
  return Array.from(ids)
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

async function loadFactEvidence(batchId: number) {
  factEvidenceLoading.value = true
  try {
    const [factsResponse, evidenceResponse] = await Promise.all([
      api.getCandidateFacts({ batch_id: batchId }),
      api.getEvidenceItems({ batch_id: batchId })
    ])
    candidateFacts.value = factsResponse.data ?? []
    evidenceItems.value = evidenceResponse.data ?? []
    selectedCandidateId.value = candidateFacts.value[0]?.id ?? null
  } catch (error) {
    candidateFacts.value = selectedPreview.value?.candidate_facts ?? []
    evidenceItems.value = []
    selectedCandidateId.value = candidateFacts.value[0]?.id ?? null
    const message = error instanceof Error ? error.message : '候选事实和证据加载失败'
    ElMessage.error(message)
  } finally {
    factEvidenceLoading.value = false
  }
}

async function loadPreview(documentId: number) {
  selectedDocumentId.value = documentId
  previewLoading.value = true
  try {
    const response = await api.getReportDocumentPreview(documentId)
    selectedPreview.value = response.data
    if (response.data?.batch.id) {
      await loadFactEvidence(response.data.batch.id)
    }
  } catch (error) {
    selectedPreview.value = null
    candidateFacts.value = []
    evidenceItems.value = []
    selectedCandidateId.value = null
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
    await Promise.all([loadDocuments(), loadFactEvidence(response.data.preview.batch.id)])
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
  color: #18212f;
  background:
    radial-gradient(circle at top left, rgba(242, 183, 73, 0.16), transparent 32rem),
    linear-gradient(180deg, #f7f4ed 0%, #eef5fb 46%, #f8fafc 100%);
}

.import-workbench-debug__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 20px;
  margin-bottom: 20px;
  padding: 24px;
  border: 1px solid rgba(36, 86, 145, 0.14);
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(255, 250, 242, 0.96), rgba(228, 239, 249, 0.96));
  box-shadow: 0 24px 60px rgba(15, 38, 72, 0.08);
}

.import-workbench-debug__eyebrow,
.import-workbench-debug__kicker {
  display: inline-flex;
  color: #b98224;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.import-workbench-debug__hero h1 {
  margin: 0 0 10px;
  color: #18212f;
  font-size: clamp(30px, 4vw, 46px);
  line-height: 1.08;
}

.import-workbench-debug__hero p,
.import-workbench-debug__section-head p {
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
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
}

.import-workbench-debug__step span,
.import-workbench-debug__step strong,
.import-workbench-debug__step small {
  display: block;
}

.import-workbench-debug__step span {
  margin-bottom: 16px;
  color: rgba(36, 86, 145, 0.38);
  font-size: 24px;
  font-weight: 900;
}

.import-workbench-debug__step strong {
  margin-bottom: 4px;
}

.import-workbench-debug__step small {
  color: #5b6b7f;
}

.import-workbench-debug__step--active {
  color: #ffffff;
  background: linear-gradient(145deg, #184f8f, #12315d);
}

.import-workbench-debug__step--active span,
.import-workbench-debug__step--active small {
  color: rgba(255, 255, 255, 0.82);
}

.import-workbench-debug__pipeline-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.82fr) minmax(420px, 1.45fr) minmax(300px, 0.9fr);
  gap: 20px;
  align-items: start;
}

.import-workbench-debug__pipeline-rail,
.import-workbench-debug__fact-stage,
.import-workbench-debug__evidence-panel {
  display: grid;
  gap: 20px;
}

.import-workbench-debug__upload-shell,
.import-workbench-debug__library-shell,
.import-workbench-debug__fact-shell,
.import-workbench-debug__preview-shell,
.import-workbench-debug__evidence-shell {
  padding: 22px;
  border: 1px solid rgba(78, 98, 125, 0.16);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 44px rgba(35, 62, 92, 0.08);
}

.import-workbench-debug__section-head h2 {
  margin: 8px 0 10px;
  color: #18212f;
  font-size: 24px;
}

.import-workbench-debug__section-head--row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
}

.import-workbench-debug__file-input {
  display: none;
}

.import-workbench-debug__dropzone {
  width: 100%;
  margin: 18px 0 16px;
  padding: 24px 18px;
  border: 1.5px dashed rgba(24, 79, 143, 0.34);
  border-radius: 22px;
  background: rgba(229, 241, 252, 0.7);
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
}

.import-workbench-debug__dropzone span,
.import-workbench-debug__upload-result span,
.import-workbench-debug__document-card span,
.import-workbench-debug__empty-state span {
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
  background: linear-gradient(160deg, #c84f3d, #e5a142);
  font-weight: 900;
  letter-spacing: 0.08em;
}

.import-workbench-debug__field-list,
.import-workbench-debug__preview-fields,
.import-workbench-debug__source-list,
.import-workbench-debug__document-list,
.import-workbench-debug__fact-list,
.import-workbench-debug__evidence-list,
.import-workbench-debug__risk-board {
  display: grid;
  gap: 10px;
}

.import-workbench-debug__field {
  min-height: 44px;
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  color: #334155;
  background: rgba(255, 255, 255, 0.94);
}

.import-workbench-debug__field--input {
  width: 100%;
  font: inherit;
  outline: none;
}

.import-workbench-debug__field--input::placeholder {
  color: #94a3b8;
}

.import-workbench-debug__button-shell,
.import-workbench-debug__batch-button {
  margin-top: 16px;
  padding: 13px 16px;
  border: none;
  border-radius: 14px;
  color: #ffffff;
  background: linear-gradient(145deg, #184f8f, #12315d);
  text-align: center;
  font: inherit;
  font-weight: 800;
}

.import-workbench-debug__button-shell--button {
  width: 100%;
  cursor: pointer;
}

.import-workbench-debug__button-shell--button:disabled {
  opacity: 0.7;
  cursor: wait;
}

.import-workbench-debug__batch-button {
  flex: 0 0 auto;
  margin-top: 0;
  background: linear-gradient(145deg, #c68428, #8a5a16);
  cursor: pointer;
}

.import-workbench-debug__upload-result,
.import-workbench-debug__empty-state,
.import-workbench-debug__coverage-rule {
  display: grid;
  gap: 6px;
  margin-top: 16px;
  padding: 16px 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.96);
}

.import-workbench-debug__library-toolbar,
.import-workbench-debug__fact-toolbar,
.import-workbench-debug__button-row,
.import-workbench-debug__review-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 18px 0 14px;
}

.import-workbench-debug__toolbar-pill,
.import-workbench-debug__toolbar-search {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  padding: 0 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  color: #53657a;
  background: rgba(255, 255, 255, 0.94);
}

.import-workbench-debug__toolbar-pill--button {
  cursor: pointer;
}

.import-workbench-debug__toolbar-pill--active {
  color: #ffffff;
  border-color: transparent;
  background: linear-gradient(145deg, #184f8f, #12315d);
}

.import-workbench-debug__toolbar-search {
  width: 100%;
  color: #334155;
}

.import-workbench-debug__toolbar-search--input {
  font: inherit;
  outline: none;
}

.import-workbench-debug__document-card,
.import-workbench-debug__fact-card {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.import-workbench-debug__document-card {
  display: grid;
  gap: 6px;
  padding: 14px;
}

.import-workbench-debug__document-card--active {
  border-color: rgba(24, 79, 143, 0.42);
  background: rgba(229, 241, 252, 0.92);
}

.import-workbench-debug__document-card strong {
  line-height: 1.45;
}

.import-workbench-debug__document-meta {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.import-workbench-debug__status-chip,
.import-workbench-debug__tag,
.import-workbench-debug__fact-tags em {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-width: 64px;
  padding: 6px 10px;
  border-radius: 999px;
  color: #9a6700;
  background: rgba(255, 244, 214, 0.95);
  font-style: normal;
  font-size: 12px;
  font-weight: 800;
}

.import-workbench-debug__status-chip--success,
.import-workbench-debug__tag--success {
  color: #0f766e;
  background: rgba(204, 251, 241, 0.95);
}

.import-workbench-debug__status-chip--warning,
.import-workbench-debug__tag--warning {
  color: #1d4ed8;
  background: rgba(219, 234, 254, 0.95);
}

.import-workbench-debug__status-chip--danger,
.import-workbench-debug__tag--danger {
  color: #b42318;
  background: rgba(254, 226, 226, 0.95);
}

.import-workbench-debug__table-empty {
  padding: 18px;
  border: 1px dashed rgba(148, 163, 184, 0.32);
  border-radius: 16px;
  color: #6b7a8c;
  background: rgba(255, 255, 255, 0.9);
}

.import-workbench-debug__fact-card {
  display: grid;
  grid-template-columns: minmax(180px, 1.2fr) minmax(130px, 0.7fr) minmax(180px, 1fr);
  gap: 12px;
  align-items: center;
  padding: 16px;
}

.import-workbench-debug__fact-card--active {
  outline: 2px solid rgba(24, 79, 143, 0.32);
}

.import-workbench-debug__fact-card--stable {
  border-left: 5px solid #0f766e;
}

.import-workbench-debug__fact-card--watch {
  border-left: 5px solid #c68428;
}

.import-workbench-debug__fact-card--danger {
  border-left: 5px solid #c84f3d;
  background: rgba(255, 247, 242, 0.96);
}

.import-workbench-debug__fact-main,
.import-workbench-debug__fact-value {
  display: grid;
  gap: 4px;
}

.import-workbench-debug__fact-main small,
.import-workbench-debug__fact-value span,
.import-workbench-debug__selected-fact small,
.import-workbench-debug__preview-headline span,
.import-workbench-debug__source-item span,
.import-workbench-debug__risk-item span {
  color: #64748b;
  line-height: 1.6;
}

.import-workbench-debug__risk-dot {
  width: fit-content;
  padding: 4px 8px;
  border-radius: 999px;
  color: #ffffff;
  background: #12315d;
  font-size: 12px;
  font-weight: 800;
}

.import-workbench-debug__fact-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.import-workbench-debug__review-actions button {
  flex: 1 1 120px;
  min-height: 42px;
  border: 1px solid rgba(24, 79, 143, 0.18);
  border-radius: 999px;
  color: #184f8f;
  background: rgba(229, 241, 252, 0.72);
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.import-workbench-debug__preview-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0 16px;
}

.import-workbench-debug__metric-shell,
.import-workbench-debug__preview-form-shell,
.import-workbench-debug__preview-notes-shell,
.import-workbench-debug__source-item,
.import-workbench-debug__evidence-card,
.import-workbench-debug__selected-fact,
.import-workbench-debug__risk-item {
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
}

.import-workbench-debug__metric-shell small,
.import-workbench-debug__metric-shell strong,
.import-workbench-debug__metric-shell span,
.import-workbench-debug__preview-headline strong,
.import-workbench-debug__preview-headline span,
.import-workbench-debug__source-item strong,
.import-workbench-debug__source-item span,
.import-workbench-debug__selected-fact span,
.import-workbench-debug__selected-fact strong,
.import-workbench-debug__selected-fact small {
  display: block;
}

.import-workbench-debug__metric-shell small,
.import-workbench-debug__selected-fact span {
  margin-bottom: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.import-workbench-debug__metric-shell strong {
  margin-bottom: 6px;
  font-size: 22px;
}

.import-workbench-debug__preview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(240px, 0.8fr);
  gap: 16px;
}

.import-workbench-debug__preview-headline {
  margin-bottom: 14px;
}

.import-workbench-debug__edit-field {
  display: grid;
  gap: 6px;
}

.import-workbench-debug__edit-label {
  color: #475569;
  font-size: 13px;
  font-weight: 800;
}

.import-workbench-debug__edit-hint {
  color: #94a3b8;
  line-height: 1.5;
}

.import-workbench-debug__button-row .import-workbench-debug__button-shell {
  flex: 1 1 180px;
  margin-top: 0;
}

.import-workbench-debug__button-shell--ghost {
  color: #184f8f;
  background: rgba(219, 234, 254, 0.78);
}

.import-workbench-debug__coverage-rule {
  border-color: rgba(198, 132, 40, 0.28);
  background: rgba(255, 248, 235, 0.94);
}

.import-workbench-debug__risk-item--stable {
  border-color: rgba(15, 118, 110, 0.24);
  background: rgba(240, 253, 250, 0.92);
}

.import-workbench-debug__risk-item--watch {
  border-color: rgba(198, 132, 40, 0.28);
  background: rgba(255, 248, 235, 0.94);
}

.import-workbench-debug__risk-item--danger {
  border-color: rgba(200, 79, 61, 0.3);
  background: rgba(255, 241, 242, 0.94);
}

.import-workbench-debug__evidence-card {
  display: grid;
  gap: 12px;
}

.import-workbench-debug__evidence-card p {
  margin: 0;
  color: #334155;
  line-height: 1.8;
}

.import-workbench-debug__evidence-card footer,
.import-workbench-debug__evidence-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.import-workbench-debug__evidence-meta span {
  padding: 5px 9px;
  border-radius: 999px;
  color: #53657a;
  background: rgba(241, 245, 249, 0.95);
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 1280px) {
  .import-workbench-debug__pipeline-layout {
    grid-template-columns: minmax(260px, 0.78fr) minmax(0, 1.4fr);
  }

  .import-workbench-debug__evidence-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 960px) {
  .import-workbench-debug__hero,
  .import-workbench-debug__steps,
  .import-workbench-debug__pipeline-layout,
  .import-workbench-debug__fact-card,
  .import-workbench-debug__preview-summary,
  .import-workbench-debug__preview-grid {
    grid-template-columns: 1fr;
  }

  .import-workbench-debug__evidence-panel {
    grid-column: auto;
  }

  .import-workbench-debug__fact-tags {
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .import-workbench-debug {
    padding: 14px;
  }

  .import-workbench-debug__hero,
  .import-workbench-debug__upload-shell,
  .import-workbench-debug__library-shell,
  .import-workbench-debug__fact-shell,
  .import-workbench-debug__preview-shell,
  .import-workbench-debug__evidence-shell {
    padding: 18px;
    border-radius: 20px;
  }

  .import-workbench-debug__section-head--row {
    display: grid;
  }

  .import-workbench-debug__library-toolbar,
  .import-workbench-debug__fact-toolbar {
    flex-direction: column;
  }
}
</style>
