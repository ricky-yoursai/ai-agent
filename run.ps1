# 启动 AI Agent (自动从 .env 加载配置)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $scriptDir "env\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[错误] 未找到虚拟环境: $venvPython" -ForegroundColor Red
    Write-Host "请先运行: python -m venv env && pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Set-Location $scriptDir
& $venvPython -m src
