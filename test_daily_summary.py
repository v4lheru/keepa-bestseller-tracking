#!/usr/bin/env python3
"""
Test script for daily summary functionality.
Tests the fixed _get_daily_stats function.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.scheduler import scheduler_service
from src.services.slack_service import slack_service


async def test_daily_summary():
    """Test the daily summary calculation and sending."""
    print("🧪 Testing Daily Summary Functionality...")
    
    try:
        # Test today's stats
        today = datetime.utcnow().date()
        start_time = datetime.combine(today, datetime.min.time())
        end_time = datetime.combine(today + timedelta(days=1), datetime.min.time())
        
        print(f"📅 Calculating stats for: {start_time.date()} to {end_time.date()}")
        
        # Get daily stats using the fixed function
        stats = await scheduler_service._get_daily_stats(start_time, end_time)
        
        print("📊 Daily Stats Retrieved:")
        print(f"   Total Changes: {stats['total_changes']}")
        print(f"   Badges Gained: {stats['badges_gained']}")
        print(f"   Badges Lost: {stats['badges_lost']}")
        print(f"   ASINs Checked: {stats['asins_checked']}")
        print(f"   API Calls: {stats['api_calls']}")
        print(f"   Cost: ${stats['cost_cents'] / 100:.2f}")
        print(f"   Top Categories: {len(stats.get('top_categories', []))}")
        
        # Test sending the summary to Slack
        print("\n📤 Testing Slack Summary Send...")
        success = await slack_service.send_daily_summary(stats)
        
        if success:
            print("✅ Daily summary sent to Slack successfully!")
        else:
            print("❌ Failed to send daily summary to Slack")
        
        return success
        
    except Exception as e:
        print(f"❌ Error testing daily summary: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("🛠️ Daily Summary Test")
    print("=" * 50)
    
    success = await test_daily_summary()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Daily summary test completed successfully!")
        print("✅ The daily summary should now show correct data!")
    else:
        print("❌ Daily summary test failed")
        print("🔧 Check the logs for more details")


if __name__ == "__main__":
    asyncio.run(main())
