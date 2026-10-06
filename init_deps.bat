@echo off
rem Watermark Remover - 首次初始化：安装依赖（联网一次）
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Please install Python 3.9+ from https://www.python.org/downloads/
  pause
  exit /b 1
)
echo Installing dependencies ...
python -m pip install -r requirements.txt
echo.
echo Done. Double-click run.bat to start the tool.
pause
endlocal
