# 人形机器人产业A股股票分析仪表板 - 设计文档

**日期**: 2026-07-03  
**状态**: 已优化确认  
**设计原则**: 最终需求全部保留，采用分阶段交付；先打通稳定数据闭环，再逐步增强数据源、PDF解析、复杂分析和部署能力。

---

## 1. 项目概述

### 1.1 目标

构建一个交互式网页仪表板，用于分析人形机器人产业相关的A股上市公司。系统覆盖产业链分析、基本面深度分析、技术面分析、个股深度档案、PDF财报补充、手工录入和多数据源自动降级能力，帮助用户全面了解人形机器人产业链上市公司的经营、估值、行情和技术走势。

系统只提供数据展示、分析辅助和信息整理，不构成任何投资建议、买卖建议或收益承诺。

### 1.2 目标市场

A股（中国内地股票市场），聚焦人形机器人产业链相关上市公司。

### 1.3 核心需求

- 产业链维度的股票分类、筛选、对比和总览分析。
- 深度基本面分析，包括业务板块拆分、费用结构、净利润归因、估值对比。
- 技术面分析，包括K线、成交量、均线、MACD、RSI、相对强弱和热力图。
- 个股深度档案，包括公司信息、产业链定位、核心产品、财务摘要、供应链标签。
- 支持用户上传PDF财报，解析后补充或覆盖数据。
- 支持手工录入和人工确认，解决PDF解析失败或API数据缺失问题。
- 支持多数据源自动降级切换，并以SQLite本地缓存作为统一读取源。
- 支持同步进度、数据缺失提示、数据来源追踪和更新时间展示。

### 1.4 分阶段交付范围

| 阶段 | 目标 | 覆盖能力 |
|------|------|----------|
| MVP | 打通端到端数据闭环 | 股票池、产业链分类、行情/K线、基础财务摘要、SQLite、基础API、前端基础页面 |
| V1 | 完成核心仪表板 | 四大Tab、基本面图表、技术指标、同步状态、Provider降级基础能力 |
| V2 | 完成数据补充能力 | PDF上传、半自动解析、人工确认覆盖、手工录入、导入记录 |
| V3 | 完成增强能力 | 8个Provider全量接入、复杂PDF精准解析、定时同步增强、部署优化、更多图表 |

最终需求全部保留，但实现顺序以稳定可验证为优先，避免在首版同时承担所有高风险功能。

---

## 2. 技术栈

### 2.1 后端

- **框架**: FastAPI (Python 3.11+)
- **数据库**: SQLite (aiosqlite 异步驱动)
- **ORM**: SQLAlchemy
- **配置管理**: pydantic-settings / python-dotenv
- **定时任务**: APScheduler
- **PDF解析**: pdfplumber / PyMuPDF
- **数据处理**: pandas
- **实时通信**: WebSocket（进度推送）
- **测试**: pytest、httpx、pytest-asyncio

### 2.2 前端

- **框架**: Vue 3 + Vite
- **图表**: ECharts + vue-echarts
- **状态管理**: Pinia
- **HTTP**: axios
- **UI组件库**: Element Plus
- **进度条**: NProgress

### 2.3 数据源Provider规划

Provider采用分批接入方式，统一通过DataProvider抽象接口暴露能力。

| 批次 | Provider | 特点 | 是否需注册 | 擅长数据类型 |
|------|----------|------|------------|--------------|
| P0 | AKShare | API覆盖面广，适合快速打通闭环 | 否 | 行情、K线、部分财务、指数 |
| P0 | 东方财富 | 数据丰富，实时性较强 | 否 | K线、行业指数、资金流向 |
| P1 | BaoStock | A股历史K线和复权数据较稳定 | 否 | 历史K线、复权数据 |
| P2 | Tushare | 数据完整度高，财报结构化能力强 | 需Token | K线、财报、估值 |
| P3 | 新浪财经 | 行情接口稳定 | 否 | 实时行情 |
| P3 | 腾讯财经 | 实时行情响应快 | 否 | 实时行情 |
| P3 | 同花顺 | 财务与技术指标丰富 | 否 | 财务基本面、技术指标 |
| P3 | 网易财经 | 历史行情CSV下载稳定 | 否 | 历史行情备份 |

MVP阶段只要求P0 Provider可用；V3阶段完成8个Provider全量接入。

---

## 3. 系统架构

### 3.1 架构图

```text
前端 Vue 3 + ECharts
    ↕ HTTP / WebSocket
FastAPI 后端
    ├── API层 routes
    ├── Service层 业务查询、分析计算、数据聚合
    ├── DataProvider层 Provider接口、注册表、降级管理
    ├── Import层 PDF解析、手工录入、人工确认、导入记录
    ├── Sync层 手动同步、定时任务、进度推送
    └── DB层 SQLite via SQLAlchemy
```

### 3.2 架构原则

- SQLite是系统读取侧的唯一数据源，前端展示、筛选、图表和分析均读取SQLite。
- 外部API只负责数据采集和同步，不直接驱动前端页面。
- 数据导入必须记录来源、时间、批次、覆盖关系和审核状态。
- Provider必须可插拔，新增Provider不应影响API层和前端。
- API返回数据必须包含数据来源和更新时间，缓存数据必须明确标记。
- 生产环境不使用Mock数据兜底；Mock只允许开发环境启用。

### 3.3 数据流

1. 用户打开页面，前端请求SQLite中的股票池、行情、K线、财务摘要和数据状态。
2. 如果SQLite缺少关键数据，前端展示DataStatusPanel，引导用户执行同步、上传PDF或手工录入。
3. 用户触发同步后，后端按Provider优先级获取数据，写入SQLite，并通过WebSocket推送进度。
4. 用户上传PDF后，系统先生成待确认的解析结果；用户确认后才写入正式财务表。
5. 所有图表和分析重新从SQLite读取，避免页面直接依赖外部API。

---

## 4. 数据库设计

### 4.1 stocks - 股票基本信息

| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(10) PRIMARY KEY | 股票代码，如688017 |
| name | VARCHAR(50) | 股票名称 |
| exchange | VARCHAR(10) | 交易所，SH/SZ/BJ |
| industry_chain | VARCHAR(50) | 产业链环节 |
| industry_chain_detail | VARCHAR(100) | 产业链细分定位 |
| core_products | TEXT | 核心产品摘要 |
| supply_chain_tags | TEXT | 供应链标签，JSON字符串 |
| list_date | DATE | 上市日期 |
| is_active | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.2 kline_data - K线数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| code | VARCHAR(10) | 股票代码 |
| period | VARCHAR(10) | day/week/month |
| date | DATE | 交易日期 |
| open | DECIMAL(12,2) | 开盘价 |
| close | DECIMAL(12,2) | 收盘价 |
| high | DECIMAL(12,2) | 最高价 |
| low | DECIMAL(12,2) | 最低价 |
| volume | BIGINT | 成交量 |
| turnover | DECIMAL(18,2) | 成交额 |
| change_pct | DECIMAL(8,2) | 涨跌幅 |
| source | VARCHAR(30) | 数据来源 |
| updated_at | DATETIME | 更新时间 |
| UNIQUE(code, period, date) | | 防止重复K线 |

索引：`idx_kline_code_period_date(code, period, date)`。

### 4.3 realtime_quotes - 实时行情快照

| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(10) PRIMARY KEY | 股票代码 |
| price | DECIMAL(12,2) | 最新价 |
| change_pct | DECIMAL(8,2) | 涨跌幅 |
| turnover_rate | DECIMAL(8,2) | 换手率 |
| volume | BIGINT | 成交量 |
| turnover | DECIMAL(18,2) | 成交额 |
| market_cap | DECIMAL(18,2) | 总市值 |
| source | VARCHAR(30) | 数据来源 |
| updated_at | DATETIME | 更新时间 |

### 4.4 financial_reports - 公司级财务报表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| code | VARCHAR(10) | 股票代码 |
| report_period | VARCHAR(20) | 报告期，如2025年报、2025Q3 |
| report_date | DATE | 报告截止日 |
| revenue | DECIMAL(18,2) | 营业收入 |
| gross_profit | DECIMAL(18,2) | 毛利 |
| gross_margin | DECIMAL(8,2) | 毛利率 |
| net_profit | DECIMAL(18,2) | 净利润 |
| operating_cash_flow | DECIMAL(18,2) | 经营现金流 |
| total_assets | DECIMAL(18,2) | 总资产 |
| net_assets | DECIMAL(18,2) | 净资产 |
| eps | DECIMAL(8,4) | 每股收益 |
| roe | DECIMAL(8,2) | 净资产收益率 |
| rd_ratio | DECIMAL(8,2) | 研发费用率 |
| source | VARCHAR(30) | api/pdf/manual |
| import_id | INTEGER | 关联导入批次 |
| review_status | VARCHAR(20) | pending/confirmed/rejected |
| updated_at | DATETIME | 更新时间 |
| UNIQUE(code, report_period) | | 防止重复报告 |

