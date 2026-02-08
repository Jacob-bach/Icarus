"""Job queue management and orchestration logic."""

import asyncio
import uuid
import docker
from datetime import datetime
from typing import Optional
from icarus.common.logging_config import get_orchestrator_logger
from icarus.orchestrator.database import DatabaseManager, Job, JobStatus as DBJobStatus, Telemetry, AuditLog
from icarus.orchestrator.docker_manager import DockerManager
from icarus.orchestrator.models import JobStatus
from sqlalchemy import select

logger = get_orchestrator_logger()


class JobQueue:
    """Manages the job queue and execution workflow."""
    
    def __init__(
        self, 
        db_manager: DatabaseManager, 
        docker_manager: DockerManager,
        sentinel=None  # Optional SystemMonitor instance
    ):
        self.db = db_manager
        self.docker = docker_manager
        self.sentinel = sentinel
        self.active_jobs = {}  # job_id -> task info
        self.queue = asyncio.Queue()
        self.max_concurrent = 3  # Updated to match test expectations
        self.processing_task = None  # Public for test access
        self.job_events = {}  # job_id -> {"error": Event, "complete": Event, "data": dict}
        
        logger.info(
            "JobQueue initialized",
            max_concurrent=self.max_concurrent,
            sentinel_enabled=sentinel is not None
        )
    
    async def start(self):
        """Start the queue processor."""
        self.processing_task = asyncio.create_task(self._process_queue())
        logger.info("Job queue processor started")
    
    async def stop(self):
        """Stop the queue processor gracefully."""
        logger.info("Stopping job queue processor...")
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Wait for active jobs to finish (with timeout)
        if self.active_jobs:
            logger.info(f"Waiting for {len(self.active_jobs)} active jobs to complete...")
            await asyncio.sleep(5)  # Give jobs a chance to finish
        
        logger.info("Job queue processor stopped")
    
    async def submit_job(self, task: str, project_path: str) -> str:
        """Submit a new job to the queue.
        
        Returns:
            job_id: Unique identifier for the job
        """
        job_id = str(uuid.uuid4())
        
        # Create job record in database
        async with self.db.async_session() as session:
            job = Job(
                job_id=job_id,
                task=task,
                status=DBJobStatus.PENDING,
                project_path=project_path
            )
            session.add(job)
            await session.commit()
        
        # Add to queue
        await self.queue.put(job_id)
        logger.info(f"Job submitted to queue", job_id=job_id, task=task[:100])
        
        return job_id
    
    async def _process_queue(self):
        """Background task to process queued jobs."""
        while True:
            try:
                # Wait for a job
                job_id = await self.queue.get()
                
                # Check if we can process (concurrent limit)
                if len(self.active_jobs) >= self.max_concurrent:
                    # Re-queue and wait
                    await self.queue.put(job_id)
                    await asyncio.sleep(5)
                    continue
                
                # Check system resources if Sentinel is available (Issue #1)
                if self.sentinel:
                    stats = self.sentinel.get_system_stats()
                    max_usage = max(stats['cpu_percent'], stats['ram_percent'])
                    
                    if max_usage >= 80:
                        logger.warning(
                            "System under load - re-queueing job",
                            job_id=job_id,
                            cpu_percent=stats['cpu_percent'],
                            ram_percent=stats['ram_percent']
                        )
                        await self.queue.put(job_id)
                        await asyncio.sleep(10)
                        continue
                
                # Process the job
                self.active_jobs[job_id] = {"status": "processing", "started_at": datetime.utcnow()}
                asyncio.create_task(self._execute_job(job_id))
                
            except Exception as e:
                logger.error_with_context("Error in queue processor", e)
                await asyncio.sleep(1)
    
    async def _execute_job(self, job_id: str):
        """Execute the full Builder -> Checker -> Review workflow."""
        job_logger = get_orchestrator_logger(job_id=job_id)
        
        # Create events for this job (Issue #6)
        self.job_events[job_id] = {
            "error": asyncio.Event(),
            "complete": asyncio.Event(),
            "data": {}
        }
        
        telemetry_task = None
        
        try:
            # Fetch job details
            async with self.db.async_session() as session:
                result = await session.execute(
                    select(Job).where(Job.job_id == job_id)
                )
                job = result.scalar_one()
                task = job.task
                project_path = job.project_path
            
            job_logger.info("Starting job execution", task=task[:100])
            
            # STEP 1: Create workspace volume
            volume_name = self.docker.create_workspace_volume(job_id)
            job_logger.info("Workspace volume created", volume=volume_name)
            
            # STEP 2: Spawn Builder agent
            await self._update_job_status(job_id, DBJobStatus.BUILDING)
            
            callback_url = f"http://host.docker.internal:8000/jobs/{job_id}/callback"
            builder_container = self.docker.spawn_builder(
                job_id=job_id,
                task=task,
                volume_name=volume_name,
                orchestrator_callback_url=callback_url
            )
            
            job_logger.info(
                "Builder container spawned",
                container_id=builder_container.id[:12],
                container_name=builder_container.name
            )
            
            # Store container ID
            async with self.db.async_session() as session:
                result = await session.execute(
                    select(Job).where(Job.job_id == job_id)
                )
                job = result.scalar_one()
                job.builder_container_id = builder_container.id
                await session.commit()
            
            # STEP 3: Start telemetry collection (Issue #7)
            telemetry_task = asyncio.create_task(
                self._collect_telemetry(job_id, builder_container.id)
            )
            
            # STEP 4: Wait for Builder with event monitoring (Issues #3, #4, #6)
            builder_exit_code = await self._wait_for_container_with_events(
                job_id, builder_container.id
            )
            
            # Stop telemetry for builder
            if telemetry_task:
                telemetry_task.cancel()
                try:
                    await telemetry_task
                except asyncio.CancelledError:
                    pass
            
            # Check Builder exit code (Issue #4)
            if builder_exit_code != 0:
                error_msg = f"Builder exited with non-zero code: {builder_exit_code}"
                job_logger.error(error_msg, exit_code=builder_exit_code)
                await self._update_job_status(job_id, DBJobStatus.FAILED, error_message=error_msg)
                return  # Don't proceed to Checker
            
            job_logger.info("Builder completed successfully", exit_code=builder_exit_code)
            
            # STEP 5: Freeze workspace (already read-only for Checker)
            
            # STEP 6: Spawn Checker agent
            await self._update_job_status(job_id, DBJobStatus.CHECKING)
            
            checker_container = self.docker.spawn_checker(
                job_id=job_id,
                task=task,
                volume_name=volume_name,
                orchestrator_callback_url=callback_url
            )
            
            job_logger.info(
                "Checker container spawned",
                container_id=checker_container.id[:12],
                container_name=checker_container.name
            )
            
            async with self.db.async_session() as session:
                result = await session.execute(
                    select(Job).where(Job.job_id == job_id)
                )
                job = result.scalar_one()
                job.checker_container_id = checker_container.id
                await session.commit()
            
            # Start telemetry for checker
            telemetry_task = asyncio.create_task(
                self._collect_telemetry(job_id, checker_container.id)
            )
            
            # STEP 7: Wait for Checker
            checker_exit_code = await self._wait_for_container_with_events(
                job_id, checker_container.id
            )
            
            # Stop telemetry for checker
            if telemetry_task:
                telemetry_task.cancel()
                try:
                    await telemetry_task
                except asyncio.CancelledError:
                    pass
            
            # Check Checker exit code (non-critical)
            if checker_exit_code != 0:
                job_logger.warning(
                    "Checker exited with non-zero code - proceeding to review anyway",
                    exit_code=checker_exit_code
                )
            else:
                job_logger.info("Checker completed successfully", exit_code=checker_exit_code)
            
            # STEP 8: Set status to awaiting approval
            await self._update_job_status(job_id, DBJobStatus.AWAITING_APPROVAL)
            
            job_logger.info("Job ready for review")
            
            # Send Discord notification (Issue #13)
            try:
                from mcp_tools.discord_mcp import DiscordMCP
                discord = DiscordMCP()
                await discord.notify_job_ready(job_id, task)
            except Exception as e:
                job_logger.error_with_context("Failed to send Discord notification", e)
            
        except Exception as e:
            job_logger.error_with_context("Job execution failed", e)
            await self._update_job_status(job_id, DBJobStatus.FAILED, error_message=str(e))
        
        finally:
            # Cleanup
            if telemetry_task and not telemetry_task.done():
                telemetry_task.cancel()
                try:
                    await telemetry_task
                except asyncio.CancelledError:
                    pass
            
            self.active_jobs.pop(job_id, None)
            self.job_events.pop(job_id, None)
    
    async def _wait_for_container_with_events(
        self, 
        job_id: str, 
        container_id: str, 
        timeout: int = 600
    ) -> int:
        """Wait for container with event monitoring (Issues #3, #4, #6).
        
        Returns:
            Exit code of the container
        """
        job_logger = get_orchestrator_logger(job_id=job_id)
        
        # Create tasks
        wait_task = asyncio.create_task(self._wait_for_container(container_id, timeout))
        error_event_task = asyncio.create_task(self.job_events[job_id]["error"].wait())
        complete_event_task = asyncio.create_task(self.job_events[job_id]["complete"].wait())
        
        try:
            done, pending = await asyncio.wait(
                [wait_task, error_event_task, complete_event_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check which completed
            if error_event_task in done:
                error_msg = self.job_events[job_id]["data"].get("error", "Agent reported error")
                job_logger.error("Early termination due to agent error", error=error_msg)
                raise RuntimeError(f"Agent error: {error_msg}")
            
            elif complete_event_task in done:
                job_logger.info("Agent signaled early completion")
                return 0  # Assume success
            
            else:
                # Container exited normally
                return wait_task.result()
        
        except asyncio.CancelledError:
            # Cancel all tasks if we're cancelled
            for task in [wait_task, error_event_task, complete_event_task]:
                if not task.done():
                    task.cancel()
            raise
    
    async def _wait_for_container(self, container_id: str, timeout: int = 600) -> int:
        """Wait for a container to exit and return exit code (Issues #3, #4).
        
        Returns:
            Exit code
        """
        start_time = datetime.utcnow()
        
        while True:
            try:
                # Use asyncio.to_thread for blocking Docker call (Issue #9)
                container = await asyncio.to_thread(
                    self.docker.client.containers.get, 
                    container_id
                )
                
                if container.status in ['exited', 'dead']:
                    exit_code = container.attrs['State']['ExitCode']
                    logger.info(
                        f"Container finished",
                        container_id=container_id[:12],
                        status=container.status,
                        exit_code=exit_code
                    )
                    return exit_code
            
            except docker.errors.NotFound:
                # Issue #3: Handle race condition
                logger.error(
                    "Container disappeared during execution",
                    container_id=container_id[:12]
                )
                raise RuntimeError(f"Container {container_id} was removed externally")
            
            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                logger.warning(
                    f"Container timeout - stopping",
                    container_id=container_id[:12],
                    timeout=timeout
                )
                await asyncio.to_thread(self.docker.stop_container, container_id)
                raise TimeoutError(f"Container {container_id} exceeded {timeout}s timeout")
            
            await asyncio.sleep(2)
    
    async def _collect_telemetry(self, job_id: str, container_id: str):
        """Continuously collect telemetry while container runs (Issue #7)."""
        job_logger = get_orchestrator_logger(job_id=job_id)
        
        job_logger.debug("Starting telemetry collection", container_id=container_id[:12])
        
        while True:
            try:
                container = await asyncio.to_thread(
                    self.docker.client.containers.get,
                    container_id
                )
                
                if container.status not in ['running']:
                    job_logger.debug(
                        "Container no longer running - stopping telemetry",
                        status=container.status
                    )
                    break
                
                # Get container stats
                stats = container.stats(stream=False)
                
                # Calculate CPU and memory usage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
                
                mem_usage_mb = stats['memory_stats']['usage'] / (1024 * 1024)
                
                # Save to database
                async with self.db.async_session() as session:
                    telemetry = Telemetry(
                        job_id=job_id,
                        cpu_usage=cpu_percent,
                        ram_usage_mb=mem_usage_mb,
                        container_id=container_id
                    )
                    session.add(telemetry)
                    await session.commit()
                
                await asyncio.sleep(5)  # Collect every 5 seconds
            
            except docker.errors.NotFound:
                job_logger.debug("Container removed - stopping telemetry")
                break
            
            except asyncio.CancelledError:
                job_logger.debug("Telemetry collection cancelled")
                break
            
            except Exception as e:
                job_logger.error_with_context(
                    "Telemetry collection error",
                    e,
                    container_id=container_id[:12]
                )
                break
    
    async def _update_job_status(
        self, 
        job_id: str, 
        status: DBJobStatus, 
        error_message: Optional[str] = None
    ):
        """Update job status in database."""
        async with self.db.async_session() as session:
            result = await session.execute(
                select(Job).where(Job.job_id == job_id)
            )
            job = result.scalar_one()
            job.status = status
            
            if error_message:
                job.error_message = error_message
            
            if status in [DBJobStatus.COMPLETED, DBJobStatus.FAILED, DBJobStatus.REJECTED]:
                job.completed_at = datetime.utcnow()
            
            await session.commit()
        
        logger.info(f"Job status updated", job_id=job_id, status=status.value)
    
    async def approve_job(self, job_id: str):
        """Approve a job after human review (Issue #8)."""
        job_logger = get_orchestrator_logger(job_id=job_id)
        
        await self._update_job_status(job_id, DBJobStatus.APPROVED)
        
        # TODO: Use GitHub MCP to commit and push changes
        # from mcp_tools.github_mcp import GitHubMCP
        # github = GitHubMCP()
        # await github.commit_and_push(job_id, workspace_path)
        
        # Cleanup resources (Issue #8)
        async with self.db.async_session() as session:
            result = await session.execute(
                select(Job).where(Job.job_id == job_id)
            )
            job = result.scalar_one()
            
            # Stop containers if still running
            if job.builder_container_id:
                try:
                    await asyncio.to_thread(
                        self.docker.stop_container,
                        job.builder_container_id
                    )
                    job_logger.info("Stopped builder container")
                except Exception as e:
                    job_logger.error_with_context("Failed to stop builder", e)
            
            if job.checker_container_id:
                try:
                    await asyncio.to_thread(
                        self.docker.stop_container,
                        job.checker_container_id
                    )
                    job_logger.info("Stopped checker container")
                except Exception as e:
                    job_logger.error_with_context("Failed to stop checker", e)
            
            # Cleanup workspace volume
            volume_name = f"icarus_workspace_{job_id}"
            try:
                self.docker.cleanup_volume(volume_name)
                job_logger.info("Cleaned up workspace volume", volume=volume_name)
            except Exception as e:
                job_logger.error_with_context("Failed to cleanup volume", e, volume=volume_name)
        
        await self._update_job_status(job_id, DBJobStatus.COMPLETED)
        job_logger.info("Job approved and cleaned up successfully")
    
    async def reject_job(self, job_id: str, comment: Optional[str] = None):
        """Reject a job and cleanup."""
        job_logger = get_orchestrator_logger(job_id=job_id)
        
        await self._update_job_status(job_id, DBJobStatus.REJECTED, error_message=comment)
        
        # Cleanup containers and volumes
        async with self.db.async_session() as session:
            result = await session.execute(
                select(Job).where(Job.job_id == job_id)
            )
            job = result.scalar_one()
            
            if job.builder_container_id:
                try:
                    await asyncio.to_thread(
                        self.docker.stop_container,
                        job.builder_container_id
                    )
                except Exception as e:
                    job_logger.error_with_context("Failed to stop builder", e)
            
            if job.checker_container_id:
                try:
                    await asyncio.to_thread(
                        self.docker.stop_container,
                        job.checker_container_id
                    )
                except Exception as e:
                    job_logger.error_with_context("Failed to stop checker", e)
            
            volume_name = f"icarus_workspace_{job_id}"
            try:
                self.docker.cleanup_volume(volume_name)
            except Exception as e:
                job_logger.error_with_context("Failed to cleanup volume", e)
        
        job_logger.info("Job rejected and cleaned up")
