@echo off
rem Watermark Remover - Windows 双击启动（无控制台）
setlocal
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw.exe run.py %*
) else (
  start "" python.exe run.py %*
)
endlocal
