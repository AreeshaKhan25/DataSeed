# Run every test. Green here means the whole demo path works.
$ErrorActionPreference = "Stop"

if (-not (Test-Path "data/fixtures/healthcare.csv")) {
    Write-Host "Building test fixtures..." -ForegroundColor Cyan
    python scripts/make_test_fixtures.py
}

python tests/test_engine.py;       if ($LASTEXITCODE -ne 0) { exit 1 }   # engine guarantees
python tests/test_api.py;          if ($LASTEXITCODE -ne 0) { exit 1 }   # every route
python tests/test_ai_fallback.py;  if ($LASTEXITCODE -ne 0) { exit 1 }   # AI with no credential
python tests/test_provider.py;     if ($LASTEXITCODE -ne 0) { exit 1 }   # the Mistral adapter
python tests/test_fixtures.py;     if ($LASTEXITCODE -ne 0) { exit 1 }   # data it has never seen
python tests/test_e2e_upload.py;   if ($LASTEXITCODE -ne 0) { exit 1 }   # the path a real user takes

Push-Location frontend
npx tsc -b --pretty false; if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location

Write-Host "`nAll suites passed." -ForegroundColor Green
Write-Host "To exercise a live model as well: python tests/test_ai_live.py" -ForegroundColor DarkGray
