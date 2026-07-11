FROM python:3.11-slim

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency definitions first to optimize Docker build caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-install-project

# Copy remaining source code
COPY . .

EXPOSE 8000

# Run FastAPI app within the uv environment using the modern FastAPI CLI
CMD ["uv", "run", "fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
