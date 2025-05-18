Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.ExpandEnvironmentStrings("%USERPROFILE%\Desktop\FinScan.lnk")
Set oLink = oWS.CreateShortcut(sLinkFile)

' Get the path of this script
Set fso = CreateObject("Scripting.FileSystemObject")
scriptPath = WScript.ScriptFullName
scriptdir = fso.GetParentFolderName(scriptPath)

' Set the properties of the shortcut
oLink.TargetPath = scriptdir & "\FinScan.bat"
oLink.IconLocation = scriptdir & "\finscan.ico"
oLink.Description = "FinScan Qt - Stock Data Analysis Tool"
oLink.WorkingDirectory = scriptdir
oLink.WindowStyle = 1

' Save the shortcut
oLink.Save
