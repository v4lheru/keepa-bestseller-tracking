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
            from src.services.slack_service import slack_service
            await slack_service.send_system_alert(
                "🚀 Best Seller Tracker started successfully!\n"
                f"Monitoring interval: {settings.check_interval_minutes} minutes\n"
                f"Next batch run: {self.next_batch_run.strftime('%Y-%m-%d %H:%M:%S UTC') if self.next_batch_run else 'Unknown'}",
                alert_type="success"
            )
            
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
            
            # Calculate yesterday's date range
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            start_time = datetime.combine(yesterday, datetime.min.time())
            end_time = datetime.combine(today, datetime.min.time())
            
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
        # This would query the database for daily stats
        # For now, return mock data
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
