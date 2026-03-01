FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ENV PATH="/sage/app/.venv/bin:$PATH"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/sage

# install psycopg2 build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /sage

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache --no-dev

COPY ./app ./app
COPY alembic.ini ./
COPY ./alembic ./alembic
COPY ./tools ./tools
COPY ./tests ./tests


EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
