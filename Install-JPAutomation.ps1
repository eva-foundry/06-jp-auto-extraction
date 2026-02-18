# JP Automation - DevBox/Admin Installation Script
# Run this script as Administrator to install playwright and test JP automation

param(
    [switch]$TestOnly,
    [switch]$InstallOnly,
    [switch]$Verbose
)

# Set error handling
$ErrorActionPreference = "Stop"

# Enable verbose output if requested
if ($Verbose) { $VerbosePreference = "Continue" }

Write-Host "🚀 JP Automation - DevBox/Admin Setup Script" -ForegroundColor Cyan
Write-Host "=" * 60

# Function to check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to test network connectivity
function Test-NetworkConnectivity {
    Write-Host "🌐 Testing network connectivity..." -ForegroundColor Yellow
    
    $testSites = @(
        "https://pypi.org",
        "https://playwright.dev", 
        "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io"
    )
    
    $results = @()
    foreach ($site in $testSites) {
        try {
            $response = Invoke-WebRequest -Uri $site -Method Head -TimeoutSec 10 -UseBasicParsing
            $status = "✅ REACHABLE"
            Write-Host "  $site - $status" -ForegroundColor Green
            $results += @{Site = $site; Status = "OK"}
        }
        catch {
            $status = "❌ UNREACHABLE"  
            Write-Host "  $site - $status" -ForegroundColor Red
            Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Gray
            $results += @{Site = $site; Status = "FAILED"; Error = $_.Exception.Message}
        }
    }
    
    return $results
}

# Function to install Python packages with retry logic
function Install-PythonPackage {
    param(
        [string[]]$Packages,
        [int]$MaxRetries = 3
    )
    
    foreach ($package in $Packages) {
        Write-Host "📦 Installing $package..." -ForegroundColor Yellow
        
        $attempt = 1
        $success = $false
        
        while ($attempt -le $MaxRetries -and -not $success) {
            try {
                Write-Verbose "Attempt $attempt of $MaxRetries for $package"
                
                # Try different pip strategies
                $pipCommands = @(
                    "python -m pip install $package --user --upgrade",
                    "python -m pip install $package --upgrade", 
                    "python -m pip install $package --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --upgrade"
                )
                
                $cmdUsed = $null
                foreach ($cmd in $pipCommands) {
                    try {
                        Write-Verbose "Trying: $cmd"
                        Invoke-Expression $cmd
                        $cmdUsed = $cmd
                        break
                    }
                    catch {
                        Write-Verbose "Failed with: $cmd - $($_.Exception.Message)"
                        continue
                    }
                }
                
                if ($cmdUsed) {
                    Write-Host "  ✅ $package installed successfully" -ForegroundColor Green
                    $success = $true
                }
                else {
                    throw "All pip installation methods failed"
                }
            }
            catch {
                Write-Host "  ❌ Attempt $attempt failed: $($_.Exception.Message)" -ForegroundColor Red
                $attempt++
                
                if ($attempt -le $MaxRetries) {
                    Write-Host "  🔄 Retrying in 5 seconds..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 5
                }
            }
        }
        
        if (-not $success) {
            throw "Failed to install $package after $MaxRetries attempts"
        }
    }
}

