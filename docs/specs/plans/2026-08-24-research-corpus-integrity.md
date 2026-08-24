# Research Corpus Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make corpus generation bind immutable intake bytes to every bundle, finish safely at an exact paid-call boundary, quarantine every incomplete outcome, and support explicit recovery without reducing recorded spend.

**Architecture:** Keep the existing production graph, Fal provider seam, JSON state file and immutable run bundles. Add one canonical intake digest, use the existing pre-submit `_fal_event_sink` callback to reject the next unaffordable call, represent graph completion explicitly inside `build_corpus.py`, and make recovery an opt-in mode of the same CLI rather than a second pipeline.

**Tech Stack:** Python 3.12, Pydantic, LangGraph, pytest, Ruff, standard-library `hashlib`/`json`/`dataclasses`/`datetime`.

## Global Constraints

- No new dependency, service, datastore, provider call path or Story Memory contract field.
- All model and Fal calls remain in `backend/providers.py`; the corpus builder uses the existing `_fal_event_sink` only.
- Every test is deterministic and mocked; no paid call, live database, Storage mutation or `.env` access.
- `withdrawal_state` is the only intake field excluded from `intake_sha256`.
- An uncertain Fal attempt always remains counted at the pinned conservative price.
- Completed bundles remain immutable and byte-identical reruns remain no-ops.
- Run backend commands from `backend/` with `uv run`.

---

## File map

- `backend/finetune/corpus_io.py`: canonical immutable-intake hashing.
- `backend/finetune/build_corpus.py`: bundle binding, paid-call boundary, explicit runner outcomes, quarantine persistence and recovery CLI.
- `backend/tests/test_corpus_io.py`: digest determinism and mutable-withdrawal coverage.
- `backend/tests/test_finetune_corpus.py`: bundle binding, exact-boundary, quarantine and recovery regressions.
- `docs/specs/research-corpus-operations.md`: already-approved behavior; only the billing-recovery wording correction in this planning commit.
- `tasks/todo.md`: progress and final verification outcome.

### Task 1: Bind completed bundles to immutable intake bytes

**Files:**

- Modify: `backend/finetune/corpus_io.py`
- Modify: `backend/finetune/build_corpus.py`
- Test: `backend/tests/test_corpus_io.py`
- Test: `backend/tests/test_finetune_corpus.py`

**Interfaces:**

- Produces: `intake_sha256(record: IntakeRecord) -> str`.
- Produces: `run_metadata["intake_sha256"]` on every fixture and production `RunBundle`.
- Consumes: existing `IntakeRecord`, `RunBundle.run_metadata` and completed-bundle skip path.

- [ ] **Step 1: Add the failing canonical-hash test**

Add to `backend/tests/test_corpus_io.py`:

```python
from finetune.corpus_io import intake_sha256


def test_intake_sha256_is_stable_and_excludes_only_withdrawal_state():
    active = IntakeRecord.model_validate(donated_record())
    withdrawn = active.model_copy(update={"withdrawal_state": "withdrawn"})

    assert intake_sha256(active) == intake_sha256(withdrawn)
    assert intake_sha256(active) != intake_sha256(active.model_copy(update={"text": "Changed"}))
    assert len(intake_sha256(active)) == 64
```

- [ ] **Step 2: Run the test and verify RED**

Run from `backend/`:

```powershell
uv run pytest tests/test_corpus_io.py -k "intake_sha256" -q
```

Expected: collection fails because `intake_sha256` does not exist.

- [ ] **Step 3: Implement canonical hashing with the standard library**

In `backend/finetune/corpus_io.py`, import `hashlib`, define the exact immutable field set, and add:

```python
IMMUTABLE_INTAKE_FIELDS = {
    "story_id",
    "text",
    "declared_characters",
    "declared_non_human",
    "provenance",
    "split",
    "candidate_role",
    "style_preset_id",
    "guardian_consent",
    "child_assent",
    "manual_pii_redaction",
    "independent_redaction_review",
    "selection_frozen_at",
}


def intake_sha256(record: IntakeRecord) -> str:
    payload = record.model_dump(mode="json", include=IMMUTABLE_INTAKE_FIELDS)
    canonical = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
```

Place the function after `IntakeRecord` so its type is defined. Do not include `withdrawal_state`.

