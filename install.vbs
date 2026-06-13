' Key-Drop Monitor - SETUP (tek seferlik kurulum)
' Kurulum islemini gizli calistirir ve bitince bilgi verir.
Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

sDir = oFSO.GetParentFolderName(WScript.ScriptFullName)
oShell.CurrentDirectory = sDir

MsgBox "Kurulum baslatiliyor." & vbCrLf & _
       "Paketler ve tarayici (chromium) indirilecek." & vbCrLf & _
       "Bu islem birkac dakika surebilir. Bittiginde haber verilecek.", _
       vbInformation, "Key-Drop Monitor - Kurulum"

' Komutlari cmd araciligiyla, pencere gizli (0) ve bekleyerek (True) calistir
cmd = "cmd /c chcp 65001 >nul && " & _
      "python -m pip install -r """ & sDir & "\src\requirements.txt"" && " & _
      "python -m playwright install chromium"

rc = oShell.Run(cmd, 0, True)

If rc = 0 Then
    MsgBox "Kurulum tamamlandi!" & vbCrLf & _
           "Artik 'start.vbs' ile programi calistirabilirsiniz.", _
           vbInformation, "Key-Drop Monitor - Kurulum"
Else
    MsgBox "Kurulum sirasinda bir hata olustu (kod: " & rc & ")." & vbCrLf & _
           "Python kurulu mu? Internet baglantinizi kontrol edin.", _
           vbCritical, "Key-Drop Monitor - Kurulum"
End If
