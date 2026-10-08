# StoryBuddy Agents Configuration

Last reviewed: 2026-10-09

## Baseline Rules
Codex and Claude Code both work this repo. Where the reading agent's own global rules are
stricter, the stricter rule wins.

- **Think before coding.** State assumptions. Search the whole repo before calling anything dead.
  Read the code you are changing rather than inferring it.
- **Simplicity.** Does it need to exist → does stdlib or the platform cover it → does an installed
  dependency cover it → minimum code that works. No abstraction with one implementation.
- **Simplicity stops at correctness.** Input validation at trust boundaries, error handling that
  prevents data loss, and security measures count as requested.
- **Reuse before writing.** One source of truth per fact: a fact that changes changes everywhere it
  is stated, in the same change.
- **UI is exempt from cutting.** Loading, empty, error, and disabled states; a way out of every
  view; confirmation before a destructive action; keyboard navigation and accessible names.
- **Surgical changes.** Every changed line traces to the request. Match existing style. Remove only
  the orphans your own change created.
- **Approval gates.** New dependency, service, or datastore; schema or API contract change; auth,
  billing, or infra; more than three modules; hard to reverse.
- **The code wins.** A plan or doc the codebase contradicts is not a spec to satisfy. Deviate, name
  what you found, flag the drift.
- **Evidence over inference.** A bug gets a command that goes red on it and two or more candidate
  causes before a fix. Label what is measured and what is hypothesis.
- **Verify before done.** Never claim complete without running the check and showing its output.
  A subagent's report is a claim until its diff or output is checked.
- **Tests prove behavior.** Each new test fails for the intended reason first. Expected values are
  hand-worked, never computed by the code under test. A skipped, deleted, or loosened test leaves
  the task unfinished.
- **Security.** Never read `.env` or secret files. Never echo credentials. Stop at the login wall
  and hand it back.
- **Commits.** No co-author or generated-by trailers.

## Project Context
- **A capstone study, not only a product.** `docs/capstone/` is the submitted artifact. Product
  status and research (Objective 4) status are separate surfaces; see Definition of Done.
- Architecture: Frontend (Vercel) posts to FastAPI (Northflank), which writes a job row and returns.
  A separate RQ worker runs the LangGraph pipeline, checkpointing to Postgres after each scene; the
  frontend watches the job row over Supabase Realtime.
- Graph (`backend/pipeline/graph.py`, 11 nodes): `input_gate → analyze → segment → char_bible →
  char_ref_mod → reveal → generate_scene → consistency_check ⇄ regenerate → output_mod → compose`.
  `output_mod` runs **inside** the per-scene loop and hands back to the next scene, so a flag stops
  spend at that scene. Two capped loops return to `char_bible`: `reveal`'s `try_again` (3 taps,
  `MAX_RETRY_TAPS`) and one redraw of a moderation-flagged reference (`MAX_MOD_REDRAWS = 1`).
  `reveal` holds the graph's only `interrupt()`. Export is cut from scope (ADR-058).
- The worker's checkpointer uses the Supabase **direct connection (5432)**, never the 6543 pooler
  (ADR-033). Adding worker replicas is a database decision.
- Critical paths, extra review: moderation ordering (input text → char-ref → output image, ADR-011);
  Presidio PII redaction before storage, captioning, or export; RLS and signed URLs (ADR-006); job
  checkpoint/resume (ADR-005, ADR-033); anything in `backend/contracts/`.

## Documentation Map
- Always read: `docs/MASTER_SPEC.md` (how the pieces connect; §5 cross-cutting concerns, §6 test
  split), and the module's spec in `docs/specs/` before building it.
