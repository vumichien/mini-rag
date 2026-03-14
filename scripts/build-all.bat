@echo off
REM Full build pipeline: Python backend → Tauri bundle → Windows installer
setlocal

set ROOT=%~dp0..

echo ===== Step 1: Build Python backend =====
call "%ROOT%\backend\build.bat"
if %ERRORLEVEL% neq 0 exit /b 1

echo ===== Step 2: Build Tauri + React =====
cd /d "%ROOT%"
npm run tauri build
if %ERRORLEVEL% neq 0 exit /b 1

echo ===== Build complete =====
echo Installer: %ROOT%\src-tauri\target\release\bundle\nsis\
