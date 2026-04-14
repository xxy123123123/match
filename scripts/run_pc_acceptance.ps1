param(
    [int]$Frames = 120,
    [double]$MinContinuity = 0.95,
    [double]$MinRecovery = 0.08,
    [double]$MaxShortTrackRatio = 0.20,
    [string]$YoloConfigPath = "config/default.yaml",
    [string]$ContourConfigPath = "config/default_contour.yaml"
)

Set-Location "$PSScriptRoot\.."

function Run-RegressionWithConfig($configPath, $tag) {
    Write-Output "=== Running regression ($tag) with config: $configPath ==="
    powershell -ExecutionPolicy Bypass -File ".\scripts\run_offline_regression.ps1" -Frames $Frames -ConfigPath $configPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Offline regression failed in mode=$tag"
        exit 1
    }
}

function Read-Metrics($path) {
    if (-not (Test-Path $path)) {
        throw "Metrics file not found: $path"
    }
    $raw = Get-Content $path -Raw -Encoding UTF8
    return $raw | ConvertFrom-Json
}

function Evaluate-CurrentMetrics($tag) {
    $virtual = Read-Metrics ".\results\metrics_virtual.json"
    $mock = Read-Metrics ".\results\metrics_mock_tcp.json"
    $replay = Read-Metrics ".\results\metrics_replay.json"

    function Check-Range($name, $value, $okExpr, $okMsg, $badMsg) {
        if (& $okExpr $value) {
            Write-Host "[PASS][$tag] ${name}: $okMsg"
            return $true
        }
        Write-Host "[FAIL][$tag] ${name}: $badMsg"
        return $false
    }

    $allPass = $true

    $allPass = (Check-Range "virtual.continuity" $virtual.continuity { param($v) $v -ge $MinContinuity } "${virtual.continuity} >= $MinContinuity" "${virtual.continuity} < $MinContinuity") -and $allPass
    $allPass = (Check-Range "virtual.short_track_ratio" $virtual.short_track_ratio { param($v) $v -le $MaxShortTrackRatio } "${virtual.short_track_ratio} <= $MaxShortTrackRatio" "${virtual.short_track_ratio} > $MaxShortTrackRatio") -and $allPass
    $allPass = (Check-Range "mock.continuity" $mock.continuity { param($v) $v -ge $MinContinuity } "${mock.continuity} >= $MinContinuity" "${mock.continuity} < $MinContinuity") -and $allPass
    $allPass = (Check-Range "mock.predict_recovery_rate" $mock.predict_recovery_rate { param($v) $v -ge $MinRecovery } "${mock.predict_recovery_rate} >= $MinRecovery" "${mock.predict_recovery_rate} < $MinRecovery") -and $allPass
    $allPass = (Check-Range "replay.continuity" $replay.continuity { param($v) $v -ge $MinContinuity } "${replay.continuity} >= $MinContinuity" "${replay.continuity} < $MinContinuity") -and $allPass

    # Hard gate: mock/replay must have actual tracked rows.
    $allPass = (Check-Range "mock.rows" $mock.rows { param($v) $v -gt 0 } "${mock.rows} > 0" "${mock.rows} <= 0") -and $allPass
    $allPass = (Check-Range "replay.rows" $replay.rows { param($v) $v -gt 0 } "${replay.rows} > 0" "${replay.rows} <= 0") -and $allPass

    Write-Output ""
    Write-Output "[$tag] Virtual Metrics: $(ConvertTo-Json $virtual -Compress)"
    Write-Output "[$tag] Mock Metrics   : $(ConvertTo-Json $mock -Compress)"
    Write-Output "[$tag] Replay Metrics : $(ConvertTo-Json $replay -Compress)"

    return [PSCustomObject]@{
        Pass = $allPass
        MockRows = [int]$mock.rows
        ReplayRows = [int]$replay.rows
    }
}

# 1) Try YOLO config first.
Run-RegressionWithConfig $YoloConfigPath "yolo"
$yoloEval = Evaluate-CurrentMetrics "yolo"

if ($yoloEval.Pass) {
    Write-Output "PC acceptance gate PASSED (mode=yolo)."
    exit 0
}

# 2) If YOLO fails with empty mock/replay rows, auto-fallback to contour diagnostics.
if ($yoloEval.MockRows -le 0 -or $yoloEval.ReplayRows -le 0) {
    Write-Output "YOLO mode produced empty mock/replay rows. Retrying with contour config..."
    Run-RegressionWithConfig $ContourConfigPath "contour"
    $contourEval = Evaluate-CurrentMetrics "contour"
    if ($contourEval.Pass) {
        Write-Output "PC acceptance gate PASSED (mode=contour fallback)."
        exit 0
    }
}
Write-Error "PC acceptance gate FAILED."
exit 2
exit 0
