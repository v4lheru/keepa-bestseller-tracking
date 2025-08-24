#!/usr/bin/env python3
"""
Comprehensive audit of all Supabase data to identify flaws and mistakes.
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.supabase_http import supabase_client


async def audit_database():
    """Perform comprehensive database audit."""
    print("🔍 COMPREHENSIVE SUPABASE DATA AUDIT")
    print("=" * 70)
    
    issues_found = []
    warnings = []
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            
            # 1. AUDIT TRACKED_ASINS TABLE
            print("\n📋 1. AUDITING TRACKED_ASINS TABLE")
            print("-" * 40)
            
            url = f"{supabase_client.base_url}/tracked_asins?select=*"
            response = await client.get(url, headers=supabase_client.headers)
            
            if response.status_code == 200:
                tracked_asins = response.json()
                print(f"✅ Total tracked ASINs: {len(tracked_asins)}")
                
                # Check for duplicates
                asins = [record['asin'] for record in tracked_asins]
                duplicates = set([asin for asin in asins if asins.count(asin) > 1])
                if duplicates:
                    issues_found.append(f"Duplicate ASINs in tracked_asins: {duplicates}")
                else:
                    print("✅ No duplicate ASINs found")
                
                # Check active vs inactive
                active_count = len([r for r in tracked_asins if r.get('is_active', True)])
                inactive_count = len(tracked_asins) - active_count
                print(f"✅ Active ASINs: {active_count}, Inactive: {inactive_count}")
                
                # Check for missing required fields
                missing_fields = []
                for record in tracked_asins:
                    if not record.get('asin'):
                        missing_fields.append("Missing ASIN")
                    if not record.get('monitoring_frequency'):
                        missing_fields.append(f"Missing frequency for {record.get('asin')}")
                
                if missing_fields:
                    issues_found.extend(missing_fields)
                else:
                    print("✅ All required fields present")
            else:
                issues_found.append(f"Failed to fetch tracked_asins: {response.status_code}")
            
            # 2. AUDIT ASIN_CURRENT_STATE TABLE
            print("\n📊 2. AUDITING ASIN_CURRENT_STATE TABLE")
            print("-" * 40)
            
            url = f"{supabase_client.base_url}/asin_current_state?select=*"
            response = await client.get(url, headers=supabase_client.headers)
            
            if response.status_code == 200:
                current_states = response.json()
                print(f"✅ Total current state records: {len(current_states)}")
                
                # Check if all tracked ASINs have current state
                tracked_asin_set = set(asins) if 'asins' in locals() else set()
                current_state_asins = set([r['asin'] for r in current_states])
                missing_states = tracked_asin_set - current_state_asins
                
                if missing_states:
                    warnings.append(f"ASINs without current state: {len(missing_states)} ASINs")
                    print(f"⚠️  ASINs missing current state: {len(missing_states)}")
                else:
                    print("✅ All tracked ASINs have current state")
                
                # Check for orphaned current states
                orphaned_states = current_state_asins - tracked_asin_set
                if orphaned_states:
                    warnings.append(f"Orphaned current states: {len(orphaned_states)} ASINs")
                    print(f"⚠️  Orphaned current states: {len(orphaned_states)}")
                
                # Check data quality
                null_titles = len([r for r in current_states if not r.get('product_title')])
                null_badges = len([r for r in current_states if not r.get('bestseller_badges')])
                print(f"📊 Records with null titles: {null_titles}")
                print(f"📊 Records with null badges: {null_badges}")
                
            else:
                issues_found.append(f"Failed to fetch asin_current_state: {response.status_code}")
            
            # 3. AUDIT ASIN_HISTORY TABLE
            print("\n📚 3. AUDITING ASIN_HISTORY TABLE")
            print("-" * 40)
            
            # Get recent history (last 7 days)
            cutoff_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
            url = f"{supabase_client.base_url}/asin_history?select=*&check_timestamp=gte.{cutoff_date}&limit=1000"
            response = await client.get(url, headers=supabase_client.headers)
            
            if response.status_code == 200:
                history_records = response.json()
                print(f"✅ Recent history records (7 days): {len(history_records)}")
                
                # Check for missing foreign keys
                missing_fk = len([r for r in history_records if not r.get('tracked_asin_id')])
                if missing_fk > 0:
                    issues_found.append(f"History records missing tracked_asin_id: {missing_fk}")
                else:
                    print("✅ All history records have foreign keys")
                
                # Check data completeness
                null_raw_data = len([r for r in history_records if not r.get('raw_keepa_response')])
                null_sales_ranks = len([r for r in history_records if not r.get('sales_ranks')])
                
                print(f"📊 Records with null raw_keepa_response: {null_raw_data}")
                print(f"📊 Records with null sales_ranks: {null_sales_ranks}")
                
                if null_raw_data > len(history_records) * 0.1:  # More than 10%
                    warnings.append(f"High percentage of null raw Keepa data: {null_raw_data}/{len(history_records)}")
                
                # Check for recent activity
                today_records = len([r for r in history_records if r.get('check_timestamp', '').startswith(datetime.utcnow().date().isoformat())])
                print(f"📊 Records from today: {today_records}")
                
                if today_records == 0:
                    warnings.append("No history records from today - system may not be running")
                
            else:
                issues_found.append(f"Failed to fetch asin_history: {response.status_code}")
            
            # 4. AUDIT API_USAGE_LOG TABLE
            print("\n💰 4. AUDITING API_USAGE_LOG TABLE")
            print("-" * 40)
            
            url = f"{supabase_client.base_url}/api_usage_log?select=*&processing_completed_at=gte.{cutoff_date}"
            response = await client.get(url, headers=supabase_client.headers)
            
            if response.status_code == 200:
                api_logs = response.json()
                print(f"✅ Recent API usage logs: {len(api_logs)}")
                
                # Check for cost calculation accuracy
                total_tokens = sum([r.get('tokens_consumed', 0) for r in api_logs])
                total_cost_cents = sum([r.get('estimated_cost_cents', 0) for r in api_logs])
                expected_cost = total_tokens * 0.1  # $0.001 per token = 0.1 cents
                
                print(f"📊 Total tokens consumed: {total_tokens}")
                print(f"📊 Total cost (cents): {total_cost_cents}")
                print(f"📊 Expected cost (cents): {expected_cost}")
                
                if abs(total_cost_cents - expected_cost) > 10:  # More than 10 cents difference
                    warnings.append(f"Cost calculation discrepancy: {total_cost_cents} vs {expected_cost} cents")
                
                # Check for missing batch IDs
                missing_batch_ids = len([r for r in api_logs if not r.get('batch_id')])
                if missing_batch_ids > 0:
                    warnings.append(f"API logs missing batch_id: {missing_batch_ids}")
                
            else:
                issues_found.append(f"Failed to fetch api_usage_log: {response.status_code}")
            
            # 5. AUDIT BESTSELLER_CHANGES TABLE
            print("\n🏆 5. AUDITING BESTSELLER_CHANGES TABLE")
            print("-" * 40)
            
            url = f"{supabase_client.base_url}/bestseller_changes?select=*"
            response = await client.get(url, headers=supabase_client.headers)
            
            if response.status_code == 200:
                changes = response.json()
                print(f"✅ Total bestseller changes: {len(changes)}")
                
                if len(changes) == 0:
                    print("📊 No badge changes recorded (expected based on analysis)")
                else:
                    # Analyze changes
                    gained = len([r for r in changes if r.get('change_type') == 'gained'])
                    lost = len([r for r in changes if r.get('change_type') == 'lost'])
                    print(f"📊 Badges gained: {gained}, lost: {lost}")
                    
                    # Check for notification status
                    notified = len([r for r in changes if r.get('notification_sent')])
                    print(f"📊 Changes with notifications sent: {notified}")
                
            else:
                issues_found.append(f"Failed to fetch bestseller_changes: {response.status_code}")
            
            # 6. AUDIT ERROR_LOG TABLE
            print("\n🚨 6. AUDITING ERROR_LOG TABLE")
            print("-" * 40)
            
            url = f"{supabase_client.base_url}/error_log?select=*&occurred_at=gte.{cutoff_date}"
            response = await client.get(url, headers=supabase_client.headers)
            
            if response.status_code == 200:
                errors = response.json()
                print(f"✅ Recent errors (7 days): {len(errors)}")
                
                if len(errors) > 0:
                    # Analyze error types
                    error_types = {}
                    for error in errors:
                        error_type = error.get('error_type', 'unknown')
                        error_types[error_type] = error_types.get(error_type, 0) + 1
                    
                    print("📊 Error breakdown:")
                    for error_type, count in error_types.items():
                        print(f"     {error_type}: {count}")
                        
                        if count > 10:  # More than 10 errors of same type
                            warnings.append(f"High error count for {error_type}: {count}")
                
            else:
                issues_found.append(f"Failed to fetch error_log: {response.status_code}")
            
            # 7. AUDIT NOTIFICATION_LOG TABLE
            print("\n📱 7. AUDITING NOTIFICATION_LOG TABLE")
            print("-" * 40)
            
            url = f"{supabase_client.base_url}/notification_log?select=*&sent_at=gte.{cutoff_date}"
            response = await client.get(url, headers=supabase_client.headers)
            
            if response.status_code == 200:
                notifications = response.json()
                print(f"✅ Recent notifications (7 days): {len(notifications)}")
                
                if len(notifications) > 0:
                    successful = len([n for n in notifications if n.get('success')])
                    failed = len(notifications) - successful
                    print(f"📊 Successful: {successful}, Failed: {failed}")
                    
                    if failed > successful:
                        warnings.append(f"High notification failure rate: {failed}/{len(notifications)}")
                
            else:
                # This might be expected if table doesn't exist yet
                print("⚠️  notification_log table not accessible (may not exist)")
            
            # SUMMARY
            print("\n" + "=" * 70)
            print("📋 COMPREHENSIVE AUDIT SUMMARY")
            print("=" * 70)
            
            if issues_found:
                print("🚨 CRITICAL ISSUES FOUND:")
                for i, issue in enumerate(issues_found, 1):
                    print(f"   {i}. ❌ {issue}")
            else:
                print("✅ NO CRITICAL ISSUES FOUND!")
            
            if warnings:
                print(f"\n⚠️  WARNINGS ({len(warnings)}):")
                for i, warning in enumerate(warnings, 1):
                    print(f"   {i}. ⚠️  {warning}")
            else:
                print("\n✅ NO WARNINGS!")
            
            # Overall health score
            total_checks = 20  # Approximate number of checks performed
            issues_score = max(0, total_checks - len(issues_found) - len(warnings))
            health_percentage = (issues_score / total_checks) * 100
            
            print(f"\n🎯 OVERALL SYSTEM HEALTH: {health_percentage:.1f}%")
            
            if health_percentage >= 90:
                print("🎉 EXCELLENT - System is in great shape!")
            elif health_percentage >= 75:
                print("👍 GOOD - Minor issues to address")
            elif health_percentage >= 50:
                print("⚠️  FAIR - Several issues need attention")
            else:
                print("🚨 POOR - Major issues require immediate attention")
            
            return len(issues_found) == 0 and len(warnings) <= 2
            
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main audit function."""
    success = await audit_database()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Database audit completed successfully!")
        print("🎯 Your system appears to be healthy and functioning properly")
    else:
        print("❌ Database audit found issues that need attention")
        print("🔧 Review the detailed analysis above")


if __name__ == "__main__":
    asyncio.run(main())
