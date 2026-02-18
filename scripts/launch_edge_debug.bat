@echo off
echo Starting Edge with debugging enabled...
echo.
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\jp-edge-debug" --no-first-run --no-default-browser-check "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io"