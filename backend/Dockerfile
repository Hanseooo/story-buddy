# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation and use copy mode for caching
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Kept for the PyPI fetches, which have never been the problem. The one that was — the
# en_core_web_sm wheel from github.com releases — is now vendored (pyproject.toml), so no build
# depends on that CDN any more. Raising this 3 -> 10 did not save the 2026-08-12 20:51 build:
# it failed "after 10 retries" having spent 814s inside them.
ENV UV_HTTP_RETRIES=10

# Install dependencies using the lockfile (cache effectively).
# `vendor` is mounted because the lockfile now resolves en_core_web_sm from a path inside it;
# without this the layer fails on a missing file rather than a refused stream.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=vendor,target=vendor \
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
