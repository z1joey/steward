# T0-02 · T0-01: backend image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
ENV PATH="/srv/.venv/bin:$PATH"
EXPOSE 8000
