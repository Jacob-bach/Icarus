# 🔧 Common Utilities - Shared ICARUS Components

The Common module provides shared utilities used across all ICARUS components, including structured logging, secrets management, and configuration helpers.

## Table of Contents

- [Overview](#overview)
- [Logging Configuration](#logging-configuration)
- [Secrets Management](#secrets-management)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

## Overview

### Files

- `logging_config.py`: Structured logging setup with context and JSON support
- `secrets.py`: Environment variable management with validation and masking
- `__init__.py`: Module exports

### Purpose

Provides consistent, secure, and production-ready utilities for:
- **Logging**: Structured logs with context fields
- **Secrets**: Safe environment variable handling
- **Security**: Automatic secret masking in logs

## Logging Configuration

### Features

- ✅ **Structured Logging**: Key-value logging with context
- ✅ **Multiple Loggers**: Component-specific loggers (orchestrator, sentinel, etc.)
- ✅ **JSON Output**: Optional JSON formatting for log aggregation
- ✅ **Secret Masking**: Automatically masks sensitive data in logs

### Setup

```python
from common.logging_config import setup_logging, get_orchestrator_logger

# Initialize logging system (call once at startup)
setup_logging(log_level="INFO", json_logs=False)

# Get component-specific logger
logger = get_orchestrator_logger()
```

### Available Loggers

```python
from common.logging_config import (
    get_orchestrator_logger,
    get_sentinel_logger,
    get_builder_logger,
    get_checker_logger
)

# Each returns a configured structlog logger
orchestrator_logger = get_orchestrator_logger()
sentinel_logger = get_sentinel_logger()
builder_logger = get_builder_logger(job_id="12345")  # Optional job_id
checker_logger = get_checker_logger(job_id="12345")
```

### Usage Examples

**Basic Logging:**
```python
logger = get_orchestrator_logger()

logger.info("Job created successfully")
logger.warning("Resource usage high", cpu_percent=85.2, ram_percent=78.1)
logger.error("Database connection failed", error="Connection timeout")
```

**Output (Human-readable):**
```
2026-02-07 16:30:00 - orchestrator - INFO - Job created successfully
2026-02-07 16:30:15 - orchestrator - WARNING - Resource usage high | cpu_percent=85.2 ram_percent=78.1
2026-02-07 16:30:20 - orchestrator - ERROR - Database connection failed | error=Connection timeout
```

**With Context:**
```python
logger = get_orchestrator_logger(job_id="550e8400-...")

logger.info(
    "Container spawned",
    container_id="d4e5f6g7h8i9",
    image="icarus-builder:latest",
    cpu_limit=1.0
)
```

**Output:**
```
2026-02-07 16:30:25 - orchestrator - INFO - Container spawned | job_id=550e8400-... container_id=d4e5f6g7h8i9 image=icarus-builder:latest cpu_limit=1.0
```

**Error with Exception:**
```python
try:
    result = risky_operation()
except Exception as e:
    logger.error_with_context("Operation failed", e, operation="risky_operation")
```

**Output:**
```
2026-02-07 16:30:30 - orchestrator - ERROR - Operation failed | operation=risky_operation exception=ValueError('Invalid input') traceback=...
```

### JSON Logging

Enable JSON output for production log aggregation:

```python
# At startup
setup_logging(log_level="INFO", json_logs=True)

logger.info("Job created", job_id="12345", status="pending")
```

**Output:**
```json
{
  "timestamp": "2026-02-07T22:30:00.123Z",
  "level": "info",
  "logger": "orchestrator",
  "message": "Job created",
  "job_id": "12345",
  "status": "pending"
}
```

### Log Levels

```python
logger.debug("Detailed debugging info")      # DEBUG
logger.info("General information")           # INFO
logger.warning("Warning messages")           # WARNING
logger.error("Error occurred")               # ERROR
logger.critical("Critical system failure")   # CRITICAL
```

## Secrets Management

### Features

- ✅ **Environment Variables**: Reads from `.env` and system environment
- ✅ **Validation**: Ensures required secrets are present at startup
- ✅ **Type Conversion**: `get_int()`, `get_float()`, `get_bool()`
- ✅ **Secret Masking**: Automatic masking in logs and output

### Usage

```python
from common.secrets import secrets, validate_secrets_at_startup

# Validate all required secrets at startup
try:
    validate_secrets_at_startup()
except ValueError as e:
    print(f"Missing secrets: {e}")
    sys.exit(1)

# Get secrets
api_key = secrets.get("OPENAI_API_KEY")
db_url = secrets.get("DATABASE_URL")

# With default value
port = secrets.get("ORCHESTRATOR_PORT", "8000")

# Type conversion
port = secrets.get_int("ORCHESTRATOR_PORT", 8000)
threshold = secrets.get_float("SENTINEL_YELLOW_THRESHOLD", 80.0)
enabled = secrets.get_bool("SENTINEL_ENABLED", True)
```

### Required Secrets

The following secrets are validated at startup:

```python
REQUIRED_SECRETS = [
    "DATABASE_URL",
    # At least one LLM provider
    "OPENAI_API_KEY" or "ANTHROPIC_API_KEY",
    "TAVILY_API_KEY"  # For Phase I web search
]
```

### Secret Masking

Secrets are automatically masked in logs:

```python
api_key = "sk-1234567890abcdef"
logger.info("Using API key", api_key=api_key)
# Output: Using API key | api_key=sk-12***def
```

**Manual Masking:**
```python
from common.secrets import secrets

masked = secrets.mask("OPENAI_API_KEY", "sk-1234567890abcdef")
print(masked)  # "sk-12***def"

# Mask arbitrary strings
masked = secrets.mask_value("super_secret_password_123")
print(masked)  # "sup***123"
```

### Type Conversion Examples

```python
# Integer with validation
max_jobs = secrets.get_int("MAX_CONCURRENT_JOBS", 2)
# Raises ValueError if not a valid integer

# Float
threshold = secrets.get_float("SENTINEL_YELLOW_THRESHOLD", 80.0)

# Boolean (accepts: "true", "1", "yes", "on")
enabled = secrets.get_bool("FEATURE_FLAG_ENABLED", False)

# All of these return True:
# FEATURE_FLAG_ENABLED=true
# FEATURE_FLAG_ENABLED=1
# FEATURE_FLAG_ENABLED=yes
# FEATURE_FLAG_ENABLED=on
```

## Usage Examples

### Orchestrator Example

```python
from common.logging_config import setup_logging, get_orchestrator_logger
from common.secrets import secrets, validate_secrets_at_startup

# Startup
setup_logging(log_level="INFO", json_logs=False)
logger = get_orchestrator_logger()

# Validate secrets
try:
    validate_secrets_at_startup()
except ValueError as e:
    logger.critical("Secrets validation failed", error=str(e))
    raise

# Get configuration
database_url = secrets.get("DATABASE_URL")
port = secrets.get_int("ORCHESTRATOR_PORT", 8000)

logger.info(
    "Starting orchestrator",
    port=port,
    database=secrets.mask("DATABASE_URL", database_url)
)
```

### Agent Example

```python
from common.logging_config import get_builder_logger
import os

job_id = os.getenv("JOB_ID")
logger = get_builder_logger(job_id=job_id)

logger.info("Builder agent started", task=os.getenv("TASK"))

try:
    # Agent work
    logger.info("Researching task requirements")
    result = await research()
    logger.info("Research complete", results_count=len(result))
except Exception as e:
    logger.error_with_context("Builder agent failed", e)
    raise
```

### Sentinel Example

```python
from common.logging_config import get_sentinel_logger

logger = get_sentinel_logger()

# Log with structured data
stats = {
    "cpu_percent": 85.2,
    "ram_percent": 78.3,
    "disk_percent": 45.0
}

logger.warning(
    "Yellow alert triggered",
    **stats,
    threshold=80.0
)
```

## Troubleshooting

### Log File Permissions

**Problem:** "Permission denied" when writing logs

**Solutions:**
```bash
# 1. Check log directory permissions
ls -la logs/

# 2. Create logs directory with correct permissions
mkdir -p logs
chmod 755 logs

# 3. Change log file ownership  (Linux/Mac)
sudo chown -R $USER:$USER logs/

# Windows - run as administrator or adjust folder security
```

---

### Missing Environment Variables

**Problem:** "Required secret XYZ not found"

**Solutions:**
```bash
# 1. Verify .env file exists
ls -la .env

# 2. Check .env is loaded
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('OPENAI_API_KEY'))"

# 3. Set environment variable temporarily
export OPENAI_API_KEY=sk-your-key

# 4. Add to .env file
echo "OPENAI_API_KEY=sk-your-key" >> .env
```

---

### Secrets Not Being Masked

**Problem:** Secrets appear in plain text in logs

**Solutions:**
1. **Use logger from common.logging_config**:
   ```python
   # ❌ Don't use basic logging
   import logging
   logging.info(f"Key: {api_key}")
   
   # ✅ Use structured logger
   from common.logging_config import get_orchestrator_logger
   logger = get_orchestrator_logger()
   logger.info("Using API key", api_key=api_key)  # Automatically masked
   ```

2. **Manual masking**:
   ```python
   from common.secrets import secrets
   logger.info(f"Database: {secrets.mask('DATABASE_URL', db_url)}")
   ```

---

### Logger Not Found

**Problem:** "AttributeError: module 'common.logging_config' has no attribute 'get_orchestrator_logger'"

**Solutions:**
```bash
# 1. Verify common module is in Python path
python -c "import common.logging_config; print(dir(common.logging_config))"

# 2. Check __init__.py exports
cat icarus/common/__init__.py

# 3. Reinstall dependencies
pip install -r requirements.txt

# 4. Verify import path
# Should be: from common.logging_config import ...
# Not: from icarus.common.logging_config import ...
```

---

For related documentation, see:
- [Orchestrator](../orchestrator/README.md)
- [Sentinel](../sentinel/README.md)
- [Builder Agent](../agents/builder/README.md)
