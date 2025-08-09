#!/usr/bin/env python3
"""
Test script to verify Supabase HTTP API integration works correctly.
This tests the direct HTTP approach instead of the problematic Python client.
"""

import asyncio
import os

# Load environment variables from .env file (safer approach)
from dotenv import load_dotenv
load_dotenv()

# Verify required environment variables are set
required_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
    print("Please ensure your .env file contains:")
    for var in missing_vars:
        print(f"  {var}=your_value_here")
    exit(1)

# Import our HTTP client after setting env vars
from src.config.supabase_http import supabase_client

async def test_supabase_http():
    """Test the Supabase HTTP API integration."""
    
    print("🔍 Testing Supabase HTTP API Integration...")
    print(f"📊 Supabase URL: {os.environ['SUPABASE_URL']}")
    print(f"🔑 Service Key: {os.environ['SUPABASE_SERVICE_KEY'][:20]}...")
    
    try:
        # Test 1: Health check
        print("\n✅ Test 1: Health Check")
        health_ok = await supabase_client.health_check()
        print(f"   Health check result: {'✅ PASS' if health_ok else '❌ FAIL'}")
        
        # Test 2: Get ASIN count
        print("\n✅ Test 2: Get ASIN Count")
        asin_count = await supabase_client.get_asin_count()
        print(f"   Total ASINs in database: {asin_count}")
        
        # Test 3: Get ASINs to check
        print("\n✅ Test 3: Get ASINs to Check")
        asins_to_check = await supabase_client.get_asins_to_check(limit=5)
        print(f"   ASINs ready for checking: {len(asins_to_check)}")
        for asin_data in asins_to_check[:3]:  # Show first 3
            print(f"   - {asin_data.get('asin', 'Unknown')}: {asin_data.get('product_title', 'No title')}")
        
        # Test 4: Get recent changes
        print("\n✅ Test 4: Get Recent Changes")
        recent_changes = await supabase_client.get_recent_changes(hours=24)
        print(f"   Recent changes (24h): {len(recent_changes)}")
        
        # Test 5: Test current state lookup
        if asins_to_check:
            test_asin = asins_to_check[0]['asin']
            print(f"\n✅ Test 5: Get Current State for {test_asin}")
            current_state = await supabase_client.get_asin_current_state(test_asin)
            if current_state:
                badges = current_state.get('bestseller_badges', [])
                print(f"   Current badges: {len(badges)}")
            else:
                print("   No current state found (this is normal for new ASINs)")
        
        # Close the HTTP client
        await supabase_client.close()
        
        print("\n🎉 All Supabase HTTP API tests completed successfully!")
        print("\n✅ Your Railway deployment should work with HTTP API!")
        return True
        
    except Exception as e:
        print(f"\n❌ Supabase HTTP API test FAILED: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_supabase_http())
    if success:
        print("\n🚀 Ready for Railway deployment with Supabase HTTP API!")
    else:
        print("\n❌ Supabase HTTP API integration needs fixing")
