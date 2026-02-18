# Quick Start - Offline Playwright Installation

## 📦 Package Ready!

**Location**: `offline_playwright/` folder  
**Size**: 677.55 MB  
**Contents**:
- Playwright 1.57.0 package (34.86 MB)
- All dependencies (0.35 MB)
- Chromium browser binaries (642.34 MB)
- Installation scripts and documentation

## 🚀 3-Step Installation (On Local Device)

### Step 1: Transfer the Package
Copy the entire `offline_playwright` folder to your local device via USB/network share

### Step 2: Run Installer
```powershell
cd offline_playwright
.\Install-Playwright-Offline.ps1
```

### Step 3: Verify
```powershell
python -c "from playwright.sync_api import sync_playwright; print('✅ Success!')"
```

## ✅ What You Get

- **No internet required** during installation
- **Fully functional Playwright** with Chromium browser
- **Ready to automate** any accessible web application

## 📝 Important Notes

### For JP Automation Without JP App Access

Since the JP app (`ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io`) is not accessible from your local network, you have these options:

1. **Use a local JP instance** if one is running
2. **Mock JP responses** for testing/development
3. **Use VPN/network tunnel** to access the JP app
4. **Test with alternative sites** to verify Playwright works

### Testing Playwright Works (Without JP)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # visible browser
    page = browser.new_page()
    
    # Test with any accessible site
    page.goto('http://example.com')
    print(f"Page loaded: {page.title()}")
    
    # Or test with local file
    page.goto('file:///C:/path/to/test.html')
    
    browser.close()
```

## 🔧 If You Need to Access JP App

**Option A: Network/VPN Access**
- Connect to the network where JP app is hosted
- The app uses private endpoint: `ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io`

**Option B: Local JP Instance**
- Run JP locally (see EVA-JP-v1.2 deployment docs)
- Point scripts to `http://localhost:5173`

**Option C: Test Mode**
- Use Playwright for other automation tasks
- Wait for network access to JP app

## 📞 Need Help?

See full documentation in `offline_playwright/README.md`
