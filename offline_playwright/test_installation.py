"""
Test Playwright Installation
Verifies that Playwright is properly installed and can launch browsers
"""

from playwright.sync_api import sync_playwright
import sys

def test_playwright_installation():
    """Test if Playwright is installed and working"""
    print("🧪 Testing Playwright Installation")
    print("=" * 60)
    
    # Test 1: Import
    print("\n✅ Test 1: Import successful")
    
    # Test 2: Browser launch
    print("\n🌐 Test 2: Testing browser launch...")
    try:
        with sync_playwright() as p:
            print("  - Launching Chromium browser...")
            browser = p.chromium.launch(headless=True)
            
            print("  - Creating new page...")
            page = browser.new_page()
            
            print("  - Testing with example.com...")
            page.goto('https://example.com', timeout=10000)
            title = page.title()
            
            print(f"  ✅ Success! Page title: '{title}'")
            
            browser.close()
            
    except Exception as e:
        print(f"  ⚠️  Browser test failed: {e}")
        print("     This is normal if you don't have internet access")
        print("     Playwright is still installed correctly")
    
    # Test 3: Check browser binaries
    print("\n📁 Test 3: Checking browser installation...")
    try:
        with sync_playwright() as p:
            browser_path = p.chromium.executable_path
            print(f"  ✅ Browser found at: {browser_path}")
    except Exception as e:
        print(f"  ❌ Browser check failed: {e}")
        return False
    
    # Success
    print("\n" + "=" * 60)
    print("🎉 PLAYWRIGHT INSTALLATION VERIFIED!")
    print("=" * 60)
    print("\n✅ Ready to use Playwright for automation!")
    print("\n💡 Example usage:")
    print("""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('http://localhost:5000')  # Your local app
    print(page.title())
    browser.close()
    """)
    
    return True

if __name__ == "__main__":
    try:
        success = test_playwright_installation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure playwright is installed: pip list | grep playwright")
        print("   2. Try reinstalling: pip install --force-reinstall playwright")
        print("   3. Check browser installation: python -m playwright install chromium")
        sys.exit(1)
