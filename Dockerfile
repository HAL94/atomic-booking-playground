# === Base (Stage 0) ===
FROM python:3.13-alpine3.21 AS base

# operate in "unbuffered" mode for stdout and stderr
ENV PYTHONUNBUFFERED=1
#  install uv by copying the binary from the official distroless
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTE=1
ENV UV_LINK_MODE=copy

WORKDIR /src

# === Dependencies (Stage 1) ===
FROM base as deps

WORKDIR /src

COPY ./pyproject.toml ./uv.lock ./.python-version ./

# INSTALL DEPS
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ENV PATH="/src/.venv/bin:$PATH"

# === Runner (Stage 2) === 
FROM deps AS runner

RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 appuser

WORKDIR /src

# 1. Copy the virtual environment from the deps stage
COPY --from=deps --chown=appuser:appuser /src/.venv /src/.venv
# 2. Copy your application source code
COPY --chown=appuser:appuser ./ ./

USER appuser

CMD ["uv", "run", "-m", "app"]

FROM deps AS test
RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 appuser

RUN chown -R appuser:appuser /src/.venv
USER appuser

WORKDIR /src
ENV UV_PROJECT_ENVIRONMENT=/src/.venv

RUN uv sync --frozen --no-editable

COPY --chown=appuser:appuser ./tests ./tests
COPY --chown=appuser:appuser ./app ./app
COPY --chown=appuser:appuser ./migrations ./migrations 
COPY --chown=appuser:appuser ./alembic.ini ./alembic.ini
COPY --chown=appuser:appuser ./pyproject.toml ./pyproject.toml

CMD ["pytest", "-v"]
