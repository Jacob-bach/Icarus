"""Main FastAPI application for ICARUS Orchestrator."""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import os
from dotenv import load_dotenv

from icarus.common.logging_config import setup_logging, get_orchestrator_logger
from icarus.common.secrets import secrets, validate_secrets_at_startup
from orchestrator.models import ( 
    SpawnJobRequest, SpawnJobResponse, JobStatusResponse,
    TelemetryResponse, ApprovalRequest, AuditReportResponse,
    JobStatus
)
from orchestrator.database import DatabaseManager, Job, Telemetry, AuditLog, JobStatus as DBJobStatus
from orchestrator.docker_manager import DockerManager
from orchestrator.job_queue import JobQueue
from sentinel.monitor import SystemMonitor
from sqlalchemy import select, desc

# Load environment variables
load_dotenv()

# Setup structured logging
setup_logging(log_level="INFO", json_logs=False)
logger = get_orchestrator_logger()

# Global instances
db_manager = None
docker_manager = None
job_queue = None
sentinel = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for FastAPI app (Issue #14: Graceful shutdown)."""
    global db_manager, docker_manager, job_queue, sentinel
    
    # Startup
    logger.info("🚀 Starting ICARUS Orchestrator...")
    
    # Validate secrets
    try:
        validate_secrets_at_startup()
    except ValueError as e:
        logger.critical("Secrets validation failed", error=str(e))
        raise
    
    # Initialize database
    database_url = secrets.get("DATABASE_URL")
    db_manager = DatabaseManager(database_url)
    await db_manager.init_db()
    logger.info("✓ Database initialized", database=secrets.mask("DATABASE_URL", database_url))
    
    # Initialize Docker manager
    docker_manager = DockerManager()
    logger.info("✓ Docker manager initialized")
    
    # Initialize and start System Sentinel (Issue #1)
    sentinel = SystemMonitor(
        yellow_threshold=secrets.get_float("SENTINEL_YELLOW_THRESHOLD", 80.0),
        red_threshold=secrets.get_float("SENTINEL_RED_THRESHOLD", 90.0),
        poll_interval=secrets.get_int("SENTINEL_POLL_INTERVAL", 5),
        docker_manager=docker_manager
    )
    await sentinel.start()
    logger.info(
        "✓ System Sentinel started",
        yellow_threshold=sentinel.yellow_threshold,
        red_threshold=sentinel.red_threshold
    )
    
    # Initialize and start job queue with Sentinel reference
    job_queue = JobQueue(db_manager, docker_manager, sentinel=sentinel)
    await job_queue.start()
    logger.info("✓ Job queue started")
    
    logger.info("🎯 ICARUS Orchestrator ready")
    
    yield
    
    # Shutdown (Issue #14: Graceful shutdown)
    logger.info("⏹️  Initiating graceful shutdown...")
    
    try:
        # Stop accepting new jobs
        logger.info("Stopping job queue...")
        await asyncio.wait_for(job_queue.stop(), timeout=30.0)
        logger.info("✓ Job queue stopped")
    except asyncio.TimeoutError:
        logger.warning("Job queue shutdown timed out - forcing stop")
    except Exception as e:
        logger.error_with_context("Error stopping job queue", e)
    
    try:
        # Stop system monitoring
        logger.info("Stopping Sentinel...")
        await asyncio.wait_for(sentinel.stop(), timeout=10.0)
        logger.info("✓ Sentinel stopped")
    except asyncio.TimeoutError:
        logger.warning("Sentinel shutdown timed out - forcing stop")
    except Exception as e:
        logger.error_with_context("Error stopping Sentinel", e)
    
    logger.info("✅ ICARUS Orchestrator shutdown complete")


app = FastAPI(
    title="ICARUS Orchestrator",
    description="Autonomous software development environment with Builder/Checker/Reviewer architecture",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "ICARUS Orchestrator",
        "status": "operational",
        "version": "1.0.0"
    }


@app.post("/jobs/spawn", response_model=SpawnJobResponse)
async def spawn_job(request: SpawnJobRequest):
    """Spawn a new job and add it to the queue.
    
    This endpoint creates a new autonomous coding task that will:
    1. Spawn a Builder agent to implement the task
    2. Spawn a Checker agent to audit the code
    3. Wait for human approval
    """
    try:
        job_id = await job_queue.submit_job(
            task=request.task,
            project_path=request.project_path
        )
        
        return SpawnJobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message=f"Job {job_id} created and queued for execution"
        )
    
    except Exception as e:
        logger.error(f"Failed to spawn job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the current status of a job."""
    try:
        async with db_manager.async_session() as session:
            result = await session.execute(
                select(Job).where(Job.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            
            return JobStatusResponse(
                job_id=job.job_id,
                status=JobStatus(job.status.value),
                task=job.task,
                created_at=job.created_at,
                completed_at=job.completed_at,
                error_message=job.error_message
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/telemetry", response_model=TelemetryResponse)
async def get_job_telemetry(job_id: str):
    """Get real-time telemetry for a job."""
    try:
        async with db_manager.async_session() as session:
            # Get job info
            result = await session.execute(
                select(Job).where(Job.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            
            # Get active container
            container_id = job.builder_container_id if job.status == DBJobStatus.BUILDING else job.checker_container_id
            
            if container_id:
                # Get live stats from Docker
                stats = docker_manager.get_container_stats(container_id)
                cpu_usage = stats['cpu_usage']
                ram_usage_mb = stats['ram_usage_mb']
            else:
                cpu_usage = 0.0
                ram_usage_mb = 0.0
            
            # Get latest telemetry record for current_tool
            telemetry_result = await session.execute(
                select(Telemetry)
                .where(Telemetry.job_id == job_id)
                .order_by(desc(Telemetry.timestamp))
                .limit(1)
            )
            latest_telemetry = telemetry_result.scalar_one_or_none()
            current_tool = latest_telemetry.current_tool if latest_telemetry else None
            
            return TelemetryResponse(
                job_id=job_id,
                status=JobStatus(job.status.value),
                cpu_usage=cpu_usage,
                ram_usage_mb=ram_usage_mb,
                current_tool=current_tool
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get telemetry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/audit", response_model=AuditReportResponse)
async def get_audit_report(job_id: str):
    """Get the audit report for a job (generated by Checker agent)."""
    try:
        async with db_manager.async_session() as session:
            result = await session.execute(
                select(AuditLog)
                .where(AuditLog.job_id == job_id)
                .order_by(desc(AuditLog.created_at))
                .limit(1)
            )
            audit_log = result.scalar_one_or_none()
            
            if not audit_log:
                raise HTTPException(status_code=404, detail=f"No audit report found for job {job_id}")
            
            return AuditReportResponse(
                job_id=job_id,
                audit_report=audit_log.audit_report,
                created_at=audit_log.created_at
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/{job_id}/approve")
async def approve_job(job_id: str, request: ApprovalRequest):
    """Approve or reject a job after human review."""
    try:
        if request.approved:
            await job_queue.approve_job(job_id)
            return {"message": f"Job {job_id} approved", "status": "approved"}
        else:
            await job_queue.reject_job(job_id, comment=request.comment)
            return {"message": f"Job {job_id} rejected", "status": "rejected"}
    
    except Exception as e:
        logger.error(f"Failed to process approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
async def list_jobs(limit: int = 50, status: str = None):
    """List all jobs with optional status filtering."""
    try:
        async with db_manager.async_session() as session:
            query = select(Job).order_by(desc(Job.created_at)).limit(limit)
            
            if status:
                query = query.where(Job.status == DBJobStatus(status))
            
            result = await session.execute(query)
            jobs = result.scalars().all()
            
            return [
                {
                    "job_id": job.job_id,
                    "task": job.task,
                    "status": job.status.value,
                    "created_at": job.created_at,
                    "completed_at": job.completed_at
                }
                for job in jobs
            ]
    
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/jobs/{job_id}/stream")
async def stream_logs(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for streaming live terminal output from agents."""
    await websocket.accept()
    
    try:
        # TODO: Implement real-time log streaming from Docker containers
        # For now, send periodic telemetry updates
        
        while True:
            async with db_manager.async_session() as session:
                result = await session.execute(
                    select(Job).where(Job.job_id == job_id)
                )
                job = result.scalar_one_or_none()
                
                if job:
                    await websocket.send_json({
                        "type": "status_update",
                        "status": job.status.value,
                        "timestamp": job.created_at.isoformat()
                    })
            
            await asyncio.sleep(2)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


@app.post("/jobs/{job_id}/callback")
async def agent_callback(job_id: str, data: dict):
    """Callback endpoint for agents to report progress and completion (Issue #6, #11).
    
    Agents call this endpoint to:
    - Report current tool usage
    - Send completion signals
    - Report errors
    - Submit audit reports
    """
    callback_logger = get_orchestrator_logger(job_id=job_id)
    
    try:
        callback_logger.info(
            "Received callback from agent",
            callback_type=data.get("type", "unknown"),
            has_telemetry="current_tool" in data,
            has_audit="audit_report" in data
        )
        
        # Store telemetry if provided (Issue #7)
        if "current_tool" in data:
            async with db_manager.async_session() as session:
                telemetry = Telemetry(
                    job_id=job_id,
                    cpu_usage=data.get("cpu_usage", 0.0),
                    ram_usage_mb=data.get("ram_usage_mb", 0.0),
                    current_tool=data["current_tool"]
                )
                session.add(telemetry)
                await session.commit()
        
        # Store audit report if provided (from Checker) (Issue #11)
        if "audit_report" in data:
            async with db_manager.async_session() as session:
                audit_log = AuditLog(
                    job_id=job_id,
                    audit_report=data["audit_report"]
                )
                session.add(audit_log)
                await session.commit()
            
            callback_logger.info("Audit report stored")
        
        # Handle error signals from agents (Issue #6)
        if data.get("status") == "error":
            error_msg = data.get("error", "Unknown error")
            callback_logger.error(
                "Agent reported error",
                error=error_msg
            )
            
            # Signal error event for early termination
            if job_id in job_queue.job_events:
                job_queue.job_events[job_id]["data"]["error"] = error_msg
                job_queue.job_events[job_id]["error"].set()
        
        # Handle completion signals (Issue #6)
        elif data.get("status") == "completed":
            callback_logger.info("Agent reported early completion")
            
            if job_id in job_queue.job_events:
                job_queue.job_events[job_id]["complete"].set()
        
        return {"status": "acknowledged"}
    
    except Exception as e:
        callback_logger.error_with_context("Failed to process callback", e)
        raise HTTPException(status_code=500, detail="Failed to process callback")


if __name__ == "__main__":
    import uvicorn
    
    host = secrets.get("ORCHESTRATOR_HOST", "0.0.0.0")
    port = secrets.get_int("ORCHESTRATOR_PORT", 8000)
    
    uvicorn.run(app, host=host, port=port)
