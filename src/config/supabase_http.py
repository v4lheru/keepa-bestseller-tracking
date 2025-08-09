"""
Direct HTTP client for Supabase REST API.
Bypasses the problematic Python client library.
"""

import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .settings import settings
from .logging import get_logger

logger = get_logger(__name__)


class SupabaseHTTPClient:
    """Direct HTTP client for Supabase REST API operations."""
    
    def __init__(self):
        self.base_url = f"{settings.supabase_url}/rest/v1"
        self.headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info("Supabase HTTP client initialized successfully")
    
    async def health_check(self) -> bool:
        """Check if Supabase API is accessible."""
        try:
            response = await self.client.get(
                f"{self.base_url}/simple_asin_status?select=count&limit=1",
                headers=self.headers
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("Supabase health check failed", error=str(e))
            return False
    
    # ASIN Management Methods
    
    async def get_asins_to_check(self, limit: int = 100, priority_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get ASINs that need to be checked."""
        try:
            url = f"{self.base_url}/simple_asin_status?select=*&order=priority.asc,last_checked_at.asc&limit={limit}"
            
            if priority_filter:
                url += f"&priority=eq.{priority_filter}"
            
            response = await self.client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to get ASINs to check", status_code=response.status_code, response=response.text)
                return []
            
        except Exception as e:
            logger.error("Failed to get ASINs to check", error=str(e))
            return []
    
    async def get_asin_current_state(self, asin: str) -> Optional[Dict[str, Any]]:
        """Get current state for an ASIN."""
        try:
            response = await self.client.get(
                f"{self.base_url}/asin_current_state?select=*&asin=eq.{asin}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            else:
                logger.error("Failed to get ASIN current state", asin=asin, status_code=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Failed to get ASIN current state", asin=asin, error=str(e))
            return None
    
    async def update_asin_current_state(self, asin: str, state_data: Dict[str, Any]) -> bool:
        """Update or insert ASIN current state."""
        try:
            # Try to update first
            response = await self.client.patch(
                f"{self.base_url}/asin_current_state?asin=eq.{asin}",
                headers=self.headers,
                json=state_data
            )
            
            # If no rows affected (404), insert new record
            if response.status_code == 404:
                state_data['asin'] = asin
                response = await self.client.post(
                    f"{self.base_url}/asin_current_state",
                    headers=self.headers,
                    json=state_data
                )
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error("Failed to update ASIN current state", asin=asin, error=str(e))
            return False
    
    async def create_history_record(self, history_data: Dict[str, Any]) -> bool:
        """Create a new history record."""
        try:
            response = await self.client.post(
                f"{self.base_url}/asin_history",
                headers=self.headers,
                json=history_data
            )
            return response.status_code == 201
            
        except Exception as e:
            logger.error("Failed to create history record", error=str(e))
            return False
    
    async def create_bestseller_change(self, change_data: Dict[str, Any]) -> Optional[str]:
        """Create a bestseller change record and return the ID."""
        try:
            response = await self.client.post(
                f"{self.base_url}/bestseller_changes",
                headers=self.headers,
                json=change_data
            )
            
            if response.status_code == 201:
                data = response.json()
                return data[0]['id'] if data else None
            else:
                logger.error("Failed to create bestseller change", status_code=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Failed to create bestseller change", error=str(e))
            return None
    
    async def update_bestseller_change_notification(self, change_id: str, notification_data: Dict[str, Any]) -> bool:
        """Update bestseller change with notification status."""
        try:
            response = await self.client.patch(
                f"{self.base_url}/bestseller_changes?id=eq.{change_id}",
                headers=self.headers,
                json=notification_data
            )
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Failed to update bestseller change notification", change_id=change_id, error=str(e))
            return False
    
    async def update_asin_last_checked(self, asin: str) -> bool:
        """Update the last_checked_at timestamp for an ASIN."""
        try:
            response = await self.client.patch(
                f"{self.base_url}/tracked_asins?asin=eq.{asin}",
                headers=self.headers,
                json={"last_checked_at": datetime.utcnow().isoformat()}
            )
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Failed to update ASIN last checked", asin=asin, error=str(e))
            return False
    
    # Logging Methods
    
    async def log_api_usage(self, usage_data: Dict[str, Any]) -> bool:
        """Log API usage statistics."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api_usage_log",
                headers=self.headers,
                json=usage_data
            )
            return response.status_code == 201
            
        except Exception as e:
            logger.error("Failed to log API usage", error=str(e))
            return False
    
    async def log_error(self, error_data: Dict[str, Any]) -> bool:
        """Log error to database."""
        try:
            response = await self.client.post(
                f"{self.base_url}/error_log",
                headers=self.headers,
                json=error_data
            )
            return response.status_code == 201
            
        except Exception as e:
            logger.error("Failed to log error", error=str(e))
            return False
    
    # Analytics Methods
    
    async def get_recent_changes(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent bestseller changes."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            response = await self.client.get(
                f"{self.base_url}/bestseller_changes?select=*&detected_at=gte.{cutoff_time.isoformat()}&order=detected_at.desc",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to get recent changes", status_code=response.status_code)
                return []
                
        except Exception as e:
            logger.error("Failed to get recent changes", error=str(e))
            return []
    
    async def get_asin_count(self) -> int:
        """Get total count of tracked ASINs."""
        try:
            response = await self.client.get(
                f"{self.base_url}/simple_asin_status?select=count",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return len(data)
            else:
                logger.error("Failed to get ASIN count", status_code=response.status_code)
                return 0
                
        except Exception as e:
            logger.error("Failed to get ASIN count", error=str(e))
            return 0
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global Supabase HTTP client instance
supabase_client = SupabaseHTTPClient()
