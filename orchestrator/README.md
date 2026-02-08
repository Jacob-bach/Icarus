# 🎯 Orchestrator - ICARUS Core Controller

The Orchestrator is the central hub of ICARUS, managing the entire autonomous coding workflow through a FastAPI backend. It handles job queuing, Docker container lifecycle management, database state persistence, and serves as the API gateway for the dashboard.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [WebSocket Streaming](#websocket-streaming)
- [Job Lifecycle](#job-lifecycle)
- [Configuration](#configuration)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Overview

### Role in ICARUS

The Orchestrator acts as the "kernel" of the ICARUS system:

- **Job Queue Management**: Accepts tasks, queues them, and orchestrates execution
- **Container Lifecycle**: Spawns, monitors, and destroys Builder and Checker agents
- **State Persistence**: Stores job status, telemetry, and audit reports in PostgreSQL
- **API Gateway**: Provides HTTP/WebSocket endpoints for the dashboard
- **HITL (Human-in-the-Loop)**: Enforces approval gates before code deployment
- **Sentinel Integration**: Queries System Sentinel before spawning resource-intensive containers

### Technology Stack

- **FastAPI**: Async Python web framework
- **SQLAlchemy**: ORM for database operations
- **Docker SDK**: Container management
- **WebSockets**: Real-time log streaming
- **Uvicorn**: ASGI server

## Architecture

### Component Structure

```
orchestrator/
├── main.py              # FastAPI application and endpoints
├── database.py          # SQLAlchemy models and DB manager
├── docker_manager.py    # Docker container operations
├── job_queue.py         # Job orchestration logic
└── models.py            # Pydantic request/response models
```

### Request Flow

```mermaid
sequenceDiagram
    participant Client as Dashboard/API Client
    participant API as FastAPI Endpoint
    participant Queue as Job Queue
    participant Docker as Docker Manager
    participant Sentinel as System Sentinel
    participant DB as Database
    
    Client->>API: POST /jobs/spawn
    API->>Queue: submit_job()
    Queue->>Sentinel: check_can_accept_jobs()
    
    alt Resources Available
        Sentinel-->>Queue: OK (GREEN/YELLOW)
        Queue->>DB: Create Job Record
        Queue->>Docker: spawn_container(builder)
        Docker-->>Queue: Container ID
        Queue->>DB: Update Container ID
        Queue-->>API: Job ID
        API-->>Client: 201 Created
    else Resources Critical
        Sentinel-->>Queue: BLOCKED (RED)
        Queue-->>API: Service Unavailable
        API-->>Client: 503 Error
    end
```

## API Endpoints

### Job Management

#### `POST /jobs/spawn`

Create a new autonomous coding job.

**Request Body:**
```json
{
  "task": "Create a FastAPI endpoint for user authentication",
  "project_path": "/workspace"
}
```

**Response (201):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job created and queued for execution"
}
```

**Python Example:**
```python
import httpx

async def create_job(task: str, project_path: str = "/workspace"):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/jobs/spawn",
            json={"task": task, "project_path": project_path},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

# Usage
job = await create_job("Add logging to the API endpoints")
print(f"Job created: {job['job_id']}")
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/jobs/spawn \
  -H "Content-Type: application/json" \
  -d '{"task": "Create a user login endpoint", "project_path": "/workspace"}'
```

**JavaScript Example:**
```javascript
async function createJob(task, projectPath = '/workspace') {
  const response = await fetch('http://localhost:8000/jobs/spawn', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, project_path: projectPath })
  });
  
  if (!response.ok) {
    throw new Error(`Failed to create job: ${response.statusText}`);
  }
  
  return await response.json();
}

// Usage
const job = await createJob('Create a user registration endpoint');
console.log(`Job created: ${job.job_id}`);
```

---

#### `GET /jobs/{job_id}/status`

Retrieve current status of a job.

**Response (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "building",
  "task": "Create a FastAPI endpoint for user authentication",
  "created_at": "2026-02-07T16:30:00Z",
  "completed_at": null,
  "error_message": null
}
```

