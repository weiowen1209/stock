# 人形机器人产业A股股票分析仪表板 - 实现计划

**日期**: 2026-07-03  
**设计文档**: `D:\work\stock\doc\2026-07-03-humanoid-robot-stock-dashboard-design.md`  
**实现原则**: 最终需求全部实现，采用MVP、V1、V2、V3分阶段交付；每个阶段都必须形成可运行、可验证、可回归的成果。

---

## 总览

本实现计划将项目分为 **7个阶段**。阶段顺序优先保障端到端闭环，其次扩展复杂分析、PDF解析、多Provider和部署能力。

| 阶段 | 交付层级 | 核心目标 |
|------|----------|----------|
| 阶段1 | MVP | 项目脚手架、数据库、基础API、初始股票池 |
| 阶段2 | MVP | P0数据源、同步闭环、SQLite写入和缓存读取 |
| 阶段3 | MVP/V1 | 前端基础框架、股票列表、产业链总览、个股摘要、K线展示 |
| 阶段4 | V1 | 基本面、估值、技术指标和四大Tab完整页面 |
| 阶段5 | V1/V2 | Provider降级、同步状态、定时任务、数据来源追踪 |
| 阶段6 | V2/V3 | PDF上传、半自动解析、人工确认、手工录入、复杂解析增强 |
| 阶段7 | V3 | 8 Provider全量接入、联调测试、一键启动、部署和文档 |

---

## 阶段 1: 项目脚手架、数据库与基础API

**目标**: 搭建项目骨架，建立可扩展的数据模型，确保后端能启动、建表、导入初始股票池并响应基础接口。

### 任务清单

| # | 任务 | 产出文件 | 验证标准 |
|---|------|---------|---------|
| 1.1 | 创建项目目录结构 | `backend/`, `frontend/`, `data/`, `tests/` | 目录结构与设计文档第10节一致 |
| 1.2 | 编写Python依赖文件 | `requirements.txt` | `pip install -r requirements.txt` 成功 |
| 1.3 | 编写配置模块 | `backend/config.py` | 可读取数据库路径、Provider配置、上传目录、定时任务配置 |
| 1.4 | 编写SQLAlchemy模型 | `backend/models.py` | 覆盖设计文档中的所有核心表 |
| 1.5 | 编写数据库连接和初始化 | `backend/database.py` | 启动后自动创建 `data/dashboard.db` 和全部表 |
| 1.6 | 编写FastAPI入口 | `backend/main.py` | `/health` 返回 `{"status":"ok"}` |
| 1.7 | 编写Pydantic响应结构 | `backend/schemas/` | API统一返回 `data/meta/error` |
| 1.8 | 编写初始股票池 | `backend/init_data/stock_list.py` | 至少20只股票，覆盖6个产业链环节 |
| 1.9 | 编写股票基础API | `backend/api/stocks.py` | `/api/stocks`、`/api/stocks/{code}` 可返回SQLite数据 |

### 初始股票池要求

产业链环节至少包括：

- 整机/系统集成
- 核心零部件
- 传感器
- 减速器/伺服
- 软件/算法
- 材料/结构件

初始列表可参考但不限于：鸣志电器、埃斯顿、汇川技术、绿的谐波、三花智控、石头科技、海天瑞声、科大讯飞等。实现时应支持后续维护和调整，避免把概念股范围写死在业务逻辑里。

### 阶段验收

- 后端可启动。
- SQLite数据库和全部表可自动创建。
- 初始股票池可导入并通过API查询。
- API响应包含`data`、`meta`、`error`。
- 测试命令：`pytest tests`。

---

## 阶段 2: MVP数据链路与P0 Provider

**目标**: 先接入AKShare和东方财富两个P0 Provider，打通外部数据获取、Provider统一接口、SQLite写入、缓存读取和同步日志。

### 任务清单

| # | 任务 | 产出文件 | 验证标准 |
|---|------|---------|---------|
| 2.1 | 编写Provider抽象基类 | `backend/data_provider/base.py` | 定义行情、K线、财务、指数统一接口 |
| 2.2 | 编写Provider注册表 | `backend/data_provider/registry.py` | 可按数据类型返回Provider优先级链 |
| 2.3 | 实现AKShare Provider | `backend/data_provider/akshare_provider.py` | 能获取至少一只股票行情和日K数据 |
| 2.4 | 实现东方财富 Provider | `backend/data_provider/eastmoney_provider.py` | 能获取至少一只股票日K或指数数据 |
| 2.5 | 编写FailoverManager基础版 | `backend/data_provider/failover_manager.py` | 第一个Provider失败时自动尝试下一个 |
| 2.6 | 编写同步Service | `backend/services/sync_service.py` | 可触发行情、K线、基础财务同步并写入SQLite |
| 2.7 | 编写行情和K线API | `backend/api/quotes.py`, `backend/api/kline.py` | 前端可读取SQLite中的行情和K线 |
| 2.8 | 编写同步状态API | `backend/api/sync_status.py` | 可返回缺失数据、最近同步时间、失败原因 |
| 2.9 | 编写同步日志写入 | `sync_log` | 成功、失败、降级都有记录 |