### 4.5 business_segments - 业务分部数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| code | VARCHAR(10) | 股票代码 |
| report_period | VARCHAR(20) | 报告期 |
| segment_type | VARCHAR(20) | product/industry/region |
| segment_name | VARCHAR(100) | 分部名称 |
| revenue | DECIMAL(18,2) | 收入 |
| cost | DECIMAL(18,2) | 成本 |
| gross_profit | DECIMAL(18,2) | 毛利 |
| gross_margin | DECIMAL(8,2) | 毛利率 |
| revenue_yoy | DECIMAL(8,2) | 收入同比 |
| source | VARCHAR(30) | api/pdf/manual |
| import_id | INTEGER | 关联导入批次 |
| review_status | VARCHAR(20) | pending/confirmed/rejected |
| UNIQUE(code, report_period, segment_type, segment_name) | | 防止重复分部 |

### 4.6 expense_items - 费用结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| code | VARCHAR(10) | 股票代码 |
| report_period | VARCHAR(20) | 报告期 |
| selling_expense | DECIMAL(18,2) | 销售费用 |
| admin_expense | DECIMAL(18,2) | 管理费用 |
| rd_expense | DECIMAL(18,2) | 研发费用 |
| finance_expense | DECIMAL(18,2) | 财务费用 |
| source | VARCHAR(30) | api/pdf/manual |
| import_id | INTEGER | 关联导入批次 |
| UNIQUE(code, report_period) | | 防止重复费用记录 |

### 4.7 valuation_metrics - 估值指标

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| code | VARCHAR(10) | 股票代码 |
| date | DATE | 指标日期 |
| pe | DECIMAL(12,2) | 市盈率 |
| pb | DECIMAL(12,2) | 市净率 |
| peg | DECIMAL(12,2) | PEG |
| market_cap | DECIMAL(18,2) | 总市值 |
| source | VARCHAR(30) | 数据来源 |
| UNIQUE(code, date) | | 防止重复估值记录 |

### 4.8 industry_index - 行业指数

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| index_code | VARCHAR(20) | 指数代码 |
| index_name | VARCHAR(50) | 指数名称 |
| date | DATE | 交易日期 |
| close | DECIMAL(12,2) | 收盘点位 |
| change_pct | DECIMAL(8,2) | 涨跌幅 |
| source | VARCHAR(30) | 数据来源 |
| UNIQUE(index_code, date) | | 防止重复指数记录 |

### 4.9 import_batches - 数据导入批次

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| import_type | VARCHAR(20) | api/pdf/manual |
| file_name | VARCHAR(255) | 上传文件名 |
| code | VARCHAR(10) | 关联股票代码 |
| report_period | VARCHAR(20) | 报告期 |
| status | VARCHAR(20) | parsing/pending_review/confirmed/failed |
| summary | TEXT | 导入摘要 |
| error_detail | TEXT | 错误详情 |
| created_at | DATETIME | 创建时间 |
| confirmed_at | DATETIME | 确认时间 |

### 4.10 provider_health - Provider健康状态

| 字段 | 类型 | 说明 |
|------|------|------|
| provider | VARCHAR(30) PRIMARY KEY | Provider名称 |
| status | VARCHAR(20) | available/unavailable/probing |
| consecutive_failures | INTEGER | 连续失败次数 |
| last_success_at | DATETIME | 最近成功时间 |
| last_failure_at | DATETIME | 最近失败时间 |
| next_probe_at | DATETIME | 下次探测时间 |
| error_message | TEXT | 最近错误 |

### 4.11 sync_log - 同步日志

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| task_type | VARCHAR(50) | kline/fundamental/realtime/index |
| provider | VARCHAR(30) | 使用的Provider名称 |
| status | VARCHAR(20) | success/failed/timeout/fallback |
| records_count | INTEGER | 成功记录数 |
| detail | TEXT | 详情 |
| created_at | DATETIME | 创建时间 |

---

## 5. 数据来源、覆盖与降级策略

### 5.1 数据读取优先级

页面读取时只读SQLite，不直接读外部API。字段级数据优先级如下：

1. 已确认的人工录入数据。
2. 已确认的PDF解析数据。
3. API同步数据。
4. 开发环境Mock数据。

PDF解析结果默认进入待确认状态，用户确认后才覆盖正式数据；生产环境不展示Mock兜底数据。

### 5.2 Provider优先级链

| 数据类型 | MVP/P0 | P1 | P2 | P3 |
|---------|--------|----|----|----|
| 日K线/行情 | 东方财富、AKShare | BaoStock | Tushare | 新浪、网易财经 |
| 实时行情 | AKShare、东方财富 | - | - | 腾讯、新浪 |
| 财务基本面 | AKShare | - | Tushare | 同花顺、东方财富 |
| 行业指数 | 东方财富、AKShare | - | Tushare | 同花顺、网易财经 |

### 5.3 降级规则

- 单个Provider超时限制10秒。
- 连续失败3次自动标记为不可用，30分钟后重新探测。
- 当前Provider失败时按优先级链尝试下一个Provider。
- 全部Provider失败时返回SQLite缓存数据，并标记`stale=true`和失败原因。
- 如果SQLite也无数据，则返回数据缺失清单，引导用户同步、上传或录入。

---

## 6. API契约

所有API返回均包含`data`、`meta`、`error`三部分。`meta`至少包含`source`、`updated_at`、`stale`。

### 6.1 股票与产业链

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stocks` | 股票列表，支持产业链、关键词筛选 |
| GET | `/api/stocks/{code}` | 单只股票详情 |
| GET | `/api/stocks/by-industry` | 按产业链分组返回股票 |

### 6.2 行情、K线与技术指标

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/quotes` | 股票实时行情列表 |
| GET | `/api/kline/{code}` | K线数据，支持`period/start/end` |
| GET | `/api/technical/{code}` | MA、MACD、RSI、相对强弱等技术指标 |

### 6.3 基本面与估值

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/fundamentals/{code}` | 公司级财务摘要 |
| GET | `/api/fundamentals/{code}/segments` | 业务分部拆分 |
| GET | `/api/fundamentals/{code}/expenses` | 费用结构 |
| GET | `/api/valuation/{code}` | 估值指标与历史分位 |

### 6.4 同步与导入

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sync/status` | 数据缺失清单和最近同步状态 |
| POST | `/api/sync/trigger` | 手动触发同步 |
| WS | `/ws/sync/progress` | 同步进度推送 |
| POST | `/api/upload/pdf` | PDF上传并生成待确认解析结果 |
| GET | `/api/imports/{id}` | 查看导入结果和错误详情 |
| POST | `/api/imports/{id}/confirm` | 确认写入解析结果 |
| POST | `/api/manual/fundamentals` | 手工录入财务数据 |

---

## 7. 前端设计

### 7.1 整体布局

顶部Tab切换四大模块，每个模块最大化利用屏幕空间展示数据。页面全局展示数据更新时间、当前数据来源、同步状态和免责声明入口。

### 7.2 Tab 1 - 产业链总览

- 产业链全景结构图：整机/系统集成、核心零部件、传感器、减速器/伺服、软件/算法、材料/结构件。
- 各环节龙头公司卡片：核心产品、产业链定位、供应链标签。
- 行业指数走势图和各环节平均涨跌幅。
- 各环节估值对比：平均PE、PB、市值分布。
- 产业链热度/关注度排行，V3阶段增强。

### 7.3 Tab 2 - 基本面深度分析

- 业务板块拆分堆叠柱状图。
- 营收、成本、毛利、毛利率趋势图。
- 同比/环比变化分析。
- 费用结构分析。
- 净利润拆解瀑布图。
- 估值对比：PE、PB、PEG、历史分位。

### 7.4 Tab 3 - 技术面分析

- K线图，支持日K/周K/月K切换。
- 成交量柱状图。
- MA5/10/20/60均线。
- MACD、RSI指标。
- 板块内相对强弱。
- 涨跌幅热力图。

### 7.5 Tab 4 - 个股深度档案

- 公司基本信息卡片和产业链定位描述。
- 核心产品与技术竞争力摘要。
- 业务板块收入占比及历年变化。
- 财务摘要卡片：营收、净利、毛利率、ROE、研发费用率。
- 同行业对比雷达图。
- 供应链关系标签。
- 上传财报按钮和手工录入入口。

### 7.6 前端共享组件

| 组件 | 说明 |
|------|------|
| KLineChart | ECharts K线图，支持周期切换、均线、成交量 |
| RadarChart | 多维度同业对比雷达图 |
| StockTable | Element Plus表格，支持排序、筛选、分页 |
| MetricCard | 指标卡片，显示数值、变化趋势和更新时间 |
| IndustryTag | 产业链环节标签 |
| ProgressBar | 数据加载和同步进度条 |
| DataStatusPanel | 数据缺失提示面板，精确到股票、字段、报告期 |
| UploadPanel | PDF上传、解析进度、错误详情 |
| ManualInputModal | 手工录入弹窗 |
| SourceBadge | 数据来源、更新时间、是否缓存的标识 |

