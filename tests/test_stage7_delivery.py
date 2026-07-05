from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_local_delivery_package_files_exist():
    expected_files = [
        "README.md",
        ".env.example",
        ".gitignore",
        "scripts/start_backend.ps1",
        "scripts/start_frontend.ps1",
        "scripts/start_all.ps1",
        "scripts/run_checks.ps1",
    ]
    missing = [file for file in expected_files if not (ROOT / file).exists()]
    assert missing == []


def test_readme_documents_local_operation_commands():
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    required_phrases = [
        "机器人产业分析仪表板",
        "scripts/start_backend.ps1",
        "scripts/start_frontend.ps1",
        "scripts/start_all.ps1",
        "scripts/run_checks.ps1",
        "python -m pytest tests",
        "npm run build",
        "MVP能力边界",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in content]
    assert missing == []


def test_env_example_covers_runtime_settings():
    content = (ROOT / ".env.example").read_text(encoding="utf-8")
    expected_keys = [
        "APP_ENV=development",
        "DATABASE_URL=sqlite+aiosqlite:///",
        "UPLOAD_DIR=",
        "CORS_ORIGINS=",
        "PROVIDER_TIMEOUT_SECONDS=",
        "PROVIDER_FAILURE_THRESHOLD=",
        "PROVIDER_PROBE_INTERVAL_MINUTES=",
    ]
    missing = [key for key in expected_keys if key not in content]
    assert missing == []


def test_gitignore_excludes_local_runtime_artifacts():
    content = (ROOT / ".gitignore").read_text(encoding="utf-8")
    ignored = [
        "data/dashboard.db",
        "data/uploads/*",
        "frontend/dist/",
        "frontend/node_modules/",
        "__pycache__/",
        ".pytest_cache/",
    ]
    missing = [item for item in ignored if item not in content]
    assert missing == []


def test_import_workbench_surfaces_upload_failures():
    content = (ROOT / "frontend" / "src" / "views" / "ImportWorkbench.vue").read_text(encoding="utf-8")
    required_phrases = [
        "catch (err)",
        "ElMessage.error",
        "生成预览失败",
        "PDF文件已选择",
        "预览已生成",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in content]
    assert missing == []


def test_base_data_page_and_concept_discovery_removal_are_wired():
    app_content = (ROOT / "frontend" / "src" / "App.vue").read_text(encoding="utf-8")
    api_content = (ROOT / "frontend" / "src" / "api" / "index.ts").read_text(encoding="utf-8")
    panel_content = (ROOT / "frontend" / "src" / "components" / "DataStatusPanel.vue").read_text(encoding="utf-8")
    base_page = ROOT / "frontend" / "src" / "views" / "BaseData.vue"
    assert base_page.exists()
    assert "基础资料" in app_content
    assert "importBaseDataExcel" in api_content
    assert "upsertBaseDataStock" in api_content
    assert "getBaseDataStocks" in api_content
    assert "增量导入基础资料" in base_page.read_text(encoding="utf-8")
    assert "保存股票" in base_page.read_text(encoding="utf-8")
    assert "discoverConceptSync" not in api_content
    assert "发现并同步全量概念股" not in panel_content
