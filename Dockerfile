FROM python:3.13-slim

# Install psycopg2 build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (pinned) by copying the binary from the official distroless Docker image
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /sage

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/sage \
    PATH="/sage/.venv/bin:$PATH"

# install dependencies only (cached separately from app code)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# copy source and install the project itself
COPY ./app ./app
COPY alembic.ini ./
COPY ./alembic ./alembic
COPY ./tools ./tools
COPY ./tests ./tests
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]