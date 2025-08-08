"""
Slack notification service for Best Seller badge changes.
Handles message formatting and delivery to specified channels.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from src.config.settings import settings
from src.config.logging import LoggerMixin, log_notification_sent
from src.models.schemas import SlackNotificationPayload, BestSellerChange


class SlackService(LoggerMixin):
    """Service for sending Slack notifications."""
    
    def __init__(self):
        self.client = AsyncWebClient(token=settings.slack_bot_token)
        self.default_channel = settings.slack_channel_id
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay_seconds
    
    async def send_bestseller_alert(
        self, 
        payload
    ) -> bool:
        """
        Send a Best Seller badge change alert to Slack.
        
        Args:
            payload: Notification payload with change details (dict or SlackNotificationPayload)
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Handle both dict and SlackNotificationPayload
            if isinstance(payload, dict):
                # Convert dict to SlackNotificationPayload for consistency
                amazon_url = payload.get('amazon_url', f"https://amazon.com/dp/{payload['asin']}")
                payload_obj = SlackNotificationPayload(
                    asin=payload['asin'],
                    product_title=payload['product_title'],
                    change_type=payload['change_type'],
                    category=payload['category'],
                    category_id=payload.get('category_id'),
                    previous_rank=payload.get('previous_rank'),
                    new_rank=payload.get('new_rank'),
                    detected_at=payload.get('detected_at', datetime.utcnow()),
                    amazon_url=amazon_url
                )
            else:
                payload_obj = payload
            
            # Create message blocks
            blocks = self._create_badge_alert_blocks(payload_obj)
            
            # Send message
            response = await self.client.chat_postMessage(
                channel=self.default_channel,
                blocks=blocks,
                text=f"Best Seller Alert: {payload_obj.asin}"  # Fallback text
            )
            
            if response["ok"]:
                log_notification_sent(
                    notification_type="bestseller_change",
                    recipient=self.default_channel,
                    delivery_method="slack",
                    success=True,
                    asin=payload_obj.asin,
                    change_type=payload_obj.change_type,
                    message_ts=response.get("ts")
                )
                
                self.logger.info(
                    "Slack notification sent successfully",
                    asin=payload_obj.asin,
                    change_type=payload_obj.change_type,
                    channel=self.default_channel,
                    message_ts=response.get("ts")
                )
                return True
            else:
                self.logger.error(
                    "Slack API returned not ok",
                    response=response,
                    asin=payload_obj.asin
                )
                return False
                
        except SlackApiError as e:
            error_msg = f"Slack API error: {e.response['error']}"
            # Get ASIN safely from either payload type
            asin = payload_obj.asin if 'payload_obj' in locals() else (payload.get('asin') if isinstance(payload, dict) else payload.asin)
            change_type = payload_obj.change_type if 'payload_obj' in locals() else (payload.get('change_type') if isinstance(payload, dict) else payload.change_type)
            
            log_notification_sent(
                notification_type="bestseller_change",
                recipient=self.default_channel,
                delivery_method="slack",
                success=False,
                error=error_msg,
                asin=asin,
                change_type=change_type
            )
            
            self.logger.error(
                "Slack API error",
                error=error_msg,
                asin=asin,
                response_code=e.response.status_code
            )
            return False
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            # Get ASIN safely from either payload type
            asin = payload_obj.asin if 'payload_obj' in locals() else (payload.get('asin') if isinstance(payload, dict) else payload.asin)
            change_type = payload_obj.change_type if 'payload_obj' in locals() else (payload.get('change_type') if isinstance(payload, dict) else payload.change_type)
            
            log_notification_sent(
                notification_type="bestseller_change",
                recipient=self.default_channel,
                delivery_method="slack",
                success=False,
                error=error_msg,
                asin=asin,
                change_type=change_type
            )
            
            self.logger.error(
                "Unexpected error sending Slack notification",
                error=error_msg,
                asin=asin
            )
            return False
    
    def _create_badge_alert_blocks(
        self, 
        payload: SlackNotificationPayload
    ) -> List[Dict[str, Any]]:
        """Create Slack message blocks for badge change alert."""
        
        # Determine emoji and action text
        if payload.change_type == "gained":
            emoji = "🎉"
            action = "GAINED"
            color = "good"
        elif payload.change_type == "lost":
            emoji = "⚠️"
            action = "LOST"
            color = "warning"
        else:
            emoji = "📊"
            action = "RANK CHANGE"
            color = "#439FE0"
        
        # Format rank change text
        rank_text = ""
        if payload.previous_rank and payload.new_rank:
            rank_text = f"*Rank Change:* #{payload.previous_rank} → #{payload.new_rank}\n"
        elif payload.new_rank:
            rank_text = f"*Current Rank:* #{payload.new_rank}\n"
        
        # Create main message block
        main_text = (
            f"{emoji} *BEST SELLER ALERT!*\n\n"
            f"*ASIN:* `{payload.asin}`\n"
            f"*Product:* {payload.product_title}\n"
            f"*Status:* {action} Best Seller badge\n"
            f"*Category:* {payload.category}\n"
            f"{rank_text}"
            f"*Time:* {payload.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": main_text
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View on Amazon"
                        },
                        "url": payload.amazon_url,
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Keepa Chart"
                        },
                        "url": f"https://keepa.com/#!product/1-{payload.asin}"
                    }
                ]
            }
        ]
        
        # Add category ID if available
        if payload.category_id:
            blocks.insert(1, {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Category ID: `{payload.category_id}`"
                    }
                ]
            })
        
        return blocks
    
    async def send_multiple_changes_alert(
        self, 
        asin: str,
        product_title: str,
        changes: List[Dict[str, Any]]
    ) -> bool:
        """
        Send alert for multiple badge changes on the same ASIN.
        
        Args:
            asin: The ASIN with multiple changes
            product_title: Product title
            changes: List of change dictionaries
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Group changes by type
            gained = [c for c in changes if c["change_type"] == "gained"]
            lost = [c for c in changes if c["change_type"] == "lost"]
            
            # Create summary text
            summary_parts = []
            if gained:
                gained_text = ", ".join([f'"{c["category"]}"' for c in gained])
                summary_parts.append(f"🎉 GAINED Best Seller in {gained_text}")
            
            if lost:
                lost_text = ", ".join([f'"{c["category"]}"' for c in lost])
                summary_parts.append(f"⚠️ LOST Best Seller in {lost_text}")
            
            summary = "\n".join(summary_parts)
            
            # Create message blocks
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"🔥 *MULTIPLE CHANGES - ASIN: `{asin}`*\n\n"
                            f"*Product:* {product_title}\n\n"
                            f"{summary}\n\n"
                            f"*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        )
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View on Amazon"
                            },
                            "url": f"https://amazon.com/dp/{asin}",
                            "style": "primary"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Keepa Chart"
                            },
                            "url": f"https://keepa.com/#!product/1-{asin}"
                        }
                    ]
                }
            ]
            
            # Send message
            response = await self.client.chat_postMessage(
                channel=self.default_channel,
                blocks=blocks,
                text=f"Multiple Best Seller Changes: {asin}"
            )
            
            if response["ok"]:
                log_notification_sent(
                    notification_type="multiple_changes",
                    recipient=self.default_channel,
                    delivery_method="slack",
                    success=True,
                    asin=asin,
                    changes_count=len(changes),
                    message_ts=response.get("ts")
                )
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Error sending multiple changes alert",
                error=str(e),
                asin=asin,
                changes_count=len(changes)
            )
            return False
    
    async def send_system_alert(
        self, 
        message: str, 
        alert_type: str = "info",
        channel: Optional[str] = None
    ) -> bool:
        """
        Send a system alert message.
        
        Args:
            message: Alert message
            alert_type: Type of alert (info, warning, error)
            channel: Channel to send to (defaults to main channel)
            
        Returns:
            True if sent successfully
        """
        try:
            target_channel = channel or self.default_channel
            
            # Choose emoji based on alert type
            emoji_map = {
                "info": "ℹ️",
                "warning": "⚠️",
                "error": "🚨",
                "success": "✅"
            }
            emoji = emoji_map.get(alert_type, "📢")
            
            # Send simple text message
            response = await self.client.chat_postMessage(
                channel=target_channel,
                text=f"{emoji} *System Alert*\n{message}",
                mrkdwn=True
            )
            
            return response["ok"]
            
        except Exception as e:
            self.logger.error(
                "Error sending system alert",
                error=str(e),
                alert_type=alert_type,
                message=message
            )
            return False
    
    async def send_daily_summary(
        self, 
        stats: Dict[str, Any]
    ) -> bool:
        """
        Send daily summary of Best Seller changes.
        
        Args:
            stats: Dictionary with daily statistics
            
        Returns:
            True if sent successfully
        """
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Daily Best Seller Summary"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Changes:* {stats.get('total_changes', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Badges Gained:* {stats.get('badges_gained', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Badges Lost:* {stats.get('badges_lost', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*ASINs Checked:* {stats.get('asins_checked', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*API Calls:* {stats.get('api_calls', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Estimated Cost:* ${stats.get('cost_cents', 0) / 100:.2f}"
                        }
                    ]
                }
            ]
            
            # Add top categories if available
            if stats.get('top_categories'):
                category_text = "\n".join([
                    f"• {cat['name']}: {cat['changes']} changes"
                    for cat in stats['top_categories'][:5]
                ])
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Top Categories:*\n{category_text}"
                    }
                })
            
            response = await self.client.chat_postMessage(
                channel=self.default_channel,
                blocks=blocks,
                text="Daily Best Seller Summary"
            )
            
            return response["ok"]
            
        except Exception as e:
            self.logger.error(
                "Error sending daily summary",
                error=str(e),
                stats=stats
            )
            return False
    
    async def health_check(self) -> bool:
        """Check if Slack API is accessible."""
        try:
            response = await self.client.auth_test()
            return response["ok"]
        except Exception as e:
            self.logger.error("Slack health check failed", error=str(e))
            return False


# Global service instance
slack_service = SlackService()
