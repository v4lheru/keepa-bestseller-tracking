"""
Pydantic schemas for API request/response validation.
Defines data structures for the Best Seller Badge Tracker API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ASIN Management Schemas
class AsinCreate(BaseModel):
    """Schema for creating a new tracked ASIN."""
    asin: str = Field(..., min_length=10, max_length=10, description="Amazon ASIN")
    client_id: Optional[UUID] = Field(None, description="Client ID for multi-tenant support")
    monitoring_frequency: int = Field(default=60, ge=15, le=1440, description="Check frequency in minutes")
    priority: int = Field(default=1, ge=1, le=5, description="Priority level (1=highest)")
    
    @validator('asin')
    def validate_asin(cls, v):
        """Validate ASIN format."""
        if not v.isalnum():
            raise ValueError('ASIN must be alphanumeric')
        return v.upper()


class AsinUpdate(BaseModel):
    """Schema for updating tracked ASIN settings."""
    monitoring_frequency: Optional[int] = Field(None, ge=15, le=1440)
    priority: Optional[int] = Field(None, ge=1, le=5)
    is_active: Optional[bool] = None


class AsinResponse(BaseSchema):
    """Schema for ASIN response data."""
    id: UUID
    asin: str
    client_id: Optional[UUID]
    product_title: Optional[str]
    brand: Optional[str]
    main_category: Optional[str]
    sub_categories: List[str]
    monitoring_frequency: int
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_checked_at: Optional[datetime]


class BulkAsinCreate(BaseModel):
    """Schema for bulk ASIN creation."""
    asins: List[AsinCreate] = Field(..., min_items=1, max_items=100)


# Best Seller Badge Schemas
class BestSellerBadge(BaseModel):
    """Schema for Best Seller badge information."""
    category_id: str
    category_name: str
    rank: int
    is_bestseller: bool = Field(default=True)


class AsinCurrentStateResponse(BaseSchema):
    """Schema for current ASIN state."""
    id: UUID
    asin: str
    product_title: Optional[str]
    brand: Optional[str]
    bestseller_badges: List[BestSellerBadge]
    sales_ranks: Dict[str, int]
    current_price: Optional[int]
    availability_amazon: Optional[int]
    monthly_sold: Optional[int]
    updated_at: datetime


# Change Detection Schemas
class BestSellerChange(BaseSchema):
    """Schema for Best Seller badge changes."""
    id: UUID
    asin: str
    change_type: str
    category: str
    category_id: Optional[str]
    previous_rank: Optional[int]
    new_rank: Optional[int]
    previous_badge_status: bool
    new_badge_status: bool
    detected_at: datetime
    notification_sent: bool


class ChangesSummary(BaseModel):
    """Schema for changes summary."""
    total_changes: int
    badges_gained: int
    badges_lost: int
    rank_changes: int
    period_start: datetime
    period_end: datetime
    changes: List[BestSellerChange]


# Notification Schemas
class NotificationCreate(BaseModel):
    """Schema for creating notifications."""
    notification_type: str
    delivery_method: str = Field(default="slack")
    recipient: str
    subject: Optional[str] = None
    message_body: str


class NotificationResponse(BaseSchema):
    """Schema for notification response."""
    id: UUID
    notification_type: str
    delivery_method: str
    recipient: str
    status: str
    delivery_attempts: int
    created_at: datetime
    delivered_at: Optional[datetime]
    error_message: Optional[str]


# API Usage and Analytics Schemas
class ApiUsageStats(BaseModel):
    """Schema for API usage statistics."""
    total_calls: int
    successful_calls: int
    failed_calls: int
    tokens_consumed: int
    estimated_cost_cents: int
    avg_response_time_ms: float
    period_start: datetime
    period_end: datetime


class BatchProcessingResult(BaseModel):
    """Schema for batch processing results."""
    batch_id: UUID
    asins_processed: int
    processing_time_seconds: int
    successful_checks: int
    failed_checks: int
    changes_detected: int
    notifications_sent: int
    estimated_cost_cents: int


# Health Check Schemas
class HealthCheck(BaseModel):
    """Schema for health check response."""
    status: str = Field(default="healthy")
    timestamp: datetime
    version: str
    database_connected: bool
    services: Dict[str, bool]
    uptime_seconds: int


class SystemStatus(BaseModel):
    """Schema for detailed system status."""
    health: HealthCheck
    active_asins: int
    pending_checks: int
    recent_changes: int
    api_usage_today: ApiUsageStats
    last_batch_run: Optional[datetime]
    next_batch_run: Optional[datetime]


# Dashboard Schemas
class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""
    total_asins: int
    active_asins: int
    total_badges: int
    changes_today: int
    changes_this_week: int
    api_calls_today: int
    estimated_cost_today_cents: int
    top_categories: List[Dict[str, Any]]
    recent_changes: List[BestSellerChange]


class CategoryStats(BaseModel):
    """Schema for category statistics."""
    category_id: str
    category_name: str
    total_asins: int
    bestseller_count: int
    changes_count: int
    avg_rank: float


# Error Schemas
class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    message: str
    timestamp: datetime
    request_id: Optional[str] = None


class ValidationError(BaseModel):
    """Schema for validation errors."""
    field: str
    message: str
    invalid_value: Any


# Keepa Integration Schemas
class KeepaProductData(BaseModel):
    """Schema for Keepa product data."""
    asin: str
    title: Optional[str] = None
    brand: Optional[str] = None
    sales_ranks: Optional[Dict[str, List[int]]] = None
    category_tree: Optional[List[Dict[str, Any]]] = None
    current_price: Optional[int] = None
    availability: Optional[int] = None
    monthly_sold: Optional[int] = None
    last_update: Optional[int] = None


class KeepaApiResponse(BaseModel):
    """Schema for Keepa API response."""
    products: List[KeepaProductData]
    tokens_left: int
    refill_in: int
    refill_rate: int
    timestamp: int


# Slack Integration Schemas
class SlackMessage(BaseModel):
    """Schema for Slack message."""
    channel: str
    text: Optional[str] = None
    blocks: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class SlackNotificationPayload(BaseModel):
    """Schema for Slack notification payload."""
    asin: str
    product_title: str
    change_type: str
    category: str
    category_id: Optional[str]
    previous_rank: Optional[int]
    new_rank: Optional[int]
    detected_at: datetime
    amazon_url: str


# Configuration Schemas
class MonitoringConfig(BaseModel):
    """Schema for monitoring configuration."""
    batch_size: int = Field(default=100, ge=1, le=100)
    check_interval_minutes: int = Field(default=60, ge=15, le=1440)
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay_seconds: int = Field(default=5, ge=1, le=300)
    api_timeout_seconds: int = Field(default=30, ge=10, le=300)


class NotificationSettings(BaseModel):
    """Schema for notification settings."""
    slack_channel_id: str
    trigger_on_gained: bool = True
    trigger_on_lost: bool = True
    trigger_on_rank_change: bool = False
    min_rank_change: int = Field(default=10, ge=1)
    max_notifications_per_hour: int = Field(default=50, ge=1, le=1000)
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


# Manual Operations Schemas
class ManualCheckRequest(BaseModel):
    """Schema for manual check requests."""
    asins: Optional[List[str]] = Field(None, max_items=10)
    force_check: bool = Field(default=False)


class ManualCheckResponse(BaseModel):
    """Schema for manual check response."""
    request_id: UUID
    asins_queued: int
    estimated_completion_time: datetime
    status: str = "queued"
