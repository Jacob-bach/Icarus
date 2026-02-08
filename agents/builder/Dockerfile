FROM python:3.14.3-slim-bookworm

# Create non-root user
RUN groupadd -r agentuser && useradd -r -g agentuser agentuser

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (for JavaScript projects)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /agent

# Copy requirements first for better cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .

# Create workspace directory with proper permissions
RUN mkdir -p /workspace && chown -R agentuser:agentuser /agent /workspace

# Switch to non-root user
USER agentuser

# Run agent
CMD ["python", "agent.py"]
