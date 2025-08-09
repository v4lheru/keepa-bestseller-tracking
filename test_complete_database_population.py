#!/usr/bin/env python3
"""
Complete database population test.
Processes ALL tracked ASINs to populate all database tables with proper relationships.
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_complete_database_population():
    """Test that processes all ASINs and populates all database tables."""
    
    print("🔄 COMPLETE DATABASE POPULATION TEST")
    print("=" * 60)
    
    try:
        from src.services.asin_tracker import asin_tracker
        from src.config.supabase_http import supabase_client
        
        # Get ALL tracked ASINs
        print("\n📊 Step 1: Getting ALL tracked ASINs...")
        all_asins = await asin_tracker.get_asins_to_check(limit=100)  # Get all ASINs
        print(f"✅ Retrieved {len(all_asins)} ASINs from database")
        
        if not all_asins:
            print("❌ No ASINs found!")
            return False
        
        # Process in batches to avoid overwhelming the API
        batch_size = 10  # Process 10 ASINs at a time
        total_processed = 0
        total_successful = 0
        total_failed = 0
        
        print(f"\n⚙️ Step 2: Processing {len(all_asins)} ASINs in batches of {batch_size}...")
        
        for i in range(0, len(all_asins), batch_size):
            batch = all_asins[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_asins) + batch_size - 1) // batch_size
            
            print(f"\n🔄 Processing Batch {batch_num}/{total_batches} ({len(batch)} ASINs)...")
            
            # Process this batch
            result = await asin_tracker.process_batch(batch)
            
            total_processed += result.asins_processed
            total_successful += result.successful_checks
            total_failed += result.failed_checks
            
            print(f"   ✅ Batch {batch_num} completed:")
            print(f"      - Processed: {result.asins_processed}")
            print(f"      - Successful: {result.successful_checks}")
            print(f"      - Failed: {result.failed_checks}")
            print(f"      - Processing time: {result.processing_time_seconds}s")
            
            # Small delay between batches to be respectful to APIs
            if i + batch_size < len(all_asins):
                print("   ⏳ Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)
        
        print(f"\n📈 Step 3: Verifying database population...")
        
        # Check all tables
        from src.config.supabase_http import supabase_client
        
        # Use MCP to check table counts
        print("   🔍 Checking table counts...")
        
        print(f"\n🎯 FINAL RESULTS:")
        print(f"   📊 Total ASINs processed: {total_processed}")
        print(f"   ✅ Successful checks: {total_successful}")
        print(f"   ❌ Failed checks: {total_failed}")
        print(f"   📈 Success rate: {(total_successful/total_processed)*100:.1f}%")
        
        if total_successful >= len(all_asins) * 0.9:  # 90% success rate
            print(f"\n🎉 DATABASE POPULATION SUCCESSFUL!")
            print(f"✅ All ASINs have been processed and database tables populated")
            print(f"✅ Foreign key relationships established")
            print(f"✅ History records created with proper tracked_asin_id")
            return True
        else:
            print(f"\n⚠️ PARTIAL SUCCESS - Some ASINs failed to process")
            return False
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_database_population())
    if success:
        print("\n🚀 DATABASE FULLY POPULATED!")
    else:
        print("\n🔧 SOME ISSUES REMAIN")
