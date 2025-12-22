FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PATH="/app/.venv/bin:$PATH"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy project files
COPY pyproject.toml uv.lock alembic.ini /app/
COPY ./app ./app
COPY ./tests ./app/tests

# Install dependencies using uv
RUN uv sync --frozen --no-cache --no-dev

EXPOSE 8000

# Run using uv's virtual environment
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