### 阶段验收

- 可手动触发同步指定股票的行情和日K。
- 数据成功写入`realtime_quotes`和`kline_data`。
- Provider失败时可切换到备用Provider。
- 所有API失败且SQLite有旧数据时，API返回缓存数据并标记`stale=true`。
- SQLite无数据时，API返回明确的数据缺失清单。

---

## 阶段 3: 前端基础框架与MVP页面

**目标**: 搭建Vue 3前端，优先完成可见闭环：股票列表、产业链筛选、行情摘要、K线图和个股摘要。

### 任务清单

| # | 任务 | 产出文件 | 验证标准 |
|---|------|---------|---------|
| 3.1 | 使用Vite创建Vue 3项目 | `frontend/` | `npm run dev` 启动成功 |
| 3.2 | 安装并配置依赖 | `frontend/package.json` | Element Plus、ECharts、Pinia、axios、NProgress可用 |
| 3.3 | 配置Vite代理 | `frontend/vite.config.ts` | `/api/*` 正确转发到后端 |
| 3.4 | 编写axios封装 | `frontend/src/api/index.ts` | 统一处理`data/meta/error`响应 |
| 3.5 | 编写股票状态Store | `frontend/src/stores/stockStore.ts` | 管理股票列表、当前股票、加载状态 |
| 3.6 | 编写基础共享组件 | `StockTable`, `MetricCard`, `IndustryTag`, `SourceBadge` | 可展示数据、来源和更新时间 |
| 3.7 | 编写K线组件基础版 | `frontend/src/components/KLineChart.vue` | 可展示日K和成交量 |
| 3.8 | 编写MVP页面 | `IndustryOverview.vue`, `StockDetail.vue` | 可筛选产业链、选择股票、查看摘要和K线 |
| 3.9 | 编写数据状态面板 | `DataStatusPanel.vue` | 缺失数据时提示同步、上传或录入入口 |

### 阶段验收

- 前端可启动并连接后端。
- 股票列表可展示、筛选、排序。
- 点击股票可查看个股摘要和K线。
- 页面展示数据来源、更新时间和缓存状态。
- 缺失数据时有明确提示，不出现空白页。

---

## 阶段 4: 四大Tab、基本面和技术分析

**目标**: 完成核心仪表板，覆盖产业链总览、基本面深度分析、技术面分析和个股深度档案四大模块。

### 任务清单

| # | 任务 | 产出文件 | 验证标准 |
|---|------|---------|---------|
| 4.1 | 编写基本面Service | `backend/services/fundamental_service.py` | 可返回财务摘要、业务分部、费用结构 |
| 4.2 | 编写估值Service | `backend/services/valuation_service.py` | 可返回PE、PB、PEG、市值和历史分位 |
| 4.3 | 编写技术指标Service | `backend/services/technical_service.py` | 可计算MA、MACD、RSI、相对强弱 |
| 4.4 | 编写基本面API | `backend/api/fundamentals.py` | 财务摘要、分部、费用接口可用 |
| 4.5 | 编写估值和技术API | `backend/api/valuation.py`, `backend/api/technical.py` | 图表可直接消费返回结构 |
| 4.6 | 完成产业链总览Tab | `frontend/src/views/IndustryOverview.vue` | 分类卡片、指数走势、涨跌排行、估值对比可渲染 |
| 4.7 | 完成基本面Tab | `frontend/src/views/Fundamental.vue` | 营收趋势、费用结构、业务拆分、净利润瀑布图可渲染 |
| 4.8 | 完成技术面Tab | `frontend/src/views/Technical.vue` | K线、成交量、MA、MACD、RSI、热力图可渲染 |
| 4.9 | 完成个股档案Tab | `frontend/src/views/StockDetail.vue` | 公司信息、产品、财务摘要、同业雷达图、上传入口可渲染 |
| 4.10 | 编写雷达图组件 | `frontend/src/components/RadarChart.vue` | 可比较多只股票多维指标 |

### 阶段验收

- 四大Tab完整可切换。
- 图表在有数据、无数据、加载中、错误四种状态下表现正常。
- 技术指标计算结果有单元测试覆盖。
- 基本面接口按公司级报表、业务分部、费用结构分开返回。

