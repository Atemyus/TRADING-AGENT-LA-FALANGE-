@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Missing virtualenv python: .venv\Scripts\python.exe
  echo Run setup first in apps\mt-bridge:
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 1
)

echo [INFO] Starting MT bridge on http://127.0.0.1:9000
".venv\Scripts\python.exe" -m uvicorn src.main:app --host 127.0.0.1 --port 9000