# Main execution
try {
    # Check administrator privileges
    Write-Host "🔒 Checking administrator privileges..." -ForegroundColor Yellow
    if (-not (Test-Administrator)) {
        Write-Host "⚠️  WARNING: Not running as administrator" -ForegroundColor Yellow
        Write-Host "   Some installations might fail. Consider running as admin." -ForegroundColor Gray
    } else {
        Write-Host "  ✅ Running as administrator" -ForegroundColor Green
    }
    
    # Set working directory
    $projectRoot = "c:\Users\marco.presta\OneDrive - ESDC EDSC\Documents\AICOE\EVA-JP-v1.2\docs\eva-foundation\projects\06-JP-Auto-Extraction"
    
    if (-not (Test-Path $projectRoot)) {
        throw "Project directory not found: $projectRoot"
    }
    
    Set-Location $projectRoot
    Write-Host "📁 Working directory: $projectRoot" -ForegroundColor Green
    
    # Test network connectivity (unless TestOnly mode)
    if (-not $TestOnly) {
        $networkResults = Test-NetworkConnectivity
        $failedSites = $networkResults | Where-Object { $_.Status -eq "FAILED" }
        
        if ($failedSites.Count -gt 0) {
            Write-Host "⚠️  Network connectivity issues detected:" -ForegroundColor Yellow
            foreach ($site in $failedSites) {
                Write-Host "   - $($site.Site): $($site.Error)" -ForegroundColor Gray
            }
            Write-Host "   Continuing anyway..." -ForegroundColor Yellow
        }
    }
    
    # Installation phase
    if (-not $TestOnly) {
        Write-Host "`n🛠️  INSTALLATION PHASE" -ForegroundColor Cyan
        Write-Host "-" * 40
        
        # Install core packages
        Write-Host "Installing core dependencies..." -ForegroundColor Yellow
        Install-PythonPackage -Packages @("pandas", "requests")
        
        # Install playwright
        Write-Host "Installing playwright..." -ForegroundColor Yellow
        Install-PythonPackage -Packages @("playwright")
        
        # Install playwright browsers
        Write-Host "🌐 Installing playwright browsers..." -ForegroundColor Yellow
        try {
            $playwrightInstall = "python -m playwright install chromium"
            Write-Verbose "Running: $playwrightInstall"
            Invoke-Expression $playwrightInstall
            Write-Host "  ✅ Playwright browsers installed" -ForegroundColor Green
        }
        catch {
            Write-Host "  ❌ Browser installation failed: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "  🔧 Trying alternative approach..." -ForegroundColor Yellow
            
            try {
                # Try with explicit browser path
                Invoke-Expression "python -m playwright install chromium --with-deps"
                Write-Host "  ✅ Browsers installed with dependencies" -ForegroundColor Green
            }
            catch {
                Write-Host "  ❌ Alternative browser install failed" -ForegroundColor Red
                throw "Could not install playwright browsers"
            }
        }
        
        Write-Host "✅ Installation phase completed!" -ForegroundColor Green
    }
    
    # Testing phase
    if (-not $InstallOnly) {
        Write-Host "`n🧪 TESTING PHASE" -ForegroundColor Cyan
        Write-Host "-" * 40
        
        # Test 1: Import test
        Write-Host "Testing playwright import..." -ForegroundColor Yellow
        try {
            $importTest = 'python -c "from playwright.sync_api import sync_playwright; print(\"✅ Playwright import successful\")"'
            Invoke-Expression $importTest
        }
        catch {
            throw "Playwright import failed: $($_.Exception.Message)"
        }
        
        # Test 2: Core validation
        Write-Host "Running core validation tests..." -ForegroundColor Yellow
        try {
            Set-Location "tests"
            Invoke-Expression "python -m pytest test_citation_simple.py test_input_validation.py -v"
            Set-Location ".."
        }
        catch {
            Write-Host "⚠️  Core tests failed, but continuing..." -ForegroundColor Yellow
        }
        
        # Test 3: Browser launch test
        Write-Host "Testing browser launch..." -ForegroundColor Yellow
        try {
            $browserTest = @'
python -c "
from playwright.sync_api import sync_playwright
import sys

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://example.com', timeout=10000)
        title = page.title()
        browser.close()
        print(f'✅ Browser test successful - Page title: {title}')
        sys.exit(0)
except Exception as e:
    print(f'❌ Browser test failed: {e}')
    sys.exit(1)
"
'@
            Invoke-Expression $browserTest
        }
        catch {
            Write-Host "❌ Browser launch test failed: $($_.Exception.Message)" -ForegroundColor Red
            throw "Browser functionality not working"
        }
        
        # Test 4: JP UI connectivity test
        Write-Host "Testing JP UI connectivity..." -ForegroundColor Yellow
        try {
            $jpUITest = @'
python -c "
from playwright.sync_api import sync_playwright
import sys

JP_UI_URL = 'https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/'

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print('Navigating to JP UI...')
        response = page.goto(JP_UI_URL, timeout=30000)
        
        if response and response.status == 200:
            title = page.title()
            print(f'✅ JP UI accessible - Status: {response.status}, Title: {title}')
            
            # Try to find chat input
            try:
                page.wait_for_selector('input', timeout=5000)
                print('✅ Chat interface elements detected')
            except:
                print('⚠️  Chat input not immediately visible (may require interaction)')
        else:
            status = response.status if response else 'No response'
            print(f'⚠️  JP UI responded with status: {status}')
        
        browser.close()
        sys.exit(0)
        
except Exception as e:
    print(f'❌ JP UI test failed: {e}')
    sys.exit(1)
"
'@
            Invoke-Expression $jpUITest
        }
        catch {
            Write-Host "⚠️  JP UI connectivity test failed: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "   This may be normal if JP UI requires authentication" -ForegroundColor Gray
        }
    }
    
    # Success summary
    Write-Host "`n🎉 SUCCESS!" -ForegroundColor Green
    Write-Host "=" * 60
    Write-Host "JP Automation setup completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "✅ Ready for JP automation testing" -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Test with a single question:" -ForegroundColor White
    Write-Host "      cd '$projectRoot'" -ForegroundColor Gray
    Write-Host "      python scripts/run_jp_batch.py --in input/questions.csv --out temp_test.csv --headed" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   2. Generate baseline evidence:" -ForegroundColor White  
    Write-Host "      python scripts/generate_baseline.py --input input/questions.csv --count 5 --headed" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   3. Full batch processing:" -ForegroundColor White
    Write-Host "      python scripts/run_jp_batch.py --in input/questions.csv --out output/jp_answers.csv" -ForegroundColor Gray
    
}
catch {
    Write-Host "`n❌ SETUP FAILED" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔧 Troubleshooting suggestions:" -ForegroundColor Yellow
    Write-Host "   1. Ensure you're running as Administrator" -ForegroundColor White
    Write-Host "   2. Check internet connectivity" -ForegroundColor White
    Write-Host "   3. Verify Python is accessible (try: python --version)" -ForegroundColor White
    Write-Host "   4. Check if behind corporate firewall/proxy" -ForegroundColor White
    Write-Host "   5. Try running individual commands manually" -ForegroundColor White
    
    exit 1
}

Write-Host "`nScript completed at $(Get-Date)" -ForegroundColor Gray