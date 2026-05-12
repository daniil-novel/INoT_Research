param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($Dev) {
    .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
} else {
    .\.venv\Scripts\python.exe -m pip install -e .
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Put OPENROUTER_API_KEY into it before real runs." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Ready. Activate with:" -ForegroundColor Green
Write-Host "  cd $Root"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Smoke test:" -ForegroundColor Green
Write-Host "  python -m inot check"
