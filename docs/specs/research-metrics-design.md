# Research Metrics View — Design Spec

**Date:** 2026-08-10  
**Status:** approved  
**Phase:** 2.5 (alongside annotation-surface)  
**Requires:** ADR-030 (Langfuse replaces LangSmith — must be written in the same change)

---

## 1. Purpose

Give the research team and adviser/panel a single URL that shows:

- **Aggregates:** total runs, completion rate, total images generated, total regenerations, estimated total cost
- **Per-run table:** one row per job with scene outcomes, cost estimate, and a deep link to the full Langfuse trace (per-model cost breakdown lives there)

No new auth role. No account provisioning. Access model: **public route** at `/research` — the data (aggregate counts, cost estimates, pass rates) contains no PII and no child content; a capstone project does not need access control on non-sensitive summary statistics.

---

## 2. What this is NOT

- Not a live monitoring dashboard (ADR-026 rejected that)
- Not a replacement for Tool A (`functional-verification-matrix.md`) — Tool A runs offline over Langfuse exports for Objectives 1–2
- Not a per-model cost breakdown on the page itself — that lives in Langfuse, one click away per run

---

## 3. Data layer — migration `0013`

File: `supabase/migrations/0013_jobs_research_metrics.sql`

```sql
alter table jobs
  add column image_count       integer,
  add column regen_count       integer,
  add column ref_retry_count   integer,
  add column scenes_total      integer,
  add column scenes_passed     integer,
  add column scenes_failed     integer,
  add column scenes_unchecked  integer,
  add column usd_estimate      numeric(8,4),
  add column langfuse_trace_url text;
```

All columns nullable. Failed jobs leave them NULL — that is informative (the pipeline did not complete). No check constraints; these are research analytics columns, not product columns.

**`usd_estimate` is an approximation:** `image_count × 0.025` (USD). Labelled "est." everywhere it appears. Accurate enough for a capstone; per-model exact costs live in Langfuse.

---

## 4. Backend changes

### 4.1 Langfuse callback — `backend/worker/run_job.py`

Both `run_storybook_job` and `resume_storybook_job` get a Langfuse callback. The `trace_id=job_id` pin means the initial run and any resume share one trace in Langfuse, and the trace URL is derivable from the job ID without an API lookup.

```python
from langfuse.callback import CallbackHandler

def _langfuse_handler(job_id: str) -> tuple[CallbackHandler, str]:
    url = f"https://cloud.langfuse.com/project/{settings.langfuse_project_id}/traces/{job_id}"
    return CallbackHandler(trace_id=job_id), url
```

In `run_storybook_job`, before streaming:
1. Call `_langfuse_handler(job_id)` → `(handler, trace_url)`
2. Write `langfuse_trace_url` to `jobs` immediately (so the row has a trace URL even if the job later fails)
3. Pass `"callbacks": [handler]` into the graph config alongside `"configurable"` and `"recursion_limit"`

`resume_storybook_job` gets the same callback — same `trace_id=job_id`, so resume events append to the existing trace.

### 4.2 Cost persistence — `_finish()`

On successful completion, extend the existing `jobs.update()` call with the cost fields. Import `_outcome` from `pipeline.compose` (see §4.5) rather than re-implementing it:

```python
from pipeline.compose import _outcome

cost = result["cost"]
scenes = result["scenes"]
outcomes = [_outcome(s) for s in scenes]

supabase.table("jobs").update({
    "status": "complete",
    "current_stage": "compose",
    "pages": pages,
    "image_count": cost.image_count,
    "regen_count": cost.regen_count,
    "ref_retry_count": cost.ref_retry_count,
    "scenes_total": len(scenes),
    "scenes_passed": outcomes.count("passed"),
    "scenes_failed": outcomes.count("failing"),
    "scenes_unchecked": outcomes.count("unchecked"),
    "usd_estimate": round(cost.image_count * 0.025, 4),
}).eq("id", job_id).execute()
```

### 4.3 `_outcome` — export from `pipeline/compose.py`

`_outcome` is currently a module-private helper in `compose.py`. Make it importable by removing the leading underscore convention concern — it already has a clear contract. `run_job.py` imports it from `pipeline.compose`; `compose.py` continues using it internally. No circular dependency risk (`run_job` → `pipeline.compose` is already an established import direction).

### 4.4 Dependency change

Add `langfuse` to backend dependencies (`pyproject.toml` or `requirements.txt`). Remove `langchain-langsmith` if present. The `langfuse` package ships the LangChain callback — no separate install needed.

### 4.5 New settings fields — `backend/app/config.py`

```python
langfuse_secret_key: str | None = None
langfuse_public_key: str | None = None
langfuse_host: str = "https://cloud.langfuse.com"
langfuse_project_id: str = ""   # used to construct trace URLs written to jobs
```

### 4.6 Tests — `backend/tests/test_run_job.py`

Existing tests for `_finish()` must be updated to assert the new cost columns are written. New assertions needed:

- `_finish()` writes `image_count`, `regen_count`, `ref_retry_count`, `scenes_total`, `scenes_passed`, `scenes_failed`, `scenes_unchecked`, `usd_estimate` to `jobs` on a successful result
- `usd_estimate` equals `image_count × 0.025` (rounded to 4dp)
- `run_storybook_job()` writes `langfuse_trace_url` to `jobs` before streaming begins
- The Langfuse `CallbackHandler` is passed into the graph config's `callbacks` list (mock `CallbackHandler` at the test boundary)

---

## 5. Frontend — research page

### 5.1 Route

