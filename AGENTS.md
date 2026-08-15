# Project Agents Configuration

## Metadata
- Owner: Hanseooo (solo build)
- Last reviewed: 2026-07-27
- Review cadence: monthly, or whenever an ADR is added

---

## Baseline Rules
> Inlined verbatim from `~/.claude/CLAUDE.md` — the global source of truth. Included so agents
> that cannot read `~/.claude/` (Codex, Cursor, Copilot) still get these rules.
> Omitted: *Asking Questions* (personal; uses `AskUserQuestion` which those agents lack) and
> *Project Context* (this file is the project context). Survivors renumbered 1–5;
> cross-references name their target section instead of a number.

### 1. Think Before Coding

- State assumptions explicitly. Uncertain → ask, don't guess and run.
- Claiming something is unused, dead, or deprecated? Grep the whole repo first.
  One file is not evidence.
- Multiple valid interpretations → present them. Never pick silently.
- Confused → stop, name what's confusing, ask one focused question.

### 2. Architectural Decisions

Don't decide these alone. Ask before implementing:

- New dependency, service, or datastore
- Schema, API contract, or public interface change
- Auth, billing, or infra
- A change spanning more than ~3 modules, or one that's hard to reverse

Ask at the moment you notice, not after writing the code.

**This gate is for decisions, not for permission to work.** Bugs, failing tests,
and clearly-scoped fixes: just fix them.

If the decision needs more exploration than the remaining context supports, say so
and offer to run `/handoff` and continue in a fresh session. Never start a handoff
without approval.

### 3. Surgical Changes

- Don't improve adjacent code, comments, or formatting.
- Match existing style, even if you'd do it differently.
- Notice unrelated dead code → mention it, don't delete it.
- Remove orphans **your** change created (imports, vars, functions). Nothing else.

Test: every changed line traces to the request.

### 4. Verification

- State success criteria before starting.
- Work that skips the plan chain still starts with a failing test
  (`superpowers:test-driven-development`).
- TDD scope: anything with a branch, loop, parser, or money/security path.
  One-liners, config, and pure renames are exempt — ponytail wins there.
- Never claim done without running the check and showing its output.
- Report faithfully: tests failed → say so, with output. Step skipped → say so.

### 5. Security

- Never read `.env` or secret files. Ask for sanitized inputs.
- Never log or echo credentials, tokens, or keys.
- Flag auth/billing/infra changes before implementing (see Architectural Decisions).

---

## StoryBuddy Hard Rules
> Project-specific constraints. No agent may override these. Previously in `/CLAUDE.md`.

### Architecture is locked

Every decision in `docs/product/adr/` is **frozen**. Do not refactor around a decision,
swap a library, or change the pipeline shape because a different approach seems cleaner.

- To change a locked decision: **write a new ADR** (a new file
  `docs/product/adr/ADR-0NN-<kebab-title>.md`, plus its row in the `docs/product/ADRs.md` index)
  stating context / decision / consequences / alternatives, and **flag it to the human**. Do not
  implement until the ADR is accepted.
- If a task seems to *require* violating an ADR, stop and surface the conflict. Don't guess.
- **Architectural decisions get their own session — never decided inline while building.** Open
  ones are queued in `docs/product/DECISION_BACKLOG.md`; each is resolved in a dedicated
  ADR-writing session, then its row is deleted. If building a module forces an *undecided*
  architectural question (schema shape, LangGraph node/edge convention, resilience policy, a new
  cross-cutting concern, a library swap), **stop and log it to the backlog** — do not settle it by
  writing code.

**Two rules agents violate by reflex:**
- **Open-weight models only** (ADR-015). Never reach for Gemini/GPT/Claude to "just make this
  node work." **Provider SDKs, endpoints, and API keys live in `backend/providers.py` and nowhere
  else.** Model *IDs* live in `backend/app/config.py` as env-overridable settings — a model swap is
  an env change, a provider swap is a `providers.py` change (`config.py:16`). Never hardcode either
  at a call site.
- **No fine-tuning except the consistency judge** (ADR-016, superseded by ADR-018). The judge is
  fine-tuned per `docs/specs/judge-finetune.md` — that is the one sanctioned LoRA. If you
  conclude a LoRA is needed anywhere else, surface it, don't build it.

### Contract-first

The **Story Memory schema** (`backend/contracts/`) is the contract between every pipeline module.
It is Pydantic and it is authoritative.

> **State of play (Phase 2 in progress):** `StoryMemory` is **built** (`backend/contracts/story_memory.py`,
> 2026-07-29). `job_state.py` is **deleted**. All **eleven** pipeline nodes are on partial-return
> `(state: StoryMemory) -> dict`; `input_gate` is the graph entry point. Phase-1 nodes — `analyze`,
> `segment`, `char_bible`, `generate_scene`, `consistency_check`, `regenerate`, `compose` — plus
> Phase-2 nodes `char_ref_mod`, `output_mod` and `reveal` (ADR-029, effect-free, holds the one
> `interrupt()`) are all built. No pass-through stubs remain. See
> `docs/specs/story-memory-contract.md` for the contract and ADR-023/024 for conventions.

- Validate against it at **every LLM boundary** (strict `json_schema` structured output →
  Pydantic, always).
- A module reads its inputs and writes its outputs **through the schema**, never via ad-hoc dicts.
- Changing the schema is a contract change: update the schema, the affected specs, and every
  consumer in the same change.

### Testing bright line

Two kinds of tests. Never mix them (see `docs/MASTER_SPEC.md` §6).

- **Deterministic tests** (Vitest / pytest / Playwright): **mock every model call**
  (`backend/providers.py`). Never assert on generated content ("is the character consistent?"
  is not a unit test). These run in CI and **must stay green** — a change that reddens CI is
  not done.
- **Eval harness** (offline, real models, story corpus): the only place fuzzy quality is
  measured. Never put it in CI. It doubles as research instrumentation (Langfuse).

**Provider smoke tests** (`backend/tests/test_smoke_providers.py`, added 2026-08-11) sit between
the two and belong to neither. They call real providers but assert only **reachability and
contract** — never quality — because the deterministic suite mocks `providers.py` and therefore
stays green for a deployment that cannot complete a single job. Three production outages in one
week were all this class (`qwen/qwen3-32b` emitting prose, a retired `llama-guard-3-8b`, an image
moderation model with no vision support). Deselected by default; opt in:

```bash
cd backend
uv run pytest -m "smoke and not smoke_image"   # text/judge/moderation, six small-model pings
uv run pytest -m smoke                         # the above plus one paid fal.ai draw
```

**Run these before any deploy that changes a model ID, a base URL, or a provider.** They skip
cleanly when only placeholder credentials are present, and never run in CI.

### Feature spec is the unit of work

Before writing code for a module, read its spec in `docs/specs/` **and** the cross-cutting
concerns registry (MASTER_SPEC §5). If a spec doesn't exist, write it from
`docs/specs/TEMPLATE.md` and get it approved before implementing.

- Behavior change → update the spec **in the same change**. Specs that lie are worse than none.

**Artifact hygiene (one home per type — avoid noise):**
- `brainstorming` writes feature specs into `docs/specs/` — never a parallel tree.
- `writing-plans` writes into `docs/specs/plans/`.
- **Specs are durable, plans are disposable.** Delete a plan once its module is built + tests
  green + spec updated — git keeps the history. `docs/specs/plans/` should only ever contain
  *in-flight* work.
- To build a module, load only `AGENTS.md` + that module's spec + the CC registry — not the
  whole docs tree. Lean context = better output.

### Safety non-negotiables (child-facing product)

- **No unmoderated generated image ever reaches a child** — including the canonical character
  reference before the reveal. Moderation order: input text → char-ref → output image.
- **PII is redacted (Presidio) before** storage, captioning, or export. A child narrating real
  life is the expected case, not the exception.
- **RLS on every table**; signed URLs for every asset; no public buckets.
  ⚠️ **Not satisfied today.** `supabase/migrations/0001_jobs_table.sql:18-21` and
  `0004_jobs_pages.sql`'s `storage.objects` policy are the only policies, and both read
  `using (true)` / `using (bucket_id = 'storybook-images')` — RLS is *enabled*, but nothing is
  *restricted*; scoping is a client-side `.eq('id', …)` convention, and no classroom/profile
  columns exist to scope by. Closes in Phase 2 (CC-4). Treat any `jobs`-table or storage-policy work
  as touching this gap.
- Failure and moderation screens get the **same** design care as success screens.
  ✅ **Now built (2026-08-02):** `input_gate` (meta-llama/llama-guard-4-12b + Presidio + OpenRouter backstop),
  `char_ref_mod` (~~qwen/qwen3-vl-32b-instruct~~ → mistralai/mistral-small-3.2-24b-instruct since 2026-08-11,
  ADR-002 amendment, + Gemma safety rubric), `output_mod` (same two-classifier check +
  soften-and-retry). `moderation_router` and `route_after_output_mod` enforce the ordering in
  `graph.py`. PII redaction via Presidio is live, with the Filipino recognizers from
  `input-gate-hardening` (`ph_recognizers.py`) wired into `providers._presidio` — stock Presidio no
  longer ships bare.

### Maintainability

- **Deterministic LangGraph nodes.** No autonomous-agent routing; conditional edges only at
  moderation pass/fail and consistency pass/fail (ADR-003).
- **One module = one concern**, one file per pipeline node. Rough ceiling: ~300 lines or mixed
  concerns is the signal to split, not a hard limit to game.
- **No parallel structures.** One canonical location per artifact type. Don't create a second
  folder that does the same job.
- **Follow the map.** New pipeline module → a file in `backend/pipeline/`; anything crossing a
  module boundary → through `backend/contracts/`. Don't invent new top-level folders without a
  reason.

### When in doubt

Stop and ask one focused question. Surfacing a confusion is cheaper than a wrong build.

---

## Project Context
- Stack: **Frontend** — Next.js 16.2.10 (App Router) + React 19 + Tailwind 4, pnpm-managed,
  Vitest unit tests, Sentry. **Backend** — FastAPI + RQ worker + LangGraph (deterministic graph)
  on Python 3.12, uv-managed, pytest + ruff. **Data** — Supabase (Postgres + Auth + Storage +
  Realtime, RLS everywhere), Redis (RQ broker). **Models** — open-weight only (ADR-015):
  `mistralai/mistral-small-3.2-24b-instruct` (text — replaced `qwen/qwen3-32b` on 2026-08-11,
  which passed Probe 3 but emitted prose instead of structured output in production, prod job
  `af068baf`) + `google/gemma-3-27b-it` (VLM judge) via OpenRouter; Qwen-Image-Edit
  (image gen) via fal.ai. All vendor calls live in `backend/providers.py`.
  **`backend/app/config.py` is the only source of truth for model IDs** — docs drift, and a
  wrong ID here is invisible to CI (every test mocks `providers.py`). Verify with
  `uv run pytest -m smoke` before deploying a model change.
  (evidence: `frontend/package.json`, `backend/pyproject.toml`)
- Architecture: Frontend (Vercel) posts to FastAPI (Northflank), which writes a job row and returns
  immediately. A separate RQ worker runs the LangGraph pipeline, checkpointing to Postgres after
  each scene. Frontend watches the job row via Supabase Realtime.
  **Target shape** — `docs/MASTER_SPEC.md` §2 is canonical and finer-grained (it splits char-ref
  moderation, `regenerate`, output moderation, and `export` into their own nodes):
  `input_gate → analyze → segment → char_bible → [char-ref moderation] → generate_scene →
  consistency_check → [regenerate] → [output moderation] → compose → export`.
  **Built today** (`backend/pipeline/graph.py`):
  `input_gate → [moderation_router] → analyze → segment → char_bible → char_ref_mod →
  [moderation_router] → reveal → [route_reveal] → generate_scene → consistency_check →
  [route_after_check] → regenerate → consistency_check → output_mod →
  [route_after_output_mod] → … → compose`.
  ⚠️ **`output_mod` is INSIDE the scene loop** (2026-08-13): each scene is screened the moment it
  finalizes, and `route_after_output_mod` hands back to `route_next_scene` rather than going
  straight to `compose`. It used to run once over the finished book, which meant the gate could
  only ever fire after every image was drawn and paid for — prod job 4f7698d5 (2026-08-12) died on
  s2 of 8 and took 11 fal images with it. ADR-025's no-partial-book rule is unchanged; only the
  bill is. This is what `RECURSION_LIMIT`'s `MAX_SCENES * 7` counts (×5 → ×7 with ADR-037's
  second corrected retry).
  `moderation_router` (ADR-024 pure router) handles both post-`input_gate` and post-`char_ref_mod`
  edges; `route_after_output_mod` reads `moderation_status="failed"` and raises.
  ⚠️ **The post-`char_ref_mod` edge can also route BACK to `char_bible`** (2026-08-13,
  `reference-moderation-retry`): a flagged reference buys one redraw before the terminal
  `ref_flagged`, closing a `char_bible → char_ref_mod → char_bible` loop that runs at most twice.
  This is the second cap-bounded loop back into `char_bible`, alongside `route_reveal`'s
  `"try_again"`, and it is the +2 in `SUPER_STEP_PRELUDE`.
  `char_ref_mod` runs `settings.moderation_primary_image_model` (mistralai/mistral-small-3.2-24b-instruct
  since 2026-08-11 — replaced qwen/qwen3-vl-32b-instruct, which emitted its verdict before its reasoning on
  Alibaba Cloud and hard-failed the job here; ADR-002 amendment) + Gemma safety rubric on each canonical
  ref image.
  `reveal` (ADR-029) is effect-free and holds one `interrupt()`; `route_reveal` loops `"try_again"`
  back to `char_bible` and enforces the 3-tap cap.
  `output_mod` runs the same two-classifier check on each output scene, with one soften-and-retry,
  and logs **which** classifier flagged and whether the other was consulted (CC-5) — a flag that
  kills a book used to leave no account of who killed it.
  All provider calls (meta-llama/llama-guard-4-12b, Presidio, mistralai/mistral-small-3.2-24b-instruct, OpenRouter backstops) go through
  `backend/providers.py`; `get_signed_url` lives there too (Storage seam). `export` is not yet built.
  The worker's LangGraph checkpointer reaches Supabase Postgres on the **direct connection (5432)**, never
  the 6543 transaction pooler — `PostgresSaver.from_conn_string` hardcodes `prepare_threshold=0` (ADR-033).
- Critical paths (extra review): moderation ordering (input text → char-ref → output image), PII
  redaction (Presidio) before any storage/caption/export, RLS + signed URLs on every table/asset,
  job checkpoint/resume logic — see `docs/product/ADRs.md` and StoryBuddy Hard Rules above.

## Documentation Map
- Always read: `./AGENTS.md` (this file — all hard rules + commands), `docs/MASTER_SPEC.md`
  (how pieces connect).
- Read when:
  - Visual styling / UI/UX decisions → `DESIGN.md` (neo-pop / neo-brutalist theme reference)
  - Product rationale / why a decision was made → `docs/product/ADRs.md` (frozen — see
    "Architecture is locked" above before touching anything it governs)
  - What the product is / user flow → `docs/product/PRD_v2.md`
  - Build order / what phase we're in → `docs/product/ROADMAP.md`
  - Day-to-day "what tool, what size" → `docs/WORKFLOW.md`
  - Building/changing a pipeline module → its spec in `docs/specs/<module>.md` (from
    `docs/specs/TEMPLATE.md`); write one before implementing if it doesn't exist
  - **This is a capstone study, not only a product.** What the research claims and how it is
    measured → `docs/capstone/` (`research_direction_and_goals.md` for the objectives,
    `methodology.md` for how they're measured). These are the submitted artifact.
  - Anything touching the VLM judge → `docs/specs/judge-finetune.md` (Objective 4: fine-tune a
    consistency judge) **and** `docs/product/PREREGISTRATION_OBJ4.md` (frozen 2026-08-14).
    ⚠️ `settings.vlm_judge_model` is a **pre-registered baseline** — prompted `gemma-3-27b-it` is
    §7.3's product gate. Swapping it to fix a bad verdict is a moved goalpost by the
    pre-registration's own definition. The judge is a control signal, never an outcome measure
    (ADR-004).
  - Frontend-specific framework notes → `frontend/AGENTS.md` (Next.js version-delta notes,
    auto-generated — not a project doc)
  - DB schema work → `supabase/migrations/`
- Fallback: if a module has no spec yet, don't guess its contract slice — write the spec first.

---

## Commands (Use Exactly)
Two independent projects, no shared root tooling — run commands from the named directory.

### Frontend (`frontend/`)
- Install: `pnpm install` (evidence: `frontend/pnpm-lock.yaml`)
- Lint: `pnpm lint` (evidence: `frontend/package.json` scripts)
- Build (includes type checking): `pnpm build`
- Unit tests: `pnpm test` (evidence: `frontend/package.json` → `vitest run`)
- Dev server: `pnpm dev`

### Backend (`backend/`)
- Install: `uv sync` (evidence: `backend/uv.lock`)
- Lint: `uv run ruff check .` (evidence: `backend/pyproject.toml` dev deps + `[tool.ruff]`)
  Note: `ruff format` is **not** adopted — see the comment in `backend/pyproject.toml` for why.
- Unit tests: `uv run pytest` (evidence: `pyproject.toml` `[tool.pytest.ini_options]`,
  `testpaths = ["tests"]`)
- Run web (dev): `uv run uvicorn app.main:app --reload`
  (prod form, evidence `backend/Procfile:1`: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`)
- Run worker: `uv run python -m worker.run_worker` (evidence: `backend/Procfile:2`)
  Must be the `-m` module form — `python worker/run_worker.py` puts `worker/` on `sys.path` instead of
  `backend/` and dies with `ModuleNotFoundError: No module named 'app'`.

### Pre-merge verify
`.github/workflows/ci.yml` runs both on PRs to `main` and pushes to `main`. Run them locally first:
- Frontend (from `frontend/`): `pnpm lint && pnpm test`
- Backend (from `backend/`): `uv run ruff check . && uv run pytest`

### Granular Testing
- Frontend, single file: `pnpm exec vitest run app/write/page.test.tsx` (path relative to
  `frontend/`)
- Frontend, watch mode: `pnpm exec vitest` (no `run` flag) — for iteration, not verification
- Backend, single file: `uv run pytest tests/test_analyze_node.py`
- Backend, single case: `uv run pytest tests/test_analyze_node.py -k "case_name"`

---

## Tooling Lock
- Frontend package manager: **pnpm only** (evidence: `frontend/pnpm-lock.yaml`). Forbidden:
  npm, yarn, bun.
- Backend package manager: **uv only** (evidence: `backend/uv.lock`). Forbidden: bare
  `pip install`, `poetry`, `pipenv`.
- Python env: always `uv run <cmd>` from `backend/` (pinned to `backend/.venv`, Python ≥3.12
  per `pyproject.toml`). Never install globally.

## Testing Contract
- What "passing" means: `pnpm lint && pnpm test` green (frontend) + `uv run ruff check . &&
  uv run pytest` green (backend).
- Enforced by CI (`.github/workflows/ci.yml`) on PRs to `main` and pushes to `main`. Branch
  protection is not configured, so the check reports but does not block merge.
- Deterministic tests mock every `providers.py` call. Never assert on generated content quality;
  that belongs to the offline eval harness, never CI.
- Intentional skips: `tests/test_rls_isolation.py` (needs `SUPABASE_DB_URL` → a local Supabase) and
  `tests/test_smoke_providers.py` (needs real provider credentials). Both skip clean in CI by design.
  Known flaky: none documented yet.

## Project-Specific Invariants
- Story Memory (`backend/contracts/`) is the only channel between pipeline modules — no ad-hoc
  dicts crossing module boundaries.
- Every structured-output call is validated into the Pydantic schema. On OpenRouter, always send
  `provider.require_parameters: true` — without it a routed provider silently downgrades
  `json_schema` to loose JSON mode (ADR-002).
- **Only open-weight models** (ADR-015). Prefer Apache-2.0/MIT. Never adopt a FLUX.1-dev-based
  adapter (InstantCharacter, DreamO, UNO, ACE++, InstantID, PuLID) — their permissive wrapper
  licenses do not override the restrictive base.
- Provider SDKs, endpoints, and keys are named in `backend/providers.py` and nowhere else; model IDs
  are env-overridable settings in `backend/app/config.py`.
- LangGraph nodes are deterministic; conditional edges exist only at moderation pass/fail and
  consistency pass/fail (ADR-003).
- One pipeline module = one file in `backend/pipeline/`.
- **A server layout that fetches data owns it.** Client pages under it receive that data as props —
  they never refetch it in `useEffect`. Supabase is remote (~60 ms warm, ~200 ms on a cold
  connection), so every duplicated `getUser()` or `select` is a visible stall, and a client refetch
  also forces the RSC → HTML → hydrate → fetch waterfall. Share server-side reads through a
  `cache()`-wrapped helper (`frontend/utils/supabase/teacher.ts`) so the layout and the page cost one
  round trip, not two. Branch on server-fetched data with `redirect()` in a server component, never
  with `router.replace()` in an effect — the latter is a second full navigation the user watches.
  Note `auth.getUser()` is a network call to GoTrue, not a JWT decode (`frontend/middleware.ts:28`).
- **Middleware is the only auth gate; a render that disagrees with it must throw, never redirect.**
  `middleware.ts` bounces authenticated users off `/login`, so any server component that answers
  "no user" with `redirect("/login")` creates an infinite 307 loop and a white screen. Server
  Components also cannot write cookies — `cookies().set()` throws unless the request phase is
  `"action"` — so a Supabase server client's `setAll` must be wrapped in try/catch
  (`frontend/utils/supabase/server.ts`); letting it throw is what makes the two layers disagree in
  the first place. Only middleware refreshes tokens.
- **`supabase/migrations/` is not self-applying.** There is no `config.toml` and no CLI link — the
  files are hand-run SQL, so the repo is a record of intent, not of what any database contains.
  Before blaming app code for a missing row, confirm the schema is actually present in the project
  `.env.local` points at. A trigger added in a migration also fires on INSERT only: applying it to a
  project that already has `auth.users` rows leaves those accounts orphaned forever, which is what
  `0012_backfill_orphaned_profiles.sql` exists to repair.
- **Every async route segment ships a `loading.tsx`.** No Suspense boundary means the browser paints
  nothing for the entire server render — a blank screen, not a slow one. Pair it with `error.tsx`
  so a thrown invariant renders a message instead of a blank page.

## Critical Paths & Extra Review Triggers
- Moderation stack and ordering (input → char-ref → output) — ADR-011
- PII redaction (Presidio) — ADR-011
- RLS policies / signed URL generation — ADR-006
- Job checkpoint/resume (LangGraph + Postgres) — ADR-005, ADR-033 (direct connection on 5432, not the
  6543 pooler; adding worker replicas is a database decision, not just a hosting one)
- Anything touching `backend/contracts/` — it's the frozen inter-module contract; changing it
  changes every consumer
- Any change that conflicts with a decision in `docs/product/ADRs.md` — stop, write a new ADR,
  flag it

## Definition of Done
- Completion report includes: commands run, key results, what was verified vs not, residual risks.
- Never mark complete without proof (passing tests, logs, demonstrated correctness).
- Behavior change → the relevant spec in `docs/specs/` is updated in the same change (specs
  that lie are worse than none).
- **Finding change → same rule, wider blast radius.** A probe result, a new ADR, or an ADR
  amendment settles a question that other docs still describe as open, or names a model/phase
  other docs still name differently. Before calling it done: `grep -rn` the repo for what changed
  (the model ID, the ADR number, the phase name, the probe number) and fix every hit in the same
  change. One doc updated is not done.
  - In pre-registered docs (`PHASE_05_RESULTS.md`, `RESEARCH_PROTOCOL.md`) superseded prose is
    **struck through and left visible**, never deleted — what was believed before the numbers
    arrived is part of the method. Elsewhere, just correct it.

### The status surface (grep target — keep it this short)

Nine files independently asserted "what phase are we in / did the probes run" as of 2026-07-29, and
a single day's results made **nine** of them wrong at once. The list below is the whole surface. It
is not documentation of a good design; it is the blast radius, written down so the grep is bounded:

| File | What it asserts |
|---|---|
| `docs/product/PHASE_05_RESULTS.md` | **Source of truth.** Probe numbers, gates, branches taken. |
| `docs/product/ROADMAP.md` | Phase status line, entry/exit gates, schedule risk flags |
| `AGENTS.md` (*Validation Notes*, *Project Context*) | Current phase, primary models, what's built vs specced |
| `docs/MASTER_SPEC.md` §"un-run" | Which unknowns are still blocking |
| `docs/TECH_STACK.md` §8 | Known gaps / unverified |
| `docs/WORKFLOW.md` §"Right now" | The single next action |
| `docs/capstone/methodology.md`, `research_direction_and_goals.md`, `design_decisions_and_risks.md` | Phase table, contingency framing, sequencing branches |
| `backend/.env.example` | Which model overrides are live |

**Rules:**
- **Point, don't copy.** A doc that needs a probe result links to `PHASE_05_RESULTS.md`; it does not
  restate the number. Restating creates the tenth copy and the tenth rot site.
- **Do not add a file to this table.** A new doc asserting current state must instead link to one
  that already does. If you genuinely need a tenth, the right change is deleting one of the nine.
- **Capstone docs are the easiest to forget and the worst to get wrong** — they're the submitted
  artifact. They are last in the grep and first in the consequences.
- A gate with **N criteria has 2^N outcomes.** Pre-registered branch tables must enumerate all of
  them, or say which they're ignoring. Probe 1's table wrote 2 of 4 and the project landed on one of
  the missing two (identity held, separation failed) with no pre-committed action.

---

## Validation Notes
- CI added 2026-07-29 (`.github/workflows/ci.yml`): runs the pre-merge verify commands verbatim.
  Not yet a *gate* — `main` has no branch protection requiring the check.
- `ruff format` is not adopted — only `ruff check` is. See comment in `backend/pyproject.toml`
  for rationale (single repo-wide formatting commit, never inside a feature change).
- **Current phase: Phase 2 (Safety / Classroom) — in progress.** Phase 0 ✅ done. Phase 1 ✅ complete.
  Phase 0.5 ✅ closed 2026-07-29 — Probe 1 resolved (Qwen stays primary, ADR-001 amendment; missed
  separation gate carried as stated limitation), Probe 3 PASS; Probes 2 and 4 not run and neither
  gates Phase 1. Numbers in `docs/product/PHASE_05_RESULTS.md`.
  **`story-memory-contract` is built (2026-07-29):** `backend/contracts/story_memory.py` exists,
  `job_state.py` deleted, seven nodes on partial-return, `input_gate` is the graph entry point.
  **`story-analyzer` is built (2026-07-29):** `pipeline/analyze.py` mints `characters[]` (≤3),
  `locations[]`, `objects[]`, `timeline[]`.
  **`scene-segmentation` is built (2026-07-29):** `pipeline/segment.py` splits into ≤15 scenes,
  enforces verbatim excerpts, maps roster names → char_ids, sets `caption = text_excerpt` (ADR-013).
  **`character-bible` is built (2026-07-30):** `pipeline/char_bible.py` mints ≤2 canonical references
  (ADR-004), judges each against its `CharacterDescription` with a 3-draw cap and best-of fallback
  (ADR-028), persists `ref_verdict` — failing verdicts included — and bumps `cost.image_count`.
  Added `settings.default_style_fragment` (ADR-022 `cel`). CC-1 is **not** closed for the char-ref leg.
  **`prompt-optimizer` is built (2026-07-31):** `pipeline/prompt_optimizer.py` — `build_prompt` (wired
  into `generate_scene`, replacing the `caption`-stub prompt line) and `correct_prompt` (pure, no
  caller yet — `regeneration-controller` wires it in when that spec lands). `contracts/` untouched.
  **`image-generator` is built (2026-07-31):** `generate_scene` is reference-conditioned —
  `edit_image` when `canonical_ref_image` is present for a character, `text_to_image` otherwise.
  Fixes `scene-1.png` Storage-path collision (now `{story_id}/{scene_id}.png`). ADR-025 D4 breaker
  live at `IMAGE_BUDGET = 45` (was 39; the prelude went 9 → 15 with `reference-moderation-retry`).
  CC-10 Storage-exists skip (idempotent resume). `final_image_ref`
  ownership transferred to `consistency_check`. `MAX_SCENES` and `IMAGE_BUDGET` in `app/config.py`.
  **`consistency-checker` is built (2026-07-31):** `pipeline/consistency_check.py` judges each scene
  image against the canonical reference each present character was drawn from — one `providers.judge`
  call per character (ADR-004) — folds the verdicts worst-wins, gates on
  `same_character and anatomy_intact` (`style_match` recorded but non-gating), and finalizes every
  scene: pass, fail, or unchecked. Takes `final_image_ref` ownership from `generate_scene`.
  `route_next_scene` (in `graph.py`) closes ADR-024's per-scene loop — the graph's first conditional
  edges. `contracts/` untouched. Open gaps passed to `regeneration-controller`: the anatomy
  correction gap, the ADR-010 retry branch, and `recursion_limit` — all now discharged. CC-3 judge
  calls remain uncounted by `Cost` (widened to up to 4 per scene by `regeneration-controller`).
  **`regeneration-controller` is built (2026-08-02):** `pipeline/regenerate.py` implements
  ADR-010's one corrected retry; `consistency_check` gains `_rank`, the three-term finalize rule
  (`passed or verdict is None or len(attempts) >= 2`), and reverse-ordered best-of selection;
  `route_after_check` closes the consistency pass/fail branch (ADR-003); `recursion_limit` set to
  `MAX_SCENES * 4 + 9 = 69`; `correct_prompt` gains `same_character` / `anatomy_intact` booleans
  and `IDENTITY_CLAUSE` / `ANATOMY_CLAUSE` fixed strings; per-attempt Storage path
  `{story_id}/{scene_id}-{n}.png`. `contracts/` untouched.
  **`compose` is built (2026-08-02):** `pipeline/compose.py` implements the terminal gate — asserts
  ≥1 scene and every scene finalized (raise → job `failed`), classifies each page by the attempt
  that won, emits the one per-book summary log line. Returns `{}`. `contracts/` untouched.
  **Every Phase-1 feature spec is now built.**
  **`moderation-stack` is built (2026-08-02):** `pipeline/input_gate.py` (real implementation —
  meta-llama/llama-guard-4-12b OpenRouter API + Presidio PII redaction concurrent, OpenRouter backstop);
  `pipeline/char_ref_mod.py` (qwen/qwen3-vl-32b-instruct + Gemma safety rubric, two-classifier check per char ref);
  `pipeline/output_mod.py` (same two-classifier check + soften-and-retry on each output scene).
  `moderation_router` and `route_after_output_mod` added to `graph.py`. `providers.py` gains
  `get_signed_url`, `_parse_guard_response`, and five moderation provider functions.
  **`input-gate-hardening` is built (2026-08-02):** supersedes the `filipino-pii-recognizers` stub and the
  `length-guard` row. `app/length.py` `clamp_story` (ADR-012 cap, paragraph→sentence boundary with a
  retains-half floor) + a minimum-length 422 at `POST /storybooks`; `ph_recognizers.py` adds Tagalog
  marker patterns and the structured PH identifier recognizers, wired into `providers._presidio`;
  `redact_pii` pseudonymizes `PERSON`/`PH_PERSON` so `redacted_text` survives as a narrative.
  Migration `0003_jobs_truncated.sql`. Stock Presidio no longer ships bare.
  **`kid-flow-ui` is built as four specs (2026-08-02 → 2026-08-04)** — docket
  `docs/specs/kid-flow-ui-docket.md` is DONE. **S1 `kid-flow-book-persistence`:** a book is the ordered
  JSONB `jobs.pages` array of `{scene_id, caption, image_path}` (migration `0004`, durable Storage paths
  only); `run_job.py`'s `_finish` is the **only** writer of `pages` *or* `reveal`, atomically with the
  terminal status; `compose` stays pure. **S2 `kid-flow-pause-lifecycle`:** ADR-029's reveal ships —
  `pipeline/reveal.py`, migration `0005` (`awaiting_confirm` + `jobs.reveal`), `POST /jobs/{id}/confirm`
  as the only exit from a pause (404 → 422 → CAS; duplicate/late/swept → 200 with current status), 3-tap
  cap in `route_reveal`, `SUPER_STEP_PRELUDE = 15` (now 17 — see `reference-moderation-retry`).
  **S3 `kid-flow-failure-semantics`:** three verbs only
  — `redraw` / `revise` / `retry`; a terminal job is immutable (recovery is always a new job); four render
  buckets on every URL-reachable surface; the child never sees a moderation category or `jobs.error`.
  **S4 `kid-flow-reader-and-wait-states`:** the multi-page reader over `jobs.pages` (sign at read time),
  the Realtime wait stepper off `current_stage`, the inline reveal on `/process/[jobId]`, four
  `FailureScreen` kinds, and `useJob` seeding from a `SELECT` **and** subscribing. No orientation lock.
  **`job-failure-reason` is built (2026-08-04):** migration `0006` (nullable, no check constraint) + the
  taxonomy map in `run_job.py` — `child_text` only where `moderation_router` raises for the input text;
  every other value, every unknown value and `null` → `machine`. (`0007` and `0008` are now claimed by
  the auth docket's specs — see below.)
  `contracts/` untouched by all five. Still exactly **two** policy surfaces.
  **`auth-and-classroom` is specced as four specs (2026-08-05 → 2026-08-06); S1, S2 and S3's migration
  are built, S4 is not** — docket `docs/specs/auth-and-classroom-docket.md` is DONE, 42 binding
  constraints.
  **S1 `auth-identity-and-classroom-schema`:** students are real `auth.users` rows reached by
  `{nickname}@{code}.students.storybuddy.invalid`, so Supabase owns all password material; role is
  `profiles.role` read through `auth_role()`; migration `0007` creates `classrooms` + `profiles` with RLS
  on and **zero** policies. **S2 `auth-session-model`:** one mechanism for all three roles —
  `signInWithPassword` → cookie via `@supabase/ssr`. Partly built: `supabaseClient.ts` is on
  `createBrowserClient` and `get_current_user` guards `POST /storybooks` and `/confirm`.
  **S3 `auth-authorization-surface`:** migration `0008` replaces **both** legacy policy surfaces; Storage
  is classroom-scoped by joining back to `jobs`, not by changing the frozen path shape; 33 isolation
  tests. **S4 `auth-routes-and-account-ux`:** flat → `/s/[profileId]`, a path-shaped `middleware.ts` guard
  that never reads the role (S1 keeps it in `profiles`, `ROUTE_MAP.md:196` bans DB reads in middleware),
  the three-step `/join` wizard, and the bookshelf query — which filters `profile_id` explicitly, because
  S3 grants students two SELECT policies on `jobs` and RLS alone does not scope it.
  **Built so far:** `0007` and `0008` both exist; `config.py`'s sentinels are retired and `run_job.py`
  reads ownership from the row; `app/nickname.py` + `lib/nickname.ts` share S1 §5.1's fourteen vectors;
  `supabaseClient.ts` is on `createBrowserClient`; `get_current_user` guards `POST /storybooks` and
  `/confirm`. **The two legacy policy surfaces are gone** — `0008` dropped them.
  **The Tier-A isolation suite (S3-13) is built:** `backend/tests/test_rls_isolation.py`, 39 test
  functions covering spec tests 1–25 (jobs, classrooms, profiles) and 28–33 (storage). Realtime
  tests 26–27 need a WebSocket client and are deliberately out of scope for pytest.
  ⚠️ **It does not run in CI.** Every case is `skipif`-gated on `SUPABASE_DB_URL`, which CI does not
  set, so ADR-017's "real, testable boundary" is backed by tests that only a human runs:
  `SUPABASE_DB_URL=postgresql://postgres:postgres@localhost:54322/postgres uv run pytest
  tests/test_rls_isolation.py` against a local Supabase with `0007` + `0008` applied.
  **`scene-setting-and-subject-binding` is built (2026-08-13):** one artifact class across five nodes.
  `contracts/` gains **two** additive fields — `Scene.location_id` and `VlmVerdict.subjects_unique`
  (both defaulted, no `schema_version` bump); `subjects_unique` is declared last so ADR-004's order
  holds, and best-of now ranks `same_character → anatomy_intact → subjects_unique → style_match`.
  `segment.py` maps `location_name` → `loc_id` with carry-forward through all eight `ExtractedScene`
  constructions, and deduplicates `characters_present`. `prompt_optimizer.py` folds each reference's
  attributes into its roll sentence, adds `SUBJECT_COUNT_CLAUSE` + `NON_HUMAN_CLAUSE` **outside**
  `REFERENCE_CLAUSE` (so both reach the text-to-image path), emits the `Setting:` line, and adds
  `filtered_location` — **ADR-035 surface 5**. `consistency_check.py` asks the judge a uniqueness
  question, folds it worst-wins and ranks on it, but **does not gate**: `passed` is byte-identical.
  `graph.py` untouched — no new edge. `JUDGE_PROMPT_VERSION` is a module constant, not an
  `Attempt` field (it was 2 here; `lettering-suppression` has since taken it to 3).
  ⚠️ **No job has been run against this code.** D1/D2 are unmeasured *and* un-eyeballed, the §4.3
  duplicate-`char_id` fix is a mechanism fixed on principle rather than a confirmed diagnosis, and
  the first `subjects_unique` data point does not exist yet — so §8.1's gating decision stays
  blocked. Deterministic evidence only.
  **`lettering-suppression` is built (2026-08-13):** Qwen-Image renders text by design and nothing
  in the pipeline could see it; three attempts to fix it by prompt wording failed, so this adds the
  missing DETECTION channel instead of a fourth prohibition. `contracts/` gains **two** additive
  fields — `RefVerdict.text_free` and `VlmVerdict.text_free` (both defaulted `True`, both declared
  LAST, no `schema_version` bump). Both judge prompts gain one question asked in schema order, and
  both version constants bump: `char_bible.JUDGE_PROMPT_VERSION` 3→**4**,
  `consistency_check.JUDGE_PROMPT_VERSION` 2→**3**. Unlike `subjects_unique`, this one **gates**:
  reference acceptance is `not contradictions and text_free`, scene `passed` is
  `same_character and anatomy_intact and text_free`, and best-of ranks
  `same_character → anatomy_intact → text_free → subjects_unique → style_match`.
  `prompt_optimizer.TEXT_CLAUSE` ("every surface in the picture is blank and unmarked") is appended
  by `correct_prompt` on a `text_free=False` keyword — a boolean, **not** an 8th `FailureReason`
  (ADR-028, still frozen at 7) — and deliberately names none of `NEGATIVE_PROMPT`'s terms.
  `graph.py`, `providers.py` (`NEGATIVE_PROMPT`) and `STYLE_PRESETS` untouched, so the change's
  effect stays attributable.
  ⚠️ **No job has been run against this code.** The lettering rate is unmeasured and the judge's
  false-positive rate on texture (wood grain, halftone dots) is unknown; spec §4.6.2 names the
  fallback in advance — demote `text_free` to rank-only, the shape `subjects_unique` already sits in.
  **`reference-moderation-retry` is built (2026-08-13):** a flagged character reference used to end
  the book outright — every other way a reference can be wrong buys 3 draws, a moderation flag bought
  0. Prod job `4feff195` died that way on a false positive (the backstop read a red half-vest as
  blood; a 6-draw probe reproduced the prompt and drew clean every time). Now it buys exactly one
  redraw. `char_ref_mod` **clears `canonical_ref_image`** on a flag — that clear is the entire
  mechanism, because `char_bible`'s existing filter re-mints precisely the cleared characters — and
  gains a skip for characters already `"passed"` so a second pass does not re-bill both classifiers.
  `moderation_router` gains one branch returning `"char_bible"` while
  `cost.ref_mod_retry_count < MAX_MOD_REDRAWS` (**= 1**, in `char_ref_mod.py`, imported by
  `graph.py`, mirroring `reveal.MAX_RETRY_TAPS`); past the cap it raises `ref_flagged` exactly as
  before. `contracts/` gains **one** additive field, `Cost.ref_mod_retry_count`, declared LAST and
  defaulted `0` (no `schema_version` bump), counted **per book, not per character** — both refs
  flagging spends one cycle. `mint_reference` gains an `n` suffix parameter so both minting paths
  share one monotonic per-book sequence (`rc + mrc + 1` post-bump; `_mint_targeted` keeps `+2`
  pre-bump), which is what preserves the flagged PNG as evidence for the still-missing
  `tests/fixtures/moderation_cases.py`. **Neither classifier loses its veto and neither rubric moves
  — what changed is the price of a flag, not the threshold for one.** Both budget constants were
  resized *with* their arithmetic: `IMAGE_BUDGET` prelude 9→**15**, `SUPER_STEP_PRELUDE` 15→**17**
  (this supersedes `kid-flow-pause-lifecycle` §4.13's "IMAGE_BUDGET unchanged" — see its banner).
  ⚠️ **No job has been run against this code**, and the backstop's image rubric is still
  **UNMEASURED**. Known gap, named in spec §4.6: a flag landing on a *tapped* redraw falls back to an
  untargeted mint and silently loses the child's tapped attribute.
  **Consistency hardening from prod job `483056e0` (2026-08-13):** three fixes across two nodes, no
  `contracts/` change, no new spec — the existing two specs were amended.
  **(A) `segment` name recovery** (`scene-segmentation.md` §4.6): a roster name the model omitted
  from `characters_present` is recovered from the excerpt by word-boundary match and **appended**
  (article stripped, case-insensitive, routed through `name_to_id` so §4.3 path 2's first-seen-wins
  survives). Job `483056e0` lost the dragon on `s1`/`s2` — `refs=0`, so both drew via
  `text_to_image` **and** then filed unchecked. Those two failures compound and this closes both at
  the source.
  ⚠️ **(A) was REVERSED on 2026-08-14 by `visual-continuity` §4.3** — the unconditional recovery is
  gone, because a name in an excerpt does not prove the character should be *visible*, and
  over-recovery was drawing merely-mentioned characters onto the page. `characters_present` is now
  the sole cast authority; the regex survives as `_names_character`, rejecting a `visual_direction`
  that names a character outside the cast. The unchecked-page half of the original failure is now
  covered instead by §4.6's scene-constraint judge, which runs on every attempt including
  reference-free ones. See `scene-segmentation.md` → "Name recovery — removed".
  **(B) `GATING_REASONS`** (`consistency-checker.md`): `passed` gains
  `and not (GATING_REASONS & failure_reasons)` where the set is `{wrong_colour, wrong_body_feature}`.
  Job `483056e0` shipped `s3` and `s4` `passed=True` carrying those exact reasons — a green dragon
  is still `same_character=True`, so the seven-value set was inert for the one character with no
  face and no clothes. `wrong_clothing`/`wrong_style` stay non-gating (live false-positive stories).
  `FailureReason` stays frozen at 7 — this reads a **subset** at the gate, so Objective 4's F1 set is
  untouched. `_rank` widens to seven terms, `attributes_ok` last among the gating axes.
  **(C) CC-5:** an unchecked page now logs `unchecked=no_subjects` vs `unchecked=judge_failed`.
  They finalize identically and called for opposite responses, and in prod the first read as the
  second.
  ⚠️ **No job has been run against this code.** The redraw rate (B) and the over-recovery rate (A)
  are both unmeasured; each spec names its pre-registered fallback (demote to rank-only; ask the
  judge instead of a regex). **The setting is untouched** — a location reaches the canvas only as
  `build_prompt`'s `Setting:` line, no location reference image exists, and the judge is never asked
  about place. That is a queued architectural decision, not a gap these three fixes narrow.
  ➡️ **That decision was made on 2026-08-15** by `setting-consistency` (docket S4): the answer is a
  frozen textual canon and no location image. See the entry below.
  **Drift fixed in passing:** `scene-segmentation.md`'s edge-case table still said a duplicate
  roster name maps to *every* matching `char_id`, and `prompt-optimizer.md`'s said the roll could
  read `"Image 1 is the star. Image 2 is the star."` Both described the pre-§4.3 list-valued map;
  `segment`'s `name_to_id` has been `setdefault` first-seen-wins since
  `scene-setting-and-subject-binding` §4.3. Both rows now say so.
  **Two residuals closed (2026-08-13, follow-up):** (1) `correct_prompt` **drops** a clause whose
  every placeholder is empty and floors on `IDENTITY_CLAUSE` if that empties the correction —
  reachable as a page's SOLE correction only since (B) made `wrong_colour` gating, and the judge
  compares against the reference image so it can flag a colour `analyze` never recorded.
  `regenerate` invariant 5 now rests on that floor rather than on `failure_reasons` being non-empty.
  (2) `SEGMENTATION_PROMPT` gained a pronoun rule, the layer §4.6's regex structurally cannot
  reach — free, and the two fail in opposite directions. Since (A)'s reversal the pronoun rule is
  the only text-side layer, and it now also carries §4.3's visible-only qualifier. **Cast
  carry-forward was considered and rejected**: an empty cast is a pronoun beat *or* a scenery page,
  and inheriting draws a character into the scenery one. Revisit on `refs=0` in the logs.
  **The canonical reference is drawn at an angle, not head-on (2026-08-13, follow-up):**
  `REFERENCE_PROMPT`'s ~~"facing forward"~~ → **"seen from a slight angle rather than straight on"**,
  with `back view, seen from behind` added to `REFERENCE_NEGATIVE` for the overshoot. Head-on
  foreshortens away the snout, neck, tail and wing profile of a snouted or long-bodied subject, so
  the reference anchored least of the character it matters most for — job `483056e0`'s dragon came
  back front-facing and all 9 pages inherited it, pose included. **Unconditional**, on the same
  reasoning as the non-human clause: a "has a snout" test is the species word list that clause
  rejects and it is wrong on "the star" first. Not "three-quarter view" — model-sheet vocabulary the
  negative already suppresses. No `JUDGE_PROMPT_VERSION` bump (draw prompt only). ⚠️ The new risk is
  **occlusion of a stated attribute** ("a scar on its left cheek"), which `JUDGE_PROMPT` does not
  absolve the way it absolves unmentioned detail; fallback is to weaken the turn, not revert.
  Unmeasured. **Drift fixed in passing:** the whole 2026-08-13 framing and `REFERENCE_NEGATIVE`
  design existed only in code comments and tests — `character-bible.md` §4 now carries it, including
  the positive/negative division of labour and the ordered list of measured phrasings.
  **`comic`'s halftone is scoped to backgrounds and shadows (2026-08-14):** one clause in
  `STYLE_PRESETS`, no migration, no ADR, no contract change. The picker sample
  `frontend/public/style-presets/comic.png` is the evidence — the screen lands on the character's own
  body and tail, with thin limbs collapsed to solid black on a green character while one arm stayed
  outlined green. Two gates that landed 2026-08-13 both read that surface: `wrong_colour` is in
  `GATING_REASONS` and a halftone tints by dot density (one fill, two colours across reference and
  page scale), and `text_free` gates while `lettering-suppression.md:216` names halftone dots as the
  expected judge false positive. `comic` was the only preset feeding either.
  **The halftone is scoped, NOT removed** — ADR-022 makes `comic` the *gating primary* substrate
  because it is "textured enough (halftone) that the no-reference baseline can't fake the separation
  gate" (`docs/product/adr/ADR-022-selectable-art-style-presets-three-prompt-fragment.md`,
  "Choosing the three"; pre-registered `PHASE_05_RESULTS.md:512`), so deleting it would make that
  gate lenient retroactively. **The outline clause is untouched on purpose:** "of varied weight" is
  the obvious suspect for the black limbs and is the one thing that must not be pinned — `cel` lost
  "of even weight" the day before because pinning uniformity is what smooshes thin elements.
  ⚠️ **No job has been run against this fragment**, and it contradicts a recorded result: Probe 1's
  secondary arm scored `comic` identity **75%** — the *best* of the three, against `cel` 60% and
  `gouache` 40% (`PHASE_05_RESULTS.md:532-534`) — so the case for this change rests on the two new
  gates and on direct inspection of the sample, not on that table. **`comic.png` is now stale** (drawn
  with the unscoped fragment, overstates the texture); regenerating it is a paid fal draw and is NOT
  done. `backend/spikes/phase_05.py:47` keeps the old fragment deliberately — it is the record of
  what Probe 1 ran.
  **`judge-finetune`'s PRODUCER half is built (2026-08-14) — the fine-tune itself is NOT run.**
  `backend/finetune/`: `corpus_synthetic.json` (30 static stories, 39 characters, 69% non-human — checked
  in, so the train corpus is hashable for CC-7), `build_corpus.py` (drives the **existing** graph, spend-capped,
  resumable via `data/judge/build_state.json`), `manifest.py`, `build_dataset.py`, `to_llamafactory.py`,
  `train_qlora.yaml`, `evaluate.py`. `contracts/` untouched; no migration written.
  **§5.4's "open reconciliation item" was drift, not a decision** — `RESEARCH_PROTOCOL.md` §8 already said
  *"researcher-written stories appear only as judge-training-split augmentation, never as evaluation
  stimuli."* Train+val are synthetic, **test is donated-only and `manifest.py`'s guard enforces it**.
  §5.2's record gained `provenance` and the two GATING booleans `anatomy_intact`/`text_free` — the spec
  predated them and a judge trained to emit `True` unconditionally would break the loop while scoring well.
  **That adds two checkboxes and two columns the `annotations` table does not have**, and §4 makes this the
  last free moment to add them. Pre-registration: `docs/product/PREREGISTRATION_OBJ4.md` (2026-08-14).
  ⚠️ **Nothing has been run.** No fal draw, no training run, no `llamafactory-cli` invocation;
  `train_qlora.yaml` ships `model_revision: PIN_THE_EXACT_COMMIT_HASH` as a deliberate tripwire, so CC-7 is
  unmet until a human fills it. `evaluate.py` omits McNemar's exact test (needs scipy) — the char-clustered
  bootstrap CI is implemented. Deterministic evidence only.
  **`annotation-surface`'s TABLE is built (2026-08-14) — neither route is.** `0014_annotations.sql` ships the
  `annotations` table `build_dataset.py` already reads, with the closed-taxonomy CHECK, the two GATING columns
  `anatomy_intact`/`text_free` (`judge-finetune.md` §5.2 amendment — the last free moment to add them per §4),
  and two RLS policies scoping select+insert to `annotator_id = auth.uid()` for `researcher` profiles. **No
  `update`/`delete` policy** — §4's forward-only rule makes a submitted row final, so a double-submit is
  `on conflict do nothing`, not an upsert. `backend/tests/test_annotations_rls.py` is 16 `skipif`-gated cases.
  `contracts/` untouched — `FailureReason` stays frozen at 7 and the `label = not same_character` inversion
  stays in `build_dataset.build_records` alone.
  ⚠️ **`annotate/` and `adjudicate/` are BLOCKED, not skipped** — two schema questions the spec does not
  answer, logged as **D-K** (nothing maps `pair_id` → the two Storage paths; the pairs live only in the
  LangGraph checkpoint blob) and **D-L** (§2.1's "adjudicator flag" has no column) in `DECISION_BACKLOG.md`
  Tier 2e. ⚠️ **The RLS suite has not been run against any database** — `SUPABASE_DB_URL` is set but
  unreachable from the build host, so all 16 skipped.
  **`pose-viewpoint-composition` is built (2026-08-15) — prompt/ranking semantics only, no new
  code path.** The docket's S3. `contracts/` untouched — **no** new field, no `schema_version` bump,
  no node, no edge, no reference, no extra judge or draw call; `Scene.visual_direction` stays the
  sole pose/viewpoint source. Three changes: (1) `consistency_check.JUDGE_PROMPT` gains a
  viewpoint-tolerance paragraph **before** the verdict questions — rear/profile/foreshortened/
  occluded views can be the same character, and a feature the requested viewpoint hides is not
  `wrong_body_feature`/`different_face`/`character_absent` — so
  `consistency_check.JUDGE_PROMPT_VERSION` 3→**4** (ADR-004 field order byte-unchanged; **v3 and v4
  counts never pool**, BC-6). (2) `prompt_optimizer.COMPOSITION_CLAUSE` is appended **last** by
  `correct_prompt` whenever any correction fires, on all four paths, so no retry path can be
  composition-destructive; a no-op call is still byte-identical. (3) `_rank` reorders to
  **composition-first**: `checked → no scene contradictions → fewer of them → same_character →
  anatomy_intact → text_free → attributes_ok → subjects_unique → style_match`, so a
  composition-clean attempt beats an identity-clean one that contradicts the story.
  ⚠️ **Nothing here is validated against real images**, and Tier B was declined — the policy
  changed, pose/viewpoint QUALITY is unmeasured and unclaimed. The known instrument limit stands:
  the scene judge missed the observed movement-direction defect **4/4** under prompt v1 and v2, so
  composition-first ranking is only as good as contradictions it never emits. `settings.vlm_judge_model`
  untouched (BC-4); `graph.py`, `providers.py`, `app/config.py`, `regenerate.py` untouched.
  **`setting-consistency` is built (2026-08-15) — text canon only, no location artifact.** The
  docket's S4. `analyze.ExtractedLocation.description` becomes a required non-blank `str` at the
  transient LLM boundary while persisted `Location.description` stays `Optional[str]` so old
  checkpoints deserialize; `EXTRACTION_PROMPT` must copy stated permanent facts, invent missing
  permanent detail once, and exclude weather/lighting/time/damage. `SCENE_CONSTRAINT_PROMPT` now
  checks the `Setting:` line's name and permanent description and reports only concrete violations,
  so `SCENE_CONSTRAINT_PROMPT_VERSION` 2→**3** (**v2 and v3 counts never pool**, BC-6).
  ⚠️ **No location reference image, node, edge, provider call, contract field, location cap, or
  budget term** — a setting failure gates through the existing `scene_contradictions` path.
  ⚠️ Tier B declined: no paid run, and no claim that setting consistency improved. Residual: the
  judge compares each page to the canon, never page-to-page, and a hallucinated permanent detail
  becomes canon (S2's freeze-once posture, inherited without provenance).
  **`spend-and-retry-economics` is built and ratified as ADR-037 (2026-08-15) — length traded for a
  third attempt.** The docket's S5, and the docket is now **DONE throughout**. One coupled policy:
  `MAX_STORY_WORDS` 800→**300**, `MAX_SCENES` 15→**10**, new `MAX_SCENE_ATTEMPTS = 3` (initial draw
  + two corrected retries, ADR-037 amending ADR-010's one), `IMAGE_BUDGET = MAX_SCENES * 4 + 15` =
  **55**, `RECURSION_LIMIT = MAX_SCENES * 7 + 17` = **87**. ⚠️ **The two preludes (15 images, 17
  super-steps) stay unequal on purpose** — different units, only ever coincidentally equal
  (`test_config.py`). ⚠️ **The old `* 2` was already wrong**: `output_mod`'s softened redraw was
  paid but never counted or breakered. That hole is closed — every paid fal site now calls one
  `app.config.check_image_budget()` helper (ADR-025 D4), and the worst-case structural spend *fell*
  60 → 55 despite the extra attempt. No node, edge, router label, provider, model, contract field,
  or `schema_version` bump; retry allowance stays derived from `len(scene.attempts)`. `MAX_DRAWS`,
  `MAX_MOD_REDRAWS`, `MAX_RETRY_TAPS` untouched. Judge/classifier calls remain absent from `Cost`
  **by decision** — they do not weaken the paid-image breaker. ⚠️ **No evidence a third attempt
  improves consistency** (BC-1); this is product policy, not a measurement.
  **Phase 2 is in progress. Next: D-K + D-L, then the two routes.** Next free migration is
  **`0015`** — ⚠️ `0014` is the highest on disk and **`0009` is used twice**
  (`0009_avatar_id.sql`, `0009_teacher_identity.sql`). That collision is **left alone deliberately**: both
  were hand-run under those names and this directory records what a human executed, so renaming them would
  trade a visible collision for an invisible lie (rationale in `0014`'s header). Do not add a third.
- classroom-sharing (2026-08-09): gallery page + StudentTabBar built; `/s/[profileId]/gallery` live; tab bar covers Bookshelf / Gallery / Profile; logout moved to settings.
