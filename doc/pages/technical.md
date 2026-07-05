# 技术面分析页面开发文档

## 对应代码

- 页面文件：`frontend/src/views/Technical.vue`
- 主要组件：`KLineChart.vue`、`LineTrendChart.vue`
- 状态来源：`frontend/src/stores/stockStore.ts`
- 后端接口：`/api/kline/{code}`、`/api/technical/{code}`

## 页面目标

技术面分析页面用于展示当前股票的K线走势、均线系统、MACD和RSI指标，帮助用户观察趋势、动量和相对强弱。

## 布局结构

1. 顶部K线图：展示当前股票的K线走势。
2. 均线系统图：展示收盘价、MA5、MA10、MA20。
3. MACD图：展示DIF、DEA和柱状图。
4. RSI6图：展示短周期相对强弱指标。

## 数据依赖

- `store.currentStock`：图表标题中的股票名称。
- `store.kline`：K线图数据。
- `store.technical.dates`：技术指标横轴日期。
- `store.technical.close`：收盘价。
- `store.technical.ma5`、`ma10`、`ma20`：均线。
- `store.technical.macd`、`signal`、`histogram`：MACD相关数据。
- `store.technical.rsi6`：RSI6数据。

## 用户交互

- 页面不提供独立筛选器，跟随全局当前股票。
- 用户点击同步当前股票后，K线和技术指标应在同步完成后重新加载。

## 错误和空状态

- K线为空时，`KLineChart` 应显示空态或空图表，不应崩溃。
- 技术指标为空时，各 `LineTrendChart` 使用空数组并显示“暂无数据”。
- 技术指标接口失败时，`store.technical` 置为 `null`。

## 修改规则

- 新增技术指标图前，必须先更新本文件“布局结构”和“数据依赖”。
- 修改指标算法字段前，必须同步更新后端 `TechnicalIndicators` Schema、前端类型和本文件。
- 修改K线展示方式前，必须同步更新 `KLineChart.vue` 的组件说明。

## 验证要求

- `npm run build` 必须通过。
- 当前股票切换后，K线和所有技术指标图应更新。
- 后端返回空数组或 `technical=null` 时页面不应崩溃。