`frontend/app/(research)/research/page.tsx` — server component.

**The `(research)` route group does not yet exist** — it must be created as part of this implementation. `frontend/app/(research)/` is the route group directory; `layout.tsx` for the group can be a passthrough (no shared UI needed yet between research routes).

### 5.2 Access model — public route

`/research` is fully public. No token validation, no middleware, no role check. The page renders research metrics that contain no PII and no child content. Adviser and panel access the URL directly with no account.

If access control becomes necessary later (e.g. before a public deployment), adding a secret token or Vercel password protection is a one-line change. Don't build it now.

### 5.3 Data fetch

Server component queries Supabase with the **service role** client to bypass RLS and read all jobs across all classrooms. The service role key must be present in the frontend's environment (currently missing — add `SUPABASE_SERVICE_ROLE_KEY` to Vercel env vars and `.env.local`). Use `NEXT_PUBLIC_SUPABASE_URL` (the variable name the frontend already uses):

```typescript
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!   // server-only — never exposed to client
);

const { data: jobs } = await supabase
  .from("jobs")
  .select(`
    id, status, created_at, style_preset_id,
    classroom_id, failure_reason,
    image_count, regen_count, ref_retry_count,
    scenes_total, scenes_passed, scenes_failed, scenes_unchecked,
    usd_estimate, langfuse_trace_url
  `)
  .order("created_at", { ascending: false });
```

`profile_id` is omitted from the select — not useful on a summary page and marginally reduces surface area.

### 5.4 Page layout

**Aggregate stats row** (computed server-side from the jobs array — no second query):

| Stat | Derivation |
|------|-----------|
| Total runs | `jobs.length` |
| Complete | `jobs.filter(j => j.status === 'complete').length` |
| Failed | `jobs.filter(j => j.status === 'failed').length` |
| Total images generated | `SUM(image_count)` over complete jobs |
| Total regenerations | `SUM(regen_count)` |
| Est. total cost (USD) | `SUM(usd_estimate)` — labelled "est." |
| Overall pass rate | `SUM(scenes_passed) / SUM(scenes_total)` |

**Per-run table** — one row per job, newest first:

| Column | Notes |
|--------|-------|
| Job ID | First 8 chars of UUID |
| Status | `complete` / `failed` / `running` / etc. |
| Created | Datetime |
| Style preset | `cel` / `comic` / `gouache` |
| Scenes | `passed/total` (e.g. `8/10`) |
| Regens | `regen_count` |
| Est. cost | `usd_estimate` USD |
| Trace | "View →" link to `langfuse_trace_url` (NULL → no link) |

Failed jobs show `failure_reason`; cost columns show `—` for NULL.

### 5.5 No client-side state, no polling

Static server render. Refresh to see new data. No Realtime subscription — this is a research tool checked occasionally, not a live dashboard.

### 5.6 Tests — `frontend/app/(research)/research/page.test.tsx`

- Aggregate math: given a known array of job rows, the computed stats match expected values (zero-division on pass rate when `scenes_total` is 0)
- NULL handling: jobs with NULL cost columns contribute 0 to sums, show `—` in the table

---

## 6. Environment variables

### Backend (worker / Northflank)

| Variable | Purpose |
|----------|---------|
| `LANGFUSE_SECRET_KEY` | Langfuse cloud auth |
| `LANGFUSE_PUBLIC_KEY` | Langfuse cloud auth |
| `LANGFUSE_HOST` | Default: `https://cloud.langfuse.com` |
| `LANGFUSE_PROJECT_ID` | Used to construct `langfuse_trace_url` written to `jobs` |

Remove: `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`

### Frontend (Vercel)

| Variable | Purpose |
|----------|---------|
| `SUPABASE_SERVICE_ROLE_KEY` | **New** — server-only, bypasses RLS for the research page |

No `RESEARCH_TOKEN` — the page is public (§5.2).

---

## 7. ADR-030

This spec requires a new ADR written to `docs/product/ADRs.md` as ADR-030, covering the LangSmith → Langfuse decision. The ADR is written in the same change as this feature — not after. See §7 of the implementation plan for the exact content. The amendment is to ADR-014 (LangSmith, 2026-07-22).

**Summary of the decision:** LangSmith → Langfuse cloud. Reason: Langfuse maintains a model pricing table and computes per-model USD costs automatically from token counts, covering the research team's need to see "cost for the image model vs cost for the judge" without instrumenting `providers.py`. LangSmith reports tokens only. Langfuse is open-source with a cloud free tier; the integration adds one `CallbackHandler` instantiation per job rather than env-var-only zero-code (minor wiring increase, acceptable). Tool A's evaluation methodology (offline scripts over trace exports) is unchanged.

---

## 8. Out of scope

- Per-model cost on the research page itself — lives in Langfuse, one click away
- Annotation surface routes (`/annotate`, `/adjudicate`, `/books`) — separate spec
- Real-time updates — static server render, refresh to update
- Cost data for failed jobs — NULL, intentional
- Access control on `/research` — not needed for a capstone with non-sensitive aggregate data; add later if required

---

## 9. Resolved questions

- **`_outcome` extraction:** import from `pipeline.compose` — no circular dependency, no duplication (§4.3)
- **Langfuse trace URL format:** verify `https://cloud.langfuse.com/project/{id}/traces/{trace_id}` against Langfuse cloud UI before hardcoding in `_langfuse_handler`. Format is current as of 2026-08-10 but Langfuse updates their UI.
- **Auth model:** public route — data is non-sensitive aggregate counts (§5.2)
