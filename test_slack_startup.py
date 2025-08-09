#!/usr/bin/env python3
"""
Test script to verify Slack startup notification works.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_slack_startup():
    """Test the Slack startup notification."""
    
    print("🔍 Testing Slack Startup Notification...")
    
    try:
        from src.services.slack_service import slack_service
        
        # Test 1: Health check
        print("\n✅ Test 1: Slack Health Check")
        health_ok = await slack_service.health_check()
        print(f"   Health check result: {'✅ PASS' if health_ok else '❌ FAIL'}")
        
        if not health_ok:
            print("   ❌ Slack API is not accessible - check token")
            return False
        
        # Test 2: Send startup notification (like the scheduler does)
        print("\n✅ Test 2: Send Startup Notification")
        success = await slack_service.send_system_alert(
            "🚀 Best Seller Tracker started successfully! (TEST)\n"
            "Monitoring interval: 60 minutes\n"
            "Next batch run: 2025-08-09 14:30:00 UTC",
            alert_type="success"
        )
        print(f"   Startup notification result: {'✅ SENT' if success else '❌ FAILED'}")
        
        # Test 3: Send system alert
        print("\n✅ Test 3: Send System Alert")
        success2 = await slack_service.send_system_alert(
            "⚠️ This is a test system alert",
            alert_type="warning"
        )
        print(f"   System alert result: {'✅ SENT' if success2 else '❌ FAILED'}")
        
        return success and success2
        
    except Exception as e:
        print(f"\n❌ Slack test FAILED: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_slack_startup())
    if success:
        print("\n🎉 Slack notifications are working!")
        print("The issue might be that Railway deployment is not sending startup notifications.")
    else:
        print("\n❌ Slack notifications are not working properly")
