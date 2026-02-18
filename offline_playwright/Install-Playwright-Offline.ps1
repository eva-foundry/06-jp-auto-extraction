# Playwright Offline Installer
# Copy this entire 'offline_playwright' folder to your local device and run this script

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
if ($Verbose) { $VerbosePreference = "Continue" }

Write-Host "🎭 Playwright Offline Installer" -ForegroundColor Cyan
Write-Host "=" * 60

try {
    # Get script directory
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Write-Host "📁 Installation directory: $scriptDir" -ForegroundColor Green
    
    # Check Python
    Write-Host "`n🐍 Checking Python..." -ForegroundColor Yellow
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found. Please install Python first."
    }
    Write-Host "  ✅ Found: $pythonVersion" -ForegroundColor Green
    
    # Install playwright from local wheels
    Write-Host "`n📦 Installing Playwright from local packages..." -ForegroundColor Yellow
    $wheelFiles = Get-ChildItem -Path $scriptDir -Filter "*.whl"
    
    if ($wheelFiles.Count -eq 0) {
        throw "No wheel files found in $scriptDir"
    }
    
    Write-Host "  Found $($wheelFiles.Count) package(s)" -ForegroundColor Gray
    
    # Install all wheels with no-index to prevent internet access
    python -m pip install --no-index --find-links="$scriptDir" playwright
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install playwright packages"
    }
    Write-Host "  ✅ Playwright packages installed" -ForegroundColor Green
    
    # Copy browser binaries
    Write-Host "`n🌐 Installing browser binaries..." -ForegroundColor Yellow
    $browsersSource = Join-Path $scriptDir "browsers"
    $browsersTarget = Join-Path $env:LOCALAPPDATA "ms-playwright"
    
    if (-not (Test-Path $browsersSource)) {
        Write-Host "  ⚠️  Browser binaries not found. Run: python -m playwright install chromium" -ForegroundColor Yellow
    }
    else {
        # Create target directory
        if (-not (Test-Path $browsersTarget)) {
            New-Item -ItemType Directory -Path $browsersTarget -Force | Out-Null
        }
        
        # Copy browsers
        Write-Host "  Copying browsers from offline package..." -ForegroundColor Gray
        Copy-Item -Path "$browsersSource\*" -Destination $browsersTarget -Recurse -Force
        Write-Host "  ✅ Browser binaries installed to $browsersTarget" -ForegroundColor Green
    }
    
    # Test installation
    Write-Host "`n🧪 Testing installation..." -ForegroundColor Yellow
    
    # Test import
    python -c "from playwright.sync_api import sync_playwright; print('✅ Import successful')"
    if ($LASTEXITCODE -ne 0) {
        throw "Playwright import failed"
    }
    
    # Test browser launch
    Write-Host "  Testing browser launch..." -ForegroundColor Gray
    $testScript = @'
from playwright.sync_api import sync_playwright
import sys

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://example.com', timeout=10000)
        title = page.title()
        browser.close()
        print(f'✅ Browser test successful - Title: {title}')
        sys.exit(0)
except Exception as e:
    print(f'❌ Browser test failed: {e}')
    sys.exit(1)
'@
    
    $testScript | python
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  Browser test failed (may need internet for first run)" -ForegroundColor Yellow
    }
    
    # Success
    Write-Host "`n🎉 SUCCESS!" -ForegroundColor Green
    Write-Host "=" * 60
    Write-Host "Playwright installed successfully from offline package!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📦 Installed packages:" -ForegroundColor Cyan
    python -m pip list | Select-String "playwright|pyee|greenlet"
    Write-Host ""
    Write-Host "✅ Ready to use Playwright offline!" -ForegroundColor Green
    
}
catch {
    Write-Host "`n❌ INSTALLATION FAILED" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔧 Troubleshooting:" -ForegroundColor Yellow
    Write-Host "   1. Ensure Python is installed and in PATH" -ForegroundColor White
    Write-Host "   2. Verify all .whl files are in this directory" -ForegroundColor White
    Write-Host "   3. Check you have write permissions" -ForegroundColor White
    Write-Host "   4. Try running as Administrator" -ForegroundColor White
    exit 1
}

Write-Host "`nInstallation completed at $(Get-Date)" -ForegroundColor Gray
