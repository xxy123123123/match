Set-Location "$PSScriptRoot\..\pc"

if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt | Out-Null
& ".\.venv\Scripts\python.exe" -m tools.ccpd_autolabel
