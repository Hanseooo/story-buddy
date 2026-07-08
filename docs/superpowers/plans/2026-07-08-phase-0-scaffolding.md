# Phase 0 Scaffolding & Walking Skeleton — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One hardcoded/typed story flows end-to-end through real infrastructure (FastAPI → RQ worker → LangGraph → real Gemini text call → real Nano Banana image call → Supabase Storage → Realtime → Next.js slideshow) and produces one real slideshow page. Nothing is smart yet — every pipeline node except `analyze` and `generate_scene` is a pure pass-through stub.

**Architecture:** Three deployed services (ADR-005, ADR-009): Next.js/Vercel frontend, FastAPI web + RQ worker on Railway, Redis broker on Railway, Supabase for Postgres/Auth-stub/Storage/Realtime. `POST /storybooks` writes a `jobs` row and returns `job_id` immediately (never runs the pipeline inline); the RQ worker picks up the job, runs a 6-node LangGraph stub graph checkpointed to Supabase Postgres, and updates the job row on completion/failure. The frontend subscribes to the job row via Supabase Realtime and redirects to a slideshow once `status = complete`.

**Tech Stack:** Python 3.12 + `uv` (backend), FastAPI, RQ + Redis, LangGraph + `langgraph-checkpoint-postgres`, `google-genai` (Gemini text + Nano Banana image), Supabase (Postgres/Storage/Realtime, Python + JS clients), Sentry, LangSmith. Next.js (App Router) + TypeScript + Tailwind + `pnpm`, `@supabase/supabase-js`, `@sentry/nextjs`, `vitest` + Testing Library. pytest for backend.

## Global Constraints

- **Python 3.12, managed by `uv`** (`backend/pyproject.toml` + `uv.lock` committed). No Poetry, no bare pip/venv.
- **Node via `pnpm`** (`frontend/package.json` + `pnpm-lock.yaml` committed). No npm/yarn lockfiles.
- **Observability = LangSmith** (ADR-014, appended in Task 1) — tracing on from the first commit via `LANGCHAIN_TRACING_V2=true` env var, zero extra SDK code in pipeline nodes (MASTER_SPEC §8).
- **No Docker.** Local dev talks directly to the real hosted free-tier Supabase project and Railway Redis instance provisioned in this plan — not a local emulation stack.
- **RQ worker:** `rq.worker.SimpleWorker` on Windows (`sys.platform == "win32"`, no `os.fork`), default fork-based `Worker` on Railway (Linux) — one script (`worker/run_worker.py`) picks the right class automatically.
- **RLS on every table from day one** (CLAUDE.md §5), even before real auth exists (Phase 2). The Phase-0 `jobs` table uses a capability-link policy: anon `SELECT` is allowed unconditionally, but the *only* client-side query pattern is `.eq('id', job_id)` against an unguessable UUID the client already holds from the `POST /storybooks` response — nobody can list or enumerate jobs. All backend writes use the service-role key (bypasses RLS). Real per-account RLS lands in the Phase 2 `auth-and-profiles` spec.
- **Contract-first (CLAUDE.md §2):** the one real Gemini structured-output call (`analyze` node) validates through a Pydantic model, always. `backend/contracts/job_state.py` is a **deliberately minimal Phase-0 subset** — the full frozen Story Memory schema is written in the Phase 1 `story-memory-contract` spec (MASTER_SPEC §7). Do not extend this file with Phase-1 fields.
- **Tier A tests only in this plan** (CLAUDE.md §3): every test mocks Gemini and Nano Banana. Never assert on generated image/text quality — only on structural/routing/contract behavior.
- **Signed URLs only, no public buckets** (CLAUDE.md §5) — the `storybook-images` Storage bucket is created private; the frontend always reads images through a signed URL, never a public path.
- **One pipeline module = one file in `backend/pipeline/`** (MASTER_SPEC §1, §6) — nodes stay pure state-transform functions; job-row persistence side effects live in `worker/run_job.py`, not inside pipeline nodes.
- **Flagged, not guessed:** the exact Nano Banana model string (`gemini-2.5-flash-image` used below) and the exact shape of the image `Part.inline_data` field are best-effort against current `google-genai` SDK knowledge — confirm against the SDK version actually installed at Task 7 implementation time before trusting the parsing code verbatim.

---

## File Structure

```
story-buddy/
  .gitignore
  docs/product/ADRs.md          # + ADR-014 (Task 1)
  supabase/migrations/0001_jobs_table.sql
  backend/
    pyproject.toml              # uv, Python 3.12
    .env.example
    app/
      config.py                 # pydantic-settings
      db.py                     # supabase client factory
      queue.py                  # RQ queue factory
      main.py                   # FastAPI: POST /storybooks, GET /health
    contracts/
      job_state.py              # JobState TypedDict + SceneCaption (Phase-0 subset)
    pipeline/
      graph.py                  # build_graph(): wires the 6 stub nodes
      analyze.py                # REAL Gemini structured-output call
      segment.py                # stub
      char_bible.py             # stub
      generate_scene.py         # REAL Nano Banana call + Storage upload
      consistency_check.py      # stub
      compose.py                # stub
    worker/
      run_job.py                # job function: loads text, runs graph, writes job row
      run_worker.py              # Windows/Linux-aware RQ worker entrypoint
    Procfile
    tests/
      conftest.py
      test_contracts.py
      test_graph_stub.py
      test_analyze_node.py
      test_generate_scene_node.py
      test_main.py
      test_run_job.py
  frontend/
    package.json                # pnpm
    .env.local.example
    lib/supabaseClient.ts
    sentry.client.config.ts
    sentry.server.config.ts
    vitest.config.ts
    app/
      write/page.tsx            # story textarea -> POST /storybooks
      write/page.test.tsx
      process/[jobId]/page.tsx  # Realtime subscription -> redirect on complete
      process/[jobId]/page.test.tsx
      book/[jobId]/page.tsx     # signed image + caption
      book/[jobId]/page.test.tsx
```

