# Start Chrome with remote debugging so Aurora AI can control it
$chromePaths = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chrome = $null
foreach ($p in $chromePaths) {
    if (Test-Path $p) { $chrome = $p; break }
}

if (-not $chrome) {
    Write-Host "Chrome not found. Please install Chrome or specify the path manually." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Chrome with remote debugging (port 9222)..." -ForegroundColor Cyan
Write-Host "Keep this Chrome window open while using Aurora AI.`n" -ForegroundColor Yellow

$args = @(
    "--remote-debugging-port=9222"
    "--no-first-run"
)

Start-Process -FilePath $chrome -ArgumentList $args
Start-Sleep -Seconds 2
Write-Host "Chrome is ready! Now run: .\run_playground.ps1" -ForegroundColor Green
