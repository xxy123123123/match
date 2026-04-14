param(
    [int]$Frames = 120,
    [string]$ConfigPath = "config/default.yaml"
)

$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Title,
        [scriptblock]$Action
    )
    Write-Output $Title
    & $Action
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Step failed: $Title"
        exit $LASTEXITCODE
    }
}

Set-Location "$PSScriptRoot\..\pc"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:PYTHONPATH = (Get-Location).Path

$resultDir = Resolve-Path "..\results"
$streamPath = "..\dataset\samples\fpga_stream.bin"

Write-Output "[1/6] virtual run"
Run-Step "[1/6] virtual run" { python -m app.main --config $ConfigPath --source virtual }
Write-Output "[2/6] virtual eval"
Run-Step "[2/6] virtual eval" { python -m tools.eval_run_result --csv "..\results\run_result.csv" --out-json "..\results\metrics_virtual.json" }

Write-Output "[3/6] mock tcp run + stream record"
Run-Step "[3/6] mock tcp run + stream record" { powershell -ExecutionPolicy Bypass -File "..\scripts\run_mock_link.ps1" -Frames $Frames -SaveStream $streamPath -ConfigPath $ConfigPath }
Write-Output "[4/6] mock tcp eval"
Run-Step "[4/6] mock tcp eval" { python -m tools.eval_run_result --csv "..\results\run_result.csv" --out-json "..\results\metrics_mock_tcp.json" }

Write-Output "[5/6] replay run"
Run-Step "[5/6] replay run" { python -m app.main --config $ConfigPath --source fpga_replay }
Write-Output "[6/6] replay eval"
Run-Step "[6/6] replay eval" { python -m tools.eval_run_result --csv "..\results\run_result.csv" --out-json "..\results\metrics_replay.json" }

Write-Output "Done. Metrics in $resultDir"
