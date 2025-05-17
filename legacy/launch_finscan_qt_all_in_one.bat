@echo off
REM FinScan Qt Launcher - All-in-one version
REM This batch file launches the all-in-one FinScan Qt application

echo Starting FinScan Qt All-in-One...
echo.

REM Set UTF-8 encoding for console
chcp 65001 >nul

REM Set environment variables to avoid Qt WebEngine cache errors
set QTWEBENGINE_DISABLE_SANDBOX=1
set QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu
set PYTHONIOENCODING=utf-8

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python not found in PATH.
    echo Please install Python and ensure it is in your PATH.
    pause
    exit /b 1
)

REM Check if the script exists
if not exist "%~dp0finscan_qt_all_in_one.py" (
    echo Error: finscan_qt_all_in_one.py not found in the current directory.
    pause
    exit /b 1
)

REM Clear previous Qt WebEngine cache
if exist "%LOCALAPPDATA%\python3\QtWebEngine" (
    echo Clearing previous Qt WebEngine cache...
    rd /s /q "%LOCALAPPDATA%\python3\QtWebEngine" >nul 2>nul
)

REM Launch the application
echo Launching application...
python "%~dp0finscan_qt_all_in_one.py"

REM Handle any errors
if %ERRORLEVEL% neq 0 (
    echo.
    echo FinScan Qt failed to start correctly.
    echo See the error messages above for details.
    pause
)
