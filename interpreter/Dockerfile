FROM python:3.13.2-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy pyproject.toml
COPY interpreter/pyproject.toml interpreter/uv.lock .

# Install dependencies 
RUN uv sync --frozen

# Copy application code
COPY interpreter/main.py .
COPY interpreter/schema.py .
COPY interpreter/utils.py .
COPY interpreter/config.py .

# Expose port
EXPOSE 8001

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]