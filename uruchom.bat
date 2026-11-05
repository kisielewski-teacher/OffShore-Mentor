@echo off
rem ============================================================================
rem  OffShore Mentor - uruchomienie calego projektu jednym kliknieciem.
rem
rem  Co robi:
rem    1. znajduje Pythona 3.10+ (launcher "py" lub "python")
rem    2. tworzy wirtualne srodowisko .venv (jesli go nie ma lub jest uszkodzone)
rem    3. sprawdza: pliki projektu, wersje pakietow z requirements.txt,
rem       solver CBC (pulp), importy modulow, zapis do static/ i logs/
rem    4. jesli brakuje pakietow - doinstalowuje je (pip) i sprawdza ponownie
rem    5. sprawdza, czy port nie jest zajety, i uruchamia aplikacje Streamlit
rem
rem  Uzycie:
rem    uruchom.bat           - sprawdzenie zaleznosci i start aplikacji
rem    uruchom.bat test      - sprawdzenie zaleznosci i testy (pytest + ruff)
rem    uruchom.bat sprawdz   - tylko sprawdzenie zaleznosci, bez startu
rem ============================================================================
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title OffShore Mentor

set "TRYB=%~1"
set "PORT=8501"
set "PY_START="
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

echo.
echo === OffShore Mentor: sprawdzanie srodowiska ===
echo.

rem --- 1. Python 3.10+ ---------------------------------------------------------
echo [1/5] Szukam Pythona 3.10+ ...
call :znajdz_pythona
if not defined PY_START (
    echo.
    echo BLAD: nie znaleziono Pythona 3.10 lub nowszego.
    echo Pobierz go z https://www.python.org/downloads/ i przy instalacji zaznacz
    echo "Add python.exe to PATH", a potem uruchom ten plik ponownie.
    goto :koniec_blad
)
echo       znaleziono: %PY_START%

rem --- 2. Wirtualne srodowisko -------------------------------------------------
echo [2/5] Wirtualne srodowisko .venv ...
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo       .venv jest uszkodzone lub ma za stary Python - tworze od nowa
        rmdir /s /q ".venv"
    )
)
if not exist "%VENV_PY%" (
    echo       tworze .venv ...
    %PY_START% -m venv .venv
    if errorlevel 1 (
        echo BLAD: nie udalo sie utworzyc wirtualnego srodowiska.
        goto :koniec_blad
    )
)
echo       OK

rem --- 3. Kontrola zaleznosci --------------------------------------------------
echo [3/5] Kontrola plikow projektu i zaleznosci ...
"%VENV_PY%" sprawdz_zaleznosci.py
set "WYNIK=%ERRORLEVEL%"
if "%WYNIK%"=="2" (
    echo.
    echo BLAD: powyzszych problemow nie da sie naprawic automatycznie.
    goto :koniec_blad
)

rem --- 4. Doinstalowanie brakujacych pakietow ---------------------------------
if "%WYNIK%"=="1" (
    echo [4/5] Instaluje brakujace pakiety z requirements.txt ^(wymaga internetu^) ...
    "%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo.
        echo BLAD: instalacja pakietow nie powiodla sie. Sprawdz polaczenie z internetem.
        goto :koniec_blad
    )
    echo       ponowna kontrola ...
    "%VENV_PY%" sprawdz_zaleznosci.py
    if errorlevel 1 (
        echo.
        echo BLAD: po instalacji nadal sa problemy ^(patrz wyzej^).
        goto :koniec_blad
    )
) else (
    echo [4/5] Wszystkie pakiety na miejscu - instalacja niepotrzebna.
)

if /i "%TRYB%"=="sprawdz" (
    echo.
    echo Sprawdzenie zakonczone powodzeniem.
    goto :koniec_ok
)

rem --- Tryb testowy ------------------------------------------------------------
if /i "%TRYB%"=="test" (
    echo.
    echo === Testy ===
    "%VENV_PY%" -m pip install --disable-pip-version-check -q -r requirements-dev.txt
    if errorlevel 1 (
        echo BLAD: nie udalo sie zainstalowac narzedzi testowych.
        goto :koniec_blad
    )
    "%VENV_PY%" -m ruff check .
    if errorlevel 1 goto :koniec_blad
    "%VENV_PY%" -m pytest -q
    if errorlevel 1 goto :koniec_blad
    echo.
    echo Wszystkie testy przeszly.
    goto :koniec_ok
)

rem --- 5. Start aplikacji ------------------------------------------------------
echo [5/5] Uruchamiam aplikacje ...
rem Port 8501 bywa zajety przez inne aplikacje Streamlit - wybieramy pierwszy wolny.
set "PORT_START=%PORT%"
:szukaj_portu
netstat -ano | findstr /r /c:":%PORT% .*LISTENING" >nul 2>&1
if errorlevel 1 goto :port_wolny
set /a PORT+=1
if %PORT% GTR 8520 goto :brak_portu
goto :szukaj_portu
:brak_portu
echo BLAD: porty %PORT_START%-8520 sa zajete. Zamknij inne aplikacje Streamlit.
goto :koniec_blad
:port_wolny
if not "%PORT%"=="%PORT_START%" echo       port %PORT_START% jest zajety przez inny program - uzywam %PORT%
echo.
echo Aplikacja wystartuje pod adresem http://localhost:%PORT%
echo Aby ja zatrzymac, zamknij to okno lub nacisnij Ctrl+C.
echo.
"%VENV_PY%" -m streamlit run streamlit_app.py --server.port %PORT%
if errorlevel 1 (
    echo.
    echo BLAD: aplikacja zakonczyla sie z bledem.
    goto :koniec_blad
)
goto :koniec_ok

rem ============================================================================
:znajdz_pythona
for %%C in ("py -3" "python") do (
    %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_START=%%~C"
        goto :eof
    )
)
goto :eof

:koniec_blad
echo.
pause
endlocal
exit /b 1

:koniec_ok
endlocal
exit /b 0
