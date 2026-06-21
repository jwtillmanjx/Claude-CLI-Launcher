Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw """ & Replace(WScript.ScriptFullName, WScript.ScriptName, "") & "claude_code_launcher.py""", 0, False