- [ ] **Step 4: Verify the hash test is GREEN**

Run:

```powershell
uv run pytest tests/test_corpus_io.py -k "intake_sha256" -q
```

Expected: 1 passed.

- [ ] **Step 5: Add failing bundle-binding regressions**

Extend the fixture-bundle test to assert:

```python
assert bundle.run_metadata["intake_sha256"] == intake_sha256(intake_story())
```

Add to `backend/tests/test_finetune_corpus.py`:

```python
def test_completed_bundle_rejects_changed_immutable_intake(tmp_path):
    story = intake_story()
    build_corpus.build(
        [story], FakeGraph(1), out_dir=tmp_path, supabase=FakeSupabase(), fixture=True
    )

    with pytest.raises(CorpusError, match="intake digest differs"):
        build_corpus.build(
            [story.model_copy(update={"text": "Changed redacted text."})],
            FakeGraph(1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            fixture=True,
        )
```

Import `intake_sha256` into this test module.

- [ ] **Step 6: Run the binding regressions and verify RED**

Run:

```powershell
uv run pytest tests/test_finetune_corpus.py -k "intake_sha256 or changed_immutable_intake or complete_zero_cost_bundle" -q
```

Expected: failures because `_bundle` does not record or compare the digest.

- [ ] **Step 7: Persist and verify the digest**

Import `intake_sha256` in `build_corpus.py`. Add this metadata in `_bundle`:

```python
"intake_sha256": intake_sha256(story),
```

Before `_verify_bundle_assets` in the completed-bundle branch, compare:

```python
if bundles[story_id].run_metadata.get("intake_sha256") != intake_sha256(story):
    raise CorpusError(f"intake digest differs for completed bundle: {story_id}")
```

Missing legacy digests fail closed; do not rewrite an immutable `run.json`.

- [ ] **Step 8: Run focused tests**

Run:

```powershell
uv run pytest tests/test_corpus_io.py tests/test_finetune_corpus.py -q
uv run ruff check finetune/corpus_io.py finetune/build_corpus.py tests/test_corpus_io.py tests/test_finetune_corpus.py
```

Expected: all selected tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 9: Commit Task 1**

```powershell
git add -- backend/finetune/corpus_io.py backend/finetune/build_corpus.py backend/tests/test_corpus_io.py backend/tests/test_finetune_corpus.py
git commit -m "feat(research): bind corpus bundles to intake"
```

### Task 2: Stop paid calls before submission and quarantine incomplete outcomes

**Files:**

- Modify: `backend/finetune/build_corpus.py`
- Test: `backend/tests/test_finetune_corpus.py`

**Interfaces:**

- Produces: `StoryRun(values: dict, image_count: int, outcome: Literal["completed", "budget_stopped", "quarantined"], reason: str | None)`.
- Produces: quarantine `reason_code` values `budget_stopped`, `resume_exhausted`, `billing_uncertain`, `invalid_terminal` and `intake_mismatch`.
- Consumes: `_fal_event_sink`, persisted per-story telemetry and `intake_sha256` from Task 1.

- [ ] **Step 1: Make the fake graph model the real pre-submit event order**

Update `FakeGraph.stream` in `backend/tests/test_finetune_corpus.py` so paid tests execute the existing callback before recording a submitted call:

```python
def stream(self, graph_input, config, stream_mode=None):
    self.calls.append(config["configurable"]["thread_id"])
    for n in range(1, self.per_story_images + 1):
        sink = build_corpus._fal_event_sink.get()
        if sink:
            sink("attempted")
        self.consumed += 1
        if sink:
            sink("completed")
        values = graph_input.model_dump()
        values.update(
            cost=Cost(image_count=n),
            characters=[
                Character(char_id="c0", name="c0", canonical_ref_image="story/ref-c0-1.png")
            ],
        )
        yield "values", values
```

Delete `TelemetryGraph` and replace its uses with `FakeGraph`; it would otherwise double-count callbacks.

- [ ] **Step 2: Add exact-boundary, next-call and resume-exhaustion regressions**

Add tests with these assertions:

```python
def test_exact_story_draw_limit_still_writes_a_completed_bundle(tmp_path, stories):
    graph = FakeGraph(per_story_images=2)
    policy = build_corpus.SpendPolicy(
        max_usd=Decimal("0.07"), conservative_call_usd=Decimal("0.035")
    )

    summary = build_corpus.build(
        stories[:1], graph, out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )

    assert summary["stories_run"] == 1
    assert summary["halted"] is False
    assert graph.consumed == 2
    assert load_completed_bundles(tmp_path)[0].memory.story_id == "a"


def test_next_call_past_story_limit_is_blocked_before_submission(tmp_path, stories):
    graph = FakeGraph(per_story_images=3)
    policy = build_corpus.SpendPolicy(
        max_usd=Decimal("0.07"), conservative_call_usd=Decimal("0.035")
    )

    summary = build_corpus.build(
        stories[:1], graph, out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert graph.consumed == 2
    assert summary["halted"] is True
    assert state["a"]["reason_code"] == "budget_stopped"
    assert load_completed_bundles(tmp_path) == []


def test_resume_exhaustion_is_quarantined_without_a_bundle(tmp_path, stories):
    class InterruptGraph:
        calls = 0

        def stream(self, graph_input, config, stream_mode=None):
            self.calls += 1
            yield "updates", {"__interrupt__": [object()]}

    graph = InterruptGraph()
    summary = build_corpus.build(
        stories[:1], graph, out_dir=tmp_path, supabase=FakeSupabase()
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert graph.calls == build_corpus.MAX_RESUMES + 1
    assert summary["halted"] is True
    assert state["a"]["reason_code"] == "resume_exhausted"
    assert load_completed_bundles(tmp_path) == []
```

Update the existing invalid-result regression to assert `reason_code == "invalid_terminal"` and no bundle.

- [ ] **Step 3: Run the new tests and verify RED**

Run:

```powershell
uv run pytest tests/test_finetune_corpus.py -k "exact_story_draw_limit or next_call_past or resume_exhaustion or invalid_terminal" -q
```

Expected: exact-boundary completion fails, and structured runner/quarantine behavior is absent.

- [ ] **Step 4: Add the minimal runner result and pre-submit stop signal**

In `backend/finetune/build_corpus.py`, import `Literal` and `pydantic.ValidationError`, then add:

```python
class StoryBudgetStopped(Exception):
    pass


@dataclass(frozen=True)
class StoryRun:
    values: dict
    image_count: int
    outcome: Literal["completed", "budget_stopped", "quarantined"]
    reason: str | None = None
```

Replace the boolean-return runner with:

```python
def run_story(app_graph, story: IntakeRecord) -> StoryRun:
    config = {"configurable": {"thread_id": story.story_id}, "recursion_limit": RECURSION_LIMIT}
    graph_input = _initial_state(story)
    values: dict = {}
    for _ in range(MAX_RESUMES + 1):
        interrupted = False
        try:
            for chunk in app_graph.stream(graph_input, config, stream_mode=["updates", "values"]):
                mode, payload = chunk[-2:]
                if mode == "values":
                    values = payload
                elif "__interrupt__" in payload:
                    interrupted = True
        except StoryBudgetStopped:
            return StoryRun(values, _image_count(values), "budget_stopped", "budget_stopped")
        if not interrupted:
            return StoryRun(values, _image_count(values), "completed")
        graph_input = Command(resume=CONFIRM)
    return StoryRun(values, _image_count(values), "quarantined", "resume_exhausted")
```

At the beginning of `record_fal_event`, before incrementing telemetry:

```python
if event == "attempted" and story_telemetry["attempted"] >= story_draw_limit:
    raise StoryBudgetStopped
```

This works because `providers._run_fal` invokes the sink before `_fal().subscribe(...)`.

- [ ] **Step 5: Centralize quarantine persistence**

Add a helper that never decreases telemetry:

```python
def _quarantine(
    state: dict,
    state_path: pathlib.Path,
    story: IntakeRecord,
    reason_code: str,
    message: str,
    telemetry: Counter,
    policy: SpendPolicy,
) -> None:
    state[story.story_id] = {
        "quarantined": message,
        "reason_code": reason_code,
        "intake_sha256": intake_sha256(story),
        "conservative_call_usd": str(policy.conservative_call_usd),
        "telemetry": dict(telemetry),
    }
    _write_state(state_path, state)
```

Use it for budget stop, resume exhaustion, uncertain billing, invalid terminal state and intake mismatch. Replace the paid-run boolean branch with this shape:

