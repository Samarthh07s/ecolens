@echo off
REM ==========================================================================
REM  EcoLens - one-click launcher for Windows
REM  1) finds a supported Python  2) creates "venv" if missing
REM  3) installs requirements     4) starts the app and opens your browser
REM ==========================================================================
setlocal EnableExtensions
title EcoLens - AI Environmental Analyzer
cd /d "%~dp0"

echo.
echo  =====================================================
echo    EcoLens - AI Environmental Analyzer
echo  =====================================================
echo.

REM --- Refuse to run from inside a ZIP / WinRAR temporary folder -------------
echo "%~dp0" | findstr /i /c:"Rar$" /c:"Temp1_EcoLens" >nul
if not errorlevel 1 (
    echo  [ERROR] You are running EcoLens from inside the ZIP file.
    echo          Close this window, right-click EcoLens.zip,
    echo          choose "Extract to EcoLens\", open the extracted folder
    echo          and double-click run.bat there.
    echo.
    pause
    exit /b 1
)

REM --- Step 1: find Python (prefer the "py" launcher with a supported version) ---
set "PY="
for %%V in (3.13 3.12 3.14 3.11) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,14) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo  [ERROR] Python 3.11 - 3.14 was not found.
    echo.
    echo  Install Python 3.13 from https://www.python.org/downloads/
    echo  and TICK "Add python.exe to PATH" on the first installer screen.
    echo  Then close this window and double-click run.bat again.
    echo.
    where python >nul 2>&1 && (echo  Found this Python, but its version is not supported: & python --version)
    echo.
    pause
    exit /b 1
)
echo  [1/4] Using Python:
%PY% --version

REM --- Step 2: virtual environment --------------------------------------------
if exist "venv\Scripts\python.exe" (
    echo  [2/4] Virtual environment found - reusing it.
) else (
    echo  [2/4] Creating virtual environment in "venv" ^(first run only^)...
    %PY% -m venv venv
    if errorlevel 1 goto :fail
)

REM --- Step 3: install packages -----------------------------------------------
echo  [3/4] Installing / checking packages ^(first run takes 1-3 minutes^)...
"venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo.
    echo  [ERROR] Package installation failed. Check your internet connection.
    echo          If it keeps failing, delete the "venv" folder and run again.
    goto :fail
)

REM --- Step 4: start the app + open the browser after a short delay -----------
echo  [4/4] Starting EcoLens at http://127.0.0.1:5000
echo        Keep this window OPEN while you use the app. Press CTRL+C to stop.
echo.
start "" /min cmd /c "timeout /t 3 /nobreak >nul & start "" http://127.0.0.1:5000"
"venv\Scripts\python.exe" app.py
echo.
echo  EcoLens has stopped.
pause
exit /b 0

:fail
echo.
echo  Something went wrong. Read the message above, then press any key to close.
pause
exit /b 1
