@echo off
REM FinScan Launcher
REM This batch file launches the FinScan Qt application with app icon

echo Starting FinScan Qt...
start "FinScan" /B pythonw "%~dp0finscan.py"
exit