---

### Task 1: ADR-014, git init, repo skeleton

**Files:**
- Modify: `docs/product/ADRs.md` (append ADR-014)
- Create: `.gitignore`

**Interfaces:**
- Produces: an initialized git repo at the workspace root that every later task commits into.

- [ ] **Step 1: Initialize git**

```bash
git init
git status
```
Expected: `Initialized empty Git repository...`, working tree shows the existing `CLAUDE.md`, `README.md`, `docs/` as untracked.

- [ ] **Step 2: Append ADR-014 to `docs/product/ADRs.md`**

Add this block at the end of the file, after ADR-013:

```markdown

---

## ADR-014 — Observability provider: LangSmith

**Status:** Accepted

**Context:** MASTER_SPEC §8 flagged the observability provider (LangSmith vs Langfuse) as an
open Phase 0 decision — ROADMAP requires tracing wired from the first commit, and LangGraph
needs a trace destination for per-scene generation time, regen counts, and cost (PRD §16).

**Decision:** Use **LangSmith** for pipeline tracing in the MVP.

**Consequences:** Native LangGraph integration — tracing turns on via environment variables
(`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`) with no additional SDK code
in the pipeline nodes. Free tier is usage-limited; revisit if the study's trace volume exceeds it.

**Alternatives:** Langfuse — open-source, self-hostable, no vendor lock-in, but requires standing
up/administering a second project and more manual instrumentation. Rejected for MVP: solo build,
LangSmith's zero-code LangGraph wiring is the faster and lower-ops path to Day-1 instrumentation.
```

- [ ] **Step 3: Create `.gitignore`**

```
# Python
.venv/
__pycache__/
*.pyc
backend/.env

# Node
node_modules/
frontend/.next/
frontend/.env.local

# General
.DS_Store
*.log
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md README.md docs .gitignore
git commit -m "chore: init repo, record ADR-014 (LangSmith observability)"
```

---

### Task 2: Supabase provisioning — `jobs` table, RLS, Realtime, Storage bucket

**Files:**
- Create: `supabase/migrations/0001_jobs_table.sql`

**Interfaces:**
- Produces: a `jobs` table (`id, status, current_stage, input_text, caption, image_path, error, created_at, updated_at`) and a private `storybook-images` Storage bucket that every later backend task reads/writes.

- [ ] **Step 1: Manual — create the Supabase project**

Sign in at supabase.com, create a new project, region **Southeast Asia (Singapore)** (matches ADR-009). From Project Settings note down and save locally (not committed):
- Project URL → `SUPABASE_URL`
- `anon` public key → `SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `service_role` secret key → `SUPABASE_SERVICE_ROLE_KEY`
- Database → Connection string (URI, "Session pooler") → `SUPABASE_DB_URL`

- [ ] **Step 2: Write the migration**

```sql
-- supabase/migrations/0001_jobs_table.sql
create table if not exists jobs (
  id uuid primary key,
  status text not null default 'queued' check (status in ('queued','running','complete','failed')),
  current_stage text,
  input_text text not null,
  caption text,
  image_path text,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table jobs enable row level security;

-- Capability-link read policy: the UUID itself is the capability. Anon may only ever
-- query with .eq('id', job_id) client-side; there is no listing/enumeration policy.
create policy "anon can read jobs by id"
  on jobs for select
  to anon
  using (true);

alter publication supabase_realtime add table jobs;

insert into storage.buckets (id, name, public)
values ('storybook-images', 'storybook-images', false)
on conflict (id) do nothing;
```

- [ ] **Step 3: Manual — run the migration**

Paste the contents of `supabase/migrations/0001_jobs_table.sql` into the Supabase dashboard's SQL Editor and run it.

- [ ] **Step 4: Verify**

In the SQL Editor, run:
```sql
select * from jobs limit 1;
select id, public from storage.buckets;
```
Expected: first query returns an empty result with no error (table exists); second query shows a row `storybook-images | false`.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0001_jobs_table.sql
git commit -m "feat: provision jobs table with RLS, realtime, and storage bucket"
```

---

### Task 3: Backend project scaffold (`uv`, config, Supabase client)

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Interfaces:**
- Produces: `app.config.settings` (a `Settings` instance) and `app.db.get_supabase_client() -> supabase.Client`, both imported by every later backend task.

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "storybuddy-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "langgraph>=0.2.45",
    "langgraph-checkpoint-postgres>=2.0.1",
    "psycopg[binary]>=3.2",
    "google-genai>=0.3.0",
    "supabase>=2.9.1",
    "redis>=5.2",
    "rq>=2.0",
    "sentry-sdk[fastapi]>=2.17",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-mock>=3.14",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Create `backend/.python-version`**

```
3.12
```

- [ ] **Step 3: Install and verify**

```bash
cd backend
uv sync
uv run python -c "import fastapi, langgraph, supabase, rq; print('ok')"
```
Expected: `.venv/` and `uv.lock` created, prints `ok`.

- [ ] **Step 4: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    supabase_db_url: str
    redis_url: str
    gemini_api_key: str
    sentry_dsn_backend: str | None = None
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
```

- [ ] **Step 5: Create `backend/app/db.py`**

```python
from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache
def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
```

- [ ] **Step 6: Create `backend/app/__init__.py`** (empty file)

- [ ] **Step 7: Create `backend/tests/__init__.py`** (empty file)

- [ ] **Step 8: Create `backend/tests/conftest.py`**

```python
import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
```

- [ ] **Step 9: Create `backend/.env.example`**

```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=
REDIS_URL=
GEMINI_API_KEY=
SENTRY_DSN_BACKEND=
FRONTEND_ORIGIN=http://localhost:3000
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=storybuddy-dev
```

- [ ] **Step 10: Run baseline test**

```bash
uv run pytest -v
```
Expected: `0 tests collected` (or `no tests ran`), no import errors.

- [ ] **Step 11: Commit**

```bash
git add backend/pyproject.toml backend/.python-version backend/.env.example backend/app backend/tests backend/uv.lock
git commit -m "feat: scaffold backend project with uv, settings, and supabase client"
```

---

### Task 4: Contracts — Phase-0 `JobState` + `SceneCaption`

**Files:**
- Create: `backend/contracts/__init__.py`
- Create: `backend/contracts/job_state.py`
- Test: `backend/tests/test_contracts.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `contracts.job_state.JobState` (TypedDict: `job_id, input_text, caption, image_path, stage`) and `contracts.job_state.SceneCaption` (Pydantic model: `caption: str`) — used by every pipeline node from Task 5 onward.

- [ ] **Step 1: Create `backend/contracts/__init__.py`** (empty file)

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_contracts.py
import pytest
from pydantic import ValidationError

from contracts.job_state import SceneCaption


def test_scene_caption_accepts_valid_shape():
    result = SceneCaption.model_validate({"caption": "A dog runs through a sunny field."})
    assert result.caption == "A dog runs through a sunny field."


def test_scene_caption_rejects_missing_field():
    with pytest.raises(ValidationError):
        SceneCaption.model_validate({})
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_contracts.py -v
```
Expected: `ModuleNotFoundError: No module named 'contracts.job_state'`

- [ ] **Step 4: Create `backend/contracts/job_state.py`**

```python
"""Phase 0 provisional subset of the Story Memory contract (MASTER_SPEC §3).
Full field-level schema is frozen in the Phase 1 `story-memory-contract` spec — do not extend
this file with Phase 1 fields; add them there instead.
"""
from typing import Optional, TypedDict

from pydantic import BaseModel


class JobState(TypedDict):
    job_id: str
    input_text: str
    caption: Optional[str]
    image_path: Optional[str]
    stage: str


class SceneCaption(BaseModel):
    caption: str
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/test_contracts.py -v
```
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/contracts backend/tests/test_contracts.py
git commit -m "feat: add Phase-0 JobState and SceneCaption contract"
```

---

### Task 5: LangGraph stub graph — 6 pass-through nodes + routing

**Files:**
- Create: `backend/pipeline/__init__.py`
- Create: `backend/pipeline/analyze.py`
- Create: `backend/pipeline/segment.py`
- Create: `backend/pipeline/char_bible.py`
- Create: `backend/pipeline/generate_scene.py`
- Create: `backend/pipeline/consistency_check.py`
- Create: `backend/pipeline/compose.py`
- Create: `backend/pipeline/graph.py`
- Test: `backend/tests/test_graph_stub.py`

**Interfaces:**
- Consumes: `contracts.job_state.JobState` (Task 4).
- Produces: `pipeline.graph.build_graph(checkpointer=None)` — used by Task 7's integration test and Task 9's worker. Each stub node is a plain `(JobState) -> JobState` function, all named exactly for their file (`analyze`, `segment`, `char_bible`, `generate_scene`, `consistency_check`, `compose`).

- [ ] **Step 1: Create `backend/pipeline/__init__.py`** (empty file)

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_graph_stub.py
from pipeline.graph import build_graph


def test_stub_graph_runs_all_nodes_in_order():
    app_graph = build_graph()
    initial_state = {
        "job_id": "test-job",
        "input_text": "A dog runs in a field.",
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }
    result = app_graph.invoke(initial_state, config={"configurable": {"thread_id": "test-job"}})

    assert result["stage"] == "compose"
    assert result["caption"] is None
    assert result["image_path"] is None
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_graph_stub.py -v
```
Expected: `ModuleNotFoundError: No module named 'pipeline.graph'`

- [ ] **Step 4: Create the six stub node files**

```python
# backend/pipeline/analyze.py
from contracts.job_state import JobState


def analyze(state: JobState) -> JobState:
    state["stage"] = "analyze"
    return state
```

```python
# backend/pipeline/segment.py
from contracts.job_state import JobState


def segment(state: JobState) -> JobState:
    state["stage"] = "segment"
    return state
```

```python
# backend/pipeline/char_bible.py
from contracts.job_state import JobState


def char_bible(state: JobState) -> JobState:
    state["stage"] = "char_bible"
    return state
```

```python
# backend/pipeline/generate_scene.py
from contracts.job_state import JobState


def generate_scene(state: JobState) -> JobState:
    state["stage"] = "generate_scene"
    return state
```

```python
# backend/pipeline/consistency_check.py
from contracts.job_state import JobState


def consistency_check(state: JobState) -> JobState:
    state["stage"] = "consistency_check"
    return state
```

```python
# backend/pipeline/compose.py
from contracts.job_state import JobState


def compose(state: JobState) -> JobState:
    state["stage"] = "compose"
    return state
```

- [ ] **Step 5: Create `backend/pipeline/graph.py`**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from contracts.job_state import JobState
from pipeline.analyze import analyze
from pipeline.segment import segment
from pipeline.char_bible import char_bible
from pipeline.generate_scene import generate_scene
from pipeline.consistency_check import consistency_check
from pipeline.compose import compose


def build_graph(checkpointer=None):
    graph = StateGraph(JobState)
    graph.add_node("analyze", analyze)
    graph.add_node("segment", segment)
    graph.add_node("char_bible", char_bible)
    graph.add_node("generate_scene", generate_scene)
    graph.add_node("consistency_check", consistency_check)
    graph.add_node("compose", compose)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "segment")
    graph.add_edge("segment", "char_bible")
    graph.add_edge("char_bible", "generate_scene")
    graph.add_edge("generate_scene", "consistency_check")
    graph.add_edge("consistency_check", "compose")
    graph.add_edge("compose", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
```

- [ ] **Step 6: Run test to verify it passes**

```bash
uv run pytest tests/test_graph_stub.py -v
```
Expected: `1 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline backend/tests/test_graph_stub.py
git commit -m "feat: wire 6-node LangGraph stub graph with in-memory checkpointer"
```

---

### Task 6: `analyze` node — real Gemini structured-output call

**Files:**
- Modify: `backend/pipeline/analyze.py`
- Test: `backend/tests/test_analyze_node.py`

**Interfaces:**
- Consumes: `contracts.job_state.SceneCaption` (Task 4), `app.config.settings` (Task 3).
- Produces: `pipeline.analyze.call_gemini_for_caption(text: str) -> str` — a standalone, mockable function the `analyze` node calls. Sets `state["caption"]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_analyze_node.py
from unittest.mock import MagicMock, patch

from pipeline.analyze import analyze, call_gemini_for_caption


def test_call_gemini_for_caption_validates_structured_response():
    fake_response = MagicMock()
    fake_response.text = '{"caption": "A dog runs through a sunny field."}'

    with patch("pipeline.analyze.genai.Client") as mock_client_cls:
        mock_client_cls.return_value.models.generate_content.return_value = fake_response
        caption = call_gemini_for_caption("A dog runs in a field.")

    assert caption == "A dog runs through a sunny field."


def test_call_gemini_for_caption_rejects_malformed_response():
    fake_response = MagicMock()
    fake_response.text = '{"wrong_field": "oops"}'

    with patch("pipeline.analyze.genai.Client") as mock_client_cls:
        mock_client_cls.return_value.models.generate_content.return_value = fake_response
        with pytest.raises(Exception):
            call_gemini_for_caption("A dog runs in a field.")


def test_analyze_node_sets_caption_and_stage():
    state = {
        "job_id": "t1",
        "input_text": "A dog runs in a field.",
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }
    with patch("pipeline.analyze.call_gemini_for_caption", return_value="stub caption"):
        result = analyze(state)
    assert result["caption"] == "stub caption"
    assert result["stage"] == "analyze"
```

Add `import pytest` at the top of the file alongside the existing imports.

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_analyze_node.py -v
```
Expected: `ImportError: cannot import name 'call_gemini_for_caption' from 'pipeline.analyze'`

- [ ] **Step 3: Replace `backend/pipeline/analyze.py`**

```python
from google import genai
from google.genai import types

from app.config import settings
from contracts.job_state import JobState, SceneCaption


def call_gemini_for_caption(text: str) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Write one short, kid-friendly caption (max 20 words) for this story: {text}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SceneCaption,
        ),
    )
    parsed = SceneCaption.model_validate_json(response.text)
    return parsed.caption


