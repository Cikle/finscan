@echo off
REM FinScan Easy Installer
REM This script sets up FinScan with proper icons and shortcuts

echo ===================================
echo FinScan Easy Installation
echo ===================================
echo.

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python and ensure it is in your PATH.
    pause
    exit /b 1
)

REM Check required Python packages
echo Checking required Python packages...
python -m pip install -r requirements.txt

REM Create shortcuts
echo.
echo Creating program shortcut with icon...
echo.

REM Create a temporary VBScript to create the shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\FinScan.lnk" >> "%TEMP%\CreateShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
echo oLink.TargetPath = "%~dp0FinScan.bat" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.IconLocation = "%~dp0finscan.ico" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Description = "FinScan Qt - Stock Data Analysis Tool" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WorkingDirectory = "%~dp0" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"

REM Execute the script
cscript //nologo "%TEMP%\CreateShortcut.vbs"
if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Desktop shortcut created successfully!
) else (
    echo [WARNING] Could not create desktop shortcut.
)

REM Delete the temporary script
del "%TEMP%\CreateShortcut.vbs" >nul 2>nul

REM Create the Start Menu folder and shortcut if possible
echo Creating Start Menu shortcut...
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\FinScan
if not exist "%STARTMENU%" mkdir "%STARTMENU%" >nul 2>nul

REM Create a temporary VBScript to create the start menu shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateStartShortcut.vbs"
echo sLinkFile = "%STARTMENU%\FinScan.lnk" >> "%TEMP%\CreateStartShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.TargetPath = "%~dp0FinScan.bat" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.IconLocation = "%~dp0finscan.ico" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.Description = "FinScan Qt - Stock Data Analysis Tool" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.WorkingDirectory = "%~dp0" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateStartShortcut.vbs"

REM Execute the script
cscript //nologo "%TEMP%\CreateStartShortcut.vbs" >nul 2>nul
del "%TEMP%\CreateStartShortcut.vbs" >nul 2>nul

echo.
echo ===================================
echo Installation completed!
echo ===================================
echo.
echo You can now run FinScan from:
echo  1. The desktop shortcut
echo  2. The Start Menu
echo  3. Running FinScan.bat directly
echo.
echo Would you like to run FinScan now? (Y/N)
choice /c YN /n
if %ERRORLEVEL% equ 1 (
    start "" "%~dp0FinScan.bat"
)

echo.
echo Press any key to exit installer...
pause > nul
