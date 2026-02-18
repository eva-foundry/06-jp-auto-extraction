@echo off
echo Starting Microsoft Edge with debug port for JP automation...
echo This will allow the automation script to connect to an authenticated Edge session.
echo.
echo Please:
echo 1. Authenticate to your Microsoft account in the Edge window that opens
echo 2. Navigate to JP UI if desired
echo 3. Leave this Edge instance running while using the automation
echo.

start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\edge-debug-profile"

echo Edge started with debug port 9222
echo You can now run the JP automation script
pause