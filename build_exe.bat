@echo off
setlocal EnableExtensions
title Build EcoLens Windows application
cd /d "%~dp0"

echo.
echo  =====================================================
echo    EcoLens - Windows EXE Builder
echo  =====================================================
echo.

set "PY="
for %%V in (3.14 3.13 3.12 3.11) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    echo [ERROR] Python 3.11 - 3.14 was not found.
    pause
    exit /b 1
)

echo [1/4] Installing build dependencies...
%PY% -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :fail
%PY% -m pip install --disable-pip-version-check -q pyinstaller
if errorlevel 1 goto :fail

echo [2/4] Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist EcoLens.spec del /q EcoLens.spec

echo [3/4] Building EcoLens.exe...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name EcoLens ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  app.py
if errorlevel 1 goto :fail

echo [4/4] Preparing portable application folder...
if exist "EcoLens-Desktop" rmdir /s /q "EcoLens-Desktop"
mkdir "EcoLens-Desktop"
copy /y "dist\EcoLens.exe" "EcoLens-Desktop\EcoLens.exe" >nul
copy /y "PROJECT_REPORT.md" "EcoLens-Desktop\PROJECT_REPORT.md" >nul
copy /y "README.md" "EcoLens-Desktop\README.md" >nul

echo.
echo  SUCCESS
echo  Application: %CD%\EcoLens-Desktop\EcoLens.exe
echo.
echo  Double-click EcoLens.exe to start the local dashboard.
echo  The first launch may take a few seconds while the bundled app starts.
echo.
pause
exit /b 0

:fail
echo.
echo  [ERROR] Build failed. Read the message above.
pause
exit /b 1
