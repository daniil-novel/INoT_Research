param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1"
}

& $Python -m inot @Args