**Status Values:**
- `pending` - Queued, waiting for resources
- `building` - Builder agent is generating code
- `checking` - Checker agent is auditing code
- `awaiting_approval` - Human review required
- `approved` - User approved, committing to Git
- `completed` - Successfully finished
- `rejected` - User rejected the changes
- `failed` - Error occurred during execution

**Python Example:**
```python
async def get_job_status(job_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/jobs/{job_id}/status"
        )
        return response.json()

# Poll for completion
import asyncio

async def wait_for_completion(job_id: str, max_wait: int = 600):
    for _ in range(max_wait // 5):
        status = await get_job_status(job_id)
        if status['status'] in ['awaiting_approval', 'completed', 'failed']:
            return status
        await asyncio.sleep(5)
    raise TimeoutError(f"Job {job_id} did not complete in {max_wait}s")
```

---

#### `GET /jobs/{job_id}/telemetry`

Get real-time resource usage for active job.

**Response (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "building",
  "cpu_usage": 45.2,
  "ram_usage_mb": 512.8,
  "current_tool": "web_search(fastapi authentication best practices)"
}
```

---

#### `GET /jobs/{job_id}/audit`

Retrieve audit report generated by Checker agent.

**Response (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "audit_report": {
    "static_analysis": {
      "flake8": {"issues_count": 3, "issues": [...]},
      "pylint": {"score": "9.5/10", "issues_count": 2}
    },
    "security_scan": {
      "bandit": {"high_severity": 0, "medium_severity": 1}
    },
    "logic_verification": {
      "files_created": 2,
      "file_list": ["auth.py", "test_auth.py"]
    },
    "summary": "⚠️ 1 medium severity issue found"
  },
  "created_at": "2026-02-07T16:35:00Z"
}
```

---

#### `POST /jobs/{job_id}/approve`

Approve or reject a job after human review.

**Request Body:**
```json
{
  "approved": true,
  "comment": "Looks good, deploying to production!"
}
```

**Response (200):**
```json
{
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 approved",
  "status": "approved"
}
```

**Python Example:**
```python
async def approve_job(job_id: str, approved: bool, comment: str = ""):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/jobs/{job_id}/approve",
            json={"approved": approved, "comment": comment}
        )
        return response.json()

# Approve
await approve_job(job_id, approved=True, comment="LGTM!")

# Reject
await approve_job(job_id, approved=False, comment="Security issues need fixing")
```

---

#### `GET /jobs`

List all jobs with optional filtering.

**Query Parameters:**
- `limit` (int, default: 50): Maximum number of results
- `status` (str, optional): Filter by status

**Response (200):**
```json
[
  {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "task": "Create user authentication",
    "status": "completed",
    "created_at": "2026-02-07T16:30:00Z",
    "completed_at": "2026-02-07T16:45:00Z"
  }
]
```

**cURL Example:**
```bash
# Get all pending jobs
curl "http://localhost:8000/jobs?status=pending&limit=10"

# Get recent jobs
curl "http://localhost:8000/jobs?limit=20"
```

---

#### `POST /jobs/{job_id}/callback`

**(Internal)** Callback endpoint for agents to report progress.

Agents use this to:
- Report current tool usage
- Send completion signals
- Report errors
- Submit audit reports

**Request Body (Telemetry):**
```json
{
  "current_tool": "web_search(python logging best practices)",
  "cpu_usage": 35.0,
  "ram_usage_mb": 450.0
}
```

**Request Body (Completion):**
```json
{
  "status": "completed",
  "message": "Builder agent finished successfully"
}
```

**Request Body (Audit Report from Checker):**
```json
{
  "status": "completed",
  "audit_report": { ... }
}
```

## WebSocket Streaming

### `/jobs/{job_id}/stream`

