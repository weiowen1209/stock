$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$BackendScript = Join-Path $Root "scripts/start_backend.ps1"
$FrontendScript = Join-Path $Root "scripts/start_frontend.ps1"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $BackendScript
)

Start-Sleep -Seconds 3

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $FrontendScript
)

Write-Host "后端窗口已启动：http://127.0.0.1:8000"
Write-Host "前端窗口已启动：http://127.0.0.1:5173"
Write-Host "如果浏览器没有自动打开，请等待前端编译完成后访问 http://127.0.0.1:5173"
Start-Process "http://127.0.0.1:5173"
