# application/tasks.py
import asyncio
from django.utils import timezone
from .models import AutomationSession

def start_automation_task(session_id, structured_data):
    """Start automation in background"""
    try:
        session = AutomationSession.objects.get(id=session_id)
        
        # Run async function
        asyncio.run(run_browser_automation(session, structured_data))
        
        return True
    except Exception as e:
        print(f"Task error: {e}")
        return False