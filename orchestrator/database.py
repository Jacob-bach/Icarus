"""Database models and initialization for ICARUS orchestrator."""

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import enum

Base = declarative_base()


class JobStatus(str, enum.Enum):
    """Job lifecycle states."""
    PENDING = "pending"
    BUILDING = "building"
    CHECKING = "checking"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(str, enum.Enum):
    """Approval request states for HITL."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Job(Base):
    """Job tracking table."""
    __tablename__ = "jobs"
    
    job_id = Column(String, primary_key=True)
    task = Column(String, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    project_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    builder_container_id = Column(String, nullable=True)
    checker_container_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)


class Telemetry(Base):
    """System telemetry data."""
    __tablename__ = "telemetry"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    cpu_percent = Column(Float, nullable=False)  # CPU percentage
    ram_mb = Column(Float, nullable=False)  # RAM in MB
    current_tool = Column(String, nullable=True)
    container_id = Column(String, nullable=True)


class AuditLog(Base):
    """Audit reports from Checker agent."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, nullable=False)
    report = Column(JSON, nullable=False)  # Renamed from audit_report to match tests
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ApprovalRequest(Base):
    """Human-in-the-loop approval requests for restricted actions."""
    __tablename__ = "approval_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, nullable=False)
    action_type = Column(String, nullable=True)  # Made optional to match tests
    action_details = Column(JSON, nullable=True)  # Made optional to match tests
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)  # Future: user tracking
    comment = Column(String, nullable=True)


class DatabaseManager:
    """Async database manager."""
    
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_db(self):
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def get_session(self) -> AsyncSession:
        """Get async database session."""
        async with self.async_session() as session:
            yield session
