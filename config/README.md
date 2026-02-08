# ⚙️ Configuration - ICARUS Settings

The Config module contains configuration files that control ICARUS behavior, resource limits, and security settings.

## Table of Contents

- [Overview](#overview)
- [config.yaml](#configyaml)
- [whitelist.yaml](#whitelistyaml)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## Overview

### Configuration Files

- `config.yaml`: System-wide settings (resource limits, timeouts, thresholds)
- `whitelist.yaml`: Network domain whitelist for agent access
- `.env`: Sensitive environment variables (API keys, database URL)

### Configuration Hierarchy

1. **Environment Variables** (highest priority)
2. **config.yaml** (system defaults)
3 **Code Defaults** (fallback values)

## config.yaml

Main configuration file for ICARUS system settings.

### Structure

```yaml
orchestrator:
  host: "0.0.0.0"
  port: 8000
  max_concurrent_jobs: 2
  job_timeout_seconds: 1800  # 30 minutes

sentinel:
  enabled: true
  yellow_threshold: 80  # CPU/RAM percentage
  red_threshold: 90
  poll_interval_seconds: 5
  
agents:
  builder:
    image_name: "icarus-builder:latest"
    cpu_limit: 1.0  # CPU cores
    memory_limit: 1073741824  # 1GB in bytes
    timeout_seconds: 600  # 10 minutes
    network_mode: "bridge"
    
  checker:
    image_name: "icarus-checker:latest"
    cpu_limit: 0.5
    memory_limit: 536870912  # 512MB in bytes
    timeout_seconds: 300  # 5 minutes
    network_mode: "bridge"

workspace:
  base_path: "/workspace"
  mount_type: "volume"  # or "bind"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Configuration Options

#### Orchestrator

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `host` | string | `"0.0.0.0"` | Server bind address |
| `port` | integer | `8000` | API server port |
| `max_concurrent_jobs` | integer | `2` | Maximum parallel jobs |
| `job_timeout_seconds` | integer | `1800` | Global job timeout (30 min) |

**Example:**
```yaml
orchestrator:
  max_concurrent_jobs: 4  # Allow 4 parallel jobs
  job_timeout_seconds: 3600  # 1 hour timeout
```

#### Sentinel

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable resource monitoring |
| `yellow_threshold` | integer | `80` | Warning threshold (%) |
| `red_threshold` | integer | `90` | Critical threshold (%) |
| `poll_interval_seconds` | integer | `5` | Monitoring frequency |

**Tuning Tips:**
- **16GB RAM**: Use `yellow_threshold: 80, red_threshold: 90`
- **32GB+ RAM**: Use `yellow_threshold: 75, red_threshold: 85`
- **8GB RAM**: Use `yellow_threshold: 85, red_threshold: 95` (more aggressive)

#### Agents

| Option | Type | Description |
|--------|------|-------------|
| `image_name` | string | Docker image name |
| `cpu_limit` | float | CPU cores (1.0 = 1 core) |
| `memory_limit` | integer | RAM in bytes |
| `timeout_seconds` | integer | Agent execution timeout |
| `network_mode` | string | Docker network mode |

**Memory Limits:**
```yaml
memory_limit: 1073741824   # 1GB
memory_limit: 536870912    # 512MB
memory_limit: 2147483648   # 2GB
```

**CPU Limits:**
```yaml
cpu_limit: 0.5   # Half a core
cpu_limit: 1.0   # One full core
cpu_limit: 2.0   # Two cores
```

#### Workspace

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `base_path` | string | `"/workspace"` | Workspace mount path |
| `mount_type` | string | `"volume"` | "volume" or "bind" |

**Mount Types:**
- `"volume"`: Docker-managed volume (recommended)
- `"bind"`: Bind mount to host directory

## whitelist.yaml

Controls which external domains agents can access.

### Structure

```yaml
allowed_domains:
  - "pypi.org"
  - "npmjs.com"
  - "github.com"
  - "api.github.com"
  - "tavily.com"
  - "api.tavily.com"
  - "docs.python.org"
  - "fastapi.tiangolo.com"
```

### Adding Domains

```yaml
allowed_domains:
  - "pypi.org"
  - "npmjs.com"
  - "github.com"
  - "your-corporate-artifactory.com"  # Add custom domain
  - "internal-docs.company.com"
```

### Wildcard Support

**Not supported** for security reasons. Each subdomain must be explicit:

```yaml
# ❌ Not allowed
allowed_domains:
  - "*.github.com"

# ✅ Correct
allowed_domains:
  - "github.com"
  - "api.github.com"
  - "raw.githubusercontent.com"
```

## Environment Variables

Sensitive configuration stored in `.env` file (never committed to git).

### Required Variables

```bash
# LLM Provider (choose one or both)
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Web Search (Phase I)
TAVILY_API_KEY=tvly-your-tavily-key-here

# Database
DATABASE_URL=postgresql://icarus:password@localhost:5432/icarus

# Git Integration
GITHUB_TOKEN=ghp_your-github-token-here

# Optional: Discord Notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/.../...
```

### Optional Variables

```bash
# Orchestrator
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8000

# Sentinel Overrides
SENTINEL_ENABLED=true
SENTINEL_YELLOW_THRESHOLD=80
SENTINEL_RED_THRESHOLD=90
SENTINEL_POLL_INTERVAL=5

# Logging
LOG_LEVEL=INFO
JSON_LOGS=false
```

### Loading Environment

```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access variables
api_key = os.getenv("OPENAI_API_KEY")
db_url = os.getenv("DATABASE_URL")
```

### Example .env File

```bash
# ICARUS Environment Configuration
# Copy to .env and fill in your values

# LLM Provider
OPENAI_API_KEY=sk-proj-...
#ANTHROPIC_API_KEY=sk-ant-...

# Web Search
TAVILY_API_KEY=tvly-...

# Database
DATABASE_URL=postgresql://icarus:SecurePassword123@localhost:5432/icarus

# GitHub
GITHUB_TOKEN=ghp_...

# Discord (optional)
#DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Orchestrator
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8000

# Sentinel
SENTINEL_YELLOW_THRESHOLD=80
SENTINEL_RED_THRESHOLD=90
```

## Troubleshooting

### Invalid YAML Syntax

**Problem:** "YAMLError: mapping values are not allowed here"

**Solutions:**
```bash
# 1. Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('icarus/config/config.yaml'))"

# 2. Check indentation (use spaces, not tabs)
# ❌ Bad
agents:
	builder:
		cpu_limit: 1.0

# ✅ Good (2 spaces)
agents:
  builder:
    cpu_limit: 1.0

# 3. Quote strings with special characters
allowed_domains:
  - "api.example.com:8080"  # Port in URL needs quotes
```

---

### Missing Configuration Keys

**Problem:** "KeyError: 'orchestrator'" when reading config

**Solutions:**
```python
# 1. Check config file exists
import os
assert os.path.exists("icarus/config/config.yaml")

# 2. Provide defaults
import yaml

with open("icarus/config/config.yaml") as f:
    config = yaml.safe_load(f)

# Use .get() with defaults
port = config.get("orchestrator", {}).get("port", 8000)

# 3. Validate config structure at startup
requiredkeys = ["orchestrator", "sentinel", "agents"]
for key in required_keys:
    if key not in config:
        raise ValueError(f"Missing required config section: {key}")
```

---

### Whitelist Errors

**Problem:** "Domain request blocked: docs.python.org"

**Solutions:**
```bash
# 1. Add domain to whitelist.yaml
echo "  - \"docs.python.org\"" >> icarus/config/whitelist.yaml

# 2. Verify whitelist is loaded
python -c "import yaml; print(yaml.safe_load(open('icarus/config/whitelist.yaml')))"

# 3. Check for typos (case-sensitive)
# ❌ Wrong
allowed_domains:
  - "GitHub.com"

# ✅ Correct
allowed_domains:
  - "github.com"
```

---

### Environment Variable Not Set

**Problem:** "Required environment variable OPENAI_API_KEY not found"

**Solutions:**
```bash
# 1. Check .env file exists
ls -la .env

# 2. Verify variable is in .env
grep OPENAI_API_KEY .env

# 3. Ensure .env is loaded in code
# Add to Python entrypoint:
from dotenv import load_dotenv
load_dotenv()

# 4. Set temporarily for testing
export OPENAI_API_KEY=sk-test-key
python main.py
```

---

### Configuration Not Applied

**Problem:** Changed config values but system still uses old values

**Solutions:**
```bash
# 1. Restart services
docker-compose restart

# 2. Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 3. Verify config file path is correct
python -c "import os; print(os.path.abspath('icarus/config/config.yaml'))"

# 4. Check environment variables override config
# Environment variables take precedence over config.yaml
unset ORCHESTRATOR_PORT  # Remove override
```

---

For related documentation, see:
- [Main README](../../README.md)
- [Common Utilities](../common/README.md)
- [Environment Setup](.env.example)
