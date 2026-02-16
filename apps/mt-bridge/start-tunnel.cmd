@echo off
setlocal
cd /d "%~dp0"

where cloudflared >nul 2>&1
if errorlevel 1 (
  echo [ERROR] cloudflared not found in PATH.
  echo Install with:
  echo   winget install Cloudflare.cloudflared
  exit /b 1
)

echo [INFO] Starting Cloudflare quick tunnel to http://127.0.0.1:9000
echo [INFO] Copy the generated trycloudflare URL and set MT_BRIDGE_BASE_URL to that URL.
cloudflared tunnel --url http://127.0.0.1:9000 --protocol quic --no-autoupdate --loglevel info --logfile "%~dp0cloudflared.log"
