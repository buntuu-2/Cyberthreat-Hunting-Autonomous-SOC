# AI Cyberthreat Hunting & Autonomous SOC Docker Container
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including ufw, curl, iptables for simulation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ufw \
    curl \
    iptables \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
ENV FIREWALL_MODE=simulation

EXPOSE 8000

# Run FastAPI Web Command Center
CMD ["sh", "-c", "python main.py --serve --host 0.0.0.0 --port ${PORT:-8000}"]
