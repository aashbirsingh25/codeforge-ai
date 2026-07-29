FROM python:3.11-slim

WORKDIR /app

# Install standard system updates and dependency build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY app/ ./app/

EXPOSE 8000

# Set workspace directory inside container
ENV WORKSPACE_DIR=/app/workspace
RUN mkdir -p /app/workspace

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