```python
run = run_story(app_graph, story)
campaign_spent += run.image_count
invocation_spent += run.image_count
if run.outcome != "completed":
    reason = run.reason or "invalid_terminal"
    _quarantine(
        state,
        state_path,
        story,
        reason,
        reason.replace("_", " "),
        story_telemetry,
        policy,
    )
    summary["halted"] = True
    break

try:
    memory = StoryMemory.model_validate(run.values)
    refs, scenes = download_images(memory, out_dir, supabase)
    bundle = _bundle(
        story,
        memory,
        out_dir,
        fixture,
        story_telemetry,
        policy.conservative_call_usd,
    )
except (CorpusError, ValidationError) as error:
    _quarantine(
        state,
        state_path,
        story,
        "invalid_terminal",
        f"invalid terminal state: {error}",
        story_telemetry,
        policy,
    )
    raise CorpusError(f"invalid terminal state for {story_id}: {error}") from error
```

Write the prepared `bundle` only after this block. A non-completed `StoryRun` exits before validation, image download or `write_bundle`. Preserve the dedicated uncertain-billing exception branch, but make it call `_quarantine(..., "billing_uncertain", ...)`.

In the completed-bundle digest check from Task 1, persist the failure before raising:

```python
if bundles[story_id].run_metadata.get("intake_sha256") != intake_sha256(story):
    bundle_telemetry = _persisted_telemetry(
        bundles[story_id].run_metadata, policy, story_id
    )
    _quarantine(
        state,
        state_path,
        story,
        "intake_mismatch",
        "intake digest differs from completed bundle",
        bundle_telemetry,
        policy,
    )
    raise CorpusError(f"intake digest differs for completed bundle: {story_id}")
```

- [ ] **Step 6: Run focused tests and Ruff**

Run:

```powershell
uv run pytest tests/test_finetune_corpus.py -q
uv run ruff check finetune/build_corpus.py tests/test_finetune_corpus.py
```

Expected: the full corpus-runner test file passes and Ruff reports `All checks passed!`.

- [ ] **Step 7: Commit Task 2**

```powershell
git add -- backend/finetune/build_corpus.py backend/tests/test_finetune_corpus.py
git commit -m "fix(research): stop corpus spend before submission"
```

### Task 3: Add explicit, auditable quarantine recovery

**Files:**

- Modify: `backend/finetune/build_corpus.py`
- Test: `backend/tests/test_finetune_corpus.py`

**Interfaces:**

- Extends: `build(..., resume_quarantined: str | None = None, acknowledge_uncertain_billing: str | None = None) -> dict`.
- Extends CLI: `--resume-quarantined <story_id>` and `--acknowledge-uncertain-billing <story_id>`.
- Produces: optional `run_metadata["billing_acknowledged_at"]` in the recovered immutable bundle.

- [ ] **Step 1: Add failing recovery tests**

Move the existing local uncertain graph into a module-level helper and add the recoverable checkpoint helper:

```python
from types import SimpleNamespace


class UncertainGraph:
    def __init__(self):
        self.calls = 0

    def stream(self, graph_input, config, stream_mode=None):
        self.calls += 1
        sink = build_corpus._fal_event_sink.get()
        sink("attempted")
        sink("failed_uncertain")
        raise TimeoutError("provider result unknown")
        yield


class RecoverableGraph(FakeGraph):
    def __init__(self, story, per_story_images):
        super().__init__(per_story_images)
        self.story = story

    def get_state(self, config):
        return SimpleNamespace(values=build_corpus._initial_state(self.story).model_dump())
```

Then add these cases:

