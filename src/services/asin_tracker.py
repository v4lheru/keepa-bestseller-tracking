"""
Core ASIN tracking service that orchestrates Best Seller monitoring.
Handles badge detection, change comparison, and notification triggering.
Uses Supabase API instead of direct database connections.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID, uuid4

from src.config.supabase_http import supabase_client
from src.config.logging import LoggerMixin, log_asin_check, log_batch_processing
from src.models.schemas import (
    KeepaProductData, BestSellerBadge, SlackNotificationPayload,
    BatchProcessingResult
)
from src.services.keepa_service import keepa_service
from src.services.slack_service import slack_service


class AsinTracker(LoggerMixin):
    """Core service for tracking ASIN Best Seller badge changes using Supabase API."""
    
    def __init__(self):
        self.batch_size = 100  # Maximum ASINs per Keepa API call
        # Import keepa_service to avoid circular imports
        from src.services.keepa_service import keepa_service
        self.keepa_service = keepa_service
        
    async def get_asins_to_check(
        self, 
        limit: int = 100,
        priority_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ASINs that need to be checked based on their monitoring frequency.
        
        Args:
            limit: Maximum number of ASINs to return
            priority_filter: Optional priority filter (1=highest)
            
        Returns:
            List of ASIN data dictionaries ready for checking
        """
        try:
            asins = await supabase_client.get_asins_to_check(limit, priority_filter)
            
            self.logger.info(
                "Retrieved ASINs for checking",
                count=len(asins),
                priority_filter=priority_filter,
                limit=limit
            )
            
            return asins
            
        except Exception as e:
            self.logger.error("Failed to get ASINs to check", error=str(e))
            return []
    
    async def process_batch(
        self, 
        tracked_asins: List[Dict[str, Any]]
    ) -> BatchProcessingResult:
        """
        Process a batch of ASINs for Best Seller badge changes.
        
        Args:
            tracked_asins: List of ASIN data dictionaries to process
            
        Returns:
            BatchProcessingResult with processing statistics
        """
        batch_id = uuid4()
        start_time = datetime.utcnow()
        
        self.logger.info(
            "Starting batch processing",
            batch_id=str(batch_id),
            asin_count=len(tracked_asins)
        )
        
        # Initialize counters
        successful_checks = 0
        failed_checks = 0
        changes_detected = 0
        notifications_sent = 0
        
        try:
            # Extract ASINs for Keepa API call
            asins = [ta["asin"] for ta in tracked_asins]
            
            # Get current data from Keepa
            products, api_metadata = await keepa_service.get_products_batch(asins)
            
            # Create lookup for products by ASIN
            product_lookup = {p.asin: p for p in products}
            
            # Process each tracked ASIN
            for tracked_asin in tracked_asins:
                try:
                    product = product_lookup.get(tracked_asin["asin"])
                    if not product:
                        self.logger.warning(
                            "No product data returned for ASIN",
                            asin=tracked_asin["asin"]
                        )
                        failed_checks += 1
                        continue
                    
                    # Process the ASIN
                    changes = await self._process_single_asin(tracked_asin, product)
                    
                    if changes:
                        changes_detected += len(changes)
                        
                        # Send notifications for changes
                        for change in changes:
                            notification_sent = await self._send_change_notification(
                                tracked_asin, change, product
                            )
                            if notification_sent:
                                notifications_sent += 1
                    
                    successful_checks += 1
                    
                except Exception as e:
                    self.logger.error(
                        "Error processing ASIN",
                        asin=tracked_asin["asin"],
                        error=str(e)
                    )
                    failed_checks += 1
                    
                    # Log error to database
                    await self._log_error(
                        error_type="asin_processing",
                        asin=tracked_asin["asin"],
                        error_message=str(e)
                    )
            
            # Log API usage
            await self._log_api_usage(
                batch_id=batch_id,
                asins_processed=len(tracked_asins),
                successful_calls=1 if products else 0,
                failed_calls=1 if not products else 0,
                tokens_consumed=len(asins),
                api_metadata=api_metadata
            )
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_seconds = int((end_time - start_time).total_seconds())
            
            # Create result
            result = BatchProcessingResult(
                batch_id=batch_id,
                asins_processed=len(tracked_asins),
                processing_time_seconds=processing_time_seconds,
                successful_checks=successful_checks,
                failed_checks=failed_checks,
                changes_detected=changes_detected,
                notifications_sent=notifications_sent,
                estimated_cost_cents=keepa_service.estimate_cost(len(asins))
            )
            
            # Log batch completion
            log_batch_processing(
                batch_id=str(batch_id),
                asins_count=len(tracked_asins),
                processing_time_seconds=processing_time_seconds,
                successful_checks=successful_checks,
                failed_checks=failed_checks,
                changes_detected=changes_detected,
                notifications_sent=notifications_sent
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Batch processing failed",
                batch_id=str(batch_id),
                error=str(e)
            )
            raise
    
    async def _process_single_asin(
        self, 
        tracked_asin: Dict[str, Any], 
        product: KeepaProductData
    ) -> List[Dict[str, Any]]:
        """
        Process a single ASIN for badge changes using Supabase API.
        
        Args:
            tracked_asin: ASIN data dictionary
            product: Current product data from Keepa
            
        Returns:
            List of detected changes
        """
        start_time = datetime.utcnow()
        changes = []
        
        try:
            asin = tracked_asin["asin"]
            
            # Get current state from Supabase
            current_state = await supabase_client.get_asin_current_state(asin)
            
            # Extract current badges from Keepa data
            current_badges = keepa_service.extract_bestseller_badges(product)
            
            # Compare with previous state if exists
            if current_state:
                # Parse previous badges
                previous_badges = [
                    BestSellerBadge(**badge) for badge in current_state.get("bestseller_badges", [])
                ]
                
                # Compare badges
                badge_comparison = keepa_service.compare_badges(
                    previous_badges, current_badges
                )
                
                # Create change records for gained badges
                for badge in badge_comparison["gained"]:
                    change = await self._create_change_record(
                        tracked_asin=tracked_asin,
                        change_type="gained",
                        category=badge.category_name,
                        category_id=badge.category_id,
                        previous_rank=None,
                        new_rank=badge.rank,
                        previous_badge_status=False,
                        new_badge_status=True
                    )
                    if change:
                        changes.append(change)
                
                # Create change records for lost badges
                for badge in badge_comparison["lost"]:
                    # Find current rank for this category
                    current_rank = None
                    if product.sales_ranks and badge.category_id in product.sales_ranks:
                        rank_data = product.sales_ranks[badge.category_id]
                        if isinstance(rank_data, list) and len(rank_data) >= 2:
                            current_rank = rank_data[1]
                    
                    change = await self._create_change_record(
                        tracked_asin=tracked_asin,
                        change_type="lost",
                        category=badge.category_name,
                        category_id=badge.category_id,
                        previous_rank=1,  # Was #1 (Best Seller)
                        new_rank=current_rank,
                        previous_badge_status=True,
                        new_badge_status=False
                    )
                    if change:
                        changes.append(change)
                
                # Update existing state
                await self._update_current_state(asin, product, current_badges)
            else:
                # Create new state record
                await self._create_current_state(tracked_asin, product, current_badges)
            
            # Create history record
            await self._create_history_record(tracked_asin, product, current_badges)
            
            # Update last_checked_at
            await supabase_client.update_asin_last_checked(asin)
            
            # Log ASIN check
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            log_asin_check(
                asin=asin,
                badges_found=len(current_badges),
                changes_detected=len(changes),
                processing_time_ms=processing_time_ms
            )
            
            return changes
            
        except Exception as e:
            self.logger.error(
                "Error processing single ASIN",
                asin=tracked_asin.get("asin", "unknown"),
                error=str(e)
            )
            raise
    
    async def _create_change_record(
        self,
        tracked_asin: Dict[str, Any],
        change_type: str,
        category: str,
        category_id: str,
        previous_rank: Optional[int],
        new_rank: Optional[int],
        previous_badge_status: bool,
        new_badge_status: bool
    ) -> Optional[Dict[str, Any]]:
        """Create a bestseller change record using Supabase API."""
        
        change_data = {
            "asin": tracked_asin["asin"],
            "change_type": change_type,
            "category": category,
            "category_id": category_id,
            "previous_rank": previous_rank,
            "new_rank": new_rank,
            "previous_badge_status": previous_badge_status,
            "new_badge_status": new_badge_status,
            "detected_at": datetime.utcnow().isoformat()
        }
        
        change_id = await supabase_client.create_bestseller_change(change_data)
        
        if change_id:
            return {
                "id": change_id,
                "change_type": change_type,
                "category": category,
                "category_id": category_id,
                "previous_rank": previous_rank,
                "new_rank": new_rank,
                "detected_at": datetime.utcnow()
            }
        
        return None
    
    async def _send_change_notification(
        self,
        tracked_asin: Dict[str, Any],
        change: Dict[str, Any],
        product: KeepaProductData
    ) -> bool:
        """Send notification for a badge change."""
        
        try:
            payload = SlackNotificationPayload(
                asin=tracked_asin["asin"],
                product_title=product.title or tracked_asin.get("product_title") or f"Product {tracked_asin['asin']}",
                change_type=change["change_type"],
                category=change["category"],
                category_id=change.get("category_id"),
                previous_rank=change.get("previous_rank"),
                new_rank=change.get("new_rank"),
                detected_at=change["detected_at"],
                amazon_url=f"https://amazon.com/dp/{tracked_asin['asin']}"
            )
            
            success = await slack_service.send_bestseller_alert(payload)
            
            if success:
                # Update change record to mark notification as sent
                notification_data = {
                    "notification_sent": True,
                    "notification_sent_at": datetime.utcnow().isoformat(),
                    "notification_method": "slack"
                }
                await supabase_client.update_bestseller_change_notification(
                    change["id"], notification_data
                )
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Error sending change notification",
                asin=tracked_asin["asin"],
                change_type=change["change_type"],
                error=str(e)
            )
            return False
    
    async def _update_current_state(
        self,
        asin: str,
        product: KeepaProductData,
        badges: List[BestSellerBadge]
    ) -> None:
        """Update existing current state record using Supabase API."""
        
        state_data = {
            "bestseller_badges": [badge.dict() for badge in badges],
            "sales_ranks": product.sales_ranks or {},
            "category_tree": product.category_tree or [],
            "product_title": product.title,
            "brand": product.brand,
            "current_price": product.current_price,
            "availability_amazon": product.availability,
            "monthly_sold": product.monthly_sold,
            "keepa_last_update": product.last_update.isoformat() if product.last_update else None,
            "raw_keepa_data": product.dict(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await supabase_client.update_asin_current_state(asin, state_data)
    
    async def _create_current_state(
        self,
        tracked_asin: Dict[str, Any],
        product: KeepaProductData,
        badges: List[BestSellerBadge]
    ) -> None:
        """Create new current state record using Supabase API."""
        
        state_data = {
            "asin": tracked_asin["asin"],
            "bestseller_badges": [badge.dict() for badge in badges],
            "sales_ranks": product.sales_ranks or {},
            "category_tree": product.category_tree or [],
            "product_title": product.title,
            "brand": product.brand,
            "current_price": product.current_price,
            "availability_amazon": product.availability,
            "monthly_sold": product.monthly_sold,
            "keepa_last_update": product.last_update.isoformat() if product.last_update else None,
            "raw_keepa_data": product.dict(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await supabase_client.update_asin_current_state(tracked_asin["asin"], state_data)
    
    async def _create_history_record(
        self,
        tracked_asin: Dict[str, Any],
        product: KeepaProductData,
        badges: List[BestSellerBadge]
    ) -> None:
        """Create history record for this check using Supabase API."""
        
        history_data = {
            "asin": tracked_asin["asin"],
            "bestseller_badges": [badge.dict() for badge in badges],
            "sales_ranks": product.sales_ranks or {},
            "category_tree": product.category_tree or [],
            "product_title": product.title,
            "brand": product.brand,
            "availability_amazon": product.availability,
            "monthly_sold": product.monthly_sold,
            "current_price": product.current_price,
            "keepa_timestamp": product.last_update.isoformat() if product.last_update else None,
            "raw_keepa_response": product.dict(),
            "tokens_used": 1,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        await supabase_client.create_history_record(history_data)
    
    async def _log_api_usage(
        self,
        batch_id: UUID,
        asins_processed: int,
        successful_calls: int,
        failed_calls: int,
        tokens_consumed: int,
        api_metadata: Dict[str, Any]
    ) -> None:
        """Log API usage statistics using Supabase API."""
        
        usage_data = {
            "batch_id": str(batch_id),
            "processing_completed_at": datetime.utcnow().isoformat(),
            "asins_processed": asins_processed,
            "tokens_consumed": tokens_consumed,
            "api_calls_made": successful_calls + failed_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "avg_response_time_ms": api_metadata.get("response_time_ms", 0),
            "estimated_cost_cents": keepa_service.estimate_cost(tokens_consumed)
        }
        
        await supabase_client.log_api_usage(usage_data)
    
    async def _log_error(
        self,
        error_type: str,
        error_message: str,
        asin: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        request_payload: Optional[Dict] = None,
        response_payload: Optional[Dict] = None
    ) -> None:
        """Log error using Supabase API."""
        
        error_data = {
            "error_type": error_type,
            "asin": asin,
            "error_message": error_message,
            "api_endpoint": api_endpoint,
            "request_payload": request_payload,
            "response_payload": response_payload,
            "occurred_at": datetime.utcnow().isoformat()
        }
        
        await supabase_client.log_error(error_data)


# Global service instance
asin_tracker = AsinTracker()
