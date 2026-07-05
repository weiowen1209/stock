# 共享组件开发文档

## 对应代码

- `frontend/src/components/DataStatusPanel.vue`
- `frontend/src/components/StockTable.vue`
- `frontend/src/components/KLineChart.vue`
- `frontend/src/components/LineTrendChart.vue`
- `frontend/src/components/MetricCard.vue`
- `frontend/src/components/IndustryChainGraph.vue`

## 组件职责

### DataStatusPanel

顶部数据状态面板。展示“数据拉取进度”、数据缺失数量、基础资料股票池覆盖率、同步进度、Provider健康状态和“同步当前股票”按钮。

数据来源：

- `status: SyncStatus | null`
- `progress: SyncProgress | null`
- `syncing: boolean`

交互：

- 点击“同步当前股票”按钮时向父组件发出 `sync` 事件。
- 覆盖率优先展示 `status.coverage`，包含启用股票池数量、行情覆盖数量、最近 2 年日K覆盖数量和缺失数量。
- 进度优先使用WebSocket实时 `progress`，没有实时数据时回退到 `status.progress`。
- 组件不再提供“发现并同步全量概念股”按钮，也不发出 `discoverSync` 事件。

### StockTable

股票列表组件。展示基础资料中启用股票的基础信息和行情摘要，用于选择当前股票。

数据来源：

- 启用股票列表。
- 行情列表。
- 当前选中股票代码。

交互：

- 点击股票行后通知父级切换当前股票。

### KLineChart

K线图组件。使用K线数据展示股票价格走势。

数据来源：

- `title`
- `items: KLineItem[]`

空态：

- 无K线数据时应显示稳定空态，不应崩溃。

### LineTrendChart

通用趋势图组件。支持折线图和柱状图，用于基本面、估值和技术指标。

数据来源：

- `title`
- `eyebrow`
- `labels`
- `series`

空态：

- `series.length === 0` 时显示“暂无数据”。

### MetricCard

指标卡组件。展示单个指标标题、数值和辅助说明。

### IndustryChainGraph

产业链图谱组件。展示基础资料中启用股票的产业链环节和股票分布。

## 修改规则

- 修改共享组件props前，必须先更新本文档对应组件的数据来源。
- 修改共享组件事件前，必须先更新本文档对应组件的交互说明。
- 修改共享组件空态前，必须先更新本文档对应组件的空态说明。
- 共享组件被多个页面使用，修改后必须检查所有引用页面文档是否需要同步更新。
- 不能恢复 `discoverSync` 事件或“发现并同步全量概念股”按钮。

## 验证要求

- `npm run build` 必须通过。
- 修改 `DataStatusPanel` 后，应验证同步按钮、覆盖率、进度条和Provider状态显示。
- 修改 `LineTrendChart` 后，应验证基本面和技术面页面。
- 修改 `KLineChart` 后，应验证技术面和个股深度档案页面。
