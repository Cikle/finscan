@echo off
REM Create a shortcut with the finscan.ico icon

echo Creating FinScan shortcut with icon...

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

REM Delete the temporary script
del "%TEMP%\CreateShortcut.vbs"

echo Shortcut created on your desktop!
echo.
echo Press any key to exit...
pause > nul
