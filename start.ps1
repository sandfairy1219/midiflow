# MidiFlow 개발 서버 한번에 실행
# 사용법: .\start.ps1

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $projectRoot) { $projectRoot = $PWD }

Write-Host "Starting MidiFlow backend + frontend..." -ForegroundColor Cyan
Write-Host "Project root: $projectRoot" -ForegroundColor Gray

$backendCmd = "cd `"$projectRoot`"; .venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
$frontendCmd = "cd `"$projectRoot\frontend`"; npm run dev"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal

Write-Host ""
Write-Host "Backend: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Two PowerShell windows have been opened. Close them to stop the servers." -ForegroundColor Yellow
