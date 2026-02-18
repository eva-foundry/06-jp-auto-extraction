@echo off
echo ========================================
echo JP Automation - Admin Playwright Test
echo ========================================
echo.

REM Change to project directory
cd /d "c:\Users\marco.presta\OneDrive - ESDC EDSC\Documents\AICOE\EVA-JP-v1.2\docs\eva-foundation\projects\06-JP-Auto-Extraction"

echo Testing Python availability...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not available
    pause
    exit /b 1
)

echo.
echo Testing pip...
python -m pip --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Pip not available  
    pause
    exit /b 1
)

echo.
echo Installing playwright (this may take a few minutes)...
python -m pip install playwright --user --upgrade --quiet
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Playwright pip install had issues, trying alternative...
    python -m pip install playwright --upgrade --quiet
)

echo.
echo Testing playwright import...
python -c "from playwright.sync_api import sync_playwright; print('SUCCESS: Playwright import works')"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Playwright import failed
    echo This suggests the package installation didn't work properly
    pause
    exit /b 1
)

echo.
echo Installing playwright browsers (this will take several minutes)...
python -m playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Browser install failed, trying with dependencies...
    python -m playwright install chromium --with-deps
)

echo.
echo Testing browser launch...
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright(); b = p.start(); br = b.chromium.launch(); page = br.new_page(); page.goto('https://example.com'); print('SUCCESS: Browser test works - Title:', page.title()); br.close(); p.stop()"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS! Playwright is working!
    echo ========================================
    echo.
    echo You can now test JP automation:
    echo python scripts/run_jp_batch.py --in input/questions.csv --out temp_test.csv --headed
    echo.
) else (
    echo.
    echo ========================================
    echo Browser test failed
    echo ========================================
    echo Playwright installed but browser not working
    echo This might be due to missing system dependencies
    echo.
)

pause