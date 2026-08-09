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

Every decision in `docs/product/ADRs.md` is **frozen**. Do not refactor around a decision,
swap a library, or change the pipeline shape because a different approach seems cleaner.

- To change a locked decision: **write a new ADR** (append to `docs/product/ADRs.md`) stating
  context / decision / consequences / alternatives, and **flag it to the human**. Do not implement
  until the ADR is accepted.
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
  measured. Never put it in CI. It doubles as research instrumentation (LangSmith/Langfuse).

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
  ✅ **Now built (2026-08-02):** `input_gate` (Qwen3Guard-Gen + Presidio + OpenRouter backstop),
  `char_ref_mod` (Falconsai ViT + Gemma safety rubric), `output_mod` (same two-classifier check +
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
  `qwen/qwen3-32b` (text) + `google/gemma-3-27b-it` (VLM judge) via OpenRouter; Qwen-Image-Edit
  (image gen) via fal.ai. All vendor calls live in `backend/providers.py`.
  (evidence: `frontend/package.json`, `backend/pyproject.toml`)
- Architecture: Frontend (Vercel) posts to FastAPI (Railway), which writes a job row and returns
  immediately. A separate RQ worker runs the LangGraph pipeline, checkpointing to Postgres after
  each scene. Frontend watches the job row via Supabase Realtime.
  **Target shape** — `docs/MASTER_SPEC.md` §2 is canonical and finer-grained (it splits char-ref
  moderation, `regenerate`, output moderation, and `export` into their own nodes):
  `input_gate → analyze → segment → char_bible → [char-ref moderation] → generate_scene →
  consistency_check → [regenerate] → [output moderation] → compose → export`.
  **Built today** (`backend/pipeline/graph.py`):
  `input_gate → [moderation_router] → analyze → segment → char_bible → char_ref_mod →
  [moderation_router] → reveal → [route_reveal] → generate_scene → consistency_check →
  [route_after_check] → regenerate → consistency_check → … → output_mod →
  [route_after_output_mod] → compose`.
  `moderation_router` (ADR-024 pure router) handles both post-`input_gate` and post-`char_ref_mod`
  edges; `route_after_output_mod` reads `moderation_status="failed"` and raises.
  `char_ref_mod` runs Falconsai ViT + Gemma safety rubric on each canonical ref image.
  `reveal` (ADR-029) is effect-free and holds one `interrupt()`; `route_reveal` loops `"try_again"`
  back to `char_bible` and enforces the 3-tap cap.
  `output_mod` runs the same two-classifier check on each output scene, with one soften-and-retry.
  All provider calls (Qwen3Guard-Gen, Presidio, Falconsai, OpenRouter backstops) go through
  `backend/providers.py`; `get_signed_url` lives there too (Storage seam). `export` is not yet built.
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
- Intentional skips / known flaky: none documented yet.

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
- Job checkpoint/resume (LangGraph + Postgres) — ADR-005
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
  live at `IMAGE_BUDGET = 39`. CC-10 Storage-exists skip (idempotent resume). `final_image_ref`
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
  Qwen3Guard-Gen 0.6B CPU-resident + Presidio PII redaction concurrent, OpenRouter backstop);
  `pipeline/char_ref_mod.py` (Falconsai ViT + Gemma safety rubric, two-classifier check per char ref);
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
  cap in `route_reveal`, `SUPER_STEP_PRELUDE = 15`. **S3 `kid-flow-failure-semantics`:** three verbs only
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
  ⚠️ **Not built, and S3-13 says it is not optional:** the 33-test Tier-A isolation suite that is meant
  to ship *with* `0008`. Until it exists, ADR-017's "real, testable boundary" is again unbacked by a
  single test — the exact gap S3 was written to close.
  **Phase 2 is in progress. Next: S3's isolation suite, then build S4.** Next free migration is
  **`0009`**.
- classroom-sharing (2026-08-09): gallery page + StudentTabBar built; `/s/[profileId]/gallery` live; tab bar covers Bookshelf / Gallery / Profile; logout moved to settings.
