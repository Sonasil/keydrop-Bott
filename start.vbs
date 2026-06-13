' Key-Drop Monitor - START (terminal penceresi acmadan)
Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

' Bu betigin bulundugu klasor
sDir = oFSO.GetParentFolderName(WScript.ScriptFullName)
oShell.CurrentDirectory = sDir

' pythonw.exe konsol penceresi acmadan calistirir
' 0 = pencere gizli, False = beklemeden devam et
oShell.Run "pythonw """ & sDir & "\src\keydrop_ui.py""", 0, False
