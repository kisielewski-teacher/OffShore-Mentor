@echo off
rem ============================================================================
rem  OffShore Mentor - instalator: pobiera projekt z GitHuba, kopiuje go na
rem  komputer i uruchamia uruchom.bat (ktory doinstaluje zaleznosci).
rem  Ponowne uruchomienie = aktualizacja (zachowuje .venv, logs i static).
rem ============================================================================
setlocal EnableExtensions
chcp 65001 >nul
title OffShore Mentor - instalacja

set "REPO=kisielewski-teacher/OffShore-Mentor"
set "BRANCH=master"
set "DOCEL=%LOCALAPPDATA%\OffShoreMentor"
set "TMP_DIR=%TEMP%\OffShoreMentor_install"
set "ZIP=%TMP_DIR%\projekt.zip"

echo.
echo === OffShore Mentor: instalacja ===
echo Folder docelowy: %DOCEL%
echo.

if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%" || goto :blad

echo [1/3] Pobieranie projektu z GitHuba ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing 'https://github.com/%REPO%/archive/refs/heads/%BRANCH%.zip' -OutFile '%ZIP%'"
if errorlevel 1 (
    echo BLAD: nie udalo sie pobrac projektu. Sprawdz internet; jesli repozytorium
    echo jest prywatne, popros autora o dostep lub o publiczny link.
    goto :blad
)

echo [2/3] Rozpakowywanie i kopiowanie do %DOCEL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%TMP_DIR%\src' -Force"
if errorlevel 1 goto :blad
for /d %%D in ("%TMP_DIR%\src\*") do set "SRC=%%D"
if not exist "%SRC%\uruchom.bat" (
    echo BLAD: w pobranym archiwum brak uruchom.bat.
    goto :blad
)
robocopy "%SRC%" "%DOCEL%" /E /XD .venv logs static /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :blad
if not exist "%DOCEL%\static" robocopy "%SRC%\static" "%DOCEL%\static" /E /NFL /NDL /NJH /NJS /NP >nul
rmdir /s /q "%TMP_DIR%"

echo [3/3] Uruchamianie (instalacja zaleznosci przy pierwszym starcie) ...
call "%DOCEL%\uruchom.bat"
exit /b %errorlevel%

:blad
echo.
echo Instalacja nie powiodla sie.
pause
exit /b 1
