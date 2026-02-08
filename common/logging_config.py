"""Robust structured logging configuration for ICARUS."""

import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
import traceback


class ContextualLogger:
    """Logger that automatically includes context like job_id in all messages."""
    
    def __init__(self, name: str, job_id: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.job_id = job_id
        self.context: Dict[str, Any] = {}
    
    def set_job_id(self, job_id: str):
        """Set the job_id for this logger context."""
        self.job_id = job_id
    
    def add_context(self, **kwargs):
        """Add additional context to all log messages."""
        self.context.update(kwargs)
    
    def _format_message(self, msg: str, extra: Optional[Dict] = None) -> str:
        """Format message with context."""
        parts = []
        
        if self.job_id:
            # Slice job_id to first 8 characters
            job_id_short = self.job_id[:8] if isinstance(self.job_id, str) else str(self.job_id)[:8]
            parts.append(f"[job:{job_id_short}]")
        
        for key, value in self.context.items():
            parts.append(f"[{key}:{value}]")
        
        if extra:
            for key, value in extra.items():
                parts.append(f"[{key}:{value}]")
        
        context_str = " ".join(parts)
        return f"{context_str} {msg}" if context_str else msg
    
    def debug(self, msg: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._format_message(msg, kwargs))
    
    def info(self, msg: str, **kwargs):
        """Log info message with context."""
        self.logger.info(self._format_message(msg, kwargs))
    
    def warning(self, msg: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._format_message(msg, kwargs))
    
    def error(self, msg: str, exc_info: bool = False, **kwargs):
        """Log error message with context and optional exception info."""
        formatted_msg = self._format_message(msg, kwargs)
        self.logger.error(formatted_msg, exc_info=exc_info)
    
    def critical(self, msg: str, exc_info: bool = False, **kwargs):
        """Log critical message with context and optional exception info."""
        formatted_msg = self._format_message(msg, kwargs)
        self.logger.critical(formatted_msg, exc_info=exc_info)
    
    def exception(self, msg: str, **kwargs):
        """Log exception with full traceback and context."""
        formatted_msg = self._format_message(msg, kwargs)
        self.logger.exception(formatted_msg)
    
    def error_with_context(self, msg: str, error: Exception, **kwargs):
        """Log error with detailed context about what operation failed.
        
        Args:
            msg: Human-readable description of what was being attempted
            error: The exception that occurred
            **kwargs: Additional context (e.g., container_id, file_path)
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Build detailed error context
        error_context = {
            "error_type": error_type,
            "error_msg": error_msg,
            **kwargs
        }
        
        # Log with full context
        full_msg = (
            f"OPERATION FAILED: {msg} | "
            f"Error: {error_type}: {error_msg}"
        )
        
        self.logger.error(
            self._format_message(full_msg, error_context),
            exc_info=True
        )


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """Configure logging for ICARUS components.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for console only)
        json_format: Use JSON structured logging
        max_bytes: Max size of log file before rotation
        backup_count: Number of backup log files to keep
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str, job_id: Optional[str] = None) -> ContextualLogger:
    """Get a contextual logger instance.
    
    Args:
        name: Logger name (typically __name__)
        job_id: Optional job ID for context
    
    Returns:
        ContextualLogger instance
    """
    return ContextualLogger(name, job_id=job_id)


# Pre-configured loggers for different components
def get_orchestrator_logger(job_id: Optional[str] = None) -> ContextualLogger:
    """Get logger for orchestrator components."""
    logger = get_logger("icarus.orchestrator", job_id)
    logger.add_context(component="orchestrator")
    return logger


def get_agent_logger(agent_type: str, job_id: Optional[str] = None) -> ContextualLogger:
    """Get logger for agent components.
    
    Args:
        agent_type: "builder" or "checker"
        job_id: Job ID for context
    """
    logger = get_logger(f"icarus.agent.{agent_type}", job_id)
    logger.add_context(component="agent", agent_type=agent_type)
    return logger


def get_sentinel_logger() -> ContextualLogger:
    """Get logger for sentinel components."""
    logger = get_logger("icarus.sentinel")
    logger.add_context(component="sentinel")
    return logger


def get_mcp_logger(tool_name: str) -> ContextualLogger:
    """Get logger for MCP tool components.
    
    Args:
        tool_name: Name of the MCP tool (e.g., "web_access", "github")
    """
    logger = get_logger(f"icarus.mcp.{tool_name}")
    logger.add_context(component="mcp", tool=tool_name)
    return logger
