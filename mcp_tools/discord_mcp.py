"""Discord MCP - One-way webhook notifications for Phase I."""

import httpx
import os
from typing import Optional
from datetime import datetime
from icarus.common.logging_config import get_mcp_logger

logger = get_mcp_logger("discord")


class DiscordMCP:
    """Phase I: One-way Discord notifications via webhook."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        
        if not self.webhook_url:
            logger.warning("Discord webhook URL not set - notifications disabled")
        else:
            logger.info("Discord webhook initialized")
    
    async def send_notification(
        self,
        message: str,
        level: str = "INFO",
        title: Optional[str] = None,
        fields: Optional[list] = None
    ) -> bool:
        """Send a notification to Discord.
        
        Args:
            message: Message content
            level: Message level (INFO, WARNING, ERROR, SUCCESS)
            title: Optional title for the embed
            fields: Optional list of {"name": str, "value": str, "inline": bool} dicts
        
        Returns:
            True if successful
        """
        if not self.webhook_url:
            logger.debug("Discord webhook not configured - skipping notification")
            return False
        
        # Color scheme based on level
        colors = {
            "INFO": 0x3498db,  # Blue
            "SUCCESS": 0x2ecc71,  # Green
            "WARNING": 0xf39c12,  # Yellow/Orange
            "ERROR": 0xe74c3c  # Red
        }
        
        embed = {
            "title": title or f"ICARUS - {level}",
            "description": message,
            "color": colors.get(level, 0x95a5a6),
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "ICARUS Orchestrator"
            }
        }
        
        if fields:
            embed["fields"] = fields
        
        payload = {"embeds": [embed]}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"Discord notification sent successfully", level=level, title=title or level)
                return True
        
        except httpx.HTTPStatusError as e:
            logger.error_with_context(
                "Discord webhook returned error status",
                e,
                status_code=e.response.status_code,
                level=level
            )
            return False
        
        except httpx.RequestError as e:
            logger.error_with_context(
                "Failed to send Discord notification - network error",
                e,
                level=level
            )
            return False
        
        except Exception as e:
            logger.error_with_context(
                "Unexpected error sending Discord notification",
                e,
                level=level
            )
            return False
    
    async def notify_job_ready(self, job_id: str, task: str) -> bool:
        """Notify that a job is ready for review."""
        message = (
            f"**Job Ready for Review**\n\n"
            f"Job ID: `{job_id}`\n"
            f"Task: {task[:200]}" + ("..." if len(task) > 200 else "") + "\n\n"
            f"Please review the changes in the dashboard."
        )
        return await self.send_notification(message, level="SUCCESS", title="✅ Job Complete")
    
    async def notify_job_failed(self, job_id: str, error: str) -> bool:
        """Notify that a job has failed."""
        message = (
            f"**Job Failed**\n\n"
            f"Job ID: `{job_id}`\n"
            f"Error: {error}"
        )
        return await self.send_notification(message, level="ERROR", title="❌ Job Failed")
    
    async def notify_system_alert(self, alert_level: str, details: str, stats: Optional[dict] = None) -> bool:
        """Notify about system resource alerts."""
        title = f"🔔 System Alert - {alert_level}"
        
        fields = []
        if stats:
            fields.append({
                "name": "CPU Usage",
                "value": f"{stats.get('cpu_percent', 0):.1f}%",
                "inline": True
            })
            fields.append({
                "name": "RAM Usage",
                "value": f"{stats.get('ram_percent', 0):.1f}%",
                "inline": True
            })
        
        return await self.send_notification(
            details,
            level=alert_level,
            title=title,
            fields=fields if fields else None
        )
