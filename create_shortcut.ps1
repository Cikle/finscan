$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$Home\Desktop\FinScan.lnk")
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$Shortcut.TargetPath = "$ScriptPath\FinScan.bat"
$Shortcut.IconLocation = "$ScriptPath\finscan.ico"
$Shortcut.Description = "FinScan Qt - Stock Data Analysis Tool"
$Shortcut.WorkingDirectory = $ScriptPath
$Shortcut.WindowStyle = 1
$Shortcut.Save()
