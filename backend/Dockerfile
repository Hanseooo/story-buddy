# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation and use copy mode for caching
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

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

# Pre-download spaCy model and Qwen moderation model into the image cache
RUN python -m spacy download en_core_web_sm
RUN python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; AutoTokenizer.from_pretrained('Qwen/Qwen3-Guard-Gen-0.6B'); AutoModelForCausalLM.from_pretrained('Qwen/Qwen3-Guard-Gen-0.6B')"

# Default to running the API (Northflank will override this for the worker)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
