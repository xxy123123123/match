param(
    [int]$Port = 5600,
    [int]$Frames = 300,
    [string]$SaveStream = "",
    [string]$ConfigPath = "config/default.yaml",
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

$senderCmd = "Set-Location '$PWD'; .\\.venv\\Scripts\\Activate.ps1; python -m tools.fpga_mock_sender --port $Port --frames $Frames"
if ($SaveStream -ne "") {
    $senderCmd += " --save-stream '$SaveStream'"
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", $senderCmd

python -m app.main --config $ConfigPath --source fpga_tcp $showArg
