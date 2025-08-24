#!/usr/bin/env python3
"""
Comprehensive analysis of badge detection and data storage issues.
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.supabase_http import supabase_client
from src.services.keepa_service import keepa_service


async def analyze_badge_detection():
    """Analyze badge detection issues in stored data."""
    print("🔍 COMPREHENSIVE BADGE DETECTION ANALYSIS")
    print("=" * 60)
    
    try:
        # Get recent history records
        import httpx
        async with httpx.AsyncClient() as client:
            # Get recent records with raw Keepa data
            url = f"{supabase_client.base_url}/asin_history?select=asin,bestseller_badges,raw_keepa_response&check_timestamp=gte.{(datetime.utcnow() - timedelta(days=1)).isoformat()}&limit=20"
            response = await client.get(url, headers=supabase_client.headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to get history records: {response.status_code}")
                return
            
            records = response.json()
            print(f"📊 Analyzing {len(records)} recent history records...")
            
            # Analyze each record
            issues_found = []
            products_with_good_ranks = []
            
            for i, record in enumerate(records[:10]):  # Analyze first 10
                asin = record['asin']
                stored_badges = record.get('bestseller_badges', [])
                raw_response = record.get('raw_keepa_response', {})
                
                print(f"\n🔍 ASIN {i+1}: {asin}")
                print(f"   Stored badges: {len(stored_badges)}")
                
                if raw_response and 'sales_ranks' in raw_response:
                    sales_ranks = raw_response['sales_ranks']
                    if sales_ranks:
                        print(f"   Sales ranks found: {len(sales_ranks)} categories")
                        
                        # Check for good rankings
                        for category_id, rank_data in sales_ranks.items():
                            if isinstance(rank_data, list) and len(rank_data) >= 2:
                                current_rank = rank_data[1]
                                if current_rank > 0:  # Valid rank
                                    print(f"     Category {category_id}: Rank #{current_rank}")
                                    
                                    if current_rank == 1:
                                        print(f"     🎉 BEST SELLER FOUND! Category {category_id}")
                                        if len(stored_badges) == 0:
                                            issues_found.append(f"ASIN {asin}: Has #1 rank but no stored badges!")
                                    
                                    elif current_rank <= 10:
                                        products_with_good_ranks.append({
                                            'asin': asin,
                                            'category': category_id,
                                            'rank': current_rank
                                        })
                                else:
                                    print(f"     Category {category_id}: No rank (-1)")
                    else:
                        print("   ❌ Sales ranks is null")
                else:
                    print("   ❌ No sales_ranks in raw response")
            
            # Summary
            print("\n" + "=" * 60)
            print("📋 ANALYSIS SUMMARY")
            print("=" * 60)
            
            if issues_found:
                print("🚨 CRITICAL ISSUES FOUND:")
                for issue in issues_found:
                    print(f"   ❌ {issue}")
            else:
                print("✅ No Best Seller badges (#1 ranks) found - this explains 0 changes")
            
            if products_with_good_ranks:
                print(f"\n📈 PRODUCTS WITH GOOD RANKINGS (Top 10):")
                for product in products_with_good_ranks[:5]:
                    print(f"   🎯 {product['asin']}: Rank #{product['rank']} in category {product['category']}")
            
            # Test badge extraction logic
            print(f"\n🧪 TESTING BADGE EXTRACTION LOGIC...")
            if records:
                test_record = records[0]
                if test_record.get('raw_keepa_response'):
                    raw_data = test_record['raw_keepa_response']
                    
                    # Create a mock KeepaProductData object
                    from src.models.schemas import KeepaProductData
                    try:
                        product_data = KeepaProductData(
                            asin=raw_data.get('asin', ''),
                            title=raw_data.get('title'),
                            brand=raw_data.get('brand'),
                            sales_ranks=raw_data.get('sales_ranks', {}),
                            category_tree=raw_data.get('category_tree', []),
                            last_update=raw_data.get('last_update'),
                            availability=raw_data.get('availability'),
                            monthly_sold=raw_data.get('monthly_sold'),
                            current_price=raw_data.get('current_price')
                        )
                        
                        # Test badge extraction
                        badges = keepa_service.extract_bestseller_badges(product_data)
                        print(f"   Extracted badges: {len(badges)}")
                        for badge in badges:
                            print(f"     🏆 {badge.category_name} (ID: {badge.category_id}): Rank #{badge.rank}")
                        
                    except Exception as e:
                        print(f"   ❌ Error testing badge extraction: {e}")
            
            return len(issues_found) == 0
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main analysis function."""
    success = await analyze_badge_detection()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Badge detection analysis completed!")
        print("📊 The '0 badge changes' appears to be accurate - no #1 rankings found")
    else:
        print("❌ Issues found in badge detection system")
        print("🔧 Review the analysis above for details")


if __name__ == "__main__":
    asyncio.run(main())