- Read when:
  - Changing or relying on an architectural decision → `docs/product/ADRs.md` (current status of
    every ADR; frozen, see Hard Rules)
  - Hitting an undecided architectural question → `docs/product/DECISION_BACKLOG.md`
  - Visual styling or UI/UX → `DESIGN.md`
  - Mobile layout → `docs/MOBILE_GUIDELINES.md`
  - Product behavior or user flow → `docs/product/PRD_v2.md`
  - Current phase or build order → `docs/product/ROADMAP.md`
  - Probe numbers and Phase 0.5 gates → `docs/product/PHASE_05_RESULTS.md`
  - Choosing a tool or session size → `docs/WORKFLOW.md`
  - Research objectives or how they are measured → `docs/capstone/research_direction_and_goals.md`,
    `docs/capstone/methodology.md`
  - Explaining the project to a group member → `docs/capstone/group-guide.md`
  - Recording a research decision, deviation, or finding → `docs/capstone/research-changelog.md`
  - Merging a PR → `CHANGELOG.md` (each PR adds its entry in the same PR)
  - Anything touching the VLM judge or the Objective-4 chain (`backend/finetune/`) →
    `docs/specs/judge-finetune.md`, `docs/specs/annotation-surface.md`,
    `docs/product/PREREGISTRATION_OBJ4.md` (frozen), `docs/capstone/research_runbook.md`
  - Changing the Story Memory schema → `docs/specs/story-memory-contract.md`, ADR-023/024
  - Next.js APIs → `frontend/AGENTS.md` (Next 16 differs from training data; read
    `node_modules/next/dist/docs/`)
  - DB schema → `supabase/migrations/`
- `.worktrees/pipeline-hardening/` is a second full checkout, `AGENTS.md` included, and
  `brag-output*/` hold generated projects with their own agent files. Repo-wide searches hit them;
  a hit there is not this branch's state.
- Where a doc above answers the question, it outranks commit messages, roadmap history, and any
  skill that fires on its own. Design skills are reviewers, not requirements.

## Commands (Use Exactly)
Two projects, no shared root tooling. Run each from its directory.

### Frontend (`frontend/`)
- Install: `pnpm install --frozen-lockfile`
- Lint: `pnpm lint`
- Build/Typecheck: `pnpm build`
  CI runs it between lint and test with placeholder `NEXT_PUBLIC_SUPABASE_URL` /
  `NEXT_PUBLIC_SUPABASE_ANON_KEY` (`ci.yml:27-30`). Skipping it locally is how a type error
  reaches CI.
- Unit tests: `pnpm test`
- Single test: `pnpm exec vitest run path/to/file.test.tsx` (path relative to `frontend/`)
- Dev: `pnpm dev`

### Backend (`backend/`)
- Install: `uv sync --frozen`
  Not optional. Bare `uv sync` rewrites `uv.lock`, exits 0, and the drift fails the Northflank build
  with "Commit could not be built".
- Lint: `uv run ruff check .` (`ruff format` is deliberately not adopted; see `pyproject.toml`)
- Unit tests: `uv run pytest`
- Single test: `uv run pytest tests/test_x.py -k "case_name"`
- Provider smoke tests, before any deploy that changes a model ID, base URL, or provider:
  `uv run pytest -m "smoke and not smoke_image"` (free pings), `uv run pytest -m smoke` (adds one
  paid fal draw). Deselected by default; never in CI.
- Web: `uv run uvicorn app.main:app --reload`
- Worker: `uv run python -m worker.run_worker`
  Must be the `-m` form. `python worker/run_worker.py` dies with
  `ModuleNotFoundError: No module named 'app'`.

### Pre-merge verify
- Frontend: `pnpm lint && pnpm build && pnpm test`
- Backend: `uv run ruff check . && uv run pytest`

## Tooling Lock
- Frontend: **pnpm only**. Never npm, yarn, bun.
- Backend: **uv only**, `uv run <cmd>` from `backend/` (Python ≥3.12, `backend/.venv`). Never bare
  `pip install`, poetry, pipenv, or a global install.

## Testing Contract
- Passing: the pre-merge verify above, which is what `.github/workflows/ci.yml` runs on PRs to and
  pushes to `main`. No branch protection, so CI reports but does not block merge.
