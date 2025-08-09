"""
Keepa API integration service for Amazon product data.
Handles batch processing, rate limiting, and Best Seller badge detection.
"""

import asyncio
import time
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID
import httpx
import pandas as pd

from src.config.settings import settings
from src.config.logging import LoggerMixin, log_api_call
from src.models.schemas import KeepaProductData, KeepaApiResponse, BestSellerBadge


class KeepaService(LoggerMixin):
    """Service for interacting with the Keepa API."""
    
    def __init__(self):
        self.api_key = settings.keepa_api_key
        self.base_url = "https://api.keepa.com"
        self.timeout = settings.api_timeout_seconds
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay_seconds
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests
        
    async def get_products_batch(
        self, 
        asins: List[str], 
        domain: int = 1,  # 1 = Amazon.com
        stats: int = 7,   # Include sales rank stats
        history: int = 0  # No history data needed
    ) -> Tuple[List[KeepaProductData], Dict[str, Any]]:
        """
        Get product data for multiple ASINs in a single API call.
        
        Args:
            asins: List of ASINs to query (max 100)
            domain: Amazon domain (1 = .com, 2 = .co.uk, etc.)
            stats: Stats parameter for Keepa API
            history: History parameter for Keepa API
            
        Returns:
            Tuple of (product_data_list, api_metadata)
        """
        if len(asins) > 100:
            raise ValueError("Maximum 100 ASINs per batch request")
        
        # Rate limiting
        await self._enforce_rate_limit()
        
        # Prepare request
        asin_string = ",".join(asins)
        url = f"{self.base_url}/product"
        params = {
            "key": self.api_key,
            "domain": domain,
            "asin": asin_string,
            "stats": stats,
            "history": history
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                response_time_ms = int((time.time() - start_time) * 1000)
                data = response.json()
                
                # Log successful API call
                log_api_call(
                    service="keepa",
                    endpoint="/product",
                    method="GET",
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                    asins_count=len(asins),
                    tokens_consumed=len(asins)
                )
                
                # Parse response
                products = []
                if "products" in data and data["products"]:
                    for product_data in data["products"]:
                        if product_data:  # Skip null products
                            product = self._parse_product_data(product_data)
                            products.append(product)
                
                # Extract API metadata
                api_metadata = {
                    "tokens_left": data.get("tokensLeft", 0),
                    "refill_in": data.get("refillIn", 0),
                    "refill_rate": data.get("refillRate", 0),
                    "timestamp": data.get("timestamp", int(time.time())),
                    "response_time_ms": response_time_ms,
                    "asins_requested": len(asins),
                    "products_returned": len(products)
                }
                
                self.logger.info(
                    "Keepa batch request completed",
                    asins_requested=len(asins),
                    products_returned=len(products),
                    tokens_left=api_metadata["tokens_left"],
                    response_time_ms=response_time_ms
                )
                
                return products, api_metadata
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Keepa API HTTP error: {e.response.status_code}"
            log_api_call(
                service="keepa",
                endpoint="/product",
                method="GET",
                status_code=e.response.status_code,
                response_time_ms=int((time.time() - start_time) * 1000),
                error=error_msg,
                asins_count=len(asins)
            )
            raise
            
        except Exception as e:
            error_msg = f"Keepa API error: {str(e)}"
            log_api_call(
                service="keepa",
                endpoint="/product",
                method="GET",
                error=error_msg,
                response_time_ms=int((time.time() - start_time) * 1000),
                asins_count=len(asins)
            )
            raise
    
    def _parse_product_data(self, raw_data: Dict[str, Any]) -> KeepaProductData:
        """Parse raw Keepa product data into structured format."""
        
        # Extract basic product info
        asin = raw_data.get("asin", "")
        title = raw_data.get("title")
        brand = raw_data.get("brand")
        
        # Extract sales ranks (key for Best Seller detection)
        sales_ranks = raw_data.get("salesRanks", {})
        
        # Extract category tree for category name resolution
        category_tree = raw_data.get("categoryTree", [])
        
        # Extract pricing and availability
        current_price = None
        if "data" in raw_data and "NEW" in raw_data["data"]:
            price_data = raw_data["data"]["NEW"]
            if price_data and len(price_data) >= 2:
                current_price = price_data[-1]  # Latest price
        
        availability = None
        if "data" in raw_data and "AVAILABILITY" in raw_data["data"]:
            avail_data = raw_data["data"]["AVAILABILITY"]
            if avail_data and len(avail_data) >= 2:
                availability = avail_data[-1]
        
        # Extract monthly sold estimate
        monthly_sold = raw_data.get("monthlySold")
        
        # Extract timestamps
        last_update = raw_data.get("lastUpdate")
        
        return KeepaProductData(
            asin=asin,
            title=title,
            brand=brand,
            sales_ranks=sales_ranks,
            category_tree=category_tree,
            current_price=current_price,
            availability=availability,
            monthly_sold=monthly_sold,
            last_update=last_update
        )
    
    def extract_bestseller_badges(
        self, 
        product: KeepaProductData
    ) -> List[BestSellerBadge]:
        """
        Extract Best Seller badges from product sales ranks.
        A product has a Best Seller badge if it ranks #1 in any category.
        """
        badges = []
        
        # Handle None sales_ranks
        if not product.sales_ranks:
            return badges
        
        # Create category lookup from category tree (handle None)
        category_lookup = {}
        if product.category_tree:
            for category in product.category_tree:
                if isinstance(category, dict) and "catId" in category and "name" in category:
                    category_lookup[str(category["catId"])] = category["name"]
        
        # Check each sales rank for #1 position
        for category_id, rank_data in product.sales_ranks.items():
            if isinstance(rank_data, list) and len(rank_data) >= 2:
                current_rank = rank_data[1]  # Second element is current rank
                
                if current_rank == 1:  # Best Seller badge!
                    category_name = category_lookup.get(
                        category_id, 
                        f"Category {category_id}"
                    )
                    
                    badge = BestSellerBadge(
                        category_id=category_id,
                        category_name=category_name,
                        rank=current_rank,
                        is_bestseller=True
                    )
                    badges.append(badge)
        
        return badges
    
    def compare_badges(
        self, 
        previous_badges: List[BestSellerBadge], 
        current_badges: List[BestSellerBadge]
    ) -> Dict[str, List[BestSellerBadge]]:
        """
        Compare previous and current badges to detect changes.
        
        Returns:
            Dict with 'gained', 'lost', and 'unchanged' badge lists
        """
        # Convert to sets for comparison
        prev_categories = {badge.category_id for badge in previous_badges}
        curr_categories = {badge.category_id for badge in current_badges}
        
        # Find changes
        gained_categories = curr_categories - prev_categories
        lost_categories = prev_categories - curr_categories
        unchanged_categories = prev_categories & curr_categories
        
        # Build result
        result = {
            "gained": [b for b in current_badges if b.category_id in gained_categories],
            "lost": [b for b in previous_badges if b.category_id in lost_categories],
            "unchanged": [b for b in current_badges if b.category_id in unchanged_categories]
        }
        
        return result
    
    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def get_single_product(self, asin: str) -> Optional[KeepaProductData]:
        """Get data for a single ASIN (convenience method)."""
        products, _ = await self.get_products_batch([asin])
        return products[0] if products else None
    
    def estimate_cost(self, asin_count: int) -> int:
        """
        Estimate cost in cents for checking given number of ASINs.
        Keepa charges $1 per 1000 tokens, 1 token per ASIN.
        """
        tokens_needed = asin_count
        cost_cents = int((tokens_needed / 1000) * 100)  # $1 = 100 cents
        return max(cost_cents, 1)  # Minimum 1 cent
    
    async def health_check(self) -> bool:
        """Check if Keepa API is accessible."""
        try:
            # Use a known ASIN for health check
            test_asin = "B0088PUEPK"  # Western Digital hard drive
            await self.get_single_product(test_asin)
            return True
        except Exception as e:
            self.logger.error("Keepa health check failed", error=str(e))
            return False


# Global service instance
keepa_service = KeepaService()
