# 基本面深度分析页面开发文档

## 对应代码

- 页面文件：`frontend/src/views/Fundamental.vue`
- 主要组件：`MetricCard.vue`、`LineTrendChart.vue`
- 状态来源：`frontend/src/stores/stockStore.ts`
- 后端接口：`/api/fundamentals/{code}`、`/api/fundamentals/{code}/deep-analysis`、`/api/fundamentals/{code}/segments`、`/api/fundamentals/{code}/expenses`、`/api/valuation/{code}`

## 页面目标

基本面深度分析页面用于展示当前股票的增长潜力、财务质量、同比/环比拆解、杜邦分析、行业对比、估值分位和 AI 解读，帮助用户判断公司增长是否具备空间、能力、质量和估值性价比。

## 布局结构

0. 顶部股票头部卡：显示当前股票名称、代码、产业链标签、模糊搜索框和实时价格涨跌幅；搜索框支持按代码或名称模糊匹配，选中后切换分析对象。
1. 顶部指标卡：综合评分、增长潜力、财务质量、估值性价比。
2. AI 解读面板：展示一句话结论、增长亮点、风险提示和跟踪指标。
3. 增长潜力评分拆解：展示评分因子、权重依据、方向说明、评分等级和评分进度条。
4. 增长信号解读：逐期展示高质量增长、增收不增利、现金流偏弱等信号。
5. 同比/环比增长拆解图：展示营收同比、净利同比、现金流匹配。
6. 杜邦分析图：展示披露 ROE、估算 ROE、净利率、资产周转率、权益乘数。
7. 杜邦注释卡：展示每期 ROE 主驱动和解释。
8. 行业对比卡片：展示公司值、同业中位数、行业分位和结论。
9. 估值分位卡片：展示 PE、PB、PEG 的历史分位、样本数、回归中枢空间和估值提示。
10. 保留原有业务分部收入、费用结构和估值指标图。

## 数据依赖

- `store.deepFundamental`：深度基本面分析结果，包含评分、增长拆解、杜邦、行业对比、估值分位和 AI 解读。
- `store.financialReports`：财务报表数组。
- `store.businessSegments`：业务分部数组。
- `store.expenses`：费用结构数组。
- `store.valuation`：估值指标数组。
- `store.currentCode`：接口请求股票代码。

## 计算逻辑

- `deep` 取 `store.deepFundamental` 作为深度分析主数据。
- `latest` 取 `financialReports` 最后一条作为传统财务数据。
- `reportLabels` 使用 `report_period`。
- `segmentLabels` 使用 `segment_name`。
- `expenseLabels` 使用 `report_period`。
- `toNumber` 将字符串、数字或空值转换为图表可用数据。
- `percentRatio` 将后端小数口径比率转换为百分比数值。
- `formatScore` 将评分显示为整数。
- `formatWeight` 将权重小数转成百分比。
- `formatRatio` 将现金流匹配等倍数指标显示为 x 倍。
- `scoreClass` 按评分切换强弱颜色，遵循 A 股习惯：偏强用红/橙，偏弱用绿色。
- `directionText` 展示指标方向，如越高越好、越低越好、适度更好。
- `formatMoney` 将金额转为亿、万或原始数值显示。
- `formatPercent` 将百分比保留两位小数。

## 用户交互

- 页面本身不发起选股操作，完全跟随全局当前股票。
- 用户在产业链总览选择股票后，本页数据由 `store.loadStockAnalysis(code)` 自动刷新。

## 错误和空状态

- 深度分析为空时，指标卡显示 `--`，AI 解读显示“暂无深度分析结论”。
- 财务数据为空时，传统图表显示空态。
- 图表数据为空时，`LineTrendChart` 显示“暂无数据”。
- 接口失败时，`stockStore` 会清空对应数据并写入 `store.error`。

## 修改规则

- 新增财务指标卡前，必须先更新本文件“布局结构”和“数据依赖”。
- 新增图表前，必须先说明使用的数据字段、标签字段和空态。
- 修改金额或百分比格式化逻辑前，必须先更新“计算逻辑”。
- 修改后端字段前，必须同步更新 `frontend/src/api/types.ts` 和本文件。

## 验证要求

- `npm run build` 必须通过。
- 当前股票切换后，指标卡和全部图表应同步变化。
- 财务、业务分部、费用、估值任一接口为空时，页面不应崩溃。
