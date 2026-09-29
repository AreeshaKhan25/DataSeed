# Start DataSeed.  Usage:  ./run.ps1
$ErrorActionPreference = "Stop"

if (-not (Test-Path "data/demo/customers.csv")) {
    Write-Host "Generating demo data..." -ForegroundColor Cyan
    python scripts/make_demo_data.py
}

if (-not (Test-Path "web/index.html")) {
    Write-Host "Building the frontend..." -ForegroundColor Cyan
    npm --prefix frontend install
    npm --prefix frontend run build
}

$bindHost = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$bindPort = if ($env:PORT) { $env:PORT } else { "8000" }

Write-Host ""
Write-Host "  App   http://$bindHost`:$bindPort" -ForegroundColor Green
Write-Host "  Docs  http://$bindHost`:$bindPort/docs" -ForegroundColor Green
Write-Host ""

python -m uvicorn api.main:app --host $bindHost --port $bindPort
