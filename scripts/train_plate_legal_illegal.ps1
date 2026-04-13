param(
    [int]$Epochs = 30,
    [int]$ImgSize = 640,
    [int]$Batch = 8,
    [string]$LabelsCsv = "..\dataset\plate_train\cblprd\annotations\pending_labels.csv",
    [string]$ImagesDir = "..\dataset\plate_train\cblprd\images",
    [string]$OutDir = "..\dataset\plate_train\cblprd\yolo_legal",
    [string]$Model = "..\results\training\plate_det_cblprd_auto_cont2\weights\best.pt",
    [string]$RunName = "plate_legal_illegal"
)

Set-Location "$PSScriptRoot\..\pc"
$env:PYTHONPATH = (Get-Location).Path

if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

& ".\.venv\Scripts\python.exe" -m training.prepare_yolo_legal_dataset `
    --labels-csv $LabelsCsv `
    --images-dir $ImagesDir `
    --out-dir $OutDir `
    --val-ratio 0.1

& ".\.venv\Scripts\python.exe" -m training.train_yolo `
    --data "$OutDir\plate_legal_data.yaml" `
    --model $Model `
    --epochs $Epochs `
    --imgsz $ImgSize `
    --batch $Batch `
    --project "..\results\training" `
    --name $RunName
