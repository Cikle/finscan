@echo off 
REM FinScan Qt Uninstaller 
echo ================================== 
echo FinScan Qt Uninstaller 
echo ================================== 
echo. 
echo Removing shortcuts... 
del /q /f "C:\Users\Cyril Lutziger\Desktop\FinScan Qt.lnk" >nul 2>nul 
rmdir /s /q "C:\Users\Cyril Lutziger\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\FinScan Qt" >nul 2>nul 
echo. 
echo Uninstall completed! 
echo. 
echo Note: The application files remain in the folder. 
echo You can safely delete them manually if desired. 
echo. 
pause 
