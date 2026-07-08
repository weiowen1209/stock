<template>
  <section class="base-data-grid">
    <div class="panel template-panel">
      <p>基础资料模板</p>
      <h2>Excel与手工维护人形机器人股票池</h2>
      <div class="template-columns">
        <span>一级分类</span>
        <span>二级分类</span>
        <span>三级分类</span>
        <span>股票名称</span>
        <span>股票代码</span>
      </div>
      <small>股票代码列示例：002472、000837、00700.HK、HK09988、AAPL、US.TSLA；Excel数字格式会自动补齐前导0。</small>
    </div>

    <div class="panel upload-panel">
      <div class="panel-head">
        <div>
          <p>股票池维护</p>
          <h3>{{ inputModeTitle }}</h3>
        </div>
        <el-button v-if="activeInputMode === 'excel'" type="primary" plain :loading="loading" @click="downloadTemplate">模板下载</el-button>
        <el-tag v-else type="success">
          {{ activeInputMode === 'manual' ? '新增/更新' : '分类字典' }}
        </el-tag>
      </div>
      <el-segmented v-model="activeInputMode" :options="inputModeOptions" class="input-mode-tabs" />
      <div v-if="activeInputMode === 'excel'" class="input-pane">
        <el-upload :auto-upload="false" :limit="1" accept=".xlsx" :on-change="handleFileChange" :on-remove="handleFileRemove">
          <el-button type="primary">选择Excel文件</el-button>
        </el-upload>
        <div class="actions-row">
          <el-button type="danger" :loading="loading" @click="importExcel('replace')">覆盖导入基础资料</el-button>
          <el-button type="success" :loading="loading" @click="importExcel('append')">增量导入基础资料</el-button>
        </div>
      </div>
      <div v-else-if="activeInputMode === 'manual'" class="input-pane">
        <el-form :model="manualForm" label-position="top" class="manual-form">
          <el-form-item label="一级分类">
            <el-select v-model="manualForm.industry_chain" filterable placeholder="搜索并选择一级分类" @change="handleLevel1Change">
              <el-option v-for="item in level1Options" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="二级分类">
            <el-select v-model="manualForm.industry_chain_detail_level2" filterable placeholder="搜索并选择二级分类" @change="handleLevel2Change">
              <el-option v-for="item in level2Options" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="三级分类">
            <el-select v-model="manualForm.industry_chain_detail_level3" filterable placeholder="搜索并选择三级分类">
              <el-option v-for="item in level3Options" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="股票名称">
            <el-input v-model="manualForm.name" placeholder="如：拓普集团" />
          </el-form-item>
          <el-form-item label="股票代码">
            <el-input v-model="manualForm.code" placeholder="如：601689、00700.HK、AAPL" />
          </el-form-item>
        </el-form>
        <div class="actions-row manual-actions">
          <el-button type="primary" :loading="loading" @click="saveManualStock">{{ editingStockCode ? '保存修改' : '保存股票' }}</el-button>
          <el-button v-if="editingStockCode" @click="resetManualForm">取消编辑</el-button>
        </div>
      </div>
      <div v-else class="input-pane category-pane">
        <el-form :model="categoryForm" label-position="top" class="manual-form">
          <el-form-item label="一级分类">
            <el-input v-model="categoryForm.industry_chain" placeholder="如：人形机器人" />
          </el-form-item>
          <el-form-item label="二级分类">
            <el-input v-model="categoryForm.level2" placeholder="如：执行系统" />
          </el-form-item>
          <el-form-item label="三级分类">
            <el-input v-model="categoryForm.level3" placeholder="如：丝杠/线性执行器" />
          </el-form-item>
          <el-form-item label="操作">
            <div class="actions-row category-actions">
              <el-button type="primary" :loading="loading" @click="saveCategory">{{ editingCategoryId ? '保存修改' : '新增分类' }}</el-button>
              <el-button v-if="editingCategoryId" @click="resetCategoryForm">取消编辑</el-button>
            </div>
          </el-form-item>
        </el-form>
        <el-table :data="categories" height="220" class="category-table">
          <el-table-column prop="industry_chain" label="一级分类" min-width="120" />
          <el-table-column prop="level2" label="二级分类" min-width="120" />
          <el-table-column prop="level3" label="三级分类" min-width="140" />
          <el-table-column label="操作" width="138" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="editCategory(row)">修改</el-button>
              <el-button link type="danger" @click="removeCategory(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div v-if="importResult" class="panel result-panel">
      <p>最近导入结果</p>
      <div class="result-grid">
        <MetricCard label="读取行数" :value="importResult.row_count" hint="Excel有效数据行" />
        <MetricCard label="新增" :value="importResult.inserted_count" hint="新股票" />
        <MetricCard label="更新" :value="importResult.updated_count" hint="已有股票" />
        <MetricCard label="停用" :value="importResult.disabled_count" hint="覆盖导入时Excel外旧股票" />
        <MetricCard label="跳过" :value="importResult.skipped_count" hint="非A股/港股/美股或无法解析" />
        <MetricCard label="启用股票" :value="importResult.active_count" hint="当前同步范围" />
      </div>
      <el-alert v-if="showImportSkippedAlert && importResult.skipped_examples.length" type="warning" closable show-icon @close="hideImportSkippedAlert">
        <template #title>
          跳过示例：{{ importResult.skipped_examples.map((item) => `${item.item}：${item.reason}`).join('；') }}
        </template>
      </el-alert>
    </div>

    <div class="panel table-panel">
      <div class="panel-head">
        <div>
          <p>当前基础股票池</p>
          <h3>启用股票 {{ stocks.length }} 只，当前显示 {{ filteredStocks.length }} 只</h3>
        </div>
        <div class="actions-row table-actions">
          <el-dropdown :disabled="!hasSelectedStocks || syncing" @command="handleBatchSyncCommand">
            <el-button type="success" plain :disabled="!hasSelectedStocks || syncing">
              同步选中范围 {{ selectedSyncCodes.length ? `(${selectedSyncCodes.length})` : '' }}
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="incremental">按增量模式同步选中范围</el-dropdown-item>
                <el-dropdown-item command="full">按全量模式同步选中范围</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button :disabled="!hasStockFilters" @click="resetStockFilters">清空筛选</el-button>
          <el-button :loading="loading" @click="loadStocks">刷新</el-button>
        </div>
      </div>
      <div class="stock-filter-grid">
        <el-input v-model="stockFilters.code" size="small" clearable placeholder="搜代码">
          <template #prepend>代码</template>
        </el-input>
        <el-input v-model="stockFilters.name" size="small" clearable placeholder="搜名称">
          <template #prepend>名称</template>
        </el-input>
        <el-input v-model="stockFilters.exchange" size="small" clearable placeholder="搜市场">
          <template #prepend>交易所</template>
        </el-input>
        <el-input v-model="stockFilters.industry_chain" size="small" clearable placeholder="搜一级">
          <template #prepend>一级分类</template>
        </el-input>
        <el-input v-model="stockFilters.industry_chain_detail" size="small" clearable placeholder="搜分类">
          <template #prepend>二级/三级</template>
        </el-input>
        <el-input v-model="stockFilters.core_products" size="small" clearable placeholder="搜产品">
          <template #prepend>核心产品</template>
        </el-input>
      </div>
      <el-table :data="filteredStocks" height="520" class="base-table" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="52" fixed="left" />
        <el-table-column prop="code" label="代码" width="120" />
        <el-table-column prop="name" label="名称" width="130" />
        <el-table-column prop="exchange" label="交易所" width="112" />
        <el-table-column prop="industry_chain" label="一级分类" min-width="170" />
        <el-table-column prop="industry_chain_detail" label="二级/三级分类" min-width="230" />
        <el-table-column prop="core_products" label="核心产品" min-width="170" />
        <el-table-column label="操作" width="138" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="editStock(row)">修改</el-button>
            <el-button link type="danger" @click="removeStock(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import { api, type BaseDataImportResult, type BaseDataStockUpsert, type Stock, type StockCategory } from '../api'
