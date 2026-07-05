from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_start_all_script_opens_backend_and_frontend_windows():
    script = ROOT / "scripts" / "start_all.ps1"
    assert script.exists()
    content = script.read_text(encoding="utf-8")
    required_phrases = [
        "Start-Process powershell",
        "scripts/start_backend.ps1",
        "scripts/start_frontend.ps1",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in content]
    assert missing == []
