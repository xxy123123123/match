param(
    [string]$Source = "D:\CBLPRD-330k",
    [string]$ProjectRoot = "d:\文档\match"
)

$ErrorActionPreference = "Stop"

$pcDir = Join-Path $ProjectRoot "pc"
$python = Join-Path $pcDir ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Python venv not found: $python"
}

Set-Location $pcDir
$env:PYTHONPATH = $pcDir

# 1) Import new source images into isolated cblprd dataset
& $python -m tools.dataset_import `
    --src $Source `
    --dst "..\dataset\plate_train\cblprd\images" `
    --pending-csv "..\dataset\plate_train\cblprd\annotations\pending_labels.csv" `
    --mapping-csv "..\dataset\plate_train\cblprd\annotations\import_mapping.csv" `
    --start-idx 1

Write-Host "[OK] CBLPRD pre-import finished."
Write-Host "Next step when labels ready: run prepare_yolo_dataset and then train_yolo."
