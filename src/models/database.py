"""
SQLAlchemy models for the Best Seller Badge Tracker database.
Maps to existing Supabase tables with proper relationships.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Text, 
    ForeignKey, JSON, CheckConstraint, Time
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from src.config.database import Base


class Client(Base):
    """Client model for multi-tenant support."""
    __tablename__ = "clients"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notification_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tracked_asins: Mapped[List["TrackedAsin"]] = relationship("TrackedAsin", back_populates="client")
    notification_rules: Mapped[List["NotificationRule"]] = relationship("NotificationRule", back_populates="client")
    notification_logs: Mapped[List["NotificationLog"]] = relationship("NotificationLog", back_populates="client")


class TrackedAsin(Base):
    """Tracked ASIN model for monitoring configuration."""
    __tablename__ = "tracked_asins"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    asin: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    client_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"))
    product_title: Mapped[Optional[str]] = mapped_column(Text)
    brand: Mapped[Optional[str]] = mapped_column(String)
    main_category: Mapped[Optional[str]] = mapped_column(String)
    sub_categories: Mapped[list] = mapped_column(JSONB, default=list)
    monitoring_frequency: Mapped[int] = mapped_column(Integer, default=360)  # minutes
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    client: Mapped[Optional["Client"]] = relationship("Client", back_populates="tracked_asins")
    current_state: Mapped[Optional["AsinCurrentState"]] = relationship("AsinCurrentState", back_populates="tracked_asin", uselist=False)
    history: Mapped[List["AsinHistory"]] = relationship("AsinHistory", back_populates="tracked_asin")
    bestseller_changes: Mapped[List["BestsellerChange"]] = relationship("BestsellerChange", back_populates="tracked_asin")


class AsinCurrentState(Base):
    """Current state of tracked ASINs."""
    __tablename__ = "asin_current_state"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    tracked_asin_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("tracked_asins.id"), unique=True)
    asin: Mapped[str] = mapped_column(String(10), nullable=False)
    bestseller_badges: Mapped[list] = mapped_column(JSONB, default=list)
    sales_ranks: Mapped[dict] = mapped_column(JSONB, default=dict)
    category_tree: Mapped[list] = mapped_column(JSONB, default=list)
    product_title: Mapped[Optional[str]] = mapped_column(Text)
    brand: Mapped[Optional[str]] = mapped_column(String)
    current_price: Mapped[Optional[int]] = mapped_column(Integer)  # in cents
    availability_amazon: Mapped[Optional[int]] = mapped_column(Integer)
    monthly_sold: Mapped[Optional[int]] = mapped_column(Integer)
    keepa_last_update: Mapped[Optional[int]] = mapped_column(Integer)
    keepa_processing_time: Mapped[Optional[int]] = mapped_column(Integer)
    raw_keepa_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tracked_asin: Mapped[Optional["TrackedAsin"]] = relationship("TrackedAsin", back_populates="current_state")


class AsinHistory(Base):
    """Historical tracking data for ASINs."""
    __tablename__ = "asin_history"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    tracked_asin_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("tracked_asins.id"))
    asin: Mapped[str] = mapped_column(String(10), nullable=False)
    bestseller_badges: Mapped[list] = mapped_column(JSONB, default=list)
    sales_ranks: Mapped[dict] = mapped_column(JSONB, default=dict)
    category_tree: Mapped[list] = mapped_column(JSONB, default=list)
    product_title: Mapped[Optional[str]] = mapped_column(Text)
    brand: Mapped[Optional[str]] = mapped_column(String)
    availability_amazon: Mapped[Optional[int]] = mapped_column(Integer)
    monthly_sold: Mapped[Optional[int]] = mapped_column(Integer)
    current_price: Mapped[Optional[int]] = mapped_column(Integer)
    keepa_processing_time: Mapped[Optional[int]] = mapped_column(Integer)
    keepa_timestamp: Mapped[Optional[int]] = mapped_column(Integer)
    raw_keepa_response: Mapped[Optional[dict]] = mapped_column(JSONB)
    check_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    api_response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_used: Mapped[int] = mapped_column(Integer, default=1)
    
    # Relationships
    tracked_asin: Mapped[Optional["TrackedAsin"]] = relationship("TrackedAsin", back_populates="history")


class BestsellerChange(Base):
    """Best Seller badge change events."""
    __tablename__ = "bestseller_changes"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    tracked_asin_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("tracked_asins.id"))
    asin: Mapped[str] = mapped_column(String(10), nullable=False)
    change_type: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    category_id: Mapped[Optional[str]] = mapped_column(String)
    previous_rank: Mapped[Optional[int]] = mapped_column(Integer)
    new_rank: Mapped[Optional[int]] = mapped_column(Integer)
    previous_badge_status: Mapped[bool] = mapped_column(Boolean, default=False)
    new_badge_status: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    previous_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notification_method: Mapped[Optional[str]] = mapped_column(String)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('gained', 'lost', 'rank_change')",
            name="valid_change_type"
        ),
    )
    
    # Relationships
    tracked_asin: Mapped[Optional["TrackedAsin"]] = relationship("TrackedAsin", back_populates="bestseller_changes")
    notification_logs: Mapped[List["NotificationLog"]] = relationship("NotificationLog", back_populates="bestseller_change")


class NotificationRule(Base):
    """Notification rules and preferences."""
    __tablename__ = "notification_rules"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"))
    trigger_on_gained: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_on_lost: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_on_rank_change: Mapped[bool] = mapped_column(Boolean, default=False)
    min_rank_change: Mapped[int] = mapped_column(Integer, default=10)
    delivery_method: Mapped[str] = mapped_column(String, nullable=False)
    delivery_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    max_notifications_per_hour: Mapped[int] = mapped_column(Integer, default=10)
    quiet_hours_start: Mapped[Optional[datetime.time]] = mapped_column(Time)
    quiet_hours_end: Mapped[Optional[datetime.time]] = mapped_column(Time)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    client: Mapped[Optional["Client"]] = relationship("Client", back_populates="notification_rules")


class NotificationLog(Base):
    """Notification delivery tracking."""
    __tablename__ = "notification_log"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    bestseller_change_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("bestseller_changes.id"))
    client_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"))
    notification_type: Mapped[str] = mapped_column(String, nullable=False)
    delivery_method: Mapped[str] = mapped_column(String, nullable=False)
    recipient: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(Text)
    message_body: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'retry')",
            name="valid_notification_status"
        ),
    )
    
    # Relationships
    bestseller_change: Mapped[Optional["BestsellerChange"]] = relationship("BestsellerChange", back_populates="notification_logs")
    client: Mapped[Optional["Client"]] = relationship("Client", back_populates="notification_logs")


class ApiUsageLog(Base):
    """API usage and cost tracking."""
    __tablename__ = "api_usage_log"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), default=uuid4)
    processing_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    asins_processed: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_consumed: Mapped[Optional[int]] = mapped_column(Integer)
    api_calls_made: Mapped[Optional[int]] = mapped_column(Integer)
    successful_calls: Mapped[Optional[int]] = mapped_column(Integer)
    failed_calls: Mapped[Optional[int]] = mapped_column(Integer)
    avg_response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    total_processing_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    estimated_cost_cents: Mapped[Optional[int]] = mapped_column(Integer)


class ErrorLog(Base):
    """System error tracking."""
    __tablename__ = "error_log"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    error_type: Mapped[str] = mapped_column(String, nullable=False)
    asin: Mapped[Optional[str]] = mapped_column(String(10))
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text)
    api_endpoint: Mapped[Optional[str]] = mapped_column(String)
    request_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)


class GlobalNotificationSettings(Base):
    """Global notification settings."""
    __tablename__ = "global_notification_settings"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    setting_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    setting_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