def analyze(state: JobState) -> JobState:
    state["caption"] = call_gemini_for_caption(state["input_text"])
    state["stage"] = "analyze"
    return state
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_analyze_node.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/analyze.py backend/tests/test_analyze_node.py
git commit -m "feat: analyze node makes a real Gemini structured-output call"
```

---

### Task 7: `generate_scene` node — real Nano Banana call + Storage upload

**Files:**
- Modify: `backend/pipeline/generate_scene.py`
- Modify: `backend/tests/test_graph_stub.py` (append integration test)
- Test: `backend/tests/test_generate_scene_node.py`

**Interfaces:**
- Consumes: `app.db.get_supabase_client` (Task 3), `app.config.settings` (Task 3).
- Produces: `pipeline.generate_scene.call_nano_banana_and_store(prompt: str, job_id: str) -> str` (returns the Storage object path, e.g. `"{job_id}/scene-1.png"`). Sets `state["image_path"]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_generate_scene_node.py
from unittest.mock import MagicMock, patch

from pipeline.generate_scene import generate_scene, call_nano_banana_and_store


def test_call_nano_banana_and_store_uploads_image_bytes():
    fake_part = MagicMock()
    fake_part.inline_data.data = b"fake-png-bytes"
    fake_response = MagicMock()
    fake_response.candidates = [MagicMock(content=MagicMock(parts=[fake_part]))]

    fake_supabase = MagicMock()

    with patch("pipeline.generate_scene.genai.Client") as mock_client_cls, \
         patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase):
        mock_client_cls.return_value.models.generate_content.return_value = fake_response
        path = call_nano_banana_and_store("a friendly dog", "job-123")

    assert path == "job-123/scene-1.png"
    fake_supabase.storage.from_.assert_called_with("storybook-images")
    fake_supabase.storage.from_.return_value.upload.assert_called_once()


def test_generate_scene_node_sets_image_path_and_stage():
    state = {
        "job_id": "job-123",
        "input_text": "x",
        "caption": "a friendly dog",
        "image_path": None,
        "stage": "analyze",
    }
    with patch("pipeline.generate_scene.call_nano_banana_and_store", return_value="job-123/scene-1.png"):
        result = generate_scene(state)
    assert result["image_path"] == "job-123/scene-1.png"
    assert result["stage"] == "generate_scene"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_generate_scene_node.py -v
```
Expected: `ImportError: cannot import name 'call_nano_banana_and_store' from 'pipeline.generate_scene'`

- [ ] **Step 3: Replace `backend/pipeline/generate_scene.py`**

```python
from google import genai

from app.config import settings
from app.db import get_supabase_client
from contracts.job_state import JobState

BUCKET = "storybook-images"


def call_nano_banana_and_store(prompt: str, job_id: str) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
    )
    # NOTE: parsing shape best-effort against google-genai SDK docs — verify against the
    # installed SDK version if this breaks (flagged in plan Global Constraints).
    image_bytes = response.candidates[0].content.parts[0].inline_data.data

    path = f"{job_id}/scene-1.png"
    supabase = get_supabase_client()
    supabase.storage.from_(BUCKET).upload(
        path, image_bytes, {"content-type": "image/png"}
    )
    return path


def generate_scene(state: JobState) -> JobState:
    prompt = state["caption"] or state["input_text"]
    state["image_path"] = call_nano_banana_and_store(prompt, state["job_id"])
    state["stage"] = "generate_scene"
    return state
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_generate_scene_node.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Append the full-graph integration test to `backend/tests/test_graph_stub.py`**

```python
def test_stub_graph_full_run_with_real_call_points_mocked(monkeypatch):
    monkeypatch.setattr("pipeline.analyze.call_gemini_for_caption", lambda text: "stub caption")
    monkeypatch.setattr(
        "pipeline.generate_scene.call_nano_banana_and_store",
        lambda prompt, job_id: "stub/path.png",
    )

    app_graph = build_graph()
    initial_state = {
        "job_id": "test-job-2",
        "input_text": "A dog runs in a field.",
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }
    result = app_graph.invoke(initial_state, config={"configurable": {"thread_id": "test-job-2"}})

    assert result["stage"] == "compose"
    assert result["caption"] == "stub caption"
    assert result["image_path"] == "stub/path.png"
```

- [ ] **Step 6: Run the full backend suite**

```bash
uv run pytest -v
```
Expected: all tests pass (`test_contracts`, `test_graph_stub` x2, `test_analyze_node` x3, `test_generate_scene_node` x2).

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline/generate_scene.py backend/tests/test_generate_scene_node.py backend/tests/test_graph_stub.py
git commit -m "feat: generate_scene node makes a real Nano Banana call and uploads to storage"
```

---

### Task 8: FastAPI `POST /storybooks` + RQ enqueue + Sentry + CORS

**Files:**
- Create: `backend/app/queue.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_main.py`

**Interfaces:**
- Consumes: `app.db.get_supabase_client`, `app.config.settings` (Task 3).
- Produces: `app.main.app` (FastAPI instance) with `POST /storybooks` (enqueues `worker.run_job.run_storybook_job` by string reference — Task 9 must define that exact dotted path) and `GET /health`.

- [ ] **Step 1: Create `backend/app/queue.py`**

```python
from functools import lru_cache

from redis import Redis
from rq import Queue

from app.config import settings


@lru_cache
def get_queue() -> Queue:
    return Queue("storybook", connection=Redis.from_url(settings.redis_url))
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_main.py
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_storybook_inserts_job_and_enqueues():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()

    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": "A dog runs in a field."})

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id

    fake_supabase.table.assert_called_with("jobs")
    insert_call_args = fake_supabase.table.return_value.insert.call_args[0][0]
    assert insert_call_args["input_text"] == "A dog runs in a field."
    assert insert_call_args["id"] == job_id

    fake_queue.enqueue.assert_called_once_with("worker.run_job.run_storybook_job", job_id)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_main.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 4: Create `backend/app/main.py`**

```python
import uuid

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.db import get_supabase_client
from app.queue import get_queue

if settings.sentry_dsn_backend:
    sentry_sdk.init(dsn=settings.sentry_dsn_backend, traces_sample_rate=0.1)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class CreateStorybookRequest(BaseModel):
    text: str


class CreateStorybookResponse(BaseModel):
    job_id: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/storybooks", response_model=CreateStorybookResponse)
def create_storybook(payload: CreateStorybookRequest) -> CreateStorybookResponse:
    job_id = str(uuid.uuid4())
    supabase = get_supabase_client()
    supabase.table("jobs").insert(
        {"id": job_id, "status": "queued", "current_stage": "queued", "input_text": payload.text}
    ).execute()

    queue = get_queue()
    queue.enqueue("worker.run_job.run_storybook_job", job_id)

    return CreateStorybookResponse(job_id=job_id)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/test_main.py -v
```
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/queue.py backend/app/main.py backend/tests/test_main.py
git commit -m "feat: POST /storybooks creates a job row and enqueues the worker"
```

---

### Task 9: RQ worker entrypoint + `run_job` (Postgres checkpointer wired)

**Files:**
- Create: `backend/worker/__init__.py`
- Create: `backend/worker/run_job.py`
- Create: `backend/worker/run_worker.py`
- Create: `backend/Procfile`
- Test: `backend/tests/test_run_job.py`

**Interfaces:**
- Consumes: `pipeline.graph.build_graph` (Task 5), `app.db.get_supabase_client`, `app.config.settings` (Task 3).
- Produces: `worker.run_job.run_storybook_job(job_id: str) -> None` — the exact dotted path `POST /storybooks` (Task 8) enqueues by string reference.

- [ ] **Step 1: Create `backend/worker/__init__.py`** (empty file)

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_run_job.py
from unittest.mock import MagicMock, patch

from worker.run_job import run_storybook_job


def test_run_storybook_job_updates_row_on_success():
    fake_supabase = MagicMock()
    select_chain = fake_supabase.table.return_value.select.return_value.eq.return_value.single.return_value
    select_chain.execute.return_value.data = {"input_text": "A dog runs in a field."}

    fake_checkpointer_cm = MagicMock()
    fake_checkpointer = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = fake_checkpointer

    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {
        "caption": "stub caption",
        "image_path": "job-1/scene-1.png",
        "stage": "compose",
    }

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    update_calls = fake_supabase.table.return_value.update.call_args_list
    final_update = update_calls[-1][0][0]
    assert final_update["status"] == "complete"
    assert final_update["caption"] == "stub caption"
    assert final_update["image_path"] == "job-1/scene-1.png"


def test_run_storybook_job_marks_failed_on_exception():
    fake_supabase = MagicMock()
    select_chain = fake_supabase.table.return_value.select.return_value.eq.return_value.single.return_value
    select_chain.execute.return_value.data = {"input_text": "A dog runs in a field."}

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", side_effect=RuntimeError("db down")):
        try:
            run_storybook_job("job-2")
            assert False, "expected RuntimeError to propagate"
        except RuntimeError:
            pass

    update_calls = fake_supabase.table.return_value.update.call_args_list
    failed_update = update_calls[-1][0][0]
    assert failed_update["status"] == "failed"
    assert "db down" in failed_update["error"]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_run_job.py -v
```
Expected: `ModuleNotFoundError: No module named 'worker.run_job'`

