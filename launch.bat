@echo off
REM Hand off to the silent VBS launcher (passed as %1, or the local default),
REM detached via START so this console never waits on the GUI and always closes.
set "VBS=%~1"
if "%VBS%"=="" set "VBS=%~dp0launch.vbs"
start "" wscript.exe "%VBS%"
exit
