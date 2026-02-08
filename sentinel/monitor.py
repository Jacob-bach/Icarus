"""System Sentinel - Resource monitoring and protection service."""

import psutil
import asyncio
from enum import Enum
from typing import Dict, Optional
from datetime import datetime
from icarus.common.logging_config import get_sentinel_logger

logger = get_sentinel_logger()


class AlertLevel(Enum):
    """Alert levels for system resource monitoring."""
    GREEN = "GREEN"   # Normal operation
    YELLOW = "YELLOW" # High usage - stop new jobs
    RED = "RED"       # Critical - pause containers


class SystemMonitor:
    """Monitors system resources and enforces protection policies."""
    
    def __init__(
        self,
        yellow_threshold: float = 80.0,
        red_threshold: float = 90.0,
        poll_interval: int = 5,
        docker_manager=None  # Optional[DockerManager]
    ):
        self.yellow_threshold = yellow_threshold
        self.red_threshold = red_threshold
        self.poll_interval = poll_interval
        self.current_alert = AlertLevel.GREEN
        self._monitoring_task = None
        self.docker = docker_manager  # Alias for tests expecting 'docker'
        self.docker_manager = docker_manager
        self.paused_containers = []  # Track containers we paused during Red alert
        
        logger.info(
            "SystemMonitor initialized",
            yellow_threshold=yellow_threshold,
            red_threshold=red_threshold,
            docker_integration=docker_manager is not None
        )
    
    async def start(self):
        """Start continuous monitoring."""
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("System Sentinel monitoring started")
    
    async def stop(self):
        """Stop monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("System Sentinel monitoring stopped")
    
    async def _monitor_loop(self):
        """Continuous monitoring loop."""
        while True:
            try:
                await self._check_resources()
                await asyncio.sleep(self.poll_interval)
            
            except Exception as e:
                logger.error_with_context(
                    "Monitoring loop encountered error",
                    e,
                    current_alert=self.current_alert.value
                )
                await asyncio.sleep(self.poll_interval)
    
    async def _check_resources(self):
        """Check system resources and trigger alerts as needed."""
        stats = self.get_system_stats()
        
        cpu_percent = stats['cpu_percent']
        ram_percent = stats['ram_percent']
        
        # Determine status based on thresholds
        max_usage = max(cpu_percent, ram_percent)
        
        if max_usage >= self.red_threshold:
            if self.current_alert != AlertLevel.RED:
                await self._trigger_red_alert(stats)
                self.current_alert = AlertLevel.RED
        
        elif max_usage >= self.yellow_threshold:
            if self.current_alert == AlertLevel.GREEN:
                await self._trigger_yellow_alert(stats)
                self.current_alert = AlertLevel.YELLOW
        
        else:
            if self.current_alert != AlertLevel.GREEN:
                await self._clear_alerts()
                self.current_alert = AlertLevel.GREEN
    
    def get_system_stats(self) -> Dict:
        """Get current system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "ram_percent": ram.percent,
                "ram_total_gb": ram.total / (1024**3),
                "ram_available_gb": ram.available / (1024**3),
                "ram_used_gb": ram.used / (1024**3),
                "disk_percent": disk.percent,
                "disk_total_gb": disk.total / (1024**3),
                "disk_free_gb": disk.free / (1024**3)
            }
        except Exception as e:
            logger.error_with_context("Failed to get system stats", e)
            # Return safe defaults
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": 0.0,
                "ram_percent": 0.0,
                "cpu_count": 1,
                "ram_total_gb": 0.0,
                "ram_available_gb": 0.0,
                "ram_used_gb": 0.0,
                "disk_percent": 0.0,
                "disk_total_gb": 0.0,
                "disk_free_gb": 0.0
            }
    
    async def _trigger_yellow_alert(self, stats: Dict):
        """Yellow alert: Stop accepting new jobs."""
        max_usage = max(stats['cpu_percent'], stats['ram_percent'])
        logger.warning(
            f"⚠️ YELLOW ALERT: System resources at {max_usage:.1f}%",
            cpu_percent=stats['cpu_percent'],
            ram_percent=stats['ram_percent'],
            threshold=self.yellow_threshold
        )
        logger.warning("New job submissions should be paused until resources are freed")
        
        # TODO: Send Discord notification
        # from mcp_tools.discord_mcp import DiscordWebhook
        # discord = DiscordWebhook()
        # await discord.send_notification(
        #     title="⚠️ Yellow Alert",
        #     description=f"System resources at {max_usage:.1f}%",
        #     color=0xFFA500
        # )
    
    async def _trigger_red_alert(self, stats: Dict):
        """Red alert: Pause all containers and notify user."""
        max_usage = max(stats['cpu_percent'], stats['ram_percent'])
        logger.critical(
            f"🚨 RED ALERT: System resources CRITICAL at {max_usage:.1f}%",
            cpu_percent=stats['cpu_percent'],
            ram_percent=stats['ram_percent'],
            threshold=self.red_threshold
        )
        
        # CRITICAL: Pause all ICARUS containers to prevent system lockup
        if self.docker_manager:
            try:
                containers = self.docker_manager.client.containers.list(
                    filters={"name": "icarus_"}
                )
                
                logger.critical(
                    f"Pausing {len(containers)} active ICARUS containers",
                    container_count=len(containers)
                )
                
                for container in containers:
                    try:
                        if container.status == "running":
                            # Use the async wrapper for pause
                            await asyncio.to_thread(
                                self.docker_manager.pause_container,
                                container.id
                            )
                            self.paused_containers.append(container.id)
                            logger.info(
                                f"Paused container",
                                container_id=container.id[:12],
                                container_name=container.name
                            )
                    except Exception as e:
                        logger.error_with_context(
                            f"Failed to pause container {container.name}",
                            e,
                            container_id=container.id[:12]
                        )
                
                logger.critical(
                    f"Red alert mitigation complete: Paused {len(self.paused_containers)} containers"
                )
                
            except Exception as e:
                logger.error_with_context(
                    "Failed to execute Red alert container pause",
                    e
                )
        else:
            logger.error(
                "RED ALERT: Cannot pause containers - DockerManager not configured"
            )
        
        # TODO: Send urgent Discord notification
        # discord = DiscordWebhook()
        # await discord.send_notification(
        #     title="🚨 RED ALERT",
        #     description=f"System critical at {max_usage:.1f}%! All containers paused.",
        #     color=0xFF0000
        # )
    
    async def _clear_alerts(self):
        """Clear alerts when system returns to normal."""
        logger.info(
            f"✅ System resources back to normal - clearing {self.current_alert.value} alert",
            previous_status=self.current_alert.value
        )
        
        # Resume paused containers if we had a Red alert
        if self.current_alert == AlertLevel.RED and self.paused_containers and self.docker_manager:
            logger.info(
                f"Resuming {len(self.paused_containers)} containers paused during Red alert"
            )
            
            for container_id in self.paused_containers:
                try:
                    container = self.docker_manager.client.containers.get(container_id)
                    if container.status == "paused":
                        container.unpause()
                        logger.info(
                            f"Resumed container",
                            container_id=container_id[:12]
                        )
                except Exception as e:
                    logger.error_with_context(
                        f"Failed to resume container",
                        e,
                        container_id=container_id[:12]
                    )
            
            self.paused_containers.clear()


class DockerMonitor:
    """Monitors Docker container resource usage."""
    
    def __init__(self, docker_client):
        self.docker_client = docker_client
    
    def get_container_stats(self, container_id: str) -> Dict:
        """Get stats for a specific container."""
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
            
            # Memory usage
            mem_usage = stats['memory_stats']['usage']
            mem_limit = stats['memory_stats']['limit']
            mem_percent = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0.0
            
            return {
                "container_id": container_id,
                "cpu_percent": cpu_percent,
                "memory_usage_mb": mem_usage / (1024 * 1024),
                "memory_limit_mb": mem_limit / (1024 * 1024),
                "memory_percent": mem_percent
            }
        
        except Exception as e:
            logger.error(f"Failed to get container stats: {e}")
            return {}
    
    def list_all_containers(self) -> list:
        """List all ICARUS containers (builder and checker)."""
        try:
            containers = self.docker_client.containers.list(
                filters={"name": "icarus_"}
            )
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status
                }
                for c in containers
            ]
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []
