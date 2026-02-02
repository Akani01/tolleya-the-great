import asyncio
import os
import traceback
from django.utils import timezone
from browser_use import Agent
from playwright.async_api import async_playwright  # Direct Playwright access
from application.models import AutomationSession

async def run_browser_automation(session: AutomationSession, structured_data: dict):
    """
    SIMPLIFIED and WORKING browser automation
    """
    screenshot_dir = "media/automation"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    playwright_instance = None
    browser = None
    page = None
    
    try:
        # 1. Log start
        def log(msg, level="info"):
            print(f"[{timezone.now()}] {level.upper()}: {msg}")  # Console log
            session.application.add_automation_log(msg, level)
            session.save(update_fields=["updated_at", "preview_image"])
        
        log("Starting browser automation...")
        
        # 2. Launch browser DIRECTLY with Playwright (more reliable)
        playwright_instance = await async_playwright().start()
        browser = await playwright_instance.chromium.launch(
            headless=False,  # MUST be visible for manual login
            slow_mo=100,     # Slower for debugging
            args=['--start-maximized']  # Start maximized
        )
        
        # 3. Create context and page
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        log(f"Browser launched. Navigating to: {session.target_url}")
        
        # 4. Navigate to URL
        await page.goto(session.target_url, wait_until='networkidle')
        
        # 5. Capture initial screenshot
        screenshot_path = f"{screenshot_dir}/{session.id}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        session.preview_image = screenshot_path
        session.status = session.Status.RUNNING
        session.save()
        
        log(f"Page loaded. Screenshot saved: {screenshot_path}")
        log("WAITING FOR MANUAL LOGIN... User should now login in the browser window.", "warning")
        
        # 6. Update status and wait for user login
        session.status = session.Status.WAITING_FOR_USER
        session.save()
        
        # 7. WAIT LOOP with timeout
        max_wait_minutes = 5
        wait_seconds = 3  # Check every 3 seconds
        total_checks = (max_wait_minutes * 60) // wait_seconds
        
        for check_count in range(total_checks):
            # Update preview screenshot
            await page.screenshot(path=screenshot_path, full_page=True)
            session.preview_image = screenshot_path
            session.save(update_fields=["preview_image"])
            
            # Refresh session to check if user clicked "Continue"
            session.refresh_from_db()
            
            # Check if status changed
            if session.status != session.Status.WAITING_FOR_USER:
                log(f"Status changed to: {session.status}")
                break
            
            # Check URL to see if login might have happened
            current_url = page.url
            if check_count % 10 == 0:  # Log every 30 seconds
                log(f"Still waiting... Current URL: {current_url[:80]}...")
            
            await asyncio.sleep(wait_seconds)
        else:
            # Timeout reached
            log(f"Timeout: No login after {max_wait_minutes} minutes", "error")
            session.status = session.Status.FAILED
            session.save()
            return
        
        # 8. If user cancelled
        if session.status == session.Status.CANCELLED:
            log("Cancelled by user")
            return
        
        # 9. LOGIN COMPLETE - Now fill the form
        log("Login detected! Starting form automation...")
        session.status = session.Status.RUNNING
        session.save()
        
        # 10. Use browser-use Agent for form filling
        # First, let's see what's on the page
        page_title = await page.title()
        log(f"Page title after login: {page_title}")
        
        # Create Agent with the existing browser/page
        agent = Agent(
            task=f"""
            You are on a university application page after login.
            
            TASK: Fill the application form with this data:
            {structured_data}
            
            INSTRUCTIONS:
            1. Find all form fields on the current page
            2. Fill each field with the corresponding data
            3. DO NOT submit the form - stop before final submission
            4. Leave the form ready for user review
            
            IMPORTANT: Fill carefully, check field types, and validate inputs.
            """
        )
        
        # Run the agent on the current page
        log("Starting form filling with AI agent...")
        await agent.run()
        
        # 11. Final screenshot
        await page.screenshot(path=screenshot_path, full_page=True)
        log("Form filling completed! Ready for review.", "success")
        session.status = session.Status.COMPLETED
        session.save()
        
    except Exception as e:
        error_msg = f"CRITICAL ERROR: {str(e)}"
        print(f"\n{'='*60}\n{error_msg}\n{'='*60}")
        log(error_msg, "error")
        
        # Save error traceback
        error_trace = traceback.format_exc()
        log(f"Traceback: {error_trace}", "error")
        
        # Try to capture error screenshot
        try:
            if page and not page.is_closed():
                screenshot_path = f"{screenshot_dir}/{session.id}_ERROR.png"
                await page.screenshot(path=screenshot_path)
                session.preview_image = screenshot_path
        except:
            pass
        
        session.status = session.Status.FAILED
        session.save()
        
    finally:
        # Cleanup
        try:
            if browser:
                await browser.close()
                log("Browser closed")
        except:
            pass
            
        try:
            if playwright_instance:
                await playwright_instance.stop()
        except:
            pass