FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ENV PATH="/sage/app/.venv/bin:$PATH"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/sage

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
