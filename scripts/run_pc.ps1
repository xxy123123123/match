param(
    [string]$Config = "pc/config/default.yaml",
    [string]$Source = "virtual",
    [switch]$Show
)

Set-Location "$PSScriptRoot\..\pc"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$showArg = ""
if ($Show) {
    $showArg = "--show"
}

python -m app.main --config $Config --source $Source $showArg
