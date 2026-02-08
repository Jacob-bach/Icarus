# 🔌 MCP Tools - Model Context Protocol Integrations

The MCP Tools module provides Model Context Protocol (MCP) integrations that allow ICARUS agents to interact with external services safely and consistently. These tools abstract away API complexity and enforce security boundaries.

## Table of Contents

- [Overview](#overview)
- [Web Access](#web-access)
- [Filesystem](#filesystem)
- [GitHub MCP](#github-mcp)
- [Discord MCP](#discord-mcp)
- [Phase I vs Phase II](#phase-i-vs-phase-ii)
- [Adding New Tools](#adding-new-tools)
- [Troubleshooting](#troubleshooting)

## Overview

### What is MCP?

The Model Context Protocol (MCP) is a standard interface for AI agents to interact with external resources. ICARUS uses MCP to provide:

- **Consistent APIs**: Same interface across different tool implementations
- **Security Boundaries**: Whitelisting, rate limiting, and access control
- **Polymorphic Tooling**: Swap implementations based on phase (API vs Browser)

### Available Tools

| Tool | Purpose | Phase I | Phase II (Future) |
|------|---------|---------|-------------------|
| **Web Access** | Research & Documentation | Tavily API (text) | Playwright (full DOM/JS) |
| **Filesystem** | File operations in workspace | Safe path resolution | Same |
| **GitHub MCP** | Git operations | GitHub API | Same |
| **Discord MCP** | Notifications | Webhook | Full Bot (ChatOps) |

## Web Access

### Purpose

Allows agents to research documentation and best practices via web search and content extraction.

### Phase I Implementation

Uses **Tavily API** for fast, text-based search results.

**File:** `web_access.py`

### Usage

```python
from mcp_tools.web_access import WebAccessMCP
import os

# Initialize
web_access = WebAccessMCP(
    tavily_api_key=os.getenv("TAVILY_API_KEY")
)

# Search for information
results = await web_access.search("python asyncio tutorial")

# Returns list of results
for result in results:
    print(f"{result['title']}: {result['url']}")
    print(f"{result['snippet']}\n")

# Read content from URL
content = await web_access.read("https://docs.python.org/3/library/asyncio.html")
# Returns: Markdown-formatted text (stripped of ads/navigation)
```

### API Reference

#### `search(query: str, max_results: int = 5) -> List[Dict]`

Search the web for information.

**Parameters:**
- `query`: Search query string
- `max_results`: Maximum number of results to return (default: 5)

**Returns:**
```python
[
    {
        "title": "Python Asyncio Tutorial",
        "url": "https://example.com/asyncio",
        "snippet": "Learn how to use asyncio for concurrent programming...",
        "score": 0.95
    }
]
```

**Example:**
```python
results = await web_access.search("fastapi JWT authentication", max_results=3)
```

---

#### `read(url: str) -> str`

Extract text content from a URL.

**Parameters:**
- `url`: URL to read

**Returns:** Markdown-formatted text content

**Example:**
```python
content = await web_access.read("https://fastapi.tiangolo.com/tutorial/")
print(content[:500])  # First 500 characters
```

### Configuration

**Environment Variables:**
```bash
TAVILY_API_KEY=tvly-your-key-here
```

**Whitelist:** Add domains to `config/whitelist.yaml`:
```yaml
allowed_domains:
  - "tavily.com"
  - "docs.python.org"
  - "github.com"
```

## Filesystem

### Purpose

Provides safe file operations within the `/workspace` directory, preventing path traversal attacks.

**File:** `filesystem.py`

### Usage

```python
from mcp_tools.filesystem import FilesystemMCP

# Initialize with workspace root
fs = FilesystemMCP(workspace_root="/workspace")

# Write file
await fs.write_file("auth.py", "def login():\n    pass")

# Read file
content = await fs.read_file("auth.py")
print(content)

# List directory
files = await fs.list_dir(".")
# Returns: ["auth.py", "test_auth.py", "README.md"]

# Check if file exists
exists = await fs.file_exists("config.yaml")  # True/False
```

### API Reference

#### `write_file(path: str, content: str) -> None`

Write content to a file (creates parent directories automatically).

**Parameters:**
- `path`: Relative path within workspace
- `content`: File content as string

**Example:**
```python
await fs.write_file("src/api/auth.py", code_content)
# Creates /workspace/src/api/auth.py
```

---

#### `read_file(path: str) -> str`

Read file content.

**Parameters:**
- `path`: Relative path within workspace

**Returns:** File content as string

**Raises:** `FileNotFoundError` if file doesn't exist

**Example:**
```python
try:
    content = await fs.read_file("config.yaml")
except FileNotFoundError:
    print("Config not found")
```

---

#### `list_dir(path: str) -> List[str]`

List files and directories.

**Parameters:**
- `path`: Relative path within workspace

**Returns:** List of filenames

**Example:**
```python
files = await fs.list_dir("src")
# Returns: ["auth.py", "database.py", "__init__.py"]
```

---

#### `file_exists(path: str) -> bool`

Check if file or directory exists.

**Example:**
```python
if await fs.file_exists("requirements.txt"):
    content = await fs.read_file("requirements.txt")
```

### Security Features

**Path Traversal Prevention:**
```python
# These will raise SecurityError:
await fs.write_file("../etc/passwd", "bad")  # ❌
await fs.write_file("/etc/passwd", "bad")   # ❌
await fs.read_file("../../secrets.txt")     # ❌

# These are OK:
await fs.write_file("src/api/auth.py", "good")  # ✅
await fs.write_file("./config.yaml", "good")    # ✅
```

## GitHub MCP

### Purpose

Handles Git operations like creating branches, committing, and pushing code (used by Orchestrator after approval).

**File:** `github_mcp.py`

### Usage

```python
from mcp_tools.github_mcp import GitHubMCP
import os

# Initialize
github = GitHubMCP(
    github_token=os.getenv("GITHUB_TOKEN"),
    repo_path="/workspace"
)

# Create feature branch
await github.create_branch("feat/user-authentication")

# Commit changes
await github.commit_and_push(
    message="Add JWT authentication endpoint",
    branch="feat/user-authentication"
)
```

### API Reference

#### `create_branch(branch_name: str, base: str = "main") -> None`

Create a new Git branch.

**Parameters:**
- `branch_name`: Name of new branch (must follow pattern: `feat/`, `fix/`, `chore/`)
- `base`: Base branch to create from (default: "main")

**Example:**
```python
await github.create_branch("feat/add-logging")
await github.create_branch("fix/auth-bug", base="develop")
```

---

#### `commit_and_push(message: str, branch: str) -> None`

Commit all changes and push to remote.

**Parameters:**
- `message`: Commit message
- `branch`: Branch to commit to

**Example:**
```python
await github.commit_and_push(
    message="feat: Add user registration endpoint\n\nImplements JWT-based auth",
    branch="feat/user-registration"
)
```

### Branch Naming Conventions

**Enforced Patterns:**
- `feat/`: New features
- `fix/`: Bug fixes
- `chore/`: Maintenance tasks
- `docs/`: Documentation updates

**Example:**
```python
# ✅ Valid
await github.create_branch("feat/add-caching")
await github.create_branch("fix/cors-issue")

# ❌ Invalid - will raise ValueError
await github.create_branch("random-branch-name")
```

### Configuration

**Environment Variables:**
```bash
GITHUB_TOKEN=ghp_your-personal-access-token
```

**Required Permissions:**
- `repo` scope for private repositories
- `public_repo` for public repositories only

## Discord MCP

### Purpose

Sends notifications to Discord webhooks for monitoring and alerts.

**File:** `discord_mcp.py`

### Usage

```python
from mcp_tools.discord_mcp import DiscordWebhook
import os

# Initialize
discord = DiscordWebhook(
    webhook_url=os.getenv("DISCORD_WEBHOOK_URL")
)

# Send simple notification
await discord.send_notification(
    title="🚀 Job Completed",
    description="User authentication endpoint created successfully",
    color=0x00FF00  # Green
)

# Send with fields
await discord.send_notification(
    title="⚠️ Yellow Alert",
    description="System resources high",
    color=0xFFA500,  # Orange
    fields=[
        {"name": "CPU", "value": "82%", "inline": True},
        {"name": "RAM", "value": "78%", "inline": True}
    ]
)
```

### API Reference

#### `send_notification(title: str, description: str, color: int = 0x3498db, fields: List[Dict] = None) -> None`

Send Discord embed notification.

**Parameters:**
- `title`: Embed title
- `description`: Main message content
- `color`: Hex color code (default: blue 0x3498db)
- `fields`: Optional list of field dictionaries

**Color Examples:**
```python
0x00FF00  # Green - success
0xFFA500  # Orange - warning
0xFF0000  # Red - critical
0x3498db  # Blue - info
```

**Example with Fields:**
```python
await discord.send_notification(
    title="📊 Job Status",
    description="Builder agent completed",
    color=0x00FF00,
    fields=[
        {"name": "Job ID", "value": "550e8400-...", "inline": False},
        {"name": "Duration", "value": "5m 32s", "inline": True},
        {"name": "Files Created", "value": "3", "inline": True}
    ]
)
```

### Configuration

**Environment Variables:**
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef...
```

**Get Webhook URL:**
1. Go to Discord Server Settings
2. Integrations → Webhooks
3. Create webhook and copy URL

## Phase I vs Phase II

### Web Access Evolution

**Phase I (Current):**
```python
# Tavily API - fast, text-only
results = await web_access.search("python logging")
content = await web_access.read(url)  # Returns markdown text
```

**Phase II (Future):**
```python
# Playwright - full browser
page = await web_access.navigate(url)
screenshot = await page.screenshot()
dom = await page.get_html()
await page.click("button#submit")
```

### Discord Evolution

**Phase I (Current):**
```python
# One-way webhooks only
await discord.send_notification("Job completed")
```

**Phase II (Future):**
```python
# Full Discord bot - two-way ChatOps
@discord.command()
async def status(ctx):
    ctx.reply(f"Current jobs: {job_count}")

await discord.send_message(channel_id, "Job completed")
response = await discord.wait_for_reply()
```

## Adding New Tools

### Creating a New MCP Tool

1. **Create tool file** in `mcp_tools/`:

```python
# mcp_tools/database_mcp.py
import asyncpg

class DatabaseMCP:
    """MCP tool for database operations."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def connect(self):
        """Initialize connection pool."""
        self.pool = await asyncpg.create_pool(self.connection_string)
    
    async def query(self, sql: str) -> List[Dict]:
        """Execute SELECT query."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql)
            return [dict(row) for row in rows]
```

2. **Add to __init__.py**:

```python
from .database_mcp import DatabaseMCP
```

3. **Update whitelist** if needed in `config/whitelist.yaml`

4. **Document in this README**

## Troubleshooting

### API Key Errors

**Problem:** "Invalid API key" or "Unauthorized"

**Solutions:**
```bash
# 1. Verify API keys are set
echo $TAVILY_API_KEY
echo $GITHUB_TOKEN
echo $DISCORD_WEBHOOK_URL

# 2. Test keys directly
# Tavily
curl -X POST https://api.tavily.com/search \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'"$TAVILY_API_KEY"'", "query": "test"}'

# GitHub
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/user

# Discord
curl -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message"}'

# 3. Regenerate keys if expired
```

---

### Network Timeouts

**Problem:** "Connection timeout" when calling MCP tools

**Solutions:**
1. **Increase timeout** in tool calls:
   ```python
   # In mcp tool code
   async with httpx.AsyncClient(timeout=30.0) as client:
       response = await client.post(...)
   ```

2. **Check network connectivity**:
   ```bash
   curl -I https://api.tavily.com
   ping github.com
   ```

3. **Proxy configuration** (if behind corporate firewall):
   ```bash
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

---

### Permission Denied (Filesystem)

**Problem:** "Permission denied" when writing files

**Solutions:**
```bash
# 1. Check workspace permissions
ls -la /workspace/

# 2. Verify container user
docker exec <container_id> whoami
docker exec <container_id> id

# 3. Fix permissions
sudo chown -R 1000:1000 /workspace/
chmod -R 755 /workspace/
```

---

### Git Push Failures

**Problem:** "Failed to push to remote"

**Solutions:**
1. **Verify GitHub token has push access**:
   ```bash
   git clone https://$GITHUB_TOKEN@github.com/user/repo.git
   ```

2. **Check branch protection rules** in GitHub settings

3. **Verify remote URL**:
   ```bash
   cd /workspace
   git remote -v
   ```

4. **Test Git credentials**:
   ```python
   from mcp_tools.github_mcp import GitHubMCP
   github = GitHubMCP(github_token=os.getenv("GITHUB_TOKEN"))
   # If initialization succeeds, token format is valid
   ```

---

For related documentation, see:
- [Builder Agent](../agents/builder/README.md)
- [Checker Agent](../agents/checker/README.md)
- [Configuration](../config/README.md)
