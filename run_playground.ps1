# Aurora AI — Start the backend server
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Aurora AI — Browser Agent Server         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  📦 1. Install the Chrome extension:" -ForegroundColor Yellow
Write-Host "      chrome://extensions → Developer mode → Load unpacked" -ForegroundColor White
Write-Host "      Select: $((Join-Path $PSScriptRoot 'extension'))" -ForegroundColor White
Write-Host ""
Write-Host "  🚀 2. Start the server:" -ForegroundColor Yellow
Write-Host "      http://127.0.0.1:8080" -ForegroundColor White
Write-Host ""

try {
    $env:PYTHONIOENCODING = "utf-8"
    & ".\env\Scripts\python" ".\web\chat_server.py"
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
