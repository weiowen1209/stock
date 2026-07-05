# 前端页面开发总览

本文档根据当前代码整理前端页面结构、共享状态、数据流和后续修改规则。以后涉及页面、组件、接口字段、交互行为、样式布局的代码改动，必须先更新对应开发文档，再修改代码。

## 强制开发流程

1. 先定位本次改动影响的页面文档。
2. 先修改 `doc/pages/*.md` 中的目标、数据依赖、交互、错误处理或测试要求。
3. 如果改动跨页面，还要同步更新本文档。
4. 文档改完后再改代码。
5. 代码改完后运行相关测试和构建。
6. 总结时同时说明文档和代码改动。

## 页面清单

| 页面 | Vue文件 | 开发文档 | 入口Tab |
| --- | --- | --- | --- |
| 主应用壳 | `frontend/src/App.vue` | `doc/pages/app-shell.md` | 全局 |
| 基础资料 | `frontend/src/views/BaseData.vue` | `doc/pages/base-data.md` | 基础资料 |
| 产业链总览 | `frontend/src/views/IndustryOverview.vue` | `doc/pages/industry-overview.md` | 产业链总览 |
| 基本面深度分析 | `frontend/src/views/Fundamental.vue` | `doc/pages/fundamental.md` | 基本面深度分析 |
| 技术面分析 | `frontend/src/views/Technical.vue` | `doc/pages/technical.md` | 技术面分析 |
| 个股深度档案 | `frontend/src/views/StockDetail.vue` | `doc/pages/stock-detail.md` | 个股深度档案 |
| 导入工作台 | `frontend/src/views/ImportWorkbench.vue` | `doc/pages/import-workbench.md` | 导入工作台 |

## 共享状态

核心状态位于 `frontend/src/stores/stockStore.ts`。

- `stocks`：基础资料中启用的股票池。
- `groups`：按产业链聚合后的股票分组。
- `quotes`：实时行情。
- `kline`：当前股票K线。
- `syncStatus`：同步状态、Provider健康状态、进度快照。
- `financialReports`：当前股票财务报表。
- `businessSegments`：当前股票业务分部。
- `expenses`：当前股票费用结构。
- `valuation`：当前股票估值指标。
- `technical`：当前股票技术指标。
- `currentCode`：当前选中股票代码。
- `selectedIndustry`：产业链筛选条件。
- `loading`：初始加载状态。
- `syncing`：当前股票同步状态。
- `error`：最近一次错误。

## 共享组件

- `DataStatusPanel.vue`：顶部数据状态、同步进度、Provider健康状态、同步按钮。
- `StockTable.vue`：股票列表展示、当前股票选择。
- `KLineChart.vue`：K线图。
- `LineTrendChart.vue`：通用折线/柱状趋势图。
- `MetricCard.vue`：指标卡片。
- `IndustryChainGraph.vue`：产业链图谱。

## API入口

前端统一通过 `frontend/src/api/index.ts` 调用后端，类型定义在 `frontend/src/api/types.ts`。

重要接口：

- `getBaseDataStocks`
- `importBaseDataExcel`
- `getStocks`
- `getStocksByIndustry`
- `getQuotes`
- `getKline`
- `getSyncStatus`
- `triggerSync`
- `getFinancialReports`
- `getBusinessSegments`
- `getExpenses`
- `getValuation`
- `getTechnical`
- `uploadImport`
- `createManualImport`
- `confirmImport`
- `getImportBatches`

## 修改约束

- 新增页面前，必须先新增 `doc/pages/<page-name>.md`。
- 修改页面结构前，必须先更新对应文档的“布局结构”。
- 修改接口字段前，必须先更新对应文档的“数据依赖”和 `frontend/src/api/types.ts` 说明。
- 修改交互行为前，必须先更新对应文档的“用户交互”。
- 修改错误提示前，必须先更新对应文档的“错误和空状态”。
- 修改测试前，必须先更新对应文档的“验证要求”。
