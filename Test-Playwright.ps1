# Quick Playwright Test Script for Admin/DevBox Environment
# Test if playwright can be installed and work in current environment

Write-Host "🔬 Quick Playwright Test - Admin Environment" -ForegroundColor Cyan
Write-Host "=" * 50

# Check current directory
$currentDir = Get-Location
Write-Host "📁 Current directory: $currentDir" -ForegroundColor Green

# Test Python availability  
Write-Host "`n🐍 Testing Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✅ Python available: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "  ❌ Python not available" -ForegroundColor Red
    exit 1
}

# Test pip
Write-Host "`n📦 Testing pip..." -ForegroundColor Yellow  
try {
    $pipVersion = python -m pip --version 2>&1
    Write-Host "  ✅ Pip available: $pipVersion" -ForegroundColor Green
}
catch {
    Write-Host "  ❌ Pip not available" -ForegroundColor Red
    exit 1
}

# Test basic playwright install (just the package, not browsers yet)
Write-Host "`n🎭 Testing playwright package install..." -ForegroundColor Yellow
try {
    Write-Host "  Installing playwright package..." -ForegroundColor Gray
    python -m pip install playwright --quiet --disable-pip-version-check 2>&1 | Out-Null
    
    # Test import
    $importTest = python -c "from playwright.sync_api import sync_playwright; print('SUCCESS')" 2>&1
    if ($importTest -match "SUCCESS") {
        Write-Host "  ✅ Playwright package installed and importable" -ForegroundColor Green
    } else {
        throw "Import test failed: $importTest"
    }
}
catch {
    Write-Host "  ❌ Playwright package install failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "     This might be due to network restrictions or admin requirements" -ForegroundColor Gray
    
    # Try to give specific advice
    Write-Host "`n💡 Suggestions:" -ForegroundColor Yellow
    Write-Host "   1. Run PowerShell as Administrator" -ForegroundColor White
    Write-Host "   2. Try: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor White
    Write-Host "   3. Check if behind corporate proxy/firewall" -ForegroundColor White
    
    exit 1
}

# Test browser install
Write-Host "`n🌐 Testing playwright browser install..." -ForegroundColor Yellow
try {
    Write-Host "  Installing chromium browser..." -ForegroundColor Gray
    python -m playwright install chromium 2>&1 | Out-Null
    Write-Host "  ✅ Browser installation completed" -ForegroundColor Green
}
catch {
    Write-Host "  ❌ Browser install failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "     Browser automation may not work, but package is installed" -ForegroundColor Gray
}

# Test basic browser functionality
Write-Host "`n🚀 Testing browser launch..." -ForegroundColor Yellow
try {
    $browserTestCode = @"
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://example.com', timeout=10000)
        title = page.title()
        browser.close()
        print(f'SUCCESS:{title}')
except Exception as e:
    print(f'ERROR:{e}')
"@
    
    $result = python -c $browserTestCode 2>&1
    
    if ($result -match "SUCCESS:") {
        $title = ($result -split ":")[1]
        Write-Host "  ✅ Browser test successful - Page title: $title" -ForegroundColor Green
        
        # Test JP UI specifically
        Write-Host "`n🎯 Testing JP UI access..." -ForegroundColor Yellow
        $jpTestCode = @"
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        response = page.goto('https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/', timeout=15000)
        status = response.status if response else 'No response'
        title = page.title() if response else 'No title'
        browser.close()
        print(f'SUCCESS:{status}:{title}')
except Exception as e:
    print(f'ERROR:{e}')
"@
        
        $jpResult = python -c $jpTestCode 2>&1
        
        if ($jpResult -match "SUCCESS:") {
            $parts = ($jpResult -split ":")
            $status = $parts[1]
            $jpTitle = $parts[2]
            Write-Host "  ✅ JP UI accessible - Status: $status, Title: $jpTitle" -ForegroundColor Green
            
            Write-Host "`n🎉 EXCELLENT! Playwright is working!" -ForegroundColor Green
            Write-Host "✅ Package installed" -ForegroundColor Green
            Write-Host "✅ Browser working" -ForegroundColor Green
            Write-Host "✅ JP UI accessible" -ForegroundColor Green
            
            Write-Host "`n🚀 Ready to run JP automation!" -ForegroundColor Cyan
            Write-Host "Try this command:" -ForegroundColor White
            Write-Host 'python scripts/run_jp_batch.py --in input/questions.csv --out temp_test.csv --headed' -ForegroundColor Gray
            
        } else {
            Write-Host "  ⚠️  JP UI test failed: $jpResult" -ForegroundColor Yellow  
            Write-Host "     Playwright works, but JP UI may not be accessible from this environment" -ForegroundColor Gray
        }
        
    } else {
        throw "Browser test failed: $result"
    }
}
catch {
    Write-Host "  ❌ Browser test failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "     Playwright installed but browser functionality not working" -ForegroundColor Gray
}

Write-Host "`n📊 Test completed at $(Get-Date)" -ForegroundColor Gray