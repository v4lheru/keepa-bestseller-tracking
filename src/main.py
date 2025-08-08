"""
Main FastAPI application for Best Seller Badge Tracker.
Entry point for the web server and API endpoints.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import settings
from src.config.database import init_database, close_database
from src.config.logging import get_logger
from src.services.scheduler import scheduler_service
from src.models.schemas import HealthCheck, SystemStatus
from src import __version__

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Best Seller Badge Tracker", version=__version__)
    
    try:
        # Try to initialize database (optional for now)
        try:
            await init_database()
            logger.info("Database initialized")
        except Exception as db_error:
            logger.warning("Database initialization failed, continuing without DB", error=str(db_error))
        
        # Start scheduler (will handle DB unavailability)
        try:
            await scheduler_service.start()
            logger.info("Scheduler started")
        except Exception as scheduler_error:
            logger.warning("Scheduler start failed, continuing without scheduler", error=str(scheduler_error))
        
        # Application is ready
        logger.info("Application startup completed")
        
        yield
        
    except Exception as e:
        logger.error("Application startup failed", error=str(e))
        # Don't raise - allow app to start even with some failures
        yield
    
    finally:
        # Shutdown
        logger.info("Shutting down application")
        
        try:
            # Stop scheduler
            await scheduler_service.stop()
            logger.info("Scheduler stopped")
            
            # Close database connections
            await close_database()
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
        
        logger.info("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="Best Seller Badge Tracker",
    description="Monitor Amazon ASINs for Best Seller badge changes and send Slack notifications",
    version=__version__,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else ["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Basic health check endpoint."""
    from src.config.database import db_manager
    from src.services.keepa_service import keepa_service
    from src.services.slack_service import slack_service
    
    # Check service health
    db_healthy = await db_manager.health_check()
    keepa_healthy = await keepa_service.health_check()
    slack_healthy = await slack_service.health_check()
    
    # Calculate uptime (simplified)
    uptime_seconds = 0  # Would need to track actual startup time
    
    services = {
        "database": db_healthy,
        "keepa_api": keepa_healthy,
        "slack_api": slack_healthy,
        "scheduler": scheduler_service.is_running
    }
    
    # Determine overall status
    status = "healthy" if all(services.values()) else "degraded"
    
    return HealthCheck(
        status=status,
        timestamp=datetime.utcnow(),
        version=__version__,
        database_connected=db_healthy,
        services=services,
        uptime_seconds=uptime_seconds
    )


# System status endpoint
@app.get("/status", response_model=SystemStatus)
async def system_status():
    """Detailed system status endpoint."""
    from src.config.database import get_db_session
    from src.models.database import TrackedAsin, BestsellerChange
    from sqlalchemy import select, func
    from datetime import timedelta
    
    # Get basic health
    health = await health_check()
    
    # Get database statistics
    async with get_db_session() as session:
        # Count active ASINs
        active_asins_result = await session.execute(
            select(func.count(TrackedAsin.id)).where(TrackedAsin.is_active == True)
        )
        active_asins = active_asins_result.scalar() or 0
        
        # Count ASINs needing checks (simplified)
        pending_checks = 0  # Would need more complex query
        
        # Count recent changes (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_changes_result = await session.execute(
            select(func.count(BestsellerChange.id)).where(
                BestsellerChange.detected_at >= yesterday
            )
        )
        recent_changes = recent_changes_result.scalar() or 0
    
    # Get scheduler status
    scheduler_status = scheduler_service.get_status()
    
    # Mock API usage stats for today
    api_usage_today = {
        "total_calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "tokens_consumed": 0,
        "estimated_cost_cents": 0,
        "avg_response_time_ms": 0.0,
        "period_start": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
        "period_end": datetime.utcnow()
    }
    
    return SystemStatus(
        health=health,
        active_asins=active_asins,
        pending_checks=pending_checks,
        recent_changes=recent_changes,
        api_usage_today=api_usage_today,
        last_batch_run=datetime.fromisoformat(scheduler_status["last_batch_run"]) if scheduler_status["last_batch_run"] else None,
        next_batch_run=datetime.fromisoformat(scheduler_status["next_batch_run"]) if scheduler_status["next_batch_run"] else None
    )


# Manual batch trigger endpoint
@app.post("/trigger-batch")
async def trigger_manual_batch(
    priority_filter: int = None,
    limit: int = None
):
    """Trigger a manual batch processing run."""
    try:
        result = await scheduler_service.trigger_manual_batch(
            priority_filter=priority_filter,
            limit=limit
        )
        
        return {
            "success": True,
            "message": "Manual batch triggered successfully",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Manual batch trigger failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger manual batch: {str(e)}"
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "name": "Best Seller Badge Tracker",
        "version": __version__,
        "description": "Monitor Amazon ASINs for Best Seller badge changes",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "docs": "/docs" if not settings.is_production else "disabled",
            "trigger_batch": "/trigger-batch"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=not settings.is_production
    )