- Deterministic tests mock every `backend/providers.py` call and never assert on generated content.
  Fuzzy quality belongs to the offline eval harness, never CI.
- Smoke tests are the third kind: real providers, assert reachability and contract only. Every
  past outage of the "CI green, every job fails" class was a model ID or provider the mocks hid.
- Skip by design: `tests/test_rls_isolation.py` and `tests/test_annotations_rls.py` need
  `SUPABASE_DB_URL` pointing at a reachable local Supabase; `tests/test_smoke_providers.py` needs real
  credentials. The RLS suites have never run in CI, so the isolation boundary is human-verified only.
- Mock boundary: `backend/providers.py` (OpenRouter, fal.ai, Presidio, Storage). Everything inside
  the graph runs for real.

## Hard Rules
- **ADRs are frozen.** Do not refactor around a decision, swap a library, or reshape the pipeline
  because another approach looks cleaner. To change one, write
  `docs/product/adr/ADR-0NN-<kebab-title>.md` plus its row in `ADRs.md`, flag it, and wait for
  acceptance. A task that seems to require violating an ADR → stop and surface it.
- **Architectural questions get their own session.** One that comes up while building is logged to
  `docs/product/DECISION_BACKLOG.md`, not settled in code.
- **Open-weight models only** (ADR-015). Never reach for Gemini/GPT/Claude to make a node work.
  Never adopt a FLUX.1-dev-based adapter (InstantCharacter, DreamO, UNO, ACE++, InstantID, PuLID):
  the wrapper license does not override the base.
- **Provider SDKs, endpoints, and keys live in `backend/providers.py` only.** Model IDs are
  env-overridable fields in `backend/app/config.py`, the only source of truth for them. Never
  hardcode either at a call site.
- **The only sanctioned fine-tune is the consistency judge** (ADR-018, base amended by ADR-061).
  A LoRA anywhere else → surface it, don't build it.
- **`settings.vlm_judge_model` is a pre-registered baseline.** Swapping it to fix a bad verdict
  moves the goalpost. The judge is a control signal, never an outcome measure (ADR-004).
- **Annotation is two raters plus owner adjudication**, reported as inter-rater agreement
  (`PREREGISTRATION_OBJ4.md` §12). Anything the pre-registration binds changes only by amendment.
- **Spec first.** No spec in `docs/specs/` → write it from `docs/specs/TEMPLATE.md` and get approval.
  Behavior change → update the spec in the same change. Plans go in `docs/specs/plans/` and are
  deleted once the module is built, tested, and its spec updated.
- **Child-facing safety.** No unmoderated generated image reaches a child, the pre-reveal
  character reference included. PII is redacted before storage, captioning, or export. RLS on every
  table, signed URLs for every asset, no public buckets. Failure and moderation screens get the same
  design care as success screens; the child never sees a moderation category or `jobs.error`.

## Project Invariants
- `backend/contracts/` (Pydantic `StoryMemory`) is the only channel between pipeline modules. Nodes
  are `(state: StoryMemory) -> dict` partial returns. A schema change updates the schema, its specs,
  and every consumer in one change. New fields are additive and declared last.
- Every LLM boundary uses strict `json_schema` structured output validated into Pydantic. On
  OpenRouter always send `provider.require_parameters: true` (ADR-002). That flag picks providers
  that accept `response_format`, not ones that honor it, so a reasoning model still breaks the
  schema; the guard is the model choice.
- Nodes are deterministic. Conditional edges exist only at moderation and consistency pass/fail,
  plus the two capped loops above (ADR-003). One pipeline node = one file in `backend/pipeline/`.
- Every length, page-count, and spend bound is a named constant in `backend/app/config.py`, never a
  literal at a call site. `IMAGE_BUDGET` and `SUPER_STEP_PRELUDE` are different units; do not move
  one because the other moved. Every paid fal call runs `check_image_budget()` first (ADR-025 D4).
