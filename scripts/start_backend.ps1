# Start the VAEC backend (FastAPI + Uvicorn)
# Run from the project root: .\scripts\start_backend.ps1

$ErrorActionPreference = "Stop"

Write-Host "Starting Virtual Automotive ECU Lab — Backend" -ForegroundColor Cyan

# Activate venv if present
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . ".venv\Scripts\Activate.ps1"
}

# Install dependencies if needed
if (-not (python -c "import cantools" 2>$null)) {
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host "Backend running at http://localhost:8000" -ForegroundColor Green
Write-Host "Swagger UI      : http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray

uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
