# 🖥️ ICARUS Dashboard - React Frontend

The ICARUS Dashboard is a React-based web interface that provides real-time visibility and control over autonomous coding jobs. It offers live telemetry, log streaming, job management, and the approval interface for code review.

## Table of Contents

- [Overview](#overview)
- [Pages](#pages)
- [Components](#components)
- [WebSocket Integration](#websocket-integration)
- [Development Setup](#development-setup)
- [Build Process](#build-process)
- [Troubleshooting](#troubleshooting)

## Overview

### Technology Stack

- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **React Router**: Client-side routing
- **Recharts**: Telemetry visualization
- **WebSocket**: Real-time updates

### Features

- ✅ **Real-Time Telemetry**: Live CPU/RAM usage charts
- 📊 **Job Management**: Create, monitor, and control jobs
- 📜 **Live Logs**: WebSocket streaming of agent output
- 🔍 **Code Review**: Diff viewer and audit report display
- ⚡ **Responsive Design**: Works on desktop and tablet

### Project Structure

```
dashboard/
├── src/
│   ├── pages/
│   │   ├── JobList.jsx          # Job listing and creation
│   │   ├── JobDetail.jsx        # Live job monitoring
│   │   └── Review.jsx           # Approval interface
│   ├── components/
│   │   ├── Telemetry.jsx        # CPU/RAM charts
│   │   ├── Terminal.jsx         # Live log display
│   │   └── DiffViewer.jsx       # Code diff display
│   ├── App.jsx                  # Main app and routing
│   └── index.css                # Global styles
├── public/                      # Static assets
├── index.html                   # Entry HTML
├── vite.config.js              # Vite configuration
└── package.json                 # Dependencies
```

## Pages

### JobList (`/`)

**Purpose**: Main landing page for job management

**Features:**
- List all jobs with status filtering
- Create new jobs via form
- Quick status indicators (pending, building, checking, etc.)
- Click job to view details

**API Calls:**
```javascript
// Fetch all jobs
const response = await fetch('http://localhost:8000/jobs?limit=50');
const jobs = await response.json();

// Create new job
const response = await fetch('http://localhost:8000/jobs/spawn', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    task: "Create user authentication",
    project_path: "/workspace"
  })
});
```

---

### JobDetail (`/jobs/:jobId`)

**Purpose**: Real-time monitoring of active job

**Features:**
- Live status updates via WebSocket
- CPU/RAM telemetry charts (auto-refreshing)
- Live terminal output stream
- Current tool display
- Job metadata (created, duration, etc.)

**API Calls:**
```javascript
// Get job status
const response = await fetch(`http://localhost:8000/jobs/${jobId}/status`);
const status = await response.json();

// Get telemetry (polled every 2s)
const response = await fetch(`http://localhost:8000/jobs/${jobId}/telemetry`);
const telemetry = await response.json();

// WebSocket stream
const ws = new WebSocket(`ws://localhost:8000/jobs/${jobId}/stream`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateJobStatus(data);
};
```

---

### Review (`/jobs/:jobId/review`)

**Purpose**: Human approval interface

**Features:**
- Audit report display (static analysis, security scan results)
- Code diff viewer (files changed highlighting)
- Approve/Reject buttons
- Comment field for decision rationale

**API Calls:**
```javascript
// Get audit report
const response = await fetch(`http://localhost:8000/jobs/${jobId}/audit`);
const audit = await response.json();

// Approve or reject
const response = await fetch(`http://localhost:8000/jobs/${jobId}/approve`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    approved: true,
    comment: "Looks good!"
  })
});
```

## Components

### Telemetry Charts

**File**: `src/components/Telemetry.jsx`

**Purpose**: Display real-time CPU and RAM usage

**Usage:**
```jsx
import Telemetry from '../components/Telemetry';

function JobDetail() {
  const [telemetry, setTelemetry] = useState({ cpu: 0, ram: 0 });
  
  useEffect(() => {
    const interval = setInterval(async () => {
      const res = await fetch(`/jobs/${jobId}/telemetry`);
      const data = await res.json();
      setTelemetry({
        cpu: data.cpu_usage,
        ram: data.ram_usage_mb
      });
    }, 2000);
    
    return () => clearInterval(interval);
  }, [jobId]);
  
  return <Telemetry cpu={telemetry.cpu} ram={telemetry.ram} />;
}
```

**Props:**
- `cpu` (number): CPU usage percentage (0-100)
- `ram` (number): RAM usage in MB

---

### Terminal Component

**File**: `src/components/Terminal.jsx`

**Purpose**: Display live log stream from agents

**Usage:**
```jsx
import Terminal from '../components/Terminal';

function JobDetail() {
  const [logs, setLogs] = useState([]);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/jobs/${jobId}/stream`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLogs(prev => [...prev, data.message || data.status]);
    };
    
    return () => ws.close();
  }, [jobId]);
  
  return <Terminal logs={logs} />;
}
```

**Props:**
- `logs` (Array<string>): Log lines to display

---

### DiffViewer Component

**File**: `src/components/DiffViewer.jsx`

**Purpose**: Display code changes for review

**Usage:**
```jsx
import DiffViewer from '../components/DiffViewer';

function Review() {
  const diffs = [
    { file: 'auth.py', type: 'added', lines: '+def login():\n+    pass' },
    { file: 'test_auth.py', type: 'added', lines: '+def test_login():\n+    assert True' }
  ];
  
  return <DiffViewer diffs={diffs} />;
}
```

**Props:**
- `diffs` (Array): List of file changes

## WebSocket Integration

### Connecting to Job Stream

```jsx
import { useEffect, useState } from 'react';

function useJobStream(jobId) {
  const [status, setStatus] = useState(null);
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/jobs/${jobId}/stream`);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'status_update') {
        setStatus(data.status);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
      
      // Reconnect after 5 seconds
      setTimeout(() => {
        // Re-trigger useEffect by updating state
      }, 5000);
    };
    
    return () => {
      ws.close();
    };
  }, [jobId]);
  
  return { status, connected };
}

// Usage in component
function JobDetail({ jobId }) {
  const { status, connected } = useJobStream(jobId);
  
  return (
    <div>
      <h2>Job Status: {status}</h2>
      <div>{connected ? '🟢 Connected' : '🔴 Disconnected'}</div>
    </div>
  );
}
```

### Reconnection Strategy

```jsx
function useWebSocketWithReconnect(url, options = {}) {
  const {
    maxRetries = 5,
    retryDelay = 5000,
    onMessage,
    onConnect,
    onDisconnect
  } = options;
  
  const [retryCount, setRetryCount] = useState(0);
  
  useEffect(() => {
    if (retryCount >= maxRetries) {
      console.error('Max reconnection attempts reached');
      return;
    }
    
    const ws = new WebSocket(url);
    
    ws.onopen = () => {
      setRetryCount(0);
      onConnect?.();
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage?.(data);
    };
    
    ws.onclose = () => {
      onDisconnect?.();
      
      // Exponential backoff
      const delay = retryDelay * Math.pow(2, retryCount);
      setTimeout(() => {
        setRetryCount(prev => prev + 1);
      }, delay);
    };
    
    return () => ws.close();
  }, [url, retryCount]);
}
```

## Development Setup

### Prerequisites

```bash
node -v  # Should be 20.x or higher
npm -v   # Should be 10.x or higher
```

### Installation

```bash
cd icarus/dashboard

# Install dependencies
npm install

# Start development server
npm run dev
```

The dashboard will be available at [http://localhost:5173](http://localhost:5173)

### Environment Variables

Create `.env` file in `dashboard/`:

```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

**Usage in code:**
```javascript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

## Build Process

### Production Build

```bash
cd icarus/dashboard

# Build for production
npm run build

# Output: dist/ directory
```

### Preview Production Build

```bash
npm run preview
# Serves dist/ at http://localhost:4173
```

### Docker Deployment

```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production image
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Build and run:**
```bash
docker build -t icarus-dashboard:latest -f dashboard/Dockerfile dashboard/
docker run -p 5173:80 icarus-dashboard:latest
```

## Troubleshooting

### CORS Errors

**Problem:** "CORS policy: No 'Access-Control-Allow-Origin' header"

**Solutions:**
1. **Verify orchestrator CORS middleware** in `orchestrator/main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:5173"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **Check dashboard URL** matches CORS allowed origins

3. **For production**, update allowed origins:
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

---

### WebSocket Disconnections

**Problem:** WebSocket keeps disconnecting every few seconds

**Solutions:**
1. **Check orchestrator is running**:
   ```bash
   curl http://localhost:8000/
   ```

2. **Verify WebSocket endpoint** exists:
   ```bash
   # Should not error
   curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     http://localhost:8000/jobs/test-id/stream
   ```

3. **Implement reconnection logic** (see WebSocket Integration section)

4. **Check browser console** for specific error codes:
   - `1000`: Normal closure
   - `1006`: Abnormal closure (network issue)
   - `1011`: Server error

---

### API Connection Failures

**Problem:** "Failed to fetch" or "Network Error"

**Solutions:**
```bash
# 1. Verify orchestrator is accessible
curl http://localhost:8000/jobs

# 2. Check firewall isn't blocking port 8000
# Windows
netsh advfirewall firewall add rule name="ICARUS API" dir=in action=allow protocol=TCP localport=8000

# 3. Verify correct API URL in dashboard
console.log(import.meta.env.VITE_API_URL)

# 4. Test from browser console
fetch('http://localhost:8000/jobs').then(r => r.json()).then(console.log)
```

---

### Build Failures

**Problem:** `npm run build` fails

**Solutions:**
```bash
# 1. Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# 2. Check Node.js version
node -v  # Should be 20+

# 3. Clear Vite cache
rm -rf node_modules/.vite

# 4. Check for TypeScript errors
npm run build -- --mode development
```

---

### Hot Reload Not Working

**Problem:** Changes not reflected during `npm run dev`

**Solutions:**
1. **Restart dev server**: Ctrl+C and `npm run dev`

2. **Check Vite config** for correct paths:
   ```javascript
   // vite.config.js
   export default {
     root: '.',
     build: {
       outDir: 'dist'
     }
   }
   ```

3. **Clear browser cache**: Ctrl+Shift+R

4. **Check file watchers** (Linux):
   ```bash
   echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   ```

---

For related documentation, see:
- [Orchestrator API](../orchestrator/README.md)
- [Main README](../../README.md)
