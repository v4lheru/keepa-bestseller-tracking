"""
Supabase API client configuration and management.
Replaces direct database connections with API calls.
"""

from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from datetime import datetime, timedelta

from .settings import settings
from .logging import get_logger

logger = get_logger(__name__)


class SupabaseClient:
    """Supabase API client for all database operations."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the Supabase client."""
        try:
            # Try to create client with minimal options for better compatibility
            self.client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Supabase client", error=str(e))
            # Don't raise - allow app to start even if Supabase client fails
            # This prevents the entire app from crashing
            self.client = None
            logger.warning("Continuing without Supabase client - health checks will fail")
    
    def _check_client(self) -> bool:
        """Check if client is available."""
        if not self.client:
            logger.error("Supabase client not initialized")
            return False
        return True
    
    async def health_check(self) -> bool:
        """Check if Supabase API is accessible."""
        if not self.client:
            logger.error("Supabase client not initialized")
            return False
        try:
            # Simple query to test connection
            response = self.client.table('simple_asin_status').select('count').limit(1).execute()
            return True
        except Exception as e:
            logger.error("Supabase health check failed", error=str(e))
            return False
    
    # ASIN Management Methods
    
    async def get_asins_to_check(self, limit: int = 100, priority_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get ASINs that need to be checked."""
        if not self._check_client():
            return []
        try:
            query = self.client.table('simple_asin_status').select('*')
            
            if priority_filter:
                query = query.eq('priority', priority_filter)
            
            # Add time-based filtering logic here if needed
            query = query.order('priority', desc=False).order('last_checked_at', desc=False).limit(limit)
            
            response = query.execute()
            return response.data
            
        except Exception as e:
            logger.error("Failed to get ASINs to check", error=str(e))
            return []
    
    async def get_asin_current_state(self, asin: str) -> Optional[Dict[str, Any]]:
        """Get current state for an ASIN."""
        try:
            response = self.client.table('asin_current_state').select('*').eq('asin', asin).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("Failed to get ASIN current state", asin=asin, error=str(e))
            return None
    
    async def update_asin_current_state(self, asin: str, state_data: Dict[str, Any]) -> bool:
        """Update or insert ASIN current state."""
        try:
            # Try to update first
            response = self.client.table('asin_current_state').update(state_data).eq('asin', asin).execute()
            
            # If no rows affected, insert new record
            if not response.data:
                state_data['asin'] = asin
                response = self.client.table('asin_current_state').insert(state_data).execute()
            
            return True
        except Exception as e:
            logger.error("Failed to update ASIN current state", asin=asin, error=str(e))
            return False
    
    async def create_history_record(self, history_data: Dict[str, Any]) -> bool:
        """Create a new history record."""
        try:
            response = self.client.table('asin_history').insert(history_data).execute()
            return True
        except Exception as e:
            logger.error("Failed to create history record", error=str(e))
            return False
    
    async def create_bestseller_change(self, change_data: Dict[str, Any]) -> Optional[str]:
        """Create a bestseller change record and return the ID."""
        try:
            response = self.client.table('bestseller_changes').insert(change_data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error("Failed to create bestseller change", error=str(e))
            return None
    
    async def update_bestseller_change_notification(self, change_id: str, notification_data: Dict[str, Any]) -> bool:
        """Update bestseller change with notification status."""
        try:
            response = self.client.table('bestseller_changes').update(notification_data).eq('id', change_id).execute()
            return True
        except Exception as e:
            logger.error("Failed to update bestseller change notification", change_id=change_id, error=str(e))
            return False
    
    async def update_asin_last_checked(self, asin: str) -> bool:
        """Update the last_checked_at timestamp for an ASIN."""
        try:
            response = self.client.table('tracked_asins').update({
                'last_checked_at': datetime.utcnow().isoformat()
            }).eq('asin', asin).execute()
            return True
        except Exception as e:
            logger.error("Failed to update ASIN last checked", asin=asin, error=str(e))
            return False
    
    # Logging Methods
    
    async def log_api_usage(self, usage_data: Dict[str, Any]) -> bool:
        """Log API usage statistics."""
        try:
            response = self.client.table('api_usage_log').insert(usage_data).execute()
            return True
        except Exception as e:
            logger.error("Failed to log API usage", error=str(e))
            return False
    
    async def log_error(self, error_data: Dict[str, Any]) -> bool:
        """Log error to database."""
        try:
            response = self.client.table('error_log').insert(error_data).execute()
            return True
        except Exception as e:
            logger.error("Failed to log error", error=str(e))
            return False
    
    # Analytics Methods
    
    async def get_recent_changes(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent bestseller changes."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            response = self.client.table('bestseller_changes').select('*').gte(
                'detected_at', cutoff_time.isoformat()
            ).order('detected_at', desc=True).execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get recent changes", error=str(e))
            return []
    
    async def get_asin_count(self) -> int:
        """Get total count of tracked ASINs."""
        try:
            response = self.client.table('simple_asin_status').select('count').execute()
            return len(response.data)
        except Exception as e:
            logger.error("Failed to get ASIN count", error=str(e))
            return 0
    
    # Raw query method for complex operations
    
    async def execute_rpc(self, function_name: str, params: Dict[str, Any] = None) -> Any:
        """Execute a Supabase stored procedure/function."""
        try:
            response = self.client.rpc(function_name, params or {}).execute()
            return response.data
        except Exception as e:
            logger.error("Failed to execute RPC", function=function_name, error=str(e))
            return None


# Global Supabase client instance
supabase_client = SupabaseClient()
