# 导入工作台页面开发文档

## 对应代码

- 页面文件：`frontend/src/views/ImportWorkbench.vue`
- API入口：`frontend/src/api/index.ts`
- 类型定义：`frontend/src/api/types.ts`
- 后端接口：`/api/imports/documents`、`/api/imports/documents/upload`、`/api/imports/documents/{document_id}/preview`、`/api/imports/candidate-facts`、`/api/imports/evidence`、`/api/imports/confirmed-facts`

## 页面目标

导入工作台用于财报数据半自动导入闭环。上传财报 PDF 后生成解析预览，同步生成字段来源、证据片段和候选事实；用户复核后确认入库，确认动作写入正式事实库，并继续同步旧财务、业务分部和费用表以兼容现有页面。

## 布局结构

当前采用 A 方向三栏事实复核工作台：

1. 左侧流程导航、上传入口、文档资产库：展示资产入库、事实复核、证据确认流程；提供 PDF 上传入口和股票代码、报告期、来源站点补充字段；列出已保存文档并支持选择文档载入解析预览。
2. 中间候选事实复核队列、风险筛选、财务字段确认编辑区：按事实数据域筛选候选事实，突出冲突、低置信度和覆盖风险；保留结构化财务字段编辑区，确认导入时使用编辑后的预览值。
3. 右侧证据片段、来源信息、覆盖风险、空值不覆盖旧值规则：展示选中候选事实的证据片段、页码、章节、来源标题、信任级别和覆盖风险；明确空值不会覆盖旧值，只有确认后的非空事实参与正式入库或更新。

## 数据依赖

- `uploadFile`：当前选择的 PDF 文件。
- `uploadForm`：上传时补充的股票代码、报告期和来源站点。
- `documents`：文档资产库列表。
- `selectedDocumentId`：当前选中的文档 ID。
- `selectedPreview`：当前文档对应的解析预览。
- `candidateFacts`：当前批次候选事实列表。
- `evidenceItems`：当前批次证据片段列表。
- `selectedCandidate`：当前选中的候选事实。
- `selectedEvidence`：当前候选事实对应的证据片段。
- `factDomainFilter`：候选事实数据域筛选。
- `editableFinancial`：确认导入前可编辑的结构化财务字段。
- `loading` 状态：文档加载、预览加载、候选事实/证据加载、上传提交和确认提交分别维护，避免不同异步流程互相覆盖。

## 用户交互

- 用户选择 PDF 后，上传入口显示文件名并提示提交后进入候选事实复核。
- 点击“保存 PDF 并解析”时，如果没有文件，应提示“请先选择 PDF 文件”。
- PDF 上传成功后，应显示上传摘要，刷新文档资产库，并载入当前批次的解析预览、候选事实和证据片段。
- 选择文档资产库中的文档后，中间栏应载入解析预览和候选事实队列，右侧随选中候选事实展示证据链。
- 候选事实支持按 `fact_type` 数据域筛选，风险样式应优先暴露冲突、低置信度和可能覆盖旧值的事实。
- 确认导入时，使用 `editableFinancial`、业务分部、费用和年报深度字段构造确认 payload；空值字段不覆盖数据库旧值。
- 阶段 1 限制：逐条候选确认、修改、驳回和高可信批量确认当前是提示占位，待候选事实复核接口完成后接入。

## 错误和空状态

- 文档资产库为空时，提示当前没有匹配的 PDF 文档记录。
- 未选择文档时，解析预览区域提示请选择一份文档。
- 当前批次没有候选事实时，提示先上传 PDF 或选择已解析文档。
- 当前候选事实没有匹配证据片段时，右侧证据列表显示空态。
- 文件解析出的字段可能为空，页面显示 `--`，不阻塞预览展示。
- 扫描版 PDF 或结构异常 PDF 可能生成低可信候选事实，应保留证据和风险提示供人工复核。
- 所有异步请求必须有 `catch` 提示，不能静默失败。

## 修改规则

- 修改候选事实或证据字段前，必须同步更新后端 `CandidateFactRead`、`EvidenceItemRead`、前端类型和本文件。
- 修改导入工作台布局前，必须先更新 UI 原型并获得确认。
- 修改确认 payload 或正式事实写入规则前，必须同步更新后端测试和事实流水线文档。
- 修改提示文案前，必须先更新“用户交互”和“错误和空状态”。
- 新增导入字段前，必须同步更新后端解析、事实生成、前端类型、本文件和相关测试。

## 验证要求

本阶段完整验证必须通过：

```powershell
python -m pytest tests/test_fact_pipeline.py tests/test_import_preview_sources.py tests/test_pdf_financial_parser.py tests/test_stage6.py tests/test_stage7_delivery.py -q
Set-Location frontend
npm run build
Set-Location ..
```
