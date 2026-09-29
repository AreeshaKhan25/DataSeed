# Run every test. Green here means the whole demo path works.
$ErrorActionPreference = "Stop"

python scripts/smoke_test.py;    if ($LASTEXITCODE -ne 0) { exit 1 }   # engine guarantees
python scripts/api_test.py;      if ($LASTEXITCODE -ne 0) { exit 1 }   # every route
python scripts/ai_test.py;       if ($LASTEXITCODE -ne 0) { exit 1 }   # AI with no credential
python scripts/provider_test.py; if ($LASTEXITCODE -ne 0) { exit 1 }   # the Mistral adapter

Push-Location frontend
npx tsc -b --pretty false; if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location

Write-Host "`n200 checks + typecheck passed." -ForegroundColor Green
Write-Host "To exercise a live model as well: python scripts/mistral_test.py" -ForegroundColor DarkGray
