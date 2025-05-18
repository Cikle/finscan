@echo off
REM FinScan Qt Update Helper
echo ==================================
echo FinScan Qt Update Helper
echo ==================================
echo.

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python and ensure it is in your PATH.
    pause
    exit /b 1
)

echo Checking for application updates...
echo.

REM Add option to check for updates via GitHub if available
if exist ".git" (
    echo Detected Git repository. Checking for remote updates...
    git pull
) else (
    echo This installation is not connected to a Git repository.
    echo Please download the latest version manually if available.
)

echo.
echo Updating Python dependencies...
python -m pip install -r requirements.txt --upgrade

echo.
echo Clearing Qt WebEngine cache...
if exist "%LOCALAPPDATA%\python3\QtWebEngine" (
    rd /s /q "%LOCALAPPDATA%\python3\QtWebEngine" >nul 2>nul
)

echo.
echo Update completed!
echo.
echo Would you like to run FinScan Qt now? (Y/N)
choice /c YN /n
if %ERRORLEVEL% equ 1 (
    start "" "%~dp0launch_finscan.bat"
)
echo.
pause
