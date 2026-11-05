# PowerShell script to build a distributable exe using PyInstaller
# Usage: run from repository root in an elevated PowerShell:
#   py -m pip install -r requirements.txt
#   .\packaging\build_exe.ps1

param(
    [string]$EntryScript = "launcher.py",
    [string]$DistDir = "dist",
    [string]$BuildDir = "build",
    [switch]$OneFile = $false,
    # Release builds hide the console window (errors go to logs\launcher.log
    # / logs\animation.log and a message box - see launcher.py). Pass
    # -Console for a debug build that keeps a visible console window.
    [switch]$Console = $false,
    # Optional code signing (requires a purchased code-signing certificate).
    # See packaging/README_BUILD.md "Code signing" section for details.
    [string]$CertPath = "",
    [SecureString]$CertPassword = $null,
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

# Clean previous build artifacts
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $DistDir, $BuildDir, "${EntryScript}.spec"

$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--add-data", "assets;assets",
    "--add-data", "streamlit_app.py;.",
    "--add-data", "modules;modules",
    "--add-data", "planner;planner",
    "--add-data", "viz;viz",
    "--add-data", "requirements.txt;.",
    "--add-data", "LICENSE.txt;.",
    "--add-data", "THIRD_PARTY_LICENSES.md;.",
    "--icon", "assets\icon.ico",
    "--version-file", "packaging\version_info.txt",
    "--hidden-import", "PIL",
    "--hidden-import", "pydeck",
    "--hidden-import", "streamlit.web.server"
)

if ($OneFile) {
    $pyinstallerArgs += "--onefile"
}
else {
    $pyinstallerArgs += "--onedir"
}

if ($Console) {
    $pyinstallerArgs += "--console"
}
else {
    $pyinstallerArgs += "--windowed"
}

$pyinstallerArgs += @(
    "--name", "OffShoreMentor",
    $EntryScript
)

Write-Host "Running pyinstaller with args: $pyinstallerArgs"
pyinstaller @pyinstallerArgs

Write-Host "Build finished. See the $DistDir folder for output."

if ($CertPath) {
    $signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if (-not $signtool) {
        Write-Warning "signtool.exe not found on PATH (install the Windows SDK). Skipping code signing."
    }
    elseif (-not (Test-Path $CertPath)) {
        Write-Warning "Certificate file not found at '$CertPath'. Skipping code signing."
    }
    else {
        $exePath = Join-Path $DistDir "OffShoreMentor\OffShoreMentor.exe"
        if ($OneFile) {
            $exePath = Join-Path $DistDir "OffShoreMentor.exe"
        }

        $signArgs = @("sign", "/f", $CertPath, "/fd", "SHA256", "/tr", $TimestampUrl, "/td", "SHA256")
        if ($CertPassword) {
            $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($CertPassword)
            )
            $signArgs += @("/p", $plainPassword)
        }
        $signArgs += $exePath

        Write-Host "Signing $exePath ..."
        & $signtool.Source @signArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Code signing failed (signtool exit code $LASTEXITCODE)."
        }
        else {
            Write-Host "Code signing succeeded."
        }
    }
}
else {
    Write-Host "No -CertPath given: skipping code signing (see packaging/README_BUILD.md)."
}