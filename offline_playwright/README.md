# Playwright Offline Installation Package

This package contains everything needed to install Playwright without internet access.

## Package Contents

```
offline_playwright/
├── Install-Playwright-Offline.ps1  # Offline installer script
├── README.md                        # This file
├── playwright-1.57.0-py3-none-win_amd64.whl
├── greenlet-3.3.0-cp310-cp310-win_amd64.whl
├── pyee-13.0.0-py3-none-any.whl
├── typing_extensions-4.15.0-py3-none-any.whl
└── browsers/                        # Chromium browser binaries
    └── chromium-1200/
```

## System Requirements

- **Python**: 3.10+ (must be installed)
- **OS**: Windows 10/11
- **Disk Space**: ~500 MB

## Installation Instructions

### On Your Local Device (No Internet Required)

1. **Copy this entire `offline_playwright` folder** to your local device
   - Via USB drive, network share, or any file transfer method

2. **Open PowerShell** in the `offline_playwright` directory

3. **Run the installer:**
   ```powershell
   .\Install-Playwright-Offline.ps1
   ```

4. **Verify installation:**
   ```powershell
   python -c "from playwright.sync_api import sync_playwright; print('Success!')"
   ```

## What Gets Installed

- ✅ Playwright Python package (1.57.0)
- ✅ All Python dependencies (pyee, greenlet, typing-extensions)
- ✅ Chromium browser binaries (~300 MB)
- ✅ Browser drivers and runtime

## Installation Location

- **Python packages**: Your Python's site-packages directory
- **Browsers**: `%LOCALAPPDATA%\ms-playwright\`
  - Example: `C:\Users\YourName\AppData\Local\ms-playwright\`

## Troubleshooting

### "Python not found"
```powershell
# Verify Python is installed
python --version

# If not installed, download Python 3.10+ from python.org
```

### "Permission denied"
```powershell
# Run PowerShell as Administrator
# Right-click PowerShell → "Run as Administrator"
.\Install-Playwright-Offline.ps1
```

### "Browser test failed"
- This is normal if the target site requires internet
- Playwright is still installed correctly
- Test with a local HTML file instead

### Verify installation manually
```powershell
# Check Python package
python -m pip list | Select-String playwright

# Check browser location
Get-ChildItem "$env:LOCALAPPDATA\ms-playwright"

# Test import
python -c "from playwright.sync_api import sync_playwright; print('✅ OK')"
```

## Usage Example

After installation, use Playwright normally:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('http://localhost:5000')  # Or any accessible URL
    print(page.title())
    browser.close()
```

## For JP Automation

Once installed, you can run JP automation scripts that target **local or accessible instances**:

```powershell
# Example: Point to a locally running JP instance
python scripts/run_jp_batch.py --url "http://localhost:5173" --input questions.csv
```

## Package Creation Details

This package was created on: January 22, 2026
- Python version: 3.10
- Playwright version: 1.57.0
- Platform: Windows AMD64

## Notes

- **No internet required** during installation
- **Browser binaries** are platform-specific (this is for Windows)
- **Python version** should match (3.10+)
- Package is fully self-contained

## Support

If installation fails, check:
1. Python 3.10+ is installed
2. You have write permissions to Python site-packages
3. You have ~500 MB free disk space
4. You're using Windows (this package is Windows-specific)

---

**Created by**: JP Automation Setup Script  
**Source**: DevBox instance with internet access  
**Purpose**: Enable offline Playwright installation on restricted networks
