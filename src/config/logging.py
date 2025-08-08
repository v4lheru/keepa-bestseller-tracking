"""
Structured logging configuration for the Best Seller Badge Tracker.
Provides consistent logging across all application components.
"""

import logging
import sys
from typing import Any, Dict
import structlog
from pythonjsonlogger import jsonlogger

from .settings import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Set log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger instance for this class."""
        return get_logger(self.__class__.__name__)


def log_api_call(
    service: str,
    endpoint: str,
    method: str = "GET",
    status_code: int = None,
    response_time_ms: int = None,
    error: str = None,
    **kwargs
) -> None:
    """Log API call details in a structured format."""
    logger = get_logger("api_calls")
    
    log_data = {
        "service": service,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "error": error,
        **kwargs
    }
    
    if error:
        logger.error("API call failed", **log_data)
    else:
        logger.info("API call completed", **log_data)


def log_asin_check(
    asin: str,
    badges_found: int,
    changes_detected: int,
    processing_time_ms: int,
    error: str = None,
    **kwargs
) -> None:
    """Log ASIN check results in a structured format."""
    logger = get_logger("asin_checks")
    
    log_data = {
        "asin": asin,
        "badges_found": badges_found,
        "changes_detected": changes_detected,
        "processing_time_ms": processing_time_ms,
        "error": error,
        **kwargs
    }
    
    if error:
        logger.error("ASIN check failed", **log_data)
    else:
        logger.info("ASIN check completed", **log_data)


def log_notification_sent(
    notification_type: str,
    recipient: str,
    delivery_method: str,
    success: bool,
    error: str = None,
    **kwargs
) -> None:
    """Log notification delivery in a structured format."""
    logger = get_logger("notifications")
    
    log_data = {
        "notification_type": notification_type,
        "recipient": recipient,
        "delivery_method": delivery_method,
        "success": success,
        "error": error,
        **kwargs
    }
    
    if not success:
        logger.error("Notification delivery failed", **log_data)
    else:
        logger.info("Notification delivered successfully", **log_data)


def log_batch_processing(
    batch_id: str,
    asins_count: int,
    processing_time_seconds: int,
    successful_checks: int,
    failed_checks: int,
    changes_detected: int,
    notifications_sent: int,
    **kwargs
) -> None:
    """Log batch processing results in a structured format."""
    logger = get_logger("batch_processing")
    
    log_data = {
        "batch_id": batch_id,
        "asins_count": asins_count,
        "processing_time_seconds": processing_time_seconds,
        "successful_checks": successful_checks,
        "failed_checks": failed_checks,
        "changes_detected": changes_detected,
        "notifications_sent": notifications_sent,
        **kwargs
    }
    
    logger.info("Batch processing completed", **log_data)


# Initialize logging when module is imported
configure_logging()