import MetricCard from '../components/MetricCard.vue'
import { useStockStore } from '../stores/stockStore'

const props = defineProps<{
  syncing: boolean
}>()

const emit = defineEmits<{
  'sync-stock': [codes: string[], forceFull: boolean]
}>()

const store = useStockStore()
const stocks = ref<Stock[]>([])
const categories = ref<StockCategory[]>([])
const selectedFile = ref<File | null>(null)
const importResult = ref<BaseDataImportResult | null>(null)
const showImportSkippedAlert = ref(false)
let importSkippedAlertTimer: ReturnType<typeof window.setTimeout> | null = null
const loading = ref(false)
const selectedSyncCodes = ref<string[]>([])
const activeInputMode = ref<'excel' | 'manual' | 'category'>('excel')
const inputModeOptions = [
  { label: 'Excel导入', value: 'excel' },
  { label: '手工添加', value: 'manual' },
  { label: '分类维护', value: 'category' }
]
const manualForm = reactive<BaseDataStockUpsert>({
  industry_chain: '',
  industry_chain_detail_level2: '',
  industry_chain_detail_level3: '',
  name: '',
  code: ''
})
const editingStockCode = ref<string | null>(null)
const categoryForm = reactive({
  industry_chain: '',
  level2: '',
  level3: ''
})
const editingCategoryId = ref<number | null>(null)
const stockFilterKeys = ['code', 'name', 'exchange', 'industry_chain', 'industry_chain_detail', 'core_products'] as const
const stockFilters = reactive<Record<(typeof stockFilterKeys)[number], string>>({
  code: '',
  name: '',
  exchange: '',
  industry_chain: '',
  industry_chain_detail: '',
  core_products: ''
})
const uniqueValues = (items: Array<string | null | undefined>) => [...new Set(items.filter((item): item is string => Boolean(item)))]
const inputModeTitle = computed(() => {
  if (activeInputMode.value === 'excel') return '覆盖或增量导入基础资料'
  if (activeInputMode.value === 'manual') return editingStockCode.value ? '修改单只股票' : '保存单只股票'
  return '新增、修改和删除分类'
})
const hasStockFilters = computed(() => stockFilterKeys.some((key) => stockFilters[key].trim()))
const filteredStocks = computed(() =>
  stocks.value.filter((stock) =>
    stockFilterKeys.every((key) => {
      const keyword = stockFilters[key].trim().toLowerCase()
      if (!keyword) return true
      return String(stock[key] ?? '').toLowerCase().includes(keyword)
    })
  )
)
const level1Options = computed(() => uniqueValues(categories.value.map((category) => category.industry_chain)))
const level2Options = computed(() =>
  uniqueValues(
    categories.value
      .filter((category) => category.industry_chain === manualForm.industry_chain)
      .map((category) => category.level2)
  )
)
const level3Options = computed(() =>
  uniqueValues(
    categories.value
      .filter(
        (category) =>
          category.industry_chain === manualForm.industry_chain && category.level2 === manualForm.industry_chain_detail_level2
      )
      .map((category) => category.level3)
  )
)
const hasSelectedStocks = computed(() => selectedSyncCodes.value.length > 0)
onMounted(async () => {
  await loadStocks()
  await loadCategories()
})

