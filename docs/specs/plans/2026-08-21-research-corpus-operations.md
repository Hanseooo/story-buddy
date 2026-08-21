# Research Corpus Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the auditable, resumable path from approved stories to a frozen Objective-4 dataset while keeping Fal spend below the USD 30 campaign ceiling.

**Architecture:** Extend `finetune.build_corpus` instead of creating another generation path. Persist immutable run bundles under gitignored `data/judge/`, materialize their exact hashed assets into private Supabase Storage and `research_pairs`, then reconcile annotations and freeze the existing manifest/LLaMA-Factory outputs. Governance and paid-run gates remain explicit human operations.

**Tech Stack:** Python 3.12, Pydantic `StoryMemory`, LangGraph/PostgresSaver, Supabase Postgres + private Storage, Pillow, pytest, existing Next.js annotation surface.

**Spec:** `docs/specs/research-corpus-operations.md`

## Global Constraints

- Synthetic stories supply train and validation; donated stories supply held-out test only.
- Split by character lineage, never by pair; constructed negatives are train-only.
- Raw submissions and the identity/receipt ledger never enter this repository, Supabase research storage, logs, checkpoints, or model artifacts.
- Donated input requires guardian consent, child assent, manual PII redaction, and independent redaction review.
- `finetune.build_corpus` remains the only corpus caller of the production graph and Fal.
- Supabase Storage stays private; canonical references are PNG and scenes are WebP quality approximately 82 per ADR-027.
- USD 25 is the working allocation; USD 30 is the absolute campaign cap; uncertain billing stops the run.
- Do not change `backend/contracts/`, the annotation taxonomy, provider placement, model IDs, migrations, or public interfaces in this implementation. If execution proves one necessary, stop and open the relevant ADR/spec session.
- Never read `.env`; deterministic tests mock all provider and Supabase effects.

## File map

| File | Responsibility |
|---|---|
| `backend/finetune/corpus_io.py` | Validate sanitized intake and read/write immutable corpus run bundles and asset inventories. |
| `backend/finetune/build_corpus.py` | Drive the existing graph, enforce dollar reserves, persist completed memories, and quarantine uncertain runs. |
| `backend/providers.py` | Emit corpus-scoped Fal attempt/completion/failure events at the existing private `_run_fal` seam; ordinary product calls remain unchanged. |
| `backend/finetune/materialize_pairs.py` | Verify exact local bytes, upload idempotently, and insert deterministic blinded queue rows. No generation. |
| `backend/finetune/build_dataset.py` | Reconcile queue status from annotation truth and provide the freeze CLI over completed run bundles. |
| `backend/finetune/manifest.py` | Keep existing record validation and add only cross-bundle freeze guards that belong at the manifest boundary. |
| `backend/scripts/clear_research_pilot.py` | Privileged dry-run/confirmed pilot cleanup in the required deletion order. |
| `backend/scripts/corpus_storage_telemetry.py` | Measure the locked PNG/WebP storage design; remove the stale R2 recommendation. |
| `backend/tests/test_corpus_io.py` | Intake, bundle, inventory, and immutability tests. |
| `backend/tests/test_finetune_corpus.py` | Spend/resume/quarantine and fixture-run tests. |
| `backend/tests/test_providers.py` | Fal observer success/failure tests with the SDK and HTTP calls mocked. |
| `backend/tests/test_materialize_pairs.py` | Hash, MIME, upload, conflict, and idempotency tests. |
| `backend/tests/test_finetune_dataset.py` | Status reconciliation and freeze CLI tests. |
| `backend/tests/test_clear_research_pilot.py` | Dry-run, confirmation, ordering, and zero-count verification tests. |
| `backend/tests/test_corpus_storage_telemetry.py` | Mixed-format telemetry regression tests. |
| `docs/capstone/research_runbook.md` | Human gates, commands, stop rules, evidence capture, and school/cloud handoff. |

---

### Task 1: Governance gate and sanitized intake contract

**Files:**
- Create: `backend/finetune/corpus_io.py`
- Create: `backend/tests/test_corpus_io.py`
- Modify: `docs/capstone/story_donation_consent_and_assent_draft.md`
- Create: `docs/capstone/research_runbook.md`

**Interfaces:**
- Consumes: a controlled JSON record containing `donation_id`, `text`, `provenance`, `split`, approval booleans, `candidate_role`, and `withdrawal_state`.
- Produces: `IntakeRecord`, `load_intake(path: Path) -> list[IntakeRecord]`, and an operational approval checklist. It must not accept names, contact details, receipt codes, or raw submissions.

```python
class IntakeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    donation_id: str
    text: str
    provenance: Literal["synthetic", "donated"]
    split: Literal["train", "val", "test"]
    candidate_role: Literal["primary", "backup", "not_applicable"]
    guardian_consent: bool
    child_assent: bool
    manual_pii_redaction: bool
    independent_redaction_review: bool
    withdrawal_state: Literal["active", "withdrawn"]
    selection_frozen_at: datetime | None = None

def load_intake(path: Path) -> list[IntakeRecord]: ...
```

- [ ] **Step 1: Write failing intake tests** for rejection when any of `guardian_consent`, `child_assent`, `manual_pii_redaction`, or `independent_redaction_review` is false; reject donated train/val, synthetic test, duplicate IDs, unknown keys, blank text, withdrawn records, and primary/backup assignment made after `selection_frozen_at`.
- [ ] **Step 2: Run the focused test** from `backend/`: `uv run pytest tests/test_corpus_io.py -q`. Expected: collection fails because `finetune.corpus_io` does not exist.
- [ ] **Step 3: Implement strict Pydantic models** with `extra="forbid"`, `Provenance = Literal["synthetic", "donated"]`, `Split = Literal["train", "val", "test"]`, and `CandidateRole = Literal["primary", "backup", "not_applicable"]`. Put cross-field rules in one model validator; do not add fields to `StoryMemory`.
- [ ] **Step 4: Document the manual boundary** in the runbook: adviser/HCDC/school approval, receipt ledger location outside StoryBuddy, manual redaction plus second-person review, 10 primary + 5 backup freeze, withdrawal handling, and the rule that the draft cannot be administered until its remaining blanks and translations are institutionally approved.
- [ ] **Step 5: Run** `uv run pytest tests/test_corpus_io.py -q` and `uv run ruff check finetune/corpus_io.py tests/test_corpus_io.py`. Expected: PASS.
- [ ] **Step 6: Commit** `test/implementation/docs` together: `git commit -m "feat(research): validate sanitized corpus intake"`.

### Task 2: Immutable run bundles and zero-cost fixture mode

**Files:**
- Modify: `backend/finetune/corpus_io.py`
- Modify: `backend/finetune/build_corpus.py`
- Modify: `backend/tests/test_corpus_io.py`
- Modify: `backend/tests/test_finetune_corpus.py`

**Interfaces:**
- Produces: `AssetRecord(storage_path, local_path, sha256, mime_type, width, height, byte_length, kind)`, `RunBundle(memory, provenance, split, candidate_role, run_metadata, assets)`, `write_bundle(...)`, and `load_completed_bundles(...)`.
- Bundle layout: `data/judge/runs/<story_id>/memory.json`, `run.json`, `assets.json`; images continue under the existing `ref/` and `scene/` paths named by `local_image_path`.

```python
class AssetRecord(BaseModel):
    storage_path: str
    local_path: str
    sha256: str
    mime_type: Literal["image/png", "image/webp"]
    width: int
    height: int
    byte_length: int
    kind: Literal["ref", "scene"]

class RunBundle(BaseModel):
    memory: StoryMemory
    provenance: Literal["synthetic", "donated"]
    split: Literal["train", "val", "test"]
    candidate_role: Literal["primary", "backup", "not_applicable"]
    run_metadata: dict[str, str | int | float]
    assets: list[AssetRecord]

def write_bundle(root: Path, bundle: RunBundle) -> Path: ...
def load_completed_bundles(root: Path) -> list[RunBundle]: ...
```

