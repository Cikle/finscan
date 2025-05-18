@echo off
REM FinScan Qt Installer
REM This script sets up FinScan Qt with proper icons and shortcuts

echo ===================================
echo FinScan Qt Installation
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
echo Checking and installing required Python packages...
python -m pip install -r requirements.txt

REM Make a copy of launch_finscan.bat to FinScan.bat for compatibility
echo Creating launcher file...
copy /Y "%~dp0launch_finscan.bat" "%~dp0FinScan.bat" >nul

REM Create shortcuts
echo.
echo Creating program shortcuts with icon...

REM Create a temporary VBScript to create the desktop shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\FinScan Qt.lnk" >> "%TEMP%\CreateShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
echo oLink.TargetPath = "%~dp0launch_finscan.bat" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.IconLocation = "%~dp0finscan.ico" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Description = "FinScan Qt - Stock Data Analysis Tool" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WorkingDirectory = "%~dp0" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"

REM Execute the script
cscript //nologo "%TEMP%\CreateShortcut.vbs"
if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Desktop shortcut created successfully!
) else (
    echo [WARNING] Could not create desktop shortcut. You may need administrator privileges.
)

REM Delete the temporary script
del "%TEMP%\CreateShortcut.vbs" >nul 2>nul

REM Create the Start Menu folder and shortcut if possible
echo Creating Start Menu shortcut...
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\FinScan Qt
if not exist "%STARTMENU%" mkdir "%STARTMENU%" >nul 2>nul

REM Create a temporary VBScript to create the start menu shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateStartShortcut.vbs"
echo sLinkFile = "%STARTMENU%\FinScan Qt.lnk" >> "%TEMP%\CreateStartShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.TargetPath = "%~dp0launch_finscan.bat" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.IconLocation = "%~dp0finscan.ico" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.Description = "FinScan Qt - Stock Data Analysis Tool" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.WorkingDirectory = "%~dp0" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateStartShortcut.vbs"

REM Execute the script
cscript //nologo "%TEMP%\CreateStartShortcut.vbs" >nul 2>nul
del "%TEMP%\CreateStartShortcut.vbs" >nul 2>nul

REM Create uninstall script if it doesn't exist
if not exist "%~dp0uninstall_finscan.bat" (
    echo Creating uninstall script...
    echo @echo off > "%~dp0uninstall_finscan.bat"
    echo REM FinScan Qt Uninstaller >> "%~dp0uninstall_finscan.bat"
    echo echo ================================== >> "%~dp0uninstall_finscan.bat"
    echo echo FinScan Qt Uninstaller >> "%~dp0uninstall_finscan.bat"
    echo echo ================================== >> "%~dp0uninstall_finscan.bat"
    echo echo. >> "%~dp0uninstall_finscan.bat"
    echo echo Removing shortcuts... >> "%~dp0uninstall_finscan.bat"
    echo del /q /f "%USERPROFILE%\Desktop\FinScan Qt.lnk" ^>nul 2^>nul >> "%~dp0uninstall_finscan.bat"
    echo rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\FinScan Qt" ^>nul 2^>nul >> "%~dp0uninstall_finscan.bat"
    echo echo. >> "%~dp0uninstall_finscan.bat"
    echo echo Uninstall completed! >> "%~dp0uninstall_finscan.bat"
    echo echo. >> "%~dp0uninstall_finscan.bat"
    echo echo Note: The application files remain in the folder. >> "%~dp0uninstall_finscan.bat"
    echo echo You can safely delete them manually if desired. >> "%~dp0uninstall_finscan.bat"
    echo echo. >> "%~dp0uninstall_finscan.bat"
    echo pause >> "%~dp0uninstall_finscan.bat"
)

REM Create update script if it doesn't exist
if not exist "%~dp0update_finscan.bat" (
    echo Creating update script...
    echo @echo off > "%~dp0update_finscan.bat"
    echo REM FinScan Qt Update Helper >> "%~dp0update_finscan.bat"
    echo echo ================================== >> "%~dp0update_finscan.bat"
    echo echo FinScan Qt Update Helper >> "%~dp0update_finscan.bat"
    echo echo ================================== >> "%~dp0update_finscan.bat"
    echo echo. >> "%~dp0update_finscan.bat"
    echo echo Updating Python dependencies... >> "%~dp0update_finscan.bat"
    echo python -m pip install -r requirements.txt --upgrade >> "%~dp0update_finscan.bat"
    echo echo. >> "%~dp0update_finscan.bat"
    echo echo Clearing Qt WebEngine cache... >> "%~dp0update_finscan.bat"
    echo if exist "%%LOCALAPPDATA%%\python3\QtWebEngine" ( >> "%~dp0update_finscan.bat"
    echo     rd /s /q "%%LOCALAPPDATA%%\python3\QtWebEngine" ^>nul 2^>nul >> "%~dp0update_finscan.bat"
    echo ) >> "%~dp0update_finscan.bat"
    echo echo. >> "%~dp0update_finscan.bat"
    echo echo Update completed! >> "%~dp0update_finscan.bat"
    echo echo. >> "%~dp0update_finscan.bat"
    echo echo Would you like to run FinScan Qt now? (Y/N) >> "%~dp0update_finscan.bat"
    echo choice /c YN /n >> "%~dp0update_finscan.bat"
    echo if %%ERRORLEVEL%% equ 1 ( >> "%~dp0update_finscan.bat"
    echo     start "" "%%~dp0launch_finscan.bat" >> "%~dp0update_finscan.bat"
    echo ) >> "%~dp0update_finscan.bat"
    echo echo. >> "%~dp0update_finscan.bat"
    echo pause >> "%~dp0update_finscan.bat"
)

echo.
echo ===================================
echo Installation completed!
echo ===================================
echo.
echo You can now run FinScan Qt from:
echo  1. The desktop shortcut "FinScan Qt"
echo  2. The Start Menu under "FinScan Qt"
echo  3. Running launch_finscan.bat directly
echo.
echo To update the application in the future:
echo  - Run update_finscan.bat
echo.
echo Would you like to run FinScan Qt now? (Y/N)
choice /c YN /n
if %ERRORLEVEL% equ 1 (
    start "" "%~dp0launch_finscan.bat"
)

echo.
echo Press any key to exit installer...
pause > nul
