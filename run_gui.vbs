Set WshShell = CreateObject("WScript.Shell")
' gui.pyの絶対パスを指定
guiPath = "C:\Users\0053629\Documents\GitHub\timeclock\gui.py"
WshShell.Run "pythonw """ & guiPath & """", 0, False
Set WshShell = Nothing