- [ ] **Step 1: Add failing tests** proving a completed graph result is revalidated with `StoryMemory.model_validate`, atomically persisted via temporary file + `Path.replace`, reloadable, and immutable on identical rerun; differing bytes or metadata must raise `CorpusError` instead of overwrite.
- [ ] **Step 2: Add a failing zero-cost test** using the existing `FakeGraph`/`FakeSupabase`: `build(..., fixture=True)` must make zero provider/Storage calls, write a complete fixture bundle from checked-in/generated local fixture bytes, and pass on an identical rerun.
- [ ] **Step 3: Run** `uv run pytest tests/test_corpus_io.py tests/test_finetune_corpus.py -q`. Expected: FAIL on missing bundle API and `fixture` argument.
- [ ] **Step 4: Implement asset inspection** with `hashlib.sha256`, Pillow decode, and magic-byte checks (`image/png` for refs, `image/webp` for scenes). Encode WebP exactly once at quality 82 before hashing; never recompress an existing completed asset.
- [ ] **Step 5: Replace count-only `build_state.json` entries** with bundle completion references while preserving backward safety: legacy count-only entries are not trusted as complete and are quarantined with a clear message rather than silently skipped or regenerated.
- [ ] **Step 6: Add CLI `--fixture`**; it must be mutually exclusive with paid execution inputs and usable without Supabase/provider credentials. Keep the production graph path unchanged when absent.
- [ ] **Step 7: Run focused tests and lint.** Expected: PASS and fixture summary reports `images_spent=0`, `usd_high=0`.
- [ ] **Step 8: Commit:** `git commit -m "feat(research): persist immutable corpus bundles"`.

### Task 3: Dollar-denominated spend reserve and uncertain-billing quarantine

**Files:**
- Modify: `backend/finetune/build_corpus.py`
- Modify: `backend/providers.py`
- Modify: `backend/tests/test_finetune_corpus.py`
- Modify: `backend/tests/test_providers.py`

**Interfaces:**
- Produces: `SpendPolicy(working_usd=Decimal("25.00"), hard_usd=Decimal("30.00"), smoke_usd=Decimal("1.50"), conservative_call_usd=...)`, a corpus-scoped Fal event sink installed only by `build_corpus`, and per-run telemetry with attempted/completed/failed/uncertain call counts.

```python
@dataclass(frozen=True)
class SpendPolicy:
    max_usd: Decimal = Decimal("25.00")
    hard_usd: Decimal = Decimal("30.00")
    smoke_usd: Decimal = Decimal("1.50")
    conservative_call_usd: Decimal = Decimal("0.035")

_fal_event_sink: ContextVar[Callable[[str], None] | None] = ContextVar(
    "fal_event_sink", default=None
)
```

- [ ] **Step 1: Write failing tests** that a story starts only when its maximum remaining draws fit the reserve, three-story smoke cannot exceed USD 1.50, campaign spend cannot exceed USD 30, and a provider timeout marked billing-uncertain halts and quarantines without automatic retry.
- [ ] **Step 2: Run** `uv run pytest tests/test_finetune_corpus.py -q`. Expected: FAIL because the current cap is image-count-only and defaults to 40.
- [ ] **Step 3: Add the event sink at the existing seam:** `_run_fal` emits `attempted` immediately before `subscribe`, `completed` only after image bytes download successfully, and `failed_uncertain` for any exception after submission begins. Use a `ContextVar` defaulting to `None`, so production behavior and call signatures do not change and parallel runs cannot share counters.
- [ ] **Step 4: Implement the minimal spend policy** with `Decimal`, a required pinned conservative per-call price in run metadata, `--max-usd` defaulting to `25.00`, and an unconditional `30.00` ceiling. Retain an image counter for audit, not authorization.
- [ ] **Step 5: Derive the pre-story maximum** from existing `IMAGE_BUDGET`/graph retry caps; if it cannot fit, stop before graph submission. Preserve post-super-step checks as defense in depth.
- [ ] **Step 6: Treat uncertain billing as terminal for the invocation:** persist telemetry and quarantine state, print the reconciliation action, and return non-zero. Do not infer whether Fal charged.
- [ ] **Step 7: Run** `uv run pytest tests/test_providers.py tests/test_finetune_corpus.py -q` and lint both implementation files. Expected: PASS.
- [ ] **Step 8: Commit:** `git commit -m "feat(research): enforce fal campaign spend ceiling"`.

