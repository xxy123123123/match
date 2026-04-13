param(
    [int]$Epochs = 20,
    [int]$ImgSize = 640,
    [int]$Batch = 8
)

Set-Location "$PSScriptRoot\..\pc"

if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

& ".\.venv\Scripts\python.exe" -m training.prepare_yolo_dataset `
    --labels-csv "..\dataset\plate_train\labeled\annotations\ccpd_labels.csv" `
    --images-dir "..\dataset\plate_train\labeled\images" `
    --out-dir "..\dataset\plate_train\yolo" `
    --val-ratio 0.1

& ".\.venv\Scripts\python.exe" -m training.train_yolo `
    --data "..\dataset\plate_train\yolo\plate_data.yaml" `
    --epochs $Epochs `
    --imgsz $ImgSize `
    --batch $Batch `
    --project "..\results\training" `
    --name "plate_det"
