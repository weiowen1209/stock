from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_frontend_page_docs_exist_for_current_pages():
    expected = [
        "doc/frontend-pages.md",
        "doc/pages/app-shell.md",
        "doc/pages/base-data.md",
        "doc/pages/industry-overview.md",
        "doc/pages/fundamental.md",
        "doc/pages/technical.md",
        "doc/pages/stock-detail.md",
        "doc/pages/import-workbench.md",
        "doc/pages/shared-components.md",
    ]
    missing = [path for path in expected if not (ROOT / path).exists()]
    assert missing == []


def test_page_docs_reference_vue_files_and_required_sections():
    docs = {
        "doc/pages/app-shell.md": "frontend/src/App.vue",
        "doc/pages/base-data.md": "frontend/src/views/BaseData.vue",
        "doc/pages/industry-overview.md": "frontend/src/views/IndustryOverview.vue",
        "doc/pages/fundamental.md": "frontend/src/views/Fundamental.vue",
        "doc/pages/technical.md": "frontend/src/views/Technical.vue",
        "doc/pages/stock-detail.md": "frontend/src/views/StockDetail.vue",
        "doc/pages/import-workbench.md": "frontend/src/views/ImportWorkbench.vue",
    }
    required_sections = ["## 对应代码", "## 页面目标", "## 布局结构", "## 数据依赖", "## 用户交互", "## 错误和空状态", "## 修改规则", "## 验证要求"]
    failures = []
    for doc_path, vue_path in docs.items():
        content = (ROOT / doc_path).read_text(encoding="utf-8")
        if vue_path not in content:
            failures.append(f"{doc_path} missing {vue_path}")
        for section in required_sections:
            if section not in content:
                failures.append(f"{doc_path} missing {section}")
    assert failures == []


def test_project_rules_enforce_docs_first_workflow():
    content = (ROOT / ".trae" / "rules" / "project_rules.md").read_text(encoding="utf-8")
    required_phrases = [
        "以后所有代码改动都必须先修改开发文档，再修改代码",
        "doc/frontend-pages.md",
        "doc/pages/*.md",
        "python -m pytest tests/test_documentation_contract.py",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in content]
    assert missing == []
