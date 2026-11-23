param(
    [switch]$RequireInstaller
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "[1/3] Running PyInstaller (Windows x64)..."
python -m PyInstaller --clean --noconfirm "$RootDir\packaging\lng_simulator.spec"

$BundleDir = Join-Path $RootDir "dist\LNG Simulator"
$ExePath = Join-Path $BundleDir "LNG Simulator.exe"
if (-not (Test-Path $ExePath)) {
    throw "Expected executable not found at $ExePath"
}

Write-Host "[2/3] Creating portable ZIP package..."
$ZipPath = Join-Path $RootDir "dist\LNG-Simulator-Windows-x64-portable.zip"
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path $BundleDir -DestinationPath $ZipPath -CompressionLevel Optimal
Write-Host "Portable ZIP created: $ZipPath"

Write-Host "[3/3] Building Inno Setup installer (Setup.exe)..."
$Iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $Iscc) {
    $Candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $Iscc = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $Iscc) {
    if ($RequireInstaller) {
        throw "Inno Setup 6 (ISCC.exe) is required but was not found."
    }
    Write-Warning "ISCC.exe not found; skipping Setup.exe creation."
    exit 0
}

& $Iscc "$RootDir\packaging\windows_installer.iss"
if ($LASTEXITCODE -ne 0) {
    throw "ISCC.exe failed with exit code $LASTEXITCODE"
}

$SetupExe = Join-Path $RootDir "dist\LNG-Simulator-Setup-x64.exe"
if (-not (Test-Path $SetupExe)) {
    throw "Expected installer not found at $SetupExe"
}
Write-Host "Installer created: $SetupExe"