```python
def test_budget_stop_requires_explicit_resume_and_preserves_telemetry(tmp_path, stories):
    smoke = build_corpus.SpendPolicy(max_usd=Decimal("0.07"))
    build_corpus.build(
        stories[:1], FakeGraph(3), out_dir=tmp_path, supabase=FakeSupabase(), policy=smoke
    )

    resumed = RecoverableGraph(stories[0], per_story_images=1)
    summary = build_corpus.build(
        stories[:1],
        resumed,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        resume_quarantined="a",
    )
    [bundle] = load_completed_bundles(tmp_path)

    assert summary["stories_run"] == 1
    assert bundle.run_metadata["attempted_calls"] == 3
    assert bundle.run_metadata["completed_calls"] == 3


def test_uncertain_billing_requires_matching_acknowledgment(tmp_path):
    story = intake_story()
    with pytest.raises(CorpusError, match="billing uncertain"):
        build_corpus.build(
            [story], UncertainGraph(), out_dir=tmp_path, supabase=FakeSupabase()
        )

    resumed = RecoverableGraph(story, per_story_images=1)
    with pytest.raises(CorpusError, match="acknowledge uncertain billing"):
        build_corpus.build(
            [story],
            resumed,
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            resume_quarantined=story.story_id,
        )
    assert resumed.calls == []


def test_uncertain_billing_acknowledgment_never_reduces_spend(tmp_path):
    story = intake_story()
    with pytest.raises(CorpusError):
        build_corpus.build(
            [story], UncertainGraph(), out_dir=tmp_path, supabase=FakeSupabase()
        )

    build_corpus.build(
        [story],
        RecoverableGraph(story, per_story_images=1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        resume_quarantined=story.story_id,
        acknowledge_uncertain_billing=story.story_id,
    )
    [bundle] = load_completed_bundles(tmp_path)

    assert bundle.run_metadata["attempted_calls"] == 2
    assert bundle.run_metadata["uncertain_calls"] == 1
    assert "billing_acknowledged_at" in bundle.run_metadata


@pytest.mark.parametrize(
    ("reason_code", "include_digest", "resume_id"),
    [
        ("invalid_terminal", True, "fixture-story"),
        ("intake_mismatch", True, "fixture-story"),
        ("budget_stopped", False, "fixture-story"),
        ("budget_stopped", True, "different-story"),
    ],
)
def test_nonrecoverable_or_unbound_quarantine_cannot_resume(
    tmp_path, reason_code, include_digest, resume_id
):
    story = intake_story()
    entry = {
        "quarantined": reason_code.replace("_", " "),
        "reason_code": reason_code,
        "conservative_call_usd": "0.035",
        "telemetry": {"attempted": 1, "completed": 1, "failed": 0, "uncertain": 0},
    }
    if include_digest:
        entry["intake_sha256"] = intake_sha256(story)
    (tmp_path / "build_state.json").write_text(
        json.dumps({story.story_id: entry}), encoding="utf-8"
    )

    with pytest.raises(CorpusError):
        build_corpus.build(
            [story],
            RecoverableGraph(story, per_story_images=1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            resume_quarantined=resume_id,
        )
    assert load_completed_bundles(tmp_path) == []
```

- [ ] **Step 2: Run recovery tests and verify RED**

Run:

```powershell
uv run pytest tests/test_finetune_corpus.py -k "explicit_resume or matching_acknowledgment or never_reduces_spend or cannot_resume" -q
```

Expected: `build` does not accept the recovery arguments.

- [ ] **Step 3: Validate quarantine state before graph execution**

Add a helper with this behavior:

```python
RECOVERABLE_REASONS = {"budget_stopped", "resume_exhausted", "billing_uncertain"}


def _validate_recovery(
    app_graph,
    story: IntakeRecord,
    state_entry: dict,
    resume_quarantined: str | None,
    acknowledge_uncertain_billing: str | None,
) -> str | None:
    reason = state_entry.get("reason_code")
    if resume_quarantined != story.story_id or reason not in RECOVERABLE_REASONS:
        raise CorpusError(f"{state_entry['quarantined']} for {story.story_id}")
    if state_entry.get("intake_sha256") != intake_sha256(story):
        raise CorpusError(f"intake digest differs for quarantined story: {story.story_id}")
    if reason == "billing_uncertain" and acknowledge_uncertain_billing != story.story_id:
        raise CorpusError(f"acknowledge uncertain billing before retry: {story.story_id}")
    snapshot = app_graph.get_state({"configurable": {"thread_id": story.story_id}})
    try:
        StoryMemory.model_validate(snapshot.values)
    except (AttributeError, ValidationError) as error:
        raise CorpusError(f"checkpoint is not resumable: {story.story_id}") from error
    return (
        datetime.now(timezone.utc).isoformat()
        if reason == "billing_uncertain"
        else state_entry.get("billing_acknowledged_at")
    )
```

Import `datetime`, `timezone` and `ValidationError`. Call this before any graph stream. Do not delete or reset the state entry; the next persisted event must inherit its counters.