- [ ] **Step 4: Create `backend/worker/run_job.py`**

```python
from langgraph.checkpoint.postgres import PostgresSaver

from app.config import settings
from app.db import get_supabase_client
from pipeline.graph import build_graph


def run_storybook_job(job_id: str) -> None:
    supabase = get_supabase_client()
    row = supabase.table("jobs").select("input_text").eq("id", job_id).single().execute()
    input_text = row.data["input_text"]

    supabase.table("jobs").update({"status": "running"}).eq("id", job_id).execute()

    initial_state = {
        "job_id": job_id,
        "input_text": input_text,
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }

    try:
        with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
            checkpointer.setup()
            app_graph = build_graph(checkpointer=checkpointer)
            result = app_graph.invoke(
                initial_state, config={"configurable": {"thread_id": job_id}}
            )
    except Exception as exc:
        supabase.table("jobs").update(
            {"status": "failed", "error": str(exc)}
        ).eq("id", job_id).execute()
        raise

    supabase.table("jobs").update(
        {
            "status": "complete",
            "current_stage": "compose",
            "caption": result["caption"],
            "image_path": result["image_path"],
        }
    ).eq("id", job_id).execute()
```

> **ponytail:** job-row progress updates are coarse (`queued → running → complete/failed`), not per-node. Per-node granularity would push Supabase writes into every pipeline node, breaking "one module = one concern" (MASTER_SPEC §6). Add per-stage writes later only if the processing view genuinely needs finer feedback than "running".

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/test_run_job.py -v
```
Expected: `2 passed`

- [ ] **Step 6: Create `backend/worker/run_worker.py`**

```python
import sys

from redis import Redis
from rq import Queue, SimpleWorker, Worker

from app.config import settings


def main() -> None:
    connection = Redis.from_url(settings.redis_url)
    queue = Queue("storybook", connection=connection)
    worker_class = SimpleWorker if sys.platform == "win32" else Worker
    worker = worker_class([queue], connection=connection)
    worker.work()


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Create `backend/Procfile`**

```
web: uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: uv run python -m worker.run_worker
```

- [ ] **Step 8: Run the full backend suite**

```bash
uv run pytest -v
```
Expected: all tests across every file pass.

- [ ] **Step 9: Commit**

```bash
git add backend/worker backend/Procfile backend/tests/test_run_job.py
git commit -m "feat: RQ worker runs the checkpointed graph and updates the job row"
```

---

### Task 10: Frontend scaffold (`pnpm`, Next.js, Tailwind, Supabase client, Sentry)

**Files:**
- Create: `frontend/` (via `create-next-app`)
- Create: `frontend/.env.local.example`
- Create: `frontend/lib/supabaseClient.ts`
- Create: `frontend/sentry.client.config.ts`
- Create: `frontend/sentry.server.config.ts`
- Create: `frontend/vitest.config.ts`

**Interfaces:**
- Produces: `frontend/lib/supabaseClient.ts` exporting `supabase` — consumed by Tasks 12 and 13.

- [ ] **Step 1: Scaffold the Next.js app**

```bash
pnpm dlx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias "@/*" --no-turbopack
cd frontend
```
Expected: `frontend/package.json`, `frontend/app/page.tsx` etc. created.

- [ ] **Step 2: Install runtime and test dependencies**

```bash
pnpm add @supabase/supabase-js @sentry/nextjs
pnpm add -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react
```

- [ ] **Step 3: Create `frontend/vitest.config.ts`**

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
```

- [ ] **Step 4: Add a `test` script to `frontend/package.json`**

In the `"scripts"` block, add:
```json
"test": "vitest run"
```

- [ ] **Step 5: Create `frontend/lib/supabaseClient.ts`**

```typescript
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

- [ ] **Step 6: Create `frontend/sentry.client.config.ts`**

```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
});
```

- [ ] **Step 7: Create `frontend/sentry.server.config.ts`**

```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
});
```

