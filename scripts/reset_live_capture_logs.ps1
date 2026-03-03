param(
    [string]$RepoRoot = ".",
    [switch]$InstalledOnly
)

$targets = @()

if (-not $InstalledOnly) {
    $root = (Resolve-Path $RepoRoot).Path
    $targets += [pscustomobject]@{
        Name = "repo"
        DebugLog = Join-Path $root "FusionTutorialOverlay.bundle/Contents/debug.log"
        CaptureLog = Join-Path $root "FusionTutorialOverlay.bundle/Contents/live_capture_events.jsonl"
    }
}

$installedRoot = Join-Path $env:APPDATA "Autodesk/Autodesk Fusion 360/API/AddIns/FusionTutorialOverlay.bundle/Contents"
$targets += [pscustomobject]@{
    Name = "installed"
    DebugLog = Join-Path $installedRoot "debug.log"
    CaptureLog = Join-Path $installedRoot "live_capture_events.jsonl"
}

foreach ($t in $targets) {
    if (Test-Path $t.DebugLog) {
        Remove-Item $t.DebugLog -Force
    }
    if (Test-Path $t.CaptureLog) {
        Remove-Item $t.CaptureLog -Force
    }
}

Write-Output "Reset logs:"
foreach ($t in $targets) {
    Write-Output "[$($t.Name)] $($t.DebugLog)"
    Write-Output "[$($t.Name)] $($t.CaptureLog)"
}