### Task 4: Exact asset and pair queue materialization

**Files:**
- Create: `backend/finetune/materialize_pairs.py`
- Create: `backend/tests/test_materialize_pairs.py`
- Modify: `backend/finetune/build_dataset.py` only if `Pair`/`mint_pair_id` must be imported without duplication.

**Interfaces:**
- Consumes: `load_completed_bundles()` and existing `pairs_from_memory()`/`mint_pair_id()`.
- Produces: `materialize(bundles, supabase, bucket="private_assets") -> MaterializeSummary` and CLI `uv run python -m finetune.materialize_pairs --data ../data/judge`.

```python
@dataclass(frozen=True)
class MaterializeSummary:
    uploaded: int
    skipped: int
    pairs_inserted: int

def materialize(
    bundles: Sequence[RunBundle], supabase: Any, bucket: str = "private_assets"
) -> MaterializeSummary: ...
```

- [ ] **Step 1: Write failing tests** for exact-byte upload, private storage paths, deterministic IDs, exact `canonical_storage_path`/`scene_storage_path`, no labels or model calls, pagination, and rerun idempotency.
- [ ] **Step 2: Add conflict tests:** same path with different hash, same pair ID with different paths, missing local file, hash/length/MIME/dimension mismatch, donated non-test, synthetic test, and incomplete bundle all fail before any insert.
- [ ] **Step 3: Run** `uv run pytest tests/test_materialize_pairs.py -q`. Expected: collection failure.
- [ ] **Step 4: Implement preflight-first materialization:** validate every bundle and asset before writes; query existing objects/rows; for an existing path download and hash the remote bytes, skipping only an exact match; fail before row mutation on a mismatch; insert rows using the hardened `0017_research_pair_blinding.sql` column names. This avoids a schema migration solely for hash columns. Never add a public bucket or signed URL to stored rows.
- [ ] **Step 5: On a database insert failure**, remove only objects uploaded by this invocation after verifying their exact paths; never delete pre-existing objects.
- [ ] **Step 6: Run focused tests and lint.** Expected: PASS.
- [ ] **Step 7: Commit:** `git commit -m "feat(research): materialize blinded annotation queue"`.

### Task 5: Annotation truth reconciliation and frozen export

**Files:**
- Modify: `backend/finetune/build_dataset.py`
- Modify: `backend/finetune/manifest.py`
- Modify: `backend/finetune/to_llamafactory.py`
- Modify: `backend/tests/test_finetune_dataset.py`
- Modify: `backend/tests/test_research_integrity.py`

**Interfaces:**
- Produces: `reconcile_pair_status(rows, adjudicator_ids) -> dict[pair_id, status]`, `freeze_dataset(data_dir, out_dir) -> FreezeReport`, and CLI flags `--reconcile-only` / `--freeze`.

```python
class FreezeReport(BaseModel):
    dataset_sha256: str
    counts: dict[str, dict[str, int]]
    adjudication_rate: float
    exclusions: list[str]
    pinned_versions: dict[str, str]

def reconcile_pair_status(
    rows: Iterable[dict], adjudicator_ids: set[str]
) -> dict[str, Literal["pending", "partially_annotated", "complete", "conflicted", "adjudicated"]]: ...

def freeze_dataset(data_dir: Path, out_dir: Path) -> FreezeReport: ...
```

- [ ] **Step 1: Write failing reconciliation tests** for `pending`, `partially_annotated`, `complete`, `conflicted`, and `adjudicated`, deriving exclusively from immutable annotation rows; stale `research_pairs.status` must be repaired idempotently.
- [ ] **Step 2: Write failing freeze tests** for every spec guard: missing/duplicate/excess ordinary labels; unresolved, unnecessary, or multiple adjudications; missing/hash/MIME mismatch; character leakage; synthetic test; constructed val/test; pair-memory mismatch; duplicate IDs; and exclusions not listed in the run bundle.
- [ ] **Step 3: Run** `uv run pytest tests/test_finetune_dataset.py tests/test_research_integrity.py -q`. Expected: FAIL on missing APIs/guards.
- [ ] **Step 4: Implement reconciliation** by reusing `resolve_annotations` signatures and one bulk status update. Do not trust cached status during export.
- [ ] **Step 5: Implement freeze** by loading completed bundles, verifying local bytes again, calling existing `build_dataset` and `to_llamafactory.write_dataset`, then writing `freeze_report.json` atomically with dataset SHA-256; counts by story/character/split/class/reason; adjudication rate; exclusions; and pinned commit/schema/model/prompt/style/config values.
- [ ] **Step 6: Make freeze immutable:** if output exists, accept only byte-identical artifacts; otherwise fail. Require an explicit new output directory for a revised freeze.
- [ ] **Step 7: Run focused tests plus** `uv run pytest tests/test_annotation_pipeline_e2e.py -q`. Expected: PASS.
- [ ] **Step 8: Commit:** `git commit -m "feat(research): reconcile and freeze judge dataset"`.

