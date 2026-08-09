param(
    [string]$Venv = ".venv"
)

$ErrorActionPreference = "Stop"
python -m venv $Venv
$python = Join-Path $Venv "Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
Write-Host "Environment ready. Run: $python run_tests.py"
