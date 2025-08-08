"""
Application settings and configuration management.
All sensitive data loaded from environment variables only.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: str = Field(..., description="Supabase service role key")
    
    # Keepa API Configuration
    keepa_api_key: str = Field(..., description="Keepa API access key")
    
    # Slack Configuration
    slack_bot_token: str = Field(..., description="Slack bot token")
    slack_channel_id: str = Field(default="C099RR0Q8RJ", description="Slack channel ID")
    
    # Application Configuration
    environment: str = Field(default="development", description="Environment (development/production)")
    port: int = Field(default=8000, description="Application port")
    log_level: str = Field(default="info", description="Logging level")
    
    # Monitoring Configuration
    batch_size: int = Field(default=100, description="ASINs per Keepa API call")
    check_interval_minutes: int = Field(default=60, description="Check interval in minutes")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=5, description="Delay between retries")
    api_timeout_seconds: int = Field(default=30, description="API timeout in seconds")
    
    # Cost Management
    max_daily_api_calls: int = Field(default=10000, description="Maximum daily API calls")
    cost_alert_threshold_cents: int = Field(default=5000, description="Cost alert threshold in cents")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def database_url(self) -> str:
        """Get database connection URL."""
        # Use the correct Supabase database host
        return f"postgresql+asyncpg://postgres:{self.supabase_service_key}@db.dacxljastlbykwqaivcm.supabase.co:5432/postgres"
    
    def validate_required_settings(self) -> None:
        """Validate that all required settings are present."""
        required_fields = [
            "supabase_url",
            "supabase_service_key", 
            "keepa_api_key",
            "slack_bot_token"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(self, field, None):
                missing_fields.append(field.upper())
        
        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")


# Global settings instance
settings = Settings()

# Note: Validation moved to main.py startup to avoid import-time failures
