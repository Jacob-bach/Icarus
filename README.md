# 🚀 ICARUS - Autonomous Development Environment

**Phase I: The Speedster**  
*Local-first autonomous coding with Builder/Checker/Reviewer architecture*

## Overview

ICARUS is a containerized autonomous software development environment that safely executes complex coding tasks through a strict separation of concerns:

- **Builder Agent**: Generates code autonomously
- **Checker Agent**: Audits code with static analysis and security scans
- **Human Review**: Final approval gate before deployment
- **Orchestrator**: Manages the entire workflow
- **System Sentinel**: Monitors resources and prevents system lockup

## Architecture

```
┌─────────────┐
│    User     │
│  Dashboard  │
└──────┬──────┘
       │ HTTP/WebSocket
       ▼
┌─────────────────┐
│  Orchestrator   │ ◄── System Sentinel
│    (FastAPI)    │
└────┬──────┬─────┘
     │      │
     ▼      ▼
┌─────────┐ ┌─────────┐
│ Builder │ │ Checker │
│  Agent  │ │  Agent  │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
  ┌─────────────────┐
  │ Shared Workspace│
  │    (Volume)     │
  └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for dashboard development)

### Installation

1. **Clone the repository** (or navigate to the project directory)

```bash
cd icarus
```

2. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your API keys:
# - OPENAI_API_KEY or ANTHROPIC_API_KEY
# - TAVILY_API_KEY (for web search)
# - GITHUB_TOKEN (for Git operations)
# - DISCORD_WEBHOOK_URL (optional)
```

3. **Build Docker images**

```bash
# Build agent images
docker build -t icarus-builder:latest -f agents/builder/Dockerfile agents/builder/
docker build -t icarus-checker:latest -f agents/checker/Dockerfile agents/checker/
```

4. **Start the services**

```bash
docker-compose up -d
```

5. **Access the dashboard**

Open http://localhost:5173 in your browser

## Usage

### Creating a Job

1. Navigate to the dashboard at http://localhost:5173
2. Click "+ New Job"
3. Enter a task description (e.g., "Create a FastAPI endpoint for user authentication")
4. Specify the project path (default: `/workspace`)
5. Click "Launch Job"

### Monitoring Progress

- View real-time telemetry (CPU, RAM usage)
- Watch live terminal output via WebSocket
- Track job status: `pending` → `building` → `checking` → `awaiting_approval`

### Reviewing and Approving

1. When status changes to `awaiting_approval`, navigate to the Review page
2. Review the audit report (static analysis, security scans)
3. Check the file diffs (in the workspace volume)
4. Click "Approve & Commit" to push to Git, or "Reject & Cleanup" to discard

## API Endpoints

### Orchestrator (Port 8000)

- `POST /jobs/spawn` - Create a new job
- `GET /jobs` - List all jobs
- `GET /jobs/{job_id}/status` - Get job status
- `GET /jobs/{job_id}/telemetry` - Get real-time metrics
- `GET /jobs/{job_id}/audit` - Get audit report
- `POST /jobs/{job_id}/approve` - Approve or reject job
- `WebSocket /jobs/{job_id}/stream` - Live log streaming

## Project Structure

```
icarus/
├── orchestrator/          # FastAPI backend
│   ├── main.py           # API endpoints
│   ├── database.py       # SQLAlchemy models
│   ├── docker_manager.py # Container management
│   └── job_queue.py      # Workflow orchestration
├── sentinel/             # System monitoring
│   ├── monitor.py        # Resource tracking
│   └── alerts.py         # Alert management
├── agents/               # Docker containers
│   ├── builder/          # Code generation agent
│   └── checker/          # Audit agent
├── mcp_tools/            # Model Context Protocol tools
│   ├── web_access.py     # Tavily API integration
│   ├── filesystem.py     # Safe file operations
│   ├── github_mcp.py     # Git integration
│   └── discord_mcp.py    # Discord notifications
├── dashboard/            # React frontend
│   └── src/
│       ├── pages/        # JobList, JobDetail, Review
│       └── components/   # Telemetry, Terminal, DiffViewer
└── config/
    ├── config.yaml       # System configuration
    └── whitelist.yaml    # Domain whitelist
```

## Configuration

### Resource Limits

Edit `config/config.yaml` to adjust:

- `max_concurrent_jobs`: Number of parallel jobs
- `agents.builder.cpu_limit`: CPU cores per Builder
- `agents.builder.memory_limit`: RAM limit in bytes

### Security

- All container network access is whitelisted (`config/whitelist.yaml`)
- Builder has read-write access to workspace
- Checker has read-only access (security layer)
- Python packages and npm modules are sandboxed

### System Sentinel Thresholds

- **Yellow Alert (80%)**: Stop accepting new jobs
- **Red Alert (90%)**: Pause all containers

## Development

### Running Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start orchestrator
cd orchestrator
python main.py

# Start dashboard (separate terminal)
cd dashboard
npm install
npm run dev
```

### Building Agent Images

```bash
docker build -t icarus-builder:latest -f agents/builder/Dockerfile agents/builder/
docker build -t icarus-checker:latest -f agents/checker/Dockerfile agents/checker/
```

## Phase II Roadmap

Future enhancements (Phase II: The Autonomist):

- Headless browser support (Playwright) for full DOM access
- Local LLMs via Ollama/vLLM
- Full Discord bot integration (two-way ChatOps)
- GPU acceleration for model inference
- Advanced code execution environments

## Troubleshooting

### "Failed to spawn container"

- Ensure Docker is running
- Check that agent images are built: `docker images | grep icarus`

### "API key not set"

- Verify `.env` file exists and contains valid API keys
- Restart services: `docker-compose restart`

### Dashboard not loading

- Check orchestrator is running: `curl http://localhost:8000`
- Verify CORS settings in `orchestrator/main.py`

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.

---

**Built with ❤️ for autonomous developers**
