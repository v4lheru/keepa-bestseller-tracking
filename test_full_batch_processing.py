#!/usr/bin/env python3
"""
Comprehensive test of the entire batch processing flow.
Tests the complete pipeline from ASIN retrieval to badge detection.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_full_batch_processing():
    """Test the complete batch processing pipeline."""
    
    print("🔍 TESTING FULL BATCH PROCESSING PIPELINE")
    print("=" * 50)
    
    try:
        # Import services
        from src.services.asin_tracker import asin_tracker
        from src.services.keepa_service import keepa_service
        from src.config.supabase_http import supabase_client
        
        # Test 1: Get ASINs from database
        print("\n✅ Test 1: Get ASINs from Database")
        asins_to_check = await asin_tracker.get_asins_to_check(limit=3)
        print(f"   Retrieved {len(asins_to_check)} ASINs for testing")
        
        if not asins_to_check:
            print("   ❌ No ASINs found in database")
            return False
        
        # Show sample ASIN
        sample_asin = asins_to_check[0]
        print(f"   Sample ASIN: {sample_asin.get('asin', 'Unknown')}")
        print(f"   Product: {sample_asin.get('product_title', 'No title')}")
        
        # Test 2: Call Keepa API
        print("\n✅ Test 2: Call Keepa API")
        test_asins = [asin_data["asin"] for asin_data in asins_to_check]
        
        try:
            products, api_metadata = await keepa_service.get_products_batch(test_asins)
            print(f"   ✅ Keepa API call successful")
            print(f"   ASINs requested: {len(test_asins)}")
            print(f"   Products returned: {len(products)}")
            print(f"   Tokens left: {api_metadata.get('tokens_left', 'Unknown')}")
            print(f"   Response time: {api_metadata.get('response_time_ms', 0)}ms")
            
            if not products:
                print("   ❌ No products returned from Keepa")
                return False
                
        except Exception as e:
            print(f"   ❌ Keepa API call failed: {e}")
            return False
        
        # Test 3: Parse Product Data
        print("\n✅ Test 3: Parse Product Data")
        sample_product = products[0]
        print(f"   ASIN: {sample_product.asin}")
        print(f"   Title: {sample_product.title}")
        print(f"   Brand: {sample_product.brand}")
        print(f"   Sales Ranks: {sample_product.sales_ranks}")
        print(f"   Category Tree: {sample_product.category_tree}")
        
        # Test 4: Extract Best Seller Badges
        print("\n✅ Test 4: Extract Best Seller Badges")
        try:
            badges = keepa_service.extract_bestseller_badges(sample_product)
            print(f"   ✅ Badge extraction successful")
            print(f"   Badges found: {len(badges)}")
            
            for badge in badges:
                print(f"   - {badge.category_name} (ID: {badge.category_id}): Rank #{badge.rank}")
                
        except Exception as e:
            print(f"   ❌ Badge extraction failed: {e}")
            return False
        
        # Test 5: Database Operations
        print("\n✅ Test 5: Database Operations")
        try:
            # Test getting current state
            current_state = await supabase_client.get_asin_current_state(sample_product.asin)
            print(f"   Current state exists: {current_state is not None}")
            
            # Test creating/updating state
            state_data = {
                "bestseller_badges": [badge.model_dump() for badge in badges],
                "sales_ranks": sample_product.sales_ranks or {},
                "category_tree": sample_product.category_tree or [],
                "product_title": sample_product.title,
                "brand": sample_product.brand,
                "updated_at": "2025-08-09T18:00:00Z"
            }
            
            success = await supabase_client.update_asin_current_state(sample_product.asin, state_data)
            print(f"   ✅ Database update successful: {success}")
            
        except Exception as e:
            print(f"   ❌ Database operations failed: {e}")
            return False
        
        # Test 6: Full Batch Processing
        print("\n✅ Test 6: Full Batch Processing")
        try:
            # Process just 1 ASIN to avoid using too many tokens
            single_asin = [asins_to_check[0]]
            result = await asin_tracker.process_batch(single_asin)
            
            print(f"   ✅ Batch processing successful")
            print(f"   Batch ID: {result.batch_id}")
            print(f"   ASINs processed: {result.asins_processed}")
            print(f"   Successful checks: {result.successful_checks}")
            print(f"   Failed checks: {result.failed_checks}")
            print(f"   Changes detected: {result.changes_detected}")
            print(f"   Notifications sent: {result.notifications_sent}")
            print(f"   Processing time: {result.processing_time_seconds}s")
            print(f"   Estimated cost: {result.estimated_cost_cents} cents")
            
        except Exception as e:
            print(f"   ❌ Batch processing failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return False
        
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ The batch processing pipeline is working correctly")
        print("✅ Ready for Railway deployment")
        return True
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_batch_processing())
    if success:
        print("\n🚀 READY FOR DEPLOYMENT!")
    else:
        print("\n❌ NEEDS FIXING BEFORE DEPLOYMENT")
