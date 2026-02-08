"""Docker container management for ICARUS agents."""

import docker
from docker.models.containers import Container
from docker.types import Mount
import yaml
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker containers for Builder and Checker agents."""
    
    def __init__(self, config_path: str = "icarus/config/config.yaml"):
        self.client = docker.from_env()
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.builder_config = self.config['agents']['builder']
        self.checker_config = self.config['agents']['checker']
    
    def create_workspace_volume(self, job_id: str) -> str:
        """Create a dedicated workspace volume for a job."""
        volume_name = f"icarus_workspace_{job_id}"
        try:
            self.client.volumes.create(name=volume_name, driver='local')
            logger.info(f"Created workspace volume: {volume_name}")
            return volume_name
        except Exception as e:
            logger.error(f"Failed to create volume {volume_name}: {e}")
            raise
    
    def spawn_builder(
        self, 
        job_id: str, 
        task: str, 
        volume_name: str,
        orchestrator_callback_url: str
    ) -> Container:
        """Spawn a Builder agent container.
        
        Args:
            job_id: Unique job identifier
            task: Task description for the agent
            volume_name: Workspace volume name
            orchestrator_callback_url: URL for agent to report back
        
        Returns:
            Docker Container object
        """
        container_name = f"icarus_builder_{job_id}"
        
        # Mount configuration
        mounts = [
            Mount(
                target="/workspace",
                source=volume_name,
                type="volume",
                read_only=False
            )
        ]
        
        # Environment variables
        environment = {
            "JOB_ID": job_id,
            "TASK": task,
            "ORCHESTRATOR_CALLBACK": orchestrator_callback_url
        }
        
        try:
            container = self.client.containers.run(
                image=self.builder_config['image_name'],
                name=container_name,
                detach=True,
                mounts=mounts,
                environment=environment,
                network_mode=self.builder_config['network_mode'],
                cpu_period=100000,
                cpu_quota=int(100000 * self.builder_config['cpu_limit']),
                mem_limit=self.builder_config['memory_limit'],
                labels={"project": "icarus", "agent_type": "builder"},
                remove=False  # Keep for inspection
            )
            
            logger.info(f"Spawned Builder container: {container.id}")
            return container
            
        except Exception as e:
            logger.error(f"Failed to spawn Builder: {e}")
            raise
    
    def spawn_checker(
        self,
        job_id: str,
        task: str,
        volume_name: str,
        orchestrator_callback_url: str
    ) -> Container:
        """Spawn a Checker agent container with read-only workspace access."""
        container_name = f"icarus_checker_{job_id}"
        
        # Mount as READ-ONLY
        mounts = [
            Mount(
                target="/workspace",
                source=volume_name,
                type="volume",
                read_only=True  # Critical for security
            )
        ]
        
        environment = {
            "JOB_ID": job_id,
            "TASK": task,
            "ORCHESTRATOR_CALLBACK": orchestrator_callback_url
        }
        
        try:
            container = self.client.containers.run(
                image=self.checker_config['image_name'],
                name=container_name,
                detach=True,
                mounts=mounts,
                environment=environment,
                network_mode=self.checker_config['network_mode'],
                cpu_period=100000,
                cpu_quota=int(100000 * self.checker_config['cpu_limit']),
                mem_limit=self.checker_config['memory_limit'],
                labels={"project": "icarus", "agent_type": "checker"},
                remove=False
            )
            
            logger.info(f"Spawned Checker container: {container.id}")
            return container
            
        except Exception as e:
            logger.error(f"Failed to spawn Checker: {e}")
            raise
    
    def pause_container(self, container_id: str):
        """Pause a running container."""
        try:
            container = self.client.containers.get(container_id)
            container.pause()
            logger.info(f"Paused container: {container_id}")
        except Exception as e:
            logger.error(f"Failed to pause container {container_id}: {e}")
    
    def resume_container(self, container_id: str):
        """Resume a paused container."""
        try:
            container = self.client.containers.get(container_id)
            container.unpause()
            logger.info(f"Resumed container: {container_id}")
        except Exception as e:
            logger.error(f"Failed to resume container {container_id}: {e}")
            raise
    
    def stop_container(self, container_id: str, timeout: int = 10):
        """Stop and remove a container."""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            container.remove()
            logger.info(f"Stopped and removed container: {container_id}")
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
    
    def get_container_stats(self, container_id: str) -> Dict:
        """Get real-time stats from a container."""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
            
            # Calculate memory usage in MB
            mem_usage_mb = stats['memory_stats']['usage'] / (1024 * 1024)
            
            return {
                "cpu_percent": cpu_percent,
                "ram_mb": mem_usage_mb
            }
        except Exception as e:
            logger.error(f"Failed to get stats for {container_id}: {e}")
            return {"cpu_percent": 0.0, "ram_mb": 0.0}
    
    def list_icarus_containers(self):
        """List all ICARUS containers."""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": "project=icarus"}
            )
            return containers
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []
    
    def cleanup_volume(self, volume_name: str):
        """Remove a workspace volume."""
        try:
            volume = self.client.volumes.get(volume_name)
            volume.remove()
            logger.info(f"Removed volume: {volume_name}")
        except Exception as e:
            logger.error(f"Failed to remove volume {volume_name}: {e}")
