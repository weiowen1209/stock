$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python -m pytest tests

Set-Location (Join-Path $Root "frontend")
npm run build

Set-Location $Root
Write-Host "All checks passed."
