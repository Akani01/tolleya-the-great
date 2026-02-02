# test_automation.py
import asyncio
import sys
import os

# Add your project to path
sys.path.append('C:\\Users\\pro-musa\\Documents\\Apps\\tolleya-the-great')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school.settings')
import django
django.setup()

from application.models import AutomationSession, Application

async def test_manual():
    """Test browser manually"""
    print("Testing browser...")
    
    from playwright.async_api import async_playwright
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    
    await page.goto('https://google.com')
    print(f"Loaded: {await page.title()}")
    
    input("Press Enter to close...")
    
    await browser.close()
    await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_manual())