@echo off
REM Batch wrapper to run PowerShell build script
set ENTRY=streamlit_app.py
set ONEFILE=0
if "%1"=="onefile" set ONEFILE=1
powershell -ExecutionPolicy Bypass -File "%~dp0build_exe.ps1" -EntryScript %ENTRY% @(If %ONEFILE%==1 ( -OneFile ))
echo Build script finished.