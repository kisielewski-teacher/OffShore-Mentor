# PowerShell script to build a distributable exe using PyInstaller
# Usage: run from repository root in an elevated PowerShell:
#   py -m pip install -r requirements.txt
#   .\packaging\build_exe.ps1

param(
    [string]$EntryScript = "launcher.py",
    [string]$DistDir = "dist",
    [string]$BuildDir = "build",
    [switch]$OneFile = $false
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
    "--add-data", "Readme;Readme",
    "--add-data", "Readme_texts;Readme_texts",
    "--add-data", "requirements.txt;.",
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

$pyinstallerArgs += @(
    "--name", "OffShoreMentor",
    $EntryScript
)

Write-Host "Running pyinstaller with args: $pyinstallerArgs"
pyinstaller @pyinstallerArgs

Write-Host "Build finished. See the $DistDir folder for output."