FROM python:3.14.3-slim-bookworm

# Create non-root user
RUN groupadd -r agentuser && useradd -r -g agentuser agentuser

# Install static analysis and security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /agent

# Copy requirements first for better cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .

# Create workspace directory with proper permissions (read-only mount)
RUN mkdir -p /workspace && chown -R agentuser:agentuser /agent /workspace

# Switch to non-root user
USER agentuser

# Run agent
CMD ["python", "agent.py"]
