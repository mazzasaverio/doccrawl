# Use Python 3.11 slim base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Playwright browser
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install Python dependencies using uv
RUN uv pip install --system -r <(uv pip compile pyproject.toml)

# Install Playwright browser
RUN python -m playwright install chromium

# Create directory for logs
RUN mkdir -p logs

CMD ["python", "-m", "src.main"]