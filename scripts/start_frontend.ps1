# Start the VAEC frontend (Vite dev server)
# Run from the project root: .\scripts\start_frontend.ps1

$ErrorActionPreference = "Stop"

Write-Host "Starting Virtual Automotive ECU Lab — Frontend" -ForegroundColor Cyan

Set-Location frontend

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    npm install
}

Write-Host "Frontend running at http://localhost:5173" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray

npm run dev