### Task 6: Safe pilot-data cleanup

**Files:**
- Create: `backend/scripts/clear_research_pilot.py`
- Create: `backend/tests/test_clear_research_pilot.py`

**Interfaces:**
- Produces: `plan_cleanup(supabase, bucket="private_assets") -> CleanupPlan`, `execute_cleanup(plan, supabase, confirmation)`, and CLI requiring `--confirm DELETE-RESEARCH-PILOT` for mutation.

```python
@dataclass(frozen=True)
class CleanupPlan:
    pair_ids: tuple[str, ...]
    object_paths: tuple[str, ...]
    annotation_count: int

def plan_cleanup(supabase: Any, bucket: str = "private_assets") -> CleanupPlan: ...
def execute_cleanup(
    plan: CleanupPlan, supabase: Any, confirmation: str
) -> None: ...
```

- [ ] **Step 1: Write failing tests** proving default dry-run performs no mutation and reports annotation, pair, and `research/pilot/` object counts.
- [ ] **Step 2: Write deletion tests** proving exact order: annotations whose `pair_id` belongs to pilot pairs, then `research_pairs`, then only objects under `research/pilot/`; unrelated research rows/objects remain untouched.
- [ ] **Step 3: Add failure tests:** partial deletion stops non-zero and reports remaining IDs; confirmation mismatch performs no writes; final verification must observe zero in all three scopes.
- [ ] **Step 4: Run** `uv run pytest tests/test_clear_research_pilot.py -q`. Expected: collection failure.
- [ ] **Step 5: Implement with the existing Supabase client seam**, paginated reads, exact IDs from `is_pilot=true`, and literal prefix filtering. Do not use recursive filesystem deletion or broad Storage paths.
- [ ] **Step 6: Run focused tests and lint.** Expected: PASS.
- [ ] **Step 7: Commit:** `git commit -m "feat(research): add confirmed pilot cleanup"`.

### Task 7: Correct mixed-format storage telemetry

**Files:**
- Modify: `backend/scripts/corpus_storage_telemetry.py`
- Modify: `backend/tests/test_corpus_storage_telemetry.py`
- Modify: `docs/specs/judge-finetune.md`
- Modify: `docs/MASTER_SPEC.md`

**Interfaces:**
- Produces telemetry for PNG references plus WebP-quality-82 scenes and a Supabase-only capacity report; no provider recommendation.

```python
def calculate_corpus_projections(
    reference_png_sizes: list[int],
    scene_webp_sizes: list[int],
    canonical_references: int,
    scene_images: int,
    viewers: int = 3,
) -> dict[str, float | int]: ...
```

