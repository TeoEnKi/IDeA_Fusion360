$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceBundle = Join-Path $repoRoot "FusionChecklistCapture"
$sourceManifest = Join-Path $sourceBundle "FusionChecklistCapture.manifest"
$sourceEntryPy = Join-Path $sourceBundle "FusionChecklistCapture.py"

$targetRoot = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\AddIns"
$targetBundle = Join-Path $targetRoot "FusionChecklistCapture"
$targetManifest = Join-Path $targetBundle "FusionChecklistCapture.manifest"
$targetEntryPy = Join-Path $targetBundle "FusionChecklistCapture.py"

$requiredSymbols = @(
    "CommandStartingHandler",
    "CommandTerminatedHandler",
    "capture_command_started",
    "capture_command_terminated",
    "_append_raw_event",
    "SESSION.export"
)

function Test-Manifest {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path $Path)) {
        throw "Manifest missing: $Path"
    }

    $raw = Get-Content -Raw -Encoding UTF8 $Path

    $mAutodeskProduct = [regex]::Match($raw, '"autodeskProduct"\s*:\s*"([^"]+)"')
    $mType = [regex]::Match($raw, '"type"\s*:\s*"([^"]+)"')
    $mId = [regex]::Match($raw, '"id"\s*:\s*"([^"]+)"')
    $mVersion = [regex]::Match($raw, '"version"\s*:\s*"([^"]+)"')
    $mSupportedOs = [regex]::Match($raw, '"supportedOS"\s*:\s*"([^"]+)"')

    $autodeskProduct = if ($mAutodeskProduct.Success) { $mAutodeskProduct.Groups[1].Value } else { "" }
    $type = if ($mType.Success) { $mType.Groups[1].Value } else { "" }
    $id = if ($mId.Success) { $mId.Groups[1].Value } else { "" }
    $version = if ($mVersion.Success) { $mVersion.Groups[1].Value } else { "" }
    $supportedOS = if ($mSupportedOs.Success) { $mSupportedOs.Groups[1].Value } else { "" }

    if ($autodeskProduct -ne "Fusion") {
        throw "Manifest invalid 'autodeskProduct' in $Path. Expected 'Fusion', got '$autodeskProduct'."
    }
    if ($type -ne "addin") {
        throw "Manifest invalid 'type' in $Path. Expected 'addin', got '$type'."
    }
    if ([string]::IsNullOrWhiteSpace([string]$id)) {
        throw "Manifest missing non-empty 'id' in $Path."
    }
    if ([string]::IsNullOrWhiteSpace([string]$version)) {
        throw "Manifest missing non-empty 'version' in $Path."
    }
    if ([string]::IsNullOrWhiteSpace([string]$supportedOS)) {
        throw "Manifest missing non-empty 'supportedOS' in $Path."
    }

    return [PSCustomObject]@{
        autodeskProduct = $autodeskProduct
        type = $type
        id = $id
        version = $version
        supportedOS = $supportedOS
    }
}

function Test-EntrySymbols {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string[]]$Symbols
    )

    if (-not (Test-Path $Path)) {
        throw "Entry file missing: $Path"
    }

    foreach ($symbol in $Symbols) {
        $match = Select-String -Path $Path -Pattern $symbol -SimpleMatch
        if (-not $match) {
            throw "Required logging symbol missing in ${Path}: $symbol"
        }
    }
}

if (-not (Test-Path $sourceBundle)) {
    throw "Source bundle not found: $sourceBundle"
}

if (-not (Test-Path $targetRoot)) {
    New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
}

Write-Host "Validating source manifest and capture entrypoint..."
$sourceManifestObj = Test-Manifest -Path $sourceManifest
Test-EntrySymbols -Path $sourceEntryPy -Symbols $requiredSymbols

Write-Host "Deploying checklist add-in..."
Write-Host "Source: $sourceBundle"
Write-Host "Target: $targetBundle"

if (Test-Path $targetBundle) {
    Get-ChildItem -Path $targetBundle -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
    Remove-Item -Path $targetBundle -Recurse -Force
}

Copy-Item -Path $sourceBundle -Destination $targetBundle -Recurse -Force

Write-Host "Validating target manifest and capture entrypoint..."
$targetManifestObj = Test-Manifest -Path $targetManifest
Test-EntrySymbols -Path $targetEntryPy -Symbols $requiredSymbols

$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "Manifest OK: $($targetManifestObj.id) v$($targetManifestObj.version)"
Write-Host "Event logging checks: OK"
Write-Host "Timestamp: $now"
Write-Host "Done."
