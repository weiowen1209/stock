# 产业链总览页面开发文档

## 对应代码

- 页面文件：`frontend/src/views/IndustryOverview.vue`
- 主要组件：`IndustryChainGraph.vue`、`StockTable.vue`
- 状态来源：`frontend/src/stores/stockStore.ts`

## 页面目标

产业链总览页面用于展示基础资料中启用股票的人形机器人产业链分布、产业链分组和可筛选股票列表，帮助用户从产业环节角度选择目标股票。页面不负责发现股票，股票来源只能来自基础资料页Excel覆盖导入。

## 布局结构

1. 产业链统计或图谱区域：通过 `IndustryChainGraph` 展示启用股票的产业链分组关系。
2. 产业链筛选区域：基于 `store.industries` 提供“全部”和各产业链选项。
3. 股票列表区域：通过 `StockTable` 展示筛选后的启用股票列表。

## 数据依赖

- `store.groups`：启用股票的产业链分组数据。
- `store.industries`：筛选项。
- `store.selectedIndustry`：当前筛选条件。
- `store.filteredStocks`：筛选后的启用股票。
- `store.currentCode`：当前选中股票。
- `store.quotes`：启用股票列表中的行情字段。

## 用户交互

- 用户切换产业链筛选条件时，更新 `store.selectedIndustry`。
- 用户点击股票表格中的股票时，调用 `store.selectStock(code)`。
- 选中股票后，当前股票上下文会影响基本面、技术面、个股档案等页面。

## 错误和空状态

- `groups` 为空时，产业链图谱应显示空态或无数据状态。
- `filteredStocks` 为空时，股票表格应显示空表格。
- 股票行情缺失时，表格字段应显示兜底值，不应阻塞选股。

## 修改规则

- 修改产业链分组展示前，先更新本文件“布局结构”和“数据依赖”。
- 修改股票选择行为前，先更新本文件“用户交互”和 `doc/frontend-pages.md` 共享状态说明。
- 修改表格字段前，先同步更新 `StockTable.vue` 相关文档说明。
- 不能新增自动发现股票入口；股票池变更必须通过 `doc/pages/base-data.md` 定义的基础资料Excel导入。

## 验证要求

- `npm run build` 必须通过。
- 切换产业链筛选后，股票列表应立即变化。
- 点击任意股票后，顶部当前股票和其他Tab的数据上下文应更新。
- Excel覆盖导入后，本页只展示基础资料中启用的股票。