function handleFileChange(file: UploadFile) {
  selectedFile.value = file.raw ?? null
  if (selectedFile.value) {
    ElMessage.success('Excel文件已选择')
  }
}

function handleFileRemove() {
  selectedFile.value = null
}

function handleLevel1Change() {
  manualForm.industry_chain_detail_level2 = ''
  manualForm.industry_chain_detail_level3 = ''
}

function handleLevel2Change() {
  manualForm.industry_chain_detail_level3 = ''
}

function resetStockFilters() {
  stockFilterKeys.forEach((key) => {
    stockFilters[key] = ''
  })
}

function handleSelectionChange(rows: Stock[]) {
  selectedSyncCodes.value = rows.map((row) => row.code)
}

function handleBatchSyncCommand(command: string) {
  if (props.syncing || !selectedSyncCodes.value.length) return
  emit('sync-stock', [...selectedSyncCodes.value], command === 'full')
}

function hideImportSkippedAlert() {
  showImportSkippedAlert.value = false
  if (importSkippedAlertTimer) {
    window.clearTimeout(importSkippedAlertTimer)
    importSkippedAlertTimer = null
  }
}

function showTemporarySkippedAlert() {
  hideImportSkippedAlert()
  if (!importResult.value?.skipped_examples.length) return
  showImportSkippedAlert.value = true
  importSkippedAlertTimer = window.setTimeout(() => {
    showImportSkippedAlert.value = false
    importSkippedAlertTimer = null
  }, 8000)
}