- [ ] **Step 8: Create `frontend/.env.local.example`**

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SENTRY_DSN=
```

- [ ] **Step 9: Verify the app builds and tests run**

```bash
pnpm build
pnpm test
```
Expected: build succeeds; `pnpm test` reports no test files yet (0 passed, 0 failed) without erroring.

- [ ] **Step 10: Commit**

```bash
git add frontend
git commit -m "feat: scaffold Next.js frontend with pnpm, vitest, supabase client, sentry"
```

---

### Task 11: Frontend — write-story page

**Files:**
- Create: `frontend/app/write/page.tsx`
- Test: `frontend/app/write/page.test.tsx`

**Interfaces:**
- Consumes: `frontend/lib/supabaseClient.ts` is NOT used here (this page only calls the backend HTTP API).
- Produces: navigates to `/process/[jobId]` on submit — the exact route Task 12 implements.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/app/write/page.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WriteStoryPage from "./page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe("WriteStoryPage", () => {
  beforeEach(() => {
    pushMock.mockClear();
    global.fetch = vi.fn().mockResolvedValue({
      json: async () => ({ job_id: "abc-123" }),
    }) as unknown as typeof fetch;
  });

  it("submits the story text and redirects to the processing page", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "A dog runs in a field." },
    });
    fireEvent.click(screen.getByText("Make my book"));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/process/abc-123"));

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/storybooks"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "A dog runs in a field." }),
      })
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm test app/write/page.test.tsx
```
Expected: fails — `./page` (`page.tsx`) does not exist.

- [ ] **Step 3: Create `frontend/app/write/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function WriteStoryPage() {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/storybooks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    router.push(`/process/${data.job_id}`);
  }

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Write your story..."
        aria-label="story text"
      />
      <button type="submit" disabled={submitting}>
        {submitting ? "Sending..." : "Make my book"}
      </button>
    </form>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pnpm test app/write/page.test.tsx
```
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/app/write
git commit -m "feat: write-story page posts to /storybooks and redirects to processing"
```

---

### Task 12: Frontend — processing page (Realtime subscription)

**Files:**
- Create: `frontend/app/process/[jobId]/page.tsx`
- Test: `frontend/app/process/[jobId]/page.test.tsx`

**Interfaces:**
- Consumes: `frontend/lib/supabaseClient.ts` (Task 10).
- Produces: navigates to `/book/[jobId]` on `status === "complete"` — the exact route Task 13 implements.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/app/process/[jobId]/page.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import ProcessingPage from "./page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

let capturedCallback: (payload: unknown) => void;

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    channel: () => ({
      on: (_event: string, _filter: unknown, callback: (payload: unknown) => void) => {
        capturedCallback = callback;
        return { subscribe: () => ({}) };
      },
    }),
    removeChannel: vi.fn(),
  },
}));

describe("ProcessingPage", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it("redirects to the book page when the job completes", async () => {
    render(<ProcessingPage params={{ jobId: "abc-123" }} />);

    act(() => {
      capturedCallback({ new: { id: "abc-123", status: "complete", current_stage: "compose" } });
    });

    expect(pushMock).toHaveBeenCalledWith("/book/abc-123");
  });

  it("shows the current stage while running", () => {
    render(<ProcessingPage params={{ jobId: "abc-123" }} />);

    act(() => {
      capturedCallback({ new: { id: "abc-123", status: "running", current_stage: "generate_scene" } });
    });

    expect(screen.getByText("generate_scene")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm test app/process
```
Expected: fails — `./page` does not exist.