---

## 阶段 5: Provider降级、同步状态和定时任务

**目标**: 完成稳定性能力，包括Provider健康状态、降级熔断、同步进度推送、定时同步和数据来源追踪。

### 任务清单

| # | 任务 | 产出文件 | 验证标准 |
|---|------|---------|---------|
| 5.1 | 完善Provider健康状态 | `provider_health` | 记录连续失败、最近成功、下次探测时间 |
| 5.2 | 完善FailoverManager | `backend/data_provider/failover_manager.py` | 超时10秒、失败3次熔断、30分钟后探测 |
| 5.3 | 编写WebSocket进度推送 | `backend/api/sync_status.py` | `/ws/sync/progress` 可推送同步阶段和Provider名称 |
| 5.4 | 编写前端同步进度组合函数 | `frontend/src/composables/useSyncProgress.ts` | 可实时展示连接、下载、写库、完成状态 |
| 5.5 | 编写APScheduler调度器 | `backend/sync/scheduler.py` | 可注册行情、K线、指数、健康探测任务 |
| 5.6 | 编写定时同步任务 | `backend/sync/sync_tasks.py` | 定时任务可复用阶段2的同步Service |
| 5.7 | 完善SourceBadge | `frontend/src/components/SourceBadge.vue` | 显示来源、更新时间、缓存状态 |
| 5.8 | 编写Provider降级测试 | `tests/` | 模拟Provider失败时自动切换并记录日志 |

### 阶段验收

- 模拟首选Provider失败时，系统可自动切换备用Provider。
- 全部Provider失败时，页面展示缓存数据或缺失提示。
- 同步进度可在前端实时显示。
- 定时任务可启动、执行、记录日志。

---

## 阶段 6: PDF上传、半自动解析和手工录入

**目标**: 完成用户数据补充闭环，支持PDF上传、解析结果待确认、重复检测、字段级错误提示和手工录入。

### 任务清单

| # | 任务 | 产出文件 | 验证标准 |
|---|------|---------|---------|
| 6.1 | 编写导入批次Service | `backend/services/import_service.py` | 可创建、查询、确认、取消导入批次 |
| 6.2 | 编写PDF上传接口 | `backend/api/upload.py` | 上传PDF后生成`import_batches`记录 |
| 6.3 | 编写PDF文本和表格提取 | `backend/importers/pdf_extractor.py` | 可提取页文本和表格候选结果 |
| 6.4 | 编写财报解析器基础版 | `backend/importers/financial_parser.py` | 可识别主要会计数据、财务指标、费用字段 |
| 6.5 | 编写解析校验器 | `backend/importers/validator.py` | 校验数值范围、必填字段、重复报告期 |
| 6.6 | 编写人工确认接口 | `backend/api/imports.py` | 用户确认后写入正式财务表 |
| 6.7 | 编写手工录入接口 | `backend/api/manual.py` | 可录入或覆盖财务摘要、分部、费用数据 |
| 6.8 | 编写上传组件 | `frontend/src/components/UploadPanel.vue` | 拖拽上传、进度、错误详情可显示 |
| 6.9 | 编写手工录入弹窗 | `frontend/src/components/ManualInputModal.vue` | 支持结构化录入和提交 |
| 6.10 | 编写导入确认页面或弹窗 | `frontend/src/components/ImportReviewPanel.vue` | 展示字段差异、来源、覆盖/合并/取消选项 |

### 阶段验收

- PDF上传不会直接覆盖正式数据，必须经过人工确认。
- 重复上传同一公司同一报告期时，系统展示已有数据和新数据差异。
- 解析失败时展示页码、表格、字段和原因。
- 用户可通过手工录入补齐缺失字段。
- 已确认的人工录入数据优先级高于已确认PDF数据和API数据。

---

## 阶段 7: 全量Provider、联调测试与部署

**目标**: 完成最终增强能力，接入8个Provider，完善测试、启动脚本、README、响应式适配和生产部署。

### 任务清单

| # | 任务 | 产出文件 | 验证标准 |
|---|------|---------|---------|
| 7.1 | 实现BaoStock Provider | `backend/data_provider/baostock_provider.py` | 可获取历史K线和复权数据 |
| 7.2 | 实现Tushare Provider | `backend/data_provider/tushare_provider.py` | Token配置存在时可获取财务和估值数据 |
| 7.3 | 实现新浪和腾讯 Provider | 对应Provider文件 | 可作为实时行情备选 |
| 7.4 | 实现同花顺和网易 Provider | 对应Provider文件 | 可作为财务或历史行情备选 |
| 7.5 | 完善PDF复杂解析规则 | `backend/importers/` | 覆盖重点公司年报核心字段 |
| 7.6 | 编写端到端联调测试 | `tests/e2e/` | 首次启动、同步、展示、上传、确认流程可跑通 |
| 7.7 | 编写一键启动脚本 | `start.py` | `python start.py` 可检查依赖、初始化数据库、启动服务 |
| 7.8 | 编写README | `README.md` | 新用户可按步骤安装、配置、启动、同步数据 |
| 7.9 | 完成生产模式托管 | `backend/main.py` | 前端构建后可由FastAPI托管静态文件 |
| 7.10 | 响应式适配 | 前端样式 | 1920x1080和1366x768下均可正常使用 |
| 7.11 | 补充免责声明和配置安全检查 | 前后端 | 页面展示免责声明，日志不记录Token |

### 阶段验收

- 8个Provider全部接入统一接口。
- 端到端流程可完整跑通：首次启动 -> 缺失提示 -> 一键同步 -> 数据展示 -> PDF上传 -> 人工确认 -> 图表更新。
- 一键启动脚本可用。
- README覆盖安装、启动、配置、数据源、PDF上传和常见错误。
- 生产模式可运行。

---

## 依赖关系图

```text
阶段1 脚手架 + DB + 基础API
    ↓
阶段2 P0 Provider + 同步闭环
    ↓
阶段3 前端MVP页面
    ↓
阶段4 四大Tab + 分析计算
    ↓
阶段5 降级 + 定时同步 + 进度推送
    ↓
阶段6 PDF + 手工录入 + 人工确认
    ↓
阶段7 全量Provider + 联调 + 部署
```

阶段4和阶段5可部分并行；阶段6依赖阶段1的数据模型和阶段4的财务展示能力；阶段7必须在核心闭环稳定后进行。

---

## 数据覆盖优先级

实现时必须遵守以下优先级：

1. 已确认的人工录入数据。
2. 已确认的PDF解析数据。
3. API同步数据。
4. 开发环境Mock数据。

Mock数据只允许开发环境使用，生产环境不得将Mock作为兜底展示。

---

## 统一验收标准

每个阶段完成后必须满足：

- 后端单元测试通过：`pytest tests`。
- 前端构建或类型检查通过，具体命令以`package.json`为准。
- 新增API有成功、空数据、失败三类返回验证。
- 新增图表有加载中、有数据、无数据、错误四种状态。
- 涉及数据同步的任务必须写入`sync_log`。
- 涉及Provider调用的任务必须记录数据来源和更新时间。
- 涉及用户上传的任务必须校验文件类型、大小和解析错误。

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 免费API限流、字段变化或封禁 | 数据获取失败 | P0先打通闭环，Provider可插拔，逐步扩展P1/P2/P3，SQLite缓存兜底 |
| PDF财报格式不统一 | 解析精度不稳定 | 先做半自动解析和人工确认，再做重点模板精准解析 |
| 前端图表复杂度高 | 开发周期变长 | 先完成MVP图表，再补复杂图表；ECharts配置组件化复用 |
| 财务数据语义混乱 | 后续分析困难 | 公司级报表、业务分部、费用、估值分表存储 |
| SQLite数据量增长 | 查询变慢 | K线按`code/period/date`建索引，接口分页，基本面按需加载 |
| Token或本地敏感信息泄露 | 安全风险 | 使用`.env`，日志脱敏，README明确配置方式 |
| 股票分析被误解为投资建议 | 合规风险 | 页面和README展示免责声明，避免自动荐股和买卖建议 |

---

## 最终需求覆盖矩阵

| 用户需求 | 覆盖阶段 | 验收方式 |
|----------|----------|----------|
| 产业链股票分类和分析 | MVP/V1 | 股票池覆盖6类，产业链总览Tab可筛选和展示 |
| 基本面深度分析 | V1 | 财务摘要、业务分部、费用结构、净利润拆解图表可用 |
| 技术面分析 | V1 | K线、成交量、MA、MACD、RSI、热力图可用 |
| 个股深度档案 | MVP/V1 | 个股页面展示公司信息、产品、财务、估值和供应链标签 |
| PDF财报上传 | V2 | 上传、解析、待确认、确认写入流程可用 |
| 手工录入缺失数据 | V2 | 手工录入接口和弹窗可用，优先级高于PDF/API |
| 多数据源自动降级 | V1/V3 | FailoverManager、provider_health、sync_log验证通过 |
| 定时同步 | V1 | APScheduler任务可运行并写入日志 |
| 8个Provider全量接入 | V3 | 所有Provider实现统一接口并通过集成验证 |
| 一键运行和部署 | V3 | `python start.py`和生产托管可用 |
