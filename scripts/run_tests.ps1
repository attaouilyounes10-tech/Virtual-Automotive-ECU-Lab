# Run all backend tests
# Run from the project root: .\scripts\run_tests.ps1

$ErrorActionPreference = "Stop"

Write-Host "Running VAEC backend test suite" -ForegroundColor Cyan

# Activate venv if present
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . ".venv\Scripts\Activate.ps1"
}

pytest backend/tests/ -v --tb=short --cov=backend/app --cov-report=term-missing
