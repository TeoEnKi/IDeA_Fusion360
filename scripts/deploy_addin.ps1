$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceBundle = Join-Path $repoRoot "FusionTutorialOverlay.bundle"
$targetRoot = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\AddIns"
$targetBundle = Join-Path $targetRoot "FusionTutorialOverlay.bundle"
$targetPy = Join-Path $targetBundle "Contents\FusionTutorialOverlay.py"

if (-not (Test-Path $sourceBundle)) {
    throw "Source bundle not found: $sourceBundle"
}

if (-not (Test-Path $targetRoot)) {
    New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
}

Write-Host "Deploying add-in bundle..."
Write-Host "Source: $sourceBundle"
Write-Host "Target: $targetBundle"

if (Test-Path $targetBundle) {
    Get-ChildItem -Path $targetBundle -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
    Remove-Item -Path $targetBundle -Recurse -Force
}

Copy-Item -Path $sourceBundle -Destination $targetBundle -Recurse -Force

$buildStamp = "unknown"
if (Test-Path $targetPy) {
    $match = Select-String -Path $targetPy -Pattern 'BUILD_STAMP\s*=\s*"([^"]+)"' -AllMatches
    if ($match -and $match.Matches.Count -gt 0) {
        $buildStamp = $match.Matches[0].Groups[1].Value
    }
}

$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "Deployed build stamp: $buildStamp"
Write-Host "Timestamp: $now"
Write-Host "Done."
