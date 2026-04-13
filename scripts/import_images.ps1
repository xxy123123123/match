param(
    [Parameter(Mandatory = $true)]
    [string]$Src,
    [int]$StartIdx
)

Set-Location "$PSScriptRoot\..\pc"

if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt | Out-Null

$argsList = @(
    "-m", "tools.dataset_import",
    "--src", $Src
)

if ($PSBoundParameters.ContainsKey("StartIdx")) {
    $argsList += @("--start-idx", "$StartIdx")
}

& ".\.venv\Scripts\python.exe" @argsList