Real-time WebSocket connection for live job updates.

**JavaScript Client Example:**
```javascript
function connectJobStream(jobId) {
  const ws = new WebSocket(`ws://localhost:8000/jobs/${jobId}/stream`);
  
  ws.onopen = () => {
    console.log('Connected to job stream');
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Job update:', data);
    
    // Update UI based on status
    if (data.type === 'status_update') {
      updateJobStatus(data.status);
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
  
  ws.onclose = () => {
    console.log('Disconnected from job stream');
    // Reconnect logic
    setTimeout(() => connectJobStream(jobId), 5000);
  };
  
  return ws;
}

// Usage
const ws = connectJobStream('550e8400-e29b-41d4-a716-446655440000');
```

**Python Client Example:**
```python
import asyncio
import websockets
import json

async def stream_job_logs(job_id: str):
    uri = f"ws://localhost:8000/jobs/{job_id}/stream"
    
    async with websockets.connect(uri) as websocket:
        print(f"Connected to job {job_id} stream")
        
        async for message in websocket:
            data = json.loads(message)
            print(f"Status: {data['status']}")
            
            if data['status'] in ['completed', 'failed']:
                break

# Usage
await stream_job_logs('550e8400-e29b-41d4-a716-446655440000')
```

## Database Schema

The Orchestrator uses PostgreSQL (via SQLAlchemy) to persist state.

### Tables

#### `jobs`

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| job_id | String (UUID) | Unique job identifier |
| task | Text | User-provided task description |
| project_path | String | Workspace path |
| status | Enum | Current job status |
| builder_container_id | String | Docker container ID for builder |
| checker_container_id | String | Docker container ID for checker |
| created_at | DateTime | Job creation timestamp |
| completed_at | DateTime | Completion timestamp (nullable) |
| error_message | Text | Error details if failed (nullable) |

#### `telemetry`

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| job_id | String (FK) | Associated job |
| timestamp | DateTime | Measurement time |
| cpu_usage | Float | CPU percentage |
| ram_usage_mb | Float | RAM in MB |
| current_tool | String | Active MCP tool name |

#### `audit_logs`

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| job_id | String (FK) | Associated job |
| audit_report | JSON | Full audit report from Checker |
| created_at | DateTime | Report generation time |

### Database Manager

```python
from orchestrator.database import DatabaseManager

# Initialize
db_manager = DatabaseManager("postgresql://user:pass@localhost/icarus")
await db_manager.init_db()

# Use in async context
async with db_manager.async_session() as session:
    result = await session.execute(select(Job).where(Job.job_id == job_id))
    job = result.scalar_one_or_none()
```

## Job Lifecycle

The Orchestrator manages jobs through distinct phases:

```mermaid
stateDiagram-v2
    [*] --> Pending: Job Created
    Pending --> Building: Resources Available
    Building --> Checking: Builder Complete
    Checking --> AwaitingApproval: Checker Complete
    AwaitingApproval --> Approved: User Approves
    AwaitingApproval --> Rejected: User Rejects
    Approved --> Completed: Git Push Success
    Rejected --> [*]
    Completed --> [*]
    
    Building --> Failed: Error
    Checking --> Failed: Error
    Approved --> Failed: Git Error
    Failed --> [*]
```

### Phase Details

1. **Pending**: Job is queued, waiting for Sentinel approval
2. **Building**: Builder agent researches and generates code
3. **Checking**: Checker agent runs static analysis and security scans
4. **Awaiting Approval**: Human reviews diff and audit report
5. **Approved**: User approved, orchestrator commits to Git
6. **Completed**: Successfully merged to repository
7. **Rejected**: User rejected, workspace cleaned up
8. **Failed**: Error occurred, check `error_message` field

## Configuration

### Environment Variables

```bash
# Orchestrator Settings
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8000

# Database
DATABASE_URL=postgresql://icarus:password@localhost:5432/icarus

# LLM Provider (for agents)
OPENAI_API_KEY=sk-your-key
# or
ANTHROPIC_API_KEY=sk-ant-your-key

# Web Search
TAVILY_API_KEY=tvly-your-key

# Git Integration
GITHUB_TOKEN=ghp_your-token

# Optional: Discord Notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### config.yaml

```yaml
orchestrator:
  host: "0.0.0.0"
  port: 8000
  max_concurrent_jobs: 2
  job_timeout_seconds: 1800  # 30 minutes
```

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start orchestrator
cd icarus/orchestrator
python main.py
```

The server will start at `http://localhost:8000`

### API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Testing

```bash
# Run orchestrator tests
pytest tests/test_orchestrator/

# With coverage
pytest --cov=orchestrator tests/test_orchestrator/
```

### Adding New Endpoints

1. Define Pydantic models in `models.py`
2. Add endpoint function in `main.py`
3. Use dependency injection for `db_manager` and `job_queue`
4. Add structured logging with context

Example:
```python
@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    logger.info("Canceling job", job_id=job_id)
    
    try:
        await job_queue.cancel_job(job_id)
        return {"message": f"Job {job_id} canceled"}
    except Exception as e:
        logger.error("Failed to cancel job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

## Troubleshooting

### Docker Connection Issues

**Problem:** "Failed to spawn container"

**Solutions:**
```bash
# 1. Check Docker is running
docker ps

# 2. Verify Docker socket permissions (Linux)
sudo chmod 666 /var/run/docker.sock

# 3. Check agent images exist
docker images | grep icarus

# 4. Test Docker SDK connection
python -c "import docker; print(docker.from_env().ping())"
```

### Database Errors

**Problem:** "Database connection failed"

**Solutions:**
```bash
# 1. Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# 2. Test connection string
python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://icarus:password@localhost/icarus'); engine.connect()"

# 3. Check database exists
psql -h localhost -U icarus -l

# 4. Initialize database
python -c "from orchestrator.database import DatabaseManager; import asyncio; asyncio.run(DatabaseManager('postgresql://...').init_db())"
```

### Port Conflicts

**Problem:** "Address already in use on port 8000"

**Solutions:**
```bash
# 1. Find process using port
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/Mac
lsof -i :8000
kill -9 <pid>

# 2. Or change port in .env
ORCHESTRATOR_PORT=8001
```

### Job Stuck in Building

**Problem:** Job status stuck at "building" for too long

**Solutions:**
```bash
# 1. Check container logs
docker logs <builder_container_id>

# 2. Check if container is running
docker ps -a | grep icarus_builder

# 3. Check Sentinel hasn't paused it
# Review sentinel logs for RED alerts

# 4. Manually inspect container
docker exec -it <container_id> /bin/bash

# 5. Force cleanup
python -c "from orchestrator.job_queue import JobQueue; import asyncio; asyncio.run(JobQueue(...).cleanup_job('<job_id>'))"
```

### Callback Timeout

**Problem:** Agent callbacks failing with timeout errors

**Solutions:**
1. Check network connectivity between containers and host
2. Verify orchestrator is accessible from within containers:
   ```bash
   docker exec <container_id> curl http://host.docker.internal:8000/
   ```
3. Increase callback timeout in agent code
4. Check orchestrator logs for callback reception

### WebSocket Disconnections

**Problem:** Dashboard WebSocket keeps disconnecting

**Solutions:**
1. Check for reverse proxy timeout settings (if using nginx/etc)
2. Verify CORS middleware allows WebSocket connections
3. Check browser console for specific error codes
4. Implement reconnection logic with exponential backoff

---

For related documentation, see:
- [Job Queue Implementation](job_queue.py)
- [Docker Manager](docker_manager.py)
- [Database Models](database.py)
- [System Sentinel Integration](../sentinel/README.md)
- [Dashboard API Client](../dashboard/README.md)