- [ ] **Step 3: Create `frontend/app/process/[jobId]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";

type Job = {
  id: string;
  status: string;
  current_stage: string | null;
};

export default function ProcessingPage({ params }: { params: { jobId: string } }) {
  const [job, setJob] = useState<Job | null>(null);
  const router = useRouter();

  useEffect(() => {
    const channel = supabase
      .channel(`job-${params.jobId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "jobs",
          filter: `id=eq.${params.jobId}`,
        },
        (payload: { new: Job }) => {
          setJob(payload.new);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [params.jobId]);

  useEffect(() => {
    if (job?.status === "complete") {
      router.push(`/book/${params.jobId}`);
    }
  }, [job, params.jobId, router]);

  return (
    <div>
      <p>Making your book...</p>
      <p>{job?.current_stage ?? "queued"}</p>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pnpm test app/process
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/app/process
git commit -m "feat: processing page subscribes to job row via realtime and redirects on complete"
```

---

### Task 13: Frontend — slideshow page

**Files:**
- Create: `frontend/app/book/[jobId]/page.tsx`
- Test: `frontend/app/book/[jobId]/page.test.tsx`

**Interfaces:**
- Consumes: `frontend/lib/supabaseClient.ts` (Task 10).
- Produces: the final screen of the Phase 0 walking skeleton — no further tasks depend on this one.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/app/book/[jobId]/page.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import BookPage from "./page";

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    from: () => ({
      select: () => ({
        eq: () => ({
          single: async () => ({
            data: {
              id: "abc-123",
              caption: "A dog runs through a sunny field.",
              image_path: "abc-123/scene-1.png",
            },
          }),
        }),
      }),
    }),
    storage: {
      from: () => ({
        createSignedUrl: async () => ({ data: { signedUrl: "https://example.com/signed.png" } }),
      }),
    },
  },
}));

describe("BookPage", () => {
  it("renders the signed image and caption", async () => {
    render(<BookPage params={{ jobId: "abc-123" }} />);

    await waitFor(() =>
      expect(screen.getByAltText("A dog runs through a sunny field.")).toHaveAttribute(
        "src",
        "https://example.com/signed.png"
      )
    );
    expect(screen.getByText("A dog runs through a sunny field.")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm test app/book
```
Expected: fails — `./page` does not exist.

- [ ] **Step 3: Create `frontend/app/book/[jobId]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

type Job = {
  id: string;
  caption: string | null;
  image_path: string | null;
};

const BUCKET = "storybook-images";

export default function BookPage({ params }: { params: { jobId: string } }) {
  const [job, setJob] = useState<Job | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from("jobs")
        .select("id, caption, image_path")
        .eq("id", params.jobId)
        .single();
      setJob(data);

      if (data?.image_path) {
        const { data: signed } = await supabase.storage
          .from(BUCKET)
          .createSignedUrl(data.image_path, 60 * 60);
        setImageUrl(signed?.signedUrl ?? null);
      }
    }
    load();
  }, [params.jobId]);

  if (!job) return <p>Loading your book...</p>;

  return (
    <div>
      {imageUrl && <img src={imageUrl} alt={job.caption ?? "storybook scene"} />}
      <p>{job.caption}</p>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pnpm test app/book
```
Expected: `1 passed`

- [ ] **Step 5: Run the full frontend suite**

```bash
pnpm test
pnpm build
```
Expected: all vitest tests pass; build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/book
git commit -m "feat: slideshow page renders the signed storybook image and caption"
```

---

### Task 14: Railway + Vercel deployment wiring (manual)

**Files:** none (external service configuration)

**Interfaces:**
- Consumes: `backend/Procfile` (Task 9), `backend/.env.example` / `frontend/.env.local.example` (Tasks 3, 10).
- Produces: a publicly reachable backend URL (for `NEXT_PUBLIC_API_BASE_URL`) and frontend URL — used in Task 15's manual verification.

- [ ] **Step 1: Manual — create the Railway project**

Create a new Railway project (region: Singapore / ap-southeast). Add a **Redis** plugin — note its connection string as `REDIS_URL`.

- [ ] **Step 2: Manual — add the web and worker services**

Add two services, both pointing at the `backend/` directory of this repo:
- **web**: start command `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **worker**: start command `uv run python -m worker.run_worker`

Set these env vars on **both** services (values from Task 2 and your Gemini/Sentry/LangSmith accounts):
```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=
REDIS_URL=
GEMINI_API_KEY=
SENTRY_DSN_BACKEND=
FRONTEND_ORIGIN=<your Vercel URL, filled in after Step 3>
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=storybuddy-dev
```

- [ ] **Step 3: Manual — create the Vercel project**

Import this repo into Vercel with root directory `frontend`. Set env vars:
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=<Railway web service public URL>
NEXT_PUBLIC_SENTRY_DSN=
```
Deploy. Note the resulting Vercel URL, then go back to Step 2 and set `FRONTEND_ORIGIN` on both Railway services to it.

- [ ] **Step 4: Verify**

```bash
curl https://<railway-web-url>/health
```
Expected: `{"status":"ok"}`. Visit the Vercel URL `/write` in a browser — the page loads without console errors.

- [ ] **Step 5: No commit** — this task changes only external service configuration, not repo files.

---

### Task 15: Manual end-to-end verification against ROADMAP Phase 0 exit criteria

**Files:** none

**Interfaces:** none — this is the walking-skeleton acceptance check.

- [ ] **Step 1: Run backend + worker locally (or use the Task 14 deployment)**

```bash
cd backend
uv run uvicorn app.main:app --reload
```
In a second terminal:
```bash
cd backend
uv run python -m worker.run_worker
```

- [ ] **Step 2: Run frontend locally**

```bash
cd frontend
pnpm dev
```

- [ ] **Step 3: Walk the flow**

Open `http://localhost:3000/write`, type a short story, submit. Confirm:
- Browser redirects to `/process/<job_id>`.
- The processing page updates live (no manual refresh) as the job row's `current_stage`/`status` change via Realtime.
- On completion, browser redirects to `/book/<job_id>` and renders a real Nano Banana image (not a placeholder) with a Gemini-derived caption.

- [ ] **Step 4: Verify the infrastructure directly**

In the Supabase dashboard: `jobs` table has one row with `status = 'complete'`, non-null `caption` and `image_path`. Storage → `storybook-images` bucket contains the uploaded PNG under `<job_id>/scene-1.png`.

- [ ] **Step 5: Verify observability**

LangSmith project (`storybuddy-dev`) shows a trace for the graph run with all 6 nodes. Sentry shows no unexpected errors from this run.

- [ ] **Step 6: Confirm exit criteria met**

This satisfies ROADMAP Phase 0's exit criteria verbatim: *"Type a hardcoded story → job runs on the worker → one Nano Banana image lands in Storage → slideshow shows it live via Realtime. The pipe is real end-to-end."*

- [ ] **Step 7: Tag the milestone**

```bash
git add -A
git status
git commit -m "chore: Phase 0 walking skeleton complete" --allow-empty
git tag phase-0-complete
```

---

## Self-Review Notes

- **Spec coverage:** every ROADMAP Phase 0 bullet has a task — repo/monorepo layout (Task 1), env/secrets (Tasks 3, 10, 14), Supabase provisioning (Task 2), Railway/Vercel provisioning (Task 14), `POST /storybooks` + RQ pickup (Tasks 8–9), LangGraph stub graph + Postgres checkpointer (Tasks 5, 9), the three thin real calls (Tasks 6, 7), Next.js auth-stub/write/processing/slideshow (Tasks 10–13; auth stub is intentionally just "no real auth yet" per ROADMAP — Phase 2 owns real auth), LangSmith + Sentry tracing (Tasks 1, 8, 10, verified in Task 15).
- **Cross-cutting concerns honored where in scope:** CC-4 (RLS + signed URLs) — Task 2 + Task 13. CC-5 (Observability) — Tasks 1, 8, 10, 15. CC-10 (Checkpointing) — Task 9. CC-1/CC-2/CC-3/CC-6/CC-8/CC-9 (moderation, PII, cost control, accessibility, kid-vs-parent design, failure states) are explicitly **Phase 2/1 work**, not Phase 0 — not touched here, matching ROADMAP.
- **Open item still flagged, not guessed:** the exact Nano Banana model string and `inline_data` response shape in Task 7 (Global Constraints + inline code comment) — confirm against the installed `google-genai` SDK version before trusting verbatim.
