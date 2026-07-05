# 主应用壳开发文档

## 对应代码

- 页面文件：`frontend/src/App.vue`
- 状态来源：`frontend/src/stores/stockStore.ts`
- 同步进度：`frontend/src/composables/useSyncProgress.ts`
- 关键组件：`DataStatusPanel.vue`、各业务页面View

## 页面目标

主应用壳负责承载整套前端仪表板。它提供顶部品牌区、股票选择上下文、同步状态入口和业务Tab导航，是所有页面共享的数据加载和页面切换入口。股票池来源固定为基础资料页维护的启用股票，不再提供从外部概念源发现并同步全量概念股的入口。

## 布局结构

1. 顶部Hero区域：展示产品名称、简短定位和当前选中股票。
2. 数据状态面板：展示“数据拉取进度”、同步状态、Provider健康状态、同步进度和“同步当前股票”按钮。
3. Tab导航：承载基础资料、产业链总览、基本面深度分析、技术面分析、个股深度档案、导入工作台。

## 数据依赖

- `store.loadInitialData()`：页面挂载后加载基础资料启用股票池、产业链分组、行情和同步状态。
- `store.currentStock`：Hero当前股票展示。
- `store.syncStatus`：传给 `DataStatusPanel`。
- `store.syncing`：当前股票同步按钮loading状态。
- `useSyncProgress().progress`：WebSocket实时同步进度。
- `store.syncStatus.coverage`：展示当前启用股票池、行情和K线覆盖率。

## 用户交互

- 页面加载时自动连接同步进度WebSocket。
- 页面加载时自动调用初始数据加载。
- 用户点击顶部状态面板的“同步当前股票”按钮后，触发 `store.syncCurrentStock()`。
- 用户点击Tab后，只切换前端页面，不主动重新拉取全局数据。
- 基础资料导入成功后，用户重新加载或页面刷新会使用新的启用股票池。

## 错误和空状态

- 初始加载失败时，错误信息写入 `store.error`。
- 当前没有启用股票时，Hero中当前股票展示应为空或兜底文案。
- 同步进度WebSocket断开时，不阻塞页面主功能。

## 修改规则

- 新增Tab前，必须先更新 `doc/frontend-pages.md` 页面清单和本文件“布局结构”。
- 修改顶部同步行为前，必须同步更新 `doc/pages/shared-components.md` 中 `DataStatusPanel` 说明。
- 修改初始加载流程前，必须更新本文件“数据依赖”和“用户交互”。
- 不能恢复“发现并同步全量概念股”入口；如需新增股票来源，必须先更新基础资料页文档并确认导入规则。

## 验证要求

- `npm run build` 必须通过。
- 若Tab列表变化，应确认 `doc/frontend-pages.md` 和 `App.vue` 一致。
- 若同步入口变化，应确认点击同步当前股票按钮仍能触发 `POST /api/sync/trigger`。
- 页面不应出现“发现并同步全量概念股”按钮或调用 `/api/stocks/discover-concept-sync`。
