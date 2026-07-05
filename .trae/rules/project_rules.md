# 项目开发规则

## 文档先行

以后所有代码改动都必须先修改开发文档，再修改代码。

适用范围：

- 前端页面改动
- 前端组件改动
- API字段改动
- 交互行为改动
- 错误提示改动
- 后端接口行为改动
- 测试要求改动

执行顺序：

1. 先阅读 `doc/frontend-pages.md`。
2. 定位受影响的 `doc/pages/*.md` 页面或组件文档。
3. 先更新文档中的目标、布局、数据依赖、交互、错误状态、修改规则或验证要求。
4. 文档更新完成后，才能修改代码。
5. 修改代码后运行相关测试和构建。
6. 最终回复必须说明改了哪些文档和哪些代码。

如果改动没有对应文档，必须先创建文档。

## 验证命令

后端改动后运行：

```powershell
python -m pytest tests
```

前端改动后运行：

```powershell
cd frontend
npm run build
```

交付包或文档规则改动后运行：

```powershell
python -m pytest tests/test_documentation_contract.py
```
