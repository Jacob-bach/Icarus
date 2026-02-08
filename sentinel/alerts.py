"""Alert management for System Sentinel."""

import logging
from typing import Dict, Optional
import httpx

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self, discord_webhook_url: Optional[str] = None):
        self.discord_webhook_url = discord_webhook_url
    
    async def send_discord_notification(self, message: str, level: str = "INFO"):
        """Send notification via Discord webhook."""
        if not self.discord_webhook_url:
            logger.debug("Discord webhook not configured, skipping notification")
            return
        
        # Discord embed colors
        colors = {
            "INFO": 0x3498db,  # Blue
            "WARNING": 0xf39c12,  # Yellow
            "ERROR": 0xe74c3c  # Red
        }
        
        payload = {
            "embeds": [{
                "title": f"ICARUS Sentinel Alert - {level}",
                "description": message,
                "color": colors.get(level, 0x95a5a6),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.discord_webhook_url,
                    json=payload
                )
                response.raise_for_status()
                logger.info(f"Discord notification sent: {level}")
        
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
    
    async def notify_yellow_alert(self, stats: Dict):
        """Send yellow alert notification."""
        message = (
            f"⚠️ **Yellow Alert**: System resources at "
            f"{max(stats['cpu_percent'], stats['ram_percent']):.1f}%\n"
            f"CPU: {stats['cpu_percent']:.1f}%\n"
            f"RAM: {stats['ram_percent']:.1f}%\n"
            f"Action: Pausing new job submissions"
        )
        await self.send_discord_notification(message, level="WARNING")
    
    async def notify_red_alert(self, stats: Dict):
        """Send red alert notification."""
        message = (
            f"🚨 **RED ALERT**: Critical resource usage!\n"
            f"CPU: {stats['cpu_percent']:.1f}%\n"
            f"RAM: {stats['ram_percent']:.1f}%\n"
            f"Action: All containers paused immediately"
        )
        await self.send_discord_notification(message, level="ERROR")
    
    async def notify_job_complete(self, job_id: str):
        """Notify when a job is ready for review."""
        message = (
            f"✅ **Job Complete**: Job `{job_id}` is ready for review\n"
            f"Please check the dashboard to approve or reject changes"
        )
        await self.send_discord_notification(message, level="INFO")