- `settings.max_scene_attempts` is a field, not a constant: `finetune/build_corpus.py` lowers it.
  Read it at call time, never bind it at import.
- `SELECTABLE_STYLE_PRESET_IDS` is `{cel, gouache, cut_paper}` and also defines the corpus strata.
  `comic` stays in `STYLE_PRESETS` for Probe 1's record; `pixel` is a trial behind
  `enable_pixel_style` / `NEXT_PUBLIC_ENABLE_PIXEL_STYLE`. Adding either to the set changes the
  research dataset.
- Judge prompt versions (`JUDGE_PROMPT_VERSION`, `SCENE_CONSTRAINT_PROMPT_VERSION`,
  `SEGMENT_PROMPT_VERSION`) bump on any wording change, and counts from different versions never
  pool.
- `supabase/migrations/` is hand-run SQL with no CLI link: a record of intent, not of any database's
  contents. Confirm the schema exists in the target project before blaming app code. Triggers fire on
  INSERT only. `0009` is used twice on purpose (both were run under those names); never add a third
  duplicate. The next migration is the highest number on disk + 1.
- **A server layout that fetches data owns it.** Client pages receive it as props and never refetch
  in `useEffect`. Share server reads through a `cache()`-wrapped helper
  (`frontend/utils/supabase/teacher.ts`). Branch with `redirect()` in a server component, never
  `router.replace()` in an effect. `auth.getUser()` is a network call, not a JWT decode.
- **Middleware is the only auth gate.** A server component that answers "no user" with
  `redirect("/login")` loops 307s against `middleware.ts`; it must throw. A server Supabase client's
  `setAll` stays wrapped in try/catch (`frontend/utils/supabase/server.ts`). Only middleware
  refreshes tokens.
- Every async route segment ships `loading.tsx` and `error.tsx`. Without them the page renders
  blank, not slow.
- `jobs.input_text` is the raw pre-redaction story and RLS hands a whole approved row to any
  classmate. Classmate-facing surfaces select `title` only (`frontend/lib/displayTitle.ts`).

## Known Gaps
- `frontend/public/style-presets/comic.png` was drawn with the pre-2026-08-14 fragment and
  overstates the halftone. Regenerating it is a paid draw.
- A moderation flag on a *tapped* reference redraw falls back to an untargeted mint and loses the
  child's tapped attribute (`reference-moderation-retry` spec §4.6).
- Judge and classifier calls are not counted in `Cost`, by decision; only paid images are.

## Definition of Done
- Report the commands run, their results, what was verified and what was not.
- **A finding change has a wide blast radius.** A probe result, new ADR, amendment, model ID, or
  phase name: grep the repo for the old value and fix every hit in the same change.
- **Status surfaces.** Product status: `docs/product/PHASE_05_RESULTS.md` (source of truth),
  `ROADMAP.md`, `docs/MASTER_SPEC.md` §"un-run", `docs/TECH_STACK.md` §8, `docs/WORKFLOW.md`
  §"Right now", the three capstone docs (`methodology.md`, `research_direction_and_goals.md`,
  `design_decisions_and_risks.md`), `backend/.env.example`. Research status:
  `PREREGISTRATION_OBJ4.md`, `RESEARCH_PROTOCOL.md`, `docs/specs/annotation-surface.md`,
  `docs/capstone/research_runbook.md`. Point to these, never restate their numbers, and never add a
  new file that asserts current state. A finding that moves both tracks is grepped across both.
  Capstone docs are last in the grep and first in the consequences.
- In pre-registered docs (`PHASE_05_RESULTS.md`, `RESEARCH_PROTOCOL.md`, `PREREGISTRATION_OBJ4.md`)
  superseded prose is struck through and left visible, never deleted.
- A gate with N criteria has 2^N outcomes; a pre-registered branch table enumerates all of them or
  names the ones it ignores.
