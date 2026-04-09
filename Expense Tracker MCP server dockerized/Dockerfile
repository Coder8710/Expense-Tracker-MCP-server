# Use the official Python 3.13 slim image
FROM python:3.13-slim

# Copy the officially compiled uv binary to use it for fast installations
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory inside the container
WORKDIR /app

# Ensure Python output is sent straight to terminal (stdio)
ENV PYTHONUNBUFFERED=1

# First, copy the dependency files to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Sync dependencies using uv (creates a virtual environment in /app/.venv)
RUN uv sync --frozen --no-dev

# Copy the remaining project files (main.py, categories.json, expenses.db)
COPY . .

# FastMCP uses the Standard Input / Output (stdio) for communication.
# Therefore, we just start the server and let it handle stdin/stdout.
ENTRYPOINT ["uv", "run", "main.py"]
