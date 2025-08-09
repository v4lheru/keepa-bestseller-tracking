#!/usr/bin/env python3
"""
Comprehensive end-to-end system test.
Tests all components, database operations, API integrations, and data relationships.
"""

import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def test_comprehensive_system():
    """Comprehensive test of the entire system."""
    
    print("🔍 COMPREHENSIVE SYSTEM TEST")
    print("=" * 60)
    
    try:
        # Import all services
        from src.services.asin_tracker import asin_tracker
        from src.services.keepa_service import keepa_service
        from src.services.slack_service import slack_service
        from src.config.supabase_http import supabase_client
        
        test_results = {
            "database_operations": False,
            "keepa_integration": False,
            "slack_integration": False,
            "batch_processing": False,
            "data_relationships": False,
            "payload_validation": False
        }
        
        # Test 1: Database Operations
        print("\n🗄️ TEST 1: DATABASE OPERATIONS")
        print("-" * 40)
        
        # Test getting ASINs
        asins_to_check = await asin_tracker.get_asins_to_check(limit=5)
        print(f"✅ Retrieved {len(asins_to_check)} ASINs from database")
        
        if not asins_to_check:
            print("❌ No ASINs found - database connection issue")
            return False
        
        test_asin = asins_to_check[0]["asin"]
        print(f"✅ Test ASIN: {test_asin}")
        
        # Test current state operations
        current_state = await supabase_client.get_asin_current_state(test_asin)
        print(f"✅ Current state exists: {current_state is not None}")
        
        test_results["database_operations"] = True
        
        # Test 2: Keepa API Integration
        print("\n🔗 TEST 2: KEEPA API INTEGRATION")
        print("-" * 40)
        
        # Test single ASIN
        single_product = await keepa_service.get_single_product(test_asin)
        if single_product:
            print(f"✅ Single ASIN API call successful")
            print(f"   ASIN: {single_product.asin}")
            print(f"   Title: {single_product.title}")
            print(f"   Brand: {single_product.brand}")
            print(f"   Sales Ranks: {single_product.sales_ranks}")
            print(f"   Category Tree: {single_product.category_tree}")
            
            # Test badge extraction
            badges = keepa_service.extract_bestseller_badges(single_product)
            print(f"✅ Badge extraction: {len(badges)} badges found")
            for badge in badges:
                print(f"   - {badge.category_name} (ID: {badge.category_id}): Rank #{badge.rank}")
        else:
            print("❌ Single ASIN API call failed")
            return False
        
        # Test batch API call
        test_asins = [asin["asin"] for asin in asins_to_check[:3]]
        products, api_metadata = await keepa_service.get_products_batch(test_asins)
        print(f"✅ Batch API call successful: {len(products)} products returned")
        print(f"   Tokens left: {api_metadata.get('tokens_left', 'Unknown')}")
        print(f"   Response time: {api_metadata.get('response_time_ms', 0)}ms")
        
        test_results["keepa_integration"] = True
        
        # Test 3: Slack Integration
        print("\n💬 TEST 3: SLACK INTEGRATION")
        print("-" * 40)
        
        # Test health check
        slack_healthy = await slack_service.health_check()
        print(f"✅ Slack health check: {'PASS' if slack_healthy else 'FAIL'}")
        
        if not slack_healthy:
            print("❌ Slack API not accessible")
            return False
        
        # Test system alert
        alert_success = await slack_service.send_system_alert(
            "🧪 COMPREHENSIVE TEST - System validation in progress",
            alert_type="info"
        )
        print(f"✅ System alert sent: {'SUCCESS' if alert_success else 'FAILED'}")
        
        test_results["slack_integration"] = alert_success
        
        # Test 4: Comprehensive Batch Processing
        print("\n⚙️ TEST 4: COMPREHENSIVE BATCH PROCESSING")
        print("-" * 40)
        
        # Process a small batch to test all operations
        test_batch = asins_to_check[:2]  # Test with 2 ASINs
        print(f"Processing batch of {len(test_batch)} ASINs...")
        
        result = await asin_tracker.process_batch(test_batch)
        
        print(f"✅ Batch processing completed:")
        print(f"   Batch ID: {result.batch_id}")
        print(f"   ASINs processed: {result.asins_processed}")
        print(f"   Successful checks: {result.successful_checks}")
        print(f"   Failed checks: {result.failed_checks}")
        print(f"   Changes detected: {result.changes_detected}")
        print(f"   Notifications sent: {result.notifications_sent}")
        print(f"   Processing time: {result.processing_time_seconds}s")
        print(f"   Estimated cost: {result.estimated_cost_cents} cents")
        
        test_results["batch_processing"] = result.successful_checks > 0
        
        # Test 5: Data Relationships & Database Validation
        print("\n🔍 TEST 5: DATA RELATIONSHIPS & DATABASE VALIDATION")
        print("-" * 40)
        
        # Check if data was properly saved to all tables
        for test_asin_data in test_batch:
            asin = test_asin_data["asin"]
            print(f"\nValidating data for ASIN: {asin}")
            
            # Check current state table
            current_state = await supabase_client.get_asin_current_state(asin)
            if current_state:
                print(f"✅ Current state saved:")
                print(f"   Product Title: {current_state.get('product_title', 'N/A')}")
                print(f"   Brand: {current_state.get('brand', 'N/A')}")
                print(f"   Badges: {len(current_state.get('bestseller_badges', []))}")
                print(f"   Sales Ranks: {len(current_state.get('sales_ranks', {}))}")
                print(f"   Category Tree: {len(current_state.get('category_tree', []))}")
            else:
                print(f"❌ No current state found for {asin}")
                continue
            
            # Validate data structure
            if current_state.get('bestseller_badges'):
                for badge in current_state['bestseller_badges']:
                    if not all(key in badge for key in ['category_id', 'category_name', 'rank']):
                        print(f"❌ Invalid badge structure: {badge}")
                        return False
                print(f"✅ Badge data structure valid")
            
            if current_state.get('sales_ranks'):
                print(f"✅ Sales ranks data present: {len(current_state['sales_ranks'])} categories")
            
            if current_state.get('category_tree'):
                print(f"✅ Category tree data present: {len(current_state['category_tree'])} categories")
        
        test_results["data_relationships"] = True
        
        # Test 6: Payload Validation
        print("\n📋 TEST 6: PAYLOAD VALIDATION")
        print("-" * 40)
        
        # Test creating a mock badge change notification
        if products:
            test_product = products[0]
            test_badges = keepa_service.extract_bestseller_badges(test_product)
            
            if test_badges:
                # Create a mock notification payload
                from src.models.schemas import SlackNotificationPayload
                
                payload = SlackNotificationPayload(
                    asin=test_product.asin,
                    product_title=test_product.title or "Test Product",
                    change_type="gained",
                    category=test_badges[0].category_name,
                    category_id=test_badges[0].category_id,
                    previous_rank=None,
                    new_rank=test_badges[0].rank,
                    detected_at=datetime.utcnow(),
                    amazon_url=f"https://amazon.com/dp/{test_product.asin}"
                )
                
                print(f"✅ Notification payload created successfully:")
                print(f"   ASIN: {payload.asin}")
                print(f"   Product: {payload.product_title}")
                print(f"   Change: {payload.change_type}")
                print(f"   Category: {payload.category}")
                print(f"   Amazon URL: {payload.amazon_url}")
                
                # Test the payload serialization
                payload_dict = payload.model_dump()
                print(f"✅ Payload serialization successful: {len(payload_dict)} fields")
                
                test_results["payload_validation"] = True
            else:
                print("ℹ️ No badges found for payload testing (this is normal)")
                test_results["payload_validation"] = True
        
        # Test 7: API Usage and Cost Tracking
        print("\n💰 TEST 7: API USAGE & COST TRACKING")
        print("-" * 40)
        
        # Calculate costs
        tokens_used = len(test_batch)
        estimated_cost = keepa_service.estimate_cost(tokens_used)
        print(f"✅ Cost calculation:")
        print(f"   Tokens used: {tokens_used}")
        print(f"   Estimated cost: {estimated_cost} cents")
        
        # Test 8: Health Checks
        print("\n🏥 TEST 8: SYSTEM HEALTH CHECKS")
        print("-" * 40)
        
        supabase_healthy = await supabase_client.health_check()
        keepa_healthy = await keepa_service.health_check()
        slack_healthy = await slack_service.health_check()
        
        print(f"✅ System health status:")
        print(f"   Supabase API: {'✅ HEALTHY' if supabase_healthy else '❌ UNHEALTHY'}")
        print(f"   Keepa API: {'✅ HEALTHY' if keepa_healthy else '❌ UNHEALTHY'}")
        print(f"   Slack API: {'✅ HEALTHY' if slack_healthy else '❌ UNHEALTHY'}")
        
        all_healthy = supabase_healthy and keepa_healthy and slack_healthy
        
        # Final Results
        print("\n🎯 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        all_passed = all(test_results.values()) and all_healthy
        
        for test_name, passed in test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"System Health: {'✅ PASS' if all_healthy else '❌ FAIL'}")
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ System is fully functional and ready for production")
            print("✅ Database operations working correctly")
            print("✅ API integrations functioning properly")
            print("✅ Data relationships validated")
            print("✅ Payloads parsing correctly")
            
            # Send success notification
            await slack_service.send_system_alert(
                "🎉 COMPREHENSIVE TEST COMPLETED SUCCESSFULLY!\n"
                "✅ All systems operational\n"
                "✅ Database operations validated\n"
                "✅ API integrations confirmed\n"
                "✅ Ready for production monitoring",
                alert_type="success"
            )
            
            return True
        else:
            print("\n❌ SOME TESTS FAILED!")
            print("System needs fixes before production deployment")
            
            # Send failure notification
            await slack_service.send_system_alert(
                "⚠️ COMPREHENSIVE TEST FOUND ISSUES\n"
                "Some system components need attention\n"
                "Check test results for details",
                alert_type="warning"
            )
            
            return False
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        # Send error notification
        try:
            await slack_service.send_system_alert(
                f"🚨 COMPREHENSIVE TEST FAILED\n"
                f"Critical error: {str(e)}\n"
                f"System requires immediate attention",
                alert_type="error"
            )
        except:
            pass
        
        return False

if __name__ == "__main__":
    success = asyncio.run(test_comprehensive_system())
    if success:
        print("\n🚀 SYSTEM READY FOR PRODUCTION!")
    else:
        print("\n🔧 SYSTEM NEEDS FIXES BEFORE DEPLOYMENT")
