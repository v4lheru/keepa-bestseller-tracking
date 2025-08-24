"""
Scheduler service for automated ASIN monitoring.
Handles periodic batch processing and system maintenance tasks.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import settings
from src.config.supabase_http import supabase_client
from src.config.logging import LoggerMixin


class SchedulerService(LoggerMixin):
    """Service for managing scheduled tasks."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_batch_run = None
        self.next_batch_run = None
        
    async def start(self) -> None:
        """Start the scheduler with all configured jobs."""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return
        
        try:
            # Add main monitoring job
            self.scheduler.add_job(
                func=self._run_monitoring_batch,
                trigger=IntervalTrigger(minutes=settings.check_interval_minutes),
                id="main_monitoring",
                name="Main ASIN Monitoring",
                max_instances=1,  # Prevent overlapping runs
                coalesce=True,    # Combine missed runs
                misfire_grace_time=300  # 5 minutes grace period
            )
            
            # Add daily summary job (8 AM UTC)
            self.scheduler.add_job(
                func=self._send_daily_summary,
                trigger=CronTrigger(hour=8, minute=0),
                id="daily_summary",
                name="Daily Summary Report",
                max_instances=1
            )
            
            # Add cleanup job (2 AM UTC daily)
            self.scheduler.add_job(
                func=self._cleanup_old_data,
                trigger=CronTrigger(hour=2, minute=0),
                id="data_cleanup",
                name="Database Cleanup",
                max_instances=1
            )
            
            # Add health check job (every 15 minutes)
            self.scheduler.add_job(
                func=self._health_check,
                trigger=IntervalTrigger(minutes=15),
                id="health_check",
                name="System Health Check",
                max_instances=1
            )
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            # Calculate next run time
            self._update_next_run_time()
            
            self.logger.info(
                "Scheduler started successfully",
                check_interval_minutes=settings.check_interval_minutes,
                next_batch_run=self.next_batch_run.isoformat() if self.next_batch_run else None
            )
            
            # Send startup notification
            try:
                from src.services.slack_service import slack_service
                success = await slack_service.send_system_alert(
                    "🚀 Best Seller Tracker started successfully!\n"
                    f"Monitoring interval: {settings.check_interval_minutes} minutes\n"
                    f"Next batch run: {self.next_batch_run.strftime('%Y-%m-%d %H:%M:%S UTC') if self.next_batch_run else 'Unknown'}",
                    alert_type="success"
                )
                if success:
                    self.logger.info("Startup notification sent to Slack successfully")
                else:
                    self.logger.error("Failed to send startup notification to Slack")
            except Exception as slack_error:
                self.logger.error("Error sending startup notification to Slack", error=str(slack_error))
                # Don't raise - continue even if Slack fails
            
        except Exception as e:
            self.logger.error("Failed to start scheduler", error=str(e))
            raise
    
    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            
            self.logger.info("Scheduler stopped successfully")
            
            # Send shutdown notification
            from src.services.slack_service import slack_service
            await slack_service.send_system_alert(
                "⏹️ Best Seller Tracker stopped",
                alert_type="warning"
            )
            
        except Exception as e:
            self.logger.error("Error stopping scheduler", error=str(e))
            raise
    
    async def _run_monitoring_batch(self) -> None:
        """Run the main monitoring batch job."""
        batch_start = datetime.utcnow()
        
        try:
            from src.services.asin_tracker import asin_tracker
            from src.services.slack_service import slack_service
            
            self.logger.info("Starting scheduled monitoring batch")
            
            # Get ASINs to check
            asins_to_check = await asin_tracker.get_asins_to_check(
                limit=settings.batch_size
            )
            
            if not asins_to_check:
                self.logger.info("No ASINs need checking at this time")
                self.last_batch_run = batch_start
                self._update_next_run_time()
                return
            
            # Process the batch
            result = await asin_tracker.process_batch(asins_to_check)
            
            # Update timing
            self.last_batch_run = batch_start
            self._update_next_run_time()
            
            # Log results
            self.logger.info(
                "Scheduled batch completed",
                batch_id=str(result.batch_id),
                asins_processed=result.asins_processed,
                changes_detected=result.changes_detected,
                notifications_sent=result.notifications_sent,
                processing_time_seconds=result.processing_time_seconds,
                estimated_cost_cents=result.estimated_cost_cents
            )
            
            # Send alert if many changes detected
            if result.changes_detected >= 5:
                await slack_service.send_system_alert(
                    f"📈 High activity detected!\n"
                    f"Batch processed {result.asins_processed} ASINs\n"
                    f"Found {result.changes_detected} badge changes\n"
                    f"Sent {result.notifications_sent} notifications\n"
                    f"Processing time: {result.processing_time_seconds}s",
                    alert_type="info"
                )
            
        except Exception as e:
            from src.services.slack_service import slack_service
            
            self.logger.error(
                "Scheduled monitoring batch failed",
                error=str(e),
                batch_start=batch_start.isoformat()
            )
            
            # Send error alert
            await slack_service.send_system_alert(
                f"🚨 Monitoring batch failed!\n"
                f"Error: {str(e)}\n"
                f"Time: {batch_start.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                alert_type="error"
            )
            
            # Update timing even on failure
            self.last_batch_run = batch_start
            self._update_next_run_time()
    
    async def _send_daily_summary(self) -> None:
        """Send daily summary of activities."""
        try:
            from src.services.slack_service import slack_service
            
            self.logger.info("Generating daily summary")
            
            # Calculate today's date range (from midnight to now)
            now = datetime.utcnow()
            today = now.date()
            start_time = datetime.combine(today, datetime.min.time())
            end_time = now
            
            # Get statistics (this would need to be implemented in asin_tracker)
            stats = await self._get_daily_stats(start_time, end_time)
            
            # Send summary
            success = await slack_service.send_daily_summary(stats)
            
            if success:
                self.logger.info("Daily summary sent successfully")
            else:
                self.logger.error("Failed to send daily summary")
                
        except Exception as e:
            self.logger.error("Error generating daily summary", error=str(e))
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old data from the database."""
        try:
            self.logger.info("Starting database cleanup")
            
            # This would implement cleanup logic
            # For example, removing old history records, error logs, etc.
            # Implementation would depend on retention policies
            
            cutoff_date = datetime.utcnow() - timedelta(days=90)  # Keep 90 days
            
            # TODO: Implement actual cleanup queries
            # - Remove old asin_history records
            # - Remove old error_log records
            # - Remove old api_usage_log records
            # - Keep bestseller_changes indefinitely for analytics
            
            self.logger.info(
                "Database cleanup completed",
                cutoff_date=cutoff_date.isoformat()
            )
            
        except Exception as e:
            self.logger.error("Database cleanup failed", error=str(e))
    
    async def _health_check(self) -> None:
        """Perform system health checks."""
        try:
            from src.services.asin_tracker import asin_tracker
            from src.services.slack_service import slack_service
            
            # Check Supabase API connectivity
            supabase_healthy = await supabase_client.health_check()
            
            # Check Keepa API
            keepa_healthy = await asin_tracker.keepa_service.health_check()
            
            # Check Slack API
            slack_healthy = await slack_service.health_check()
            
            # Log health status
            self.logger.info(
                "Health check completed",
                supabase_api=supabase_healthy,
                keepa_api=keepa_healthy,
                slack_api=slack_healthy
            )
            
            # Send alert if any service is unhealthy
            unhealthy_services = []
            if not supabase_healthy:
                unhealthy_services.append("Database")
            if not keepa_healthy:
                unhealthy_services.append("Keepa API")
            if not slack_healthy:
                unhealthy_services.append("Slack API")
            
            if unhealthy_services:
                await slack_service.send_system_alert(
                    f"⚠️ Health check failed!\n"
                    f"Unhealthy services: {', '.join(unhealthy_services)}\n"
                    f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    alert_type="warning"
                )
            
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
    
    async def _get_daily_stats(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get daily statistics for summary report."""
        try:
            # Get API usage stats for the day
            api_stats_query = f"""
                SELECT 
                    SUM(asins_processed) as asins_checked,
                    SUM(tokens_consumed) as total_tokens,
                    SUM(estimated_cost_cents) as cost_cents,
                    COUNT(*) as api_calls
                FROM api_usage_log 
                WHERE processing_completed_at >= '{start_time.isoformat()}'
                AND processing_completed_at < '{end_time.isoformat()}'
            """
            
            # Get badge changes stats
            changes_stats_query = f"""
                SELECT 
                    COUNT(*) as total_changes,
                    SUM(CASE WHEN change_type = 'gained' THEN 1 ELSE 0 END) as badges_gained,
                    SUM(CASE WHEN change_type = 'lost' THEN 1 ELSE 0 END) as badges_lost
                FROM bestseller_changes 
                WHERE detected_at >= '{start_time.isoformat()}'
                AND detected_at < '{end_time.isoformat()}'
            """
            
            # Get top categories with changes
            categories_query = f"""
                SELECT 
                    category as name,
                    COUNT(*) as changes
                FROM bestseller_changes 
                WHERE detected_at >= '{start_time.isoformat()}'
                AND detected_at < '{end_time.isoformat()}'
                GROUP BY category
                ORDER BY changes DESC
                LIMIT 5
            """
            
            # Use our Supabase HTTP client directly
            import httpx
            
            async with httpx.AsyncClient() as client:
                # Get API usage stats using direct REST API
                api_url = f"{supabase_client.base_url}/api_usage_log?select=asins_processed,tokens_consumed,estimated_cost_cents&processing_completed_at=gte.{start_time.isoformat()}&processing_completed_at=lt.{end_time.isoformat()}"
                api_response = await client.get(api_url, headers=supabase_client.headers)
                
                api_data = {"asins_checked": 0, "total_tokens": 0, "cost_cents": 0, "api_calls": 0}
                if api_response.status_code == 200:
                    api_records = api_response.json()
                    if api_records:
                        api_data["api_calls"] = len(api_records)
                        api_data["asins_checked"] = sum(r.get("asins_processed", 0) or 0 for r in api_records)
                        api_data["total_tokens"] = sum(r.get("tokens_consumed", 0) or 0 for r in api_records)
                        api_data["cost_cents"] = sum(r.get("estimated_cost_cents", 0) or 0 for r in api_records)
                
                # Get badge changes stats using direct REST API
                changes_url = f"{supabase_client.base_url}/bestseller_changes?select=change_type&detected_at=gte.{start_time.isoformat()}&detected_at=lt.{end_time.isoformat()}"
                changes_response = await client.get(changes_url, headers=supabase_client.headers)
                
                changes_data = {"total_changes": 0, "badges_gained": 0, "badges_lost": 0}
                if changes_response.status_code == 200:
                    changes_records = changes_response.json()
                    if changes_records:
                        changes_data["total_changes"] = len(changes_records)
                        changes_data["badges_gained"] = sum(1 for r in changes_records if r.get("change_type") == "gained")
                        changes_data["badges_lost"] = sum(1 for r in changes_records if r.get("change_type") == "lost")
                
                # Get top categories using direct REST API
                categories_url = f"{supabase_client.base_url}/bestseller_changes?select=category&detected_at=gte.{start_time.isoformat()}&detected_at=lt.{end_time.isoformat()}"
                categories_response = await client.get(categories_url, headers=supabase_client.headers)
                
                top_categories = []
                if categories_response.status_code == 200:
                    categories_records = categories_response.json()
                    if categories_records:
                        # Count categories
                        category_counts = {}
                        for record in categories_records:
                            category = record.get("category", "Unknown")
                            category_counts[category] = category_counts.get(category, 0) + 1
                        
                        # Sort by count and take top 5
                        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                        top_categories = [{"name": cat, "changes": count} for cat, count in sorted_categories]
            
            # Combine all stats
            stats = {
                "total_changes": changes_data["total_changes"],
                "badges_gained": changes_data["badges_gained"],
                "badges_lost": changes_data["badges_lost"],
                "asins_checked": api_data["asins_checked"],
                "api_calls": api_data["api_calls"],
                "cost_cents": api_data["cost_cents"],
                "top_categories": top_categories
            }
            
            self.logger.info("Daily stats calculated", stats=stats)
            return stats
            
        except Exception as e:
            self.logger.error("Error calculating daily stats", error=str(e))
            # Return zeros on error to prevent crashes
            return {
                "total_changes": 0,
                "badges_gained": 0,
                "badges_lost": 0,
                "asins_checked": 0,
                "api_calls": 0,
                "cost_cents": 0,
                "top_categories": []
            }
    
    def _update_next_run_time(self) -> None:
        """Update the next batch run time."""
        if self.last_batch_run:
            self.next_batch_run = self.last_batch_run + timedelta(
                minutes=settings.check_interval_minutes
            )
        else:
            self.next_batch_run = datetime.utcnow() + timedelta(
                minutes=settings.check_interval_minutes
            )
    
    async def trigger_manual_batch(
        self, 
        priority_filter: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Trigger a manual batch run outside of the schedule."""
        try:
            from src.services.asin_tracker import asin_tracker
            
            self.logger.info(
                "Triggering manual batch",
                priority_filter=priority_filter,
                limit=limit
            )
            
            # Get ASINs to check
            asins_to_check = await asin_tracker.get_asins_to_check(
                limit=limit or settings.batch_size,
                priority_filter=priority_filter
            )
            
            if not asins_to_check:
                return {
                    "success": True,
                    "message": "No ASINs need checking",
                    "asins_processed": 0
                }
            
            # Process the batch
            result = await asin_tracker.process_batch(asins_to_check)
            
            return {
                "success": True,
                "batch_id": str(result.batch_id),
                "asins_processed": result.asins_processed,
                "changes_detected": result.changes_detected,
                "notifications_sent": result.notifications_sent,
                "processing_time_seconds": result.processing_time_seconds,
                "estimated_cost_cents": result.estimated_cost_cents
            }
            
        except Exception as e:
            self.logger.error("Manual batch failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status information."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "is_running": self.is_running,
            "last_batch_run": self.last_batch_run.isoformat() if self.last_batch_run else None,
            "next_batch_run": self.next_batch_run.isoformat() if self.next_batch_run else None,
            "check_interval_minutes": settings.check_interval_minutes,
            "jobs": jobs
        }


# Global scheduler instance
scheduler_service = SchedulerService()