---

## 8. PDF财报上传与解析

### 8.1 分阶段能力

| 阶段 | 能力 |
|------|------|
| V2基础 | 上传PDF、保存导入批次、提取文本和表格、生成待确认结果 |
| V2增强 | 自动识别主要会计数据、财务指标、业务分部、费用明细 |
| V3精准 | 针对重点公司年报模板优化规则，提升复杂表格解析准确率 |

### 8.2 支持的数据提取

- 主要会计数据：营收、利润、现金流、资产、净资产。
- 主要财务指标：EPS、ROE、研发费用率。
- 分行业/分产品收入、成本、毛利率和同比变化。
- 成本构成、产销量数据、研发投入和专利数据作为V3增强目标。

### 8.3 人工确认与覆盖

按公司代码 + 报告期比对SQLite已有数据：

- 不存在：解析结果进入待确认状态，用户确认后写入。
- 已存在：提示已有数据来源、更新时间和字段差异，由用户选择覆盖、合并或取消。
- 解析失败：展示失败页码、表格、字段和原因，并提供手工录入入口。

---

## 9. 定时同步任务

| 任务 | 频率 | 说明 | 阶段 |
|------|------|------|------|
| 实时行情同步 | 每30分钟 | 涨跌幅、换手率、最新价 | V1 |
| 日K线同步 | 每天收盘后15:30 | 补充当天K线数据 | V1 |
| 行业指数同步 | 每天收盘后15:30 | 机器人相关指数 | V1 |
| 基本面数据同步 | 财报季/手动触发 | PE/PB/ROE等估值指标 | V2 |
| Provider健康探测 | 每30分钟 | 恢复不可用Provider | V1 |

MVP阶段优先实现手动同步；V1开始启用定时同步。

---

## 10. 项目目录结构

```text
humanoid-robot-stock-dashboard/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── database.py
│   ├── schemas/
│   ├── data_provider/
│   ├── sync/
│   ├── services/
│   ├── importers/
│   ├── api/
│   └── init_data/
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── views/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── api/
│   │   └── stores/
│   ├── package.json
│   └── vite.config.ts
├── data/
│   └── dashboard.db
├── tests/
├── requirements.txt
├── README.md
└── start.py
```

---

## 11. 错误处理

| 场景 | 处理策略 |
|------|---------|
| API调用超时/失败 | FailoverManager自动切换下一个Provider |
| 所有API不可用 | 返回SQLite缓存数据，标记`stale=true`并提示原因 |
| SQLite无数据 | DataStatusPanel提示缺失内容，引导同步、上传或录入 |
| PDF解析失败 | 精确到页/表/字段的错误原因，提供手工录入入口 |
| PDF重复上传 | 展示已有数据和新解析数据差异，由用户决定覆盖或合并 |
| 前端请求超时 | ProgressBar标红当前步骤并提供重试按钮 |
| Provider连续失败 | 标记不可用，记录健康状态，30分钟后重新探测 |
| 配置缺失 | 启动时提示缺失配置，Tushare Token缺失不影响P0能力 |

---

## 12. 测试与验收

### 12.1 MVP验收

- 启动后自动创建SQLite数据库和所有表。
- 股票池包含至少20只股票，并覆盖6个产业链环节。
- 可从P0 Provider同步至少一只股票的行情和日K数据。
- 前端可展示股票列表、产业链筛选、基础行情、K线和个股摘要。
- API返回包含来源、更新时间和缓存标记。

### 12.2 V1验收

- 四大Tab可切换并显示真实或缓存数据。
- 基本面、技术指标、估值图表可渲染。
- Provider失败时可自动降级，并记录sync_log和provider_health。
- WebSocket可推送同步进度。

### 12.3 V2验收

- PDF可上传并生成导入批次。
- 解析结果可人工确认后写入正式表。
- 手工录入可补充或覆盖财务数据。
- 重复报告期数据有明确覆盖提示。

### 12.4 V3验收

- 8个Provider全部接入统一Provider接口。
- 复杂PDF解析能力覆盖重点公司年报核心字段。
- 定时同步、部署脚本、README和响应式适配完成。

---

## 13. 安全、配置与合规

- Tushare Token等敏感配置放入`.env`，不得写入代码仓库。
- 日志不记录Token、Cookie、账户信息或本地敏感路径。
- 上传PDF限制文件类型和大小，解析失败不影响主服务。
- 页面显著位置展示“仅供信息展示，不构成投资建议”。
- 所有外部数据需要展示来源和更新时间，避免误导用户。