When the helper returns a new acknowledgment timestamp, persist it before entering the graph so a later
failure cannot erase the audit event:

```python
billing_acknowledged_at = _validate_recovery(
    app_graph,
    story,
    state_entry,
    resume_quarantined,
    acknowledge_uncertain_billing,
)
if billing_acknowledged_at is not None:
    state_entry["billing_acknowledged_at"] = billing_acknowledged_at
    _write_state(state_path, state)
```

- [ ] **Step 4: Persist acknowledgment in the completed bundle**

Extend `_bundle` with `billing_acknowledged_at: str | None = None` and conditionally merge:

```python
**(
    {"billing_acknowledged_at": billing_acknowledged_at}
    if billing_acknowledged_at is not None
    else {}
),
```

Pass the timestamp returned by `_validate_recovery`. The uncertain call remains present in `attempted_calls` and `uncertain_calls`.

- [ ] **Step 5: Add and validate the CLI options**

Add both parser arguments:

```python
parser.add_argument("--resume-quarantined", metavar="STORY_ID")
parser.add_argument("--acknowledge-uncertain-billing", metavar="STORY_ID")
```

Reject acknowledgment unless the same story ID is also passed to `--resume-quarantined`; reject both options with `--fixture`. Perform these checks before `load_intake` and the paid-branch imports. Forward the values to `build` in the paid branch. Add:

```python
@pytest.mark.parametrize(
    "argv",
    [
        ["--fixture", "--resume-quarantined", "fixture-story"],
        ["--acknowledge-uncertain-billing", "fixture-story"],
        [
            "--resume-quarantined",
            "fixture-story",
            "--acknowledge-uncertain-billing",
            "different-story",
        ],
    ],
)
def test_cli_rejects_unsafe_recovery_combinations(argv):
    with pytest.raises(SystemExit):
        build_corpus.main(argv)
```

The direct `build` recovery tests cover the forwarded values without constructing live infrastructure.

- [ ] **Step 6: Run focused and combined verification**

Run:

```powershell
uv run pytest tests/test_corpus_io.py tests/test_finetune_corpus.py -q
uv run ruff check finetune/corpus_io.py finetune/build_corpus.py tests/test_corpus_io.py tests/test_finetune_corpus.py
```

Expected: all focused tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 7: Commit Task 3**

```powershell
git add -- backend/finetune/build_corpus.py backend/tests/test_finetune_corpus.py
git commit -m "feat(research): reconcile quarantined corpus runs"
```

### Task 4: Verify Batch 1 and close the disposable plan

**Files:**

- Modify: `tasks/todo.md`
- Delete after all checks pass: `docs/specs/plans/2026-08-24-research-corpus-integrity.md`

**Interfaces:**

- Consumes: all Batch 1 behavior from Tasks 1–3.
- Produces: a recorded verification outcome and no stale completed implementation plan.

- [ ] **Step 1: Run the full deterministic backend gate**

From `backend/`:

```powershell
uv run ruff check .
uv run pytest
```

Expected: Ruff and the full deterministic pytest suite pass. Environment-dependent RLS and provider smoke tests may skip only according to the repository’s documented markers.

- [ ] **Step 2: Run a zero-cost CLI fixture outside the canonical corpus directory**

```powershell
$datasetFixtureOut = Join-Path $env:TEMP ("storybuddy-batch1-" + [guid]::NewGuid())
uv run python -m finetune.build_corpus --fixture --limit 1 --out $datasetFixtureOut
Get-Content (Join-Path $datasetFixtureOut "build_state.json")
```

Expected: one completed bundle reference, zero paid images and `usd_high` equal to zero. Do not run the paid smoke.

- [ ] **Step 3: Record the outcome**

In `tasks/todo.md`, mark Batch 1 execution complete and record:

- focused test counts;
- full Ruff/pytest results and intentional skips;
- the zero-cost fixture summary;
- confirmation that no provider, live database or paid operation ran;
- remaining Batch 2 and Batch 3 blockers.

- [ ] **Step 4: Remove this completed plan and commit the verification record**

```powershell
git rm -- docs/specs/plans/2026-08-24-research-corpus-integrity.md
git add -- tasks/todo.md
git commit -m "docs(research): record corpus integrity outcome"
```
