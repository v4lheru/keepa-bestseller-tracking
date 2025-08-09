#!/usr/bin/env python3
"""
Detailed test to show exactly what HTTP requests are being made to Supabase.
This validates that we're using the correct API endpoints and authentication.
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

async def test_detailed_http():
    """Test with detailed HTTP request logging."""
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    
    print("🔍 DETAILED HTTP API TEST")
    print(f"📊 Base URL: {SUPABASE_URL}/rest/v1")
    print(f"🔑 Using Service Key: {SUPABASE_SERVICE_KEY[:20]}...")
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    print(f"\n🔐 Headers being sent:")
    print(f"   apikey: {SUPABASE_SERVICE_KEY[:20]}...")
    print(f"   Authorization: Bearer {SUPABASE_SERVICE_KEY[:20]}...")
    print(f"   Content-Type: application/json")
    print(f"   Prefer: return=representation")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Health Check - Query simple_asin_status table
        print(f"\n✅ Test 1: Health Check")
        url = f"{SUPABASE_URL}/rest/v1/simple_asin_status?select=count&limit=1"
        print(f"   🌐 GET {url}")
        
        try:
            response = await client.get(url, headers=headers)
            print(f"   📊 Status Code: {response.status_code}")
            print(f"   📄 Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS - Can access simple_asin_status table")
            else:
                print(f"   ❌ FAILED - Cannot access table")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        # Test 2: Get ASINs to check
        print(f"\n✅ Test 2: Get ASINs to Check")
        url = f"{SUPABASE_URL}/rest/v1/simple_asin_status?select=*&order=priority.asc,last_checked_at.asc&limit=5"
        print(f"   🌐 GET {url}")
        
        try:
            response = await client.get(url, headers=headers)
            print(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS - Retrieved {len(data)} ASINs")
                if data:
                    print(f"   📋 Sample ASIN: {data[0].get('asin', 'N/A')}")
                    print(f"   📋 Available fields: {list(data[0].keys())}")
            else:
                print(f"   ❌ FAILED - Status: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        # Test 3: Check asin_current_state table
        print(f"\n✅ Test 3: Check asin_current_state Table")
        url = f"{SUPABASE_URL}/rest/v1/asin_current_state?select=*&limit=1"
        print(f"   🌐 GET {url}")
        
        try:
            response = await client.get(url, headers=headers)
            print(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS - asin_current_state table accessible")
                print(f"   📋 Records found: {len(data)}")
                if data:
                    print(f"   📋 Available fields: {list(data[0].keys())}")
            else:
                print(f"   ❌ FAILED - Status: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        # Test 4: Check bestseller_changes table
        print(f"\n✅ Test 4: Check bestseller_changes Table")
        url = f"{SUPABASE_URL}/rest/v1/bestseller_changes?select=*&limit=1"
        print(f"   🌐 GET {url}")
        
        try:
            response = await client.get(url, headers=headers)
            print(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS - bestseller_changes table accessible")
                print(f"   📋 Records found: {len(data)}")
                if data:
                    print(f"   📋 Available fields: {list(data[0].keys())}")
            else:
                print(f"   ❌ FAILED - Status: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        # Test 5: Test POST operation (create a test record)
        print(f"\n✅ Test 5: Test POST Operation (Error Log)")
        url = f"{SUPABASE_URL}/rest/v1/error_log"
        test_data = {
            "error_type": "test",
            "error_message": "HTTP API test",
            "occurred_at": "2025-08-09T13:00:00Z"
        }
        print(f"   🌐 POST {url}")
        print(f"   📤 Data: {test_data}")
        
        try:
            response = await client.post(url, headers=headers, json=test_data)
            print(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 201:
                print(f"   ✅ SUCCESS - Can write to error_log table")
                print(f"   📄 Response: {response.text}")
            else:
                print(f"   ❌ FAILED - Status: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print(f"\n🎯 SUMMARY:")
    print(f"   The HTTP client uses Supabase REST API endpoints:")
    print(f"   - GET /rest/v1/simple_asin_status - for ASIN data")
    print(f"   - GET /rest/v1/asin_current_state - for current badge states")
    print(f"   - GET /rest/v1/bestseller_changes - for change history")
    print(f"   - POST /rest/v1/* - for creating new records")
    print(f"   - PATCH /rest/v1/* - for updating existing records")
    print(f"   ")
    print(f"   Authentication: Service key in both apikey header and Bearer token")
    print(f"   This is the standard Supabase REST API - same as your other solutions!")

if __name__ == "__main__":
    asyncio.run(test_detailed_http())
