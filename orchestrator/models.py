"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    BUILDING = "building"
    CHECKING = "checking"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class SpawnJobRequest(BaseModel):
    """Request to spawn a new job (v2.0 enhanced)."""
    task: str = Field(..., description="High-level task description")
    project_path: str = Field(..., description="Path to project workspace")
    phase: str = Field(default="I", description="Phase I or II")
    
    # v2.0 fields
    test_code: Optional[str] = Field(None, description="User-provided test code for TDD")
    project_id: str = Field(default="default", description="Project ID for RAG memory isolation")


class SpawnJobResponse(BaseModel):
    """Response after spawning a job."""
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    """Job status response (v2.0 enhanced)."""
    job_id: str
    status: JobStatus
    task: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # v2.0 fields
    reflection_iterations: Optional[int] = Field(None, description="Number of reflection iterations")
    test_results: Optional[Dict[str, Any]] = Field(None, description="Test execution results")
    memory_patterns_used: Optional[int] = Field(None, description="RAG patterns retrieved")


class TelemetryResponse(BaseModel):
    """Real-time telemetry data."""
    job_id: str
    status: JobStatus
    cpu_usage: float = Field(..., description="CPU usage percentage")
    ram_usage_mb: float = Field(..., description="RAM usage in MB")
    current_tool: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Approval or rejection request."""
    approved: bool
    comment: Optional[str] = None


class AuditReportResponse(BaseModel):
    """Audit report from Checker agent (v2.0 enhanced)."""
    job_id: str
    audit_report: Dict[str, Any]
    created_at: datetime
    security_score: Optional[int] = Field(None, description="Security score 0-100")


class MemoryStatsResponse(BaseModel):
    """RAG memory statistics (v2.0)."""
    job_id: str
    patterns_retrieved: int = Field(..., description="Number of patterns retrieved")
    patterns_stored: int = Field(..., description="Number of patterns stored this job")
    total_memory_size_kb: int = Field(..., description="Total memory database size")
    cross_job_learning_enabled: bool
