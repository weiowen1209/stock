# 机器人产业分析仪表板

这是一个面向人形机器人产业链研究的本地化股票分析仪表板。系统以 FastAPI、SQLite 和 Vue 3 为核心，覆盖股票池、实时行情、K线、基本面、估值、技术指标、同步状态、PDF/文本导入和手工确认入库。

## 当前能力

- 股票池与产业链分类展示
- 东方财富行情和K线数据同步
- Provider健康状态、失败降级和同步日志
- APScheduler本地定时任务
- WebSocket同步进度推送
- 基本面、估值、MA、MACD、RSI分析图表
- PDF/文本上传预览、手工录入、人工确认入库
- Vue 3前端仪表板和导入工作台

## 目录结构

```text
backend/                 FastAPI后端、数据模型、Provider、同步和导入服务
backend/api/             HTTP API和WebSocket入口
backend/data_provider/   行情/K线Provider抽象与实现
backend/sync/            定时任务和同步进度广播
backend/init_data/       初始股票池和样例分析数据
frontend/                Vue 3 + Vite前端
frontend/src/views/      产业链、基本面、技术面、导入工作台页面
data/                    本地SQLite数据库和上传文件目录
scripts/                 本地启动和检查脚本
tests/                   阶段1-7后端和交付包测试
doc/                     设计文档和实施计划
```

## 环境要求

- Windows PowerShell
- Python 3.12+，当前开发环境使用 Python 3.14
- Node.js 20+
- npm

## 首次配置

复制环境模板：

```powershell
Copy-Item .env.example .env
```

安装后端依赖：

```powershell
python -m pip install -r requirements.txt
```

安装前端依赖：

```powershell
Set-Location frontend
npm install
Set-Location ..
```

## 本地启动

一键启动前后端：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_all.ps1
```

该脚本会打开两个新的 PowerShell 窗口，分别运行后端和前端，并尝试打开前端页面。

后端默认地址：

```text
http://127.0.0.1:8000
```

前端默认地址：

```text
http://127.0.0.1:5173
```

如果需要分别启动，也可以手动执行后端：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_backend.ps1
```

再启动前端：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_frontend.ps1
```

## 验证命令

单独验证后端：

```powershell
python -m pytest tests
```

单独验证前端：

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

一键检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_checks.ps1
```

## 关键API

- `GET /api/stocks`
- `GET /api/stocks/by-industry`
- `GET /api/quotes`
- `GET /api/kline/{code}`
- `POST /api/sync/trigger`
- `GET /api/sync/status`
- `WebSocket /api/sync/progress`
- `GET /api/fundamentals/{code}`
- `GET /api/valuation/{code}`
- `GET /api/technical/{code}`
- `POST /api/imports/upload`
- `POST /api/imports/manual`
- `POST /api/imports/{batch_id}/confirm`

## 数据目录

- `data/dashboard.db` 是本地SQLite数据库，启动后端时会自动初始化。
- `data/uploads/` 用于保存导入文件。
- 这些文件属于本地运行数据，不建议提交到版本库。

## MVP能力边界

- 当前系统是本地研究和演示用途的MVP，不是完整生产级部署方案。
- SQLite适合本地单用户使用，暂未提供多用户权限、审计回滚和生产数据库迁移。
- PDF解析目前偏向文本型PDF、TXT、CSV等可解码内容；扫描版PDF、OCR和复杂表格解析还需要后续扩展。
- AKShare Provider当前保留接口入口，实际行情/K线链路以东方财富实现为主。
- 前端构建可能出现Vite/Rolldown关于第三方注释和chunk体积的warning，不影响当前运行。

## 常见问题

### 后端启动失败

先确认依赖已安装：

```powershell
python -m pip install -r requirements.txt
```

再运行：

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 前端无法访问API

确认后端运行在 `http://127.0.0.1:8000`，Vite代理配置位于 `frontend/vite.config.ts`。

### 数据为空

后端启动时会初始化股票池和样例分析数据。行情/K线可在前端点击“同步当前股票”，或调用：

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/sync/trigger -ContentType application/json -Body '{"codes":["688017"],"include_quotes":true,"include_kline":true,"period":"day"}'
```