- [ ] **Step 1: Write failing tests** that generated reference bytes are PNG, scene bytes are WebP, both magic bytes/dimensions are verified, totals use separate distributions, and output contains neither `Cloudflare` nor `R2`.
- [ ] **Step 2: Run** `uv run pytest tests/test_corpus_storage_telemetry.py -q`. Expected: FAIL because the script supports only PNG and recommends R2.
- [ ] **Step 3: Replace the all-PNG projection** with separate reference/scene counts and measured byte samples. Report Supabase quota headroom as a measurement, not an architecture recommendation; if limits are insufficient, the runbook says to stop and open an ADR session.
- [ ] **Step 4: Keep it zero-cost** and write reports only under `.scratch/`; do not add a new artifact home.
- [ ] **Step 5: Synchronize durable docs:** replace the stale ~50-donated-story/all-PNG/cost arithmetic in `judge-finetune.md` with a pointer to the approved corpus-operations spec, and update `MASTER_SPEC.md` so it no longer says the existing `backend/finetune/` modules are unbuilt. Preserve preregistered history where the repo rules require strike-through rather than deletion.
- [ ] **Step 6: Run focused tests, lint, and** `rg -n "Cloudflare|R2|~50 donated|all-PNG|not built yet" backend/scripts backend/tests docs/specs/judge-finetune.md docs/MASTER_SPEC.md`. Expected: no stale operational recommendation/status hit; historical/alternative mentions must be explicitly marked rejected if retained.
- [ ] **Step 7: Commit:** `git commit -m "fix(research): align storage telemetry with adr 027"`.

### Task 8: Operational gates, paid smoke, annotation, training, and evaluation

**Files:**
- Modify: `docs/capstone/research_runbook.md`
- Modify: `docs/capstone/methodology.md` only when recording the executed protocol/result, preserving preregistered prose as required.

**Interfaces:**
- Consumes: the commands built in Tasks 1-7 and the frozen preregistration.
- Produces: signed gate records and run artifacts; no new application code.

- [ ] **Step 1: Record governance approval** and finalized consent/assent version. Until signed, do not contact donors or ingest donated stories.
- [ ] **Step 2: Run pilot cleanup dry-run**, archive its counts, execute only after checking the exact IDs/prefix, then archive the zero-count verification.
- [ ] **Step 3: Run the zero-cost fixture path** and full deterministic backend verification: `uv run ruff check . && uv run pytest`. Stop on any failure.
- [ ] **Step 4: Run the three-story synthetic smoke** with `--max-usd 1.50`; record pricing source/time, attempted/completed/failed/uncertain calls, bytes, latency, signed delivery, and actual invoice reconciliation. Stop before campaign generation on discrepancy.
- [ ] **Step 5: Finalize sanitized intake** with 10 primary + 5 backup donated candidates. Replacements are allowed only for withdrawal, unusable de-identification, terminal pipeline failure, or inadequate character yield under the recorded rule.
- [ ] **Step 6: Generate synthetic train/val first**, reserving enough of the USD 30 ceiling to finish every started story; generate donated test only after the intake gate. Never select donated cases based on judge behavior.
- [ ] **Step 7: Materialize and annotate:** verify signed URLs, calibrate researchers on non-study fixtures, collect two independent labels, adjudicate only disagreements, reconcile status, and record agreement/drift after collection.
- [ ] **Step 8: Freeze once** after all integrity guards pass and adviser signs the report. Store a controlled copy of the immutable dataset and hashes.
- [ ] **Step 9: Qualify school hardware** by recording GPU/VRAM, RAM, storage, OS, driver/CUDA, and allowed runtime; run loader + one forward pass before training. Use cloud only if this predeclared qualification fails.
- [ ] **Step 10: Train seeds 0, 1, and 2** with the same scientific configuration; record only hardware-required batch/accumulation differences. Select checkpoint using synthetic validation only.
- [ ] **Step 11: Freeze evaluation code/config**, then open and evaluate the donated held-out test once under `docs/product/PREREGISTRATION_OBJ4.md`. A confirmed code defect permits only its documented controlled rerun.
- [ ] **Step 12: Report** uncertainty clustered by character, exclusions, withdrawals, costs, failures, deviations, and limitations. Deployment is a separate decision and is not part of this plan.

## Final verification

- [ ] From `backend/`: `uv run ruff check . && uv run pytest`.
- [ ] From `frontend/`: `pnpm lint && pnpm test` (annotation surface regression check; no frontend changes expected).
- [ ] Run `git diff --check` and grep for stale storage/cost guidance: `rg -n "Cloudflare|R2|--budget 40|budget 500|all-PNG|all PNG" backend docs research_strategy.html`.
- [ ] Confirm no `.env`, raw submission, identity ledger, receipt code, or generated `data/judge/` artifact is tracked by `git status --short`.
- [ ] Confirm the GitHub issue for each operational gate links back to this plan and the canonical spec.
