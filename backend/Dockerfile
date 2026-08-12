# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation and use copy mode for caching
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# The lockfile's one non-PyPI fetch is the 12 MB en_core_web_sm wheel, served by github.com
# releases (see pyproject.toml). GitHub refused the HTTP/2 stream on 2026-08-12 and failed the
# worker build; the API service built fine off the same commit, so it was a blip, not a block.
# uv's default 3 retries all burned inside 6s. Widen the window — the cache mount is per-service,
# so every cold build is exposed again.
# ponytail: retries, not a vendored wheel — vendor it if a real outage ever costs a deploy.
ENV UV_HTTP_RETRIES=10

# Install dependencies using the lockfile (cache effectively)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Add the rest of the project source code
ADD . /app

# Sync the project itself (without dev dependencies)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place the uv-created virtual environment at the front of the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Default to running the API (Northflank will override this for the worker)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