async function refreshAfterChange() {
  await loadStocks()
  await loadCategories()
  await store.loadInitialData()
}

async function loadStocks() {
  loading.value = true
  try {
    const response = await api.getBaseDataStocks()
    stocks.value = response.data ?? []
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '基础股票池加载失败')
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    const response = await api.getStockCategories()
    categories.value = response.data ?? []
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '分类加载失败')
  }
}

async function downloadTemplate() {
  loading.value = true
  try {
    const blob = await api.downloadBaseDataTemplate()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '股票池导入模板.xlsx'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    ElMessage.success('模板下载已开始')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '模板下载失败')
  } finally {
    loading.value = false
  }
}

async function importExcel(mode: 'replace' | 'append') {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择Excel文件')
    return
  }
  loading.value = true
  try {
    const response = await api.importBaseDataExcel(selectedFile.value, mode)
    importResult.value = response.data
    showTemporarySkippedAlert()
    ElMessage.success(mode === 'replace' ? '覆盖导入完成' : '增量导入完成')
    await refreshAfterChange()
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '基础资料导入失败')
  } finally {
    loading.value = false
  }
}

async function saveManualStock() {
  loading.value = true
  try {
    await api.upsertBaseDataStock(manualForm)
    ElMessage.success(editingStockCode.value ? '股票修改完成' : '股票保存完成')
    resetManualForm()
    await refreshAfterChange()
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '股票保存失败')
  } finally {
    loading.value = false
  }
}

function editStock(row: Stock) {
  const [level2 = '', level3 = ''] = (row.industry_chain_detail ?? '').split('/').map((item) => item.trim())
  editingStockCode.value = row.code
  activeInputMode.value = 'manual'
  manualForm.industry_chain = row.industry_chain
  manualForm.industry_chain_detail_level2 = level2
  manualForm.industry_chain_detail_level3 = level3
  manualForm.name = row.name
  manualForm.code = row.code
}

async function removeStock(row: Stock) {
  try {
    await ElMessageBox.confirm(`确认从股票池删除「${row.name}（${row.code}）」？`, '删除股票', {
      type: 'warning'
    })
    loading.value = true
    await api.deleteBaseDataStock(row.code)
    ElMessage.success('股票删除完成')
    if (editingStockCode.value === row.code) resetManualForm()
    await refreshAfterChange()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err instanceof Error ? err.message : '股票删除失败')
    }
  } finally {
    loading.value = false
  }
}

function resetManualForm() {
  editingStockCode.value = null
  manualForm.industry_chain = ''
  manualForm.industry_chain_detail_level2 = ''
  manualForm.industry_chain_detail_level3 = ''
  manualForm.name = ''
  manualForm.code = ''
}

async function saveCategory() {
  loading.value = true
  try {
    if (editingCategoryId.value) {
      await api.updateStockCategory(editingCategoryId.value, categoryForm)
      ElMessage.success('分类修改完成')
    } else {
      await api.createStockCategory(categoryForm)
      ElMessage.success('分类新增完成')
    }
    resetCategoryForm()
    await refreshAfterChange()
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '分类保存失败')
  } finally {
    loading.value = false
  }
}

function editCategory(row: StockCategory) {
  editingCategoryId.value = row.id
  categoryForm.industry_chain = row.industry_chain
  categoryForm.level2 = row.level2
  categoryForm.level3 = row.level3
}

async function removeCategory(row: StockCategory) {
  try {
    await ElMessageBox.confirm(`确认删除分类「${row.industry_chain} / ${row.level2} / ${row.level3}」？`, '删除分类', {
      type: 'warning'
    })
    loading.value = true
    await api.deleteStockCategory(row.id)
    ElMessage.success('分类删除完成')
    await refreshAfterChange()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err instanceof Error ? err.message : '分类删除失败')
    }
  } finally {
    loading.value = false
  }
}

function resetCategoryForm() {
  editingCategoryId.value = null
  categoryForm.industry_chain = ''
  categoryForm.level2 = ''
  categoryForm.level3 = ''
}
</script>

<style scoped>
.base-data-grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.95fr) 1.05fr;
  gap: 22px;
}

.panel {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 28px;
  padding: 22px;
  background: rgba(7, 12, 23, 0.72);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.28);
}

.template-panel {
  background:
    radial-gradient(circle at 24% 10%, rgba(45, 212, 191, 0.24), transparent 34%),
    linear-gradient(140deg, rgba(15, 23, 42, 0.95), rgba(4, 10, 20, 0.9));
}

p {
  margin: 0 0 8px;
  color: #7f93ad;
  font-size: 13px;
}

h2,
h3 {
  margin: 0;
  color: #f8fbff;
}

h2 {
  max-width: 520px;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 38px;
  line-height: 1.08;
}

small {
  display: block;
  margin-top: 16px;
  color: #8ba2bd;
}

.template-columns,
.result-grid,
.panel-head,
.actions-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.template-columns {
  margin-top: 26px;
}

.template-columns span {
  padding: 9px 12px;
  border-radius: 999px;
  color: #07131f;
  background: #7dd3fc;
  font-size: 13px;
  font-weight: 700;
}

.panel-head {
  justify-content: space-between;
  margin-bottom: 18px;
}

.actions-row {
  margin-top: 18px;
}

.table-actions {
  margin-top: 0;
}

.input-mode-tabs {
  margin-bottom: 18px;
}

.input-pane {
  min-height: 168px;
}

.manual-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
}

.manual-form :deep(.el-select) {
  width: 100%;
}

.category-actions,
.manual-actions {
  margin-top: 0;
}

.category-table {
  margin-top: 16px;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.92);
  --el-table-text-color: #dce8f6;
  --el-table-header-text-color: #8fb0d3;
  --el-table-border-color: rgba(148, 163, 184, 0.12);
  border-radius: 16px;
  overflow: hidden;
}

.result-panel,
.table-panel {
  grid-column: 1 / -1;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  margin-bottom: 16px;
}

.base-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.92);
  --el-table-text-color: #dce8f6;
  --el-table-header-text-color: #8fb0d3;
  --el-table-border-color: rgba(148, 163, 184, 0.12);
  border-radius: 18px;
  overflow: hidden;
}

.base-table :deep(.cell) {
  overflow: visible;
}

.stock-filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.stock-filter-grid :deep(.el-input-group__prepend) {
  color: #8fb0d3;
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.18);
}

.stock-filter-grid :deep(.el-input__wrapper) {
  background: rgba(248, 251, 255, 0.08);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.18);
}

.stock-filter-grid :deep(.el-input__inner) {
  color: #f8fbff;
}

.stock-filter-grid :deep(.el-input__inner::placeholder) {
  color: #7890aa;
}

@media (max-width: 1080px) {
  .base-data-grid,
  .result-grid,
  .manual-form,
  .stock-filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
