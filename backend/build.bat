@echo off
REM Build Python backend into standalone .exe using PyInstaller
setlocal

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

set VENV=%SCRIPT_DIR%.venv
set OUTPUT_DIR=%SCRIPT_DIR%..\src-tauri\binaries

if not exist "%VENV%\Scripts\activate.bat" (
    echo ERROR: venv not found. Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

call "%VENV%\Scripts\activate.bat"

REM Ensure Rust is on PATH (Rustup default install location)
set PATH=%USERPROFILE%\.cargo\bin;%PATH%

REM Get target triple for binary naming
for /f "tokens=*" %%i in ('rustc --print host-tuple 2^>nul') do set TARGET_TRIPLE=%%i
if "%TARGET_TRIPLE%"=="" (
    echo ERROR: rustc not found or returned empty target triple.
    echo Ensure Rust is installed and rustup is on PATH before running this script.
    exit /b 1
)
echo Building for target: %TARGET_TRIPLE%

pyinstaller api-server.spec --distpath "%OUTPUT_DIR%" --clean

if %ERRORLEVEL% neq 0 (
    echo Build failed!
    exit /b 1
)

REM Kill any running sidecar so the file is not locked during rename
taskkill /f /im "api-server-%TARGET_TRIPLE%.exe" >nul 2>&1
taskkill /f /im "api-server.exe" >nul 2>&1

REM Delete existing target so move never hits "Access is denied"
if exist "%OUTPUT_DIR%\api-server-%TARGET_TRIPLE%.exe" (
    del /f "%OUTPUT_DIR%\api-server-%TARGET_TRIPLE%.exe"
)

REM Rename to include target triple
if exist "%OUTPUT_DIR%\api-server.exe" (
    move "%OUTPUT_DIR%\api-server.exe" "%OUTPUT_DIR%\api-server-%TARGET_TRIPLE%.exe"
    echo Binary: %OUTPUT_DIR%\api-server-%TARGET_TRIPLE%.exe
)

echo Build complete!
