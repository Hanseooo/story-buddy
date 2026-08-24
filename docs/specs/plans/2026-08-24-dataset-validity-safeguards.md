# Dataset Validity Safeguards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. StoryBuddy's recorded owner preference is inline execution by the primary agent, so use `superpowers:executing-plans` unless the owner explicitly changes that choice.

**Goal:** Make Objective-4 materialization and freeze fail closed on hard-negative selection, current withdrawal state, donated primary/backup membership, and mutable-versus-immutable path separation.

**Architecture:** Add one focused `finetune.dataset_selection` module for the strict controlled artifact and the shared membership audit used before queue materialization and freeze. Keep record rendering in `build_dataset.py`, intake/bundle persistence in `corpus_io.py`, and immutable installation in `freeze_dataset.py`; do not change StoryMemory, providers, database schema, or graph shape.

**Tech Stack:** Python 3.12, Pydantic v2, standard-library `argparse`/`datetime`/`hashlib`/`json`, pytest, Ruff, and the existing Supabase client seam.

**Spec:** `docs/specs/research-corpus-operations.md` §3 and §4.6; `docs/specs/judge-finetune.md` §5.3–§5.5.

## Global Constraints

- Never read `.env`, call a provider, upload research data, or inspect a real held-out `test.json` during implementation.
- Add no dependency, datastore, schema, StoryMemory field, model, provider path, or graph change.
- Use only `cel`, `gouache`, and `cut_paper`; `comic` remains excluded from research intake.
- Canonical homes are `data/judge/intake/`, `data/judge/corpus/`, and `data/judge/freezes/<freeze-id>/`.
- Splits are assigned in intake before generation. Do not add a seeded or random post-generation split.
- Constructed negatives are train-only and use exactly one manually frozen same-species/same-style target per synthetic training reference.
- Donated test defaults to ten primaries. A backup replaces one primary only, preserves style, is not reused, and cites one approved reason and opaque evidence reference.
- Generation rejects withdrawn intake. `freeze_audit` may accept it only to locate and exclude completed data.
- Fixtures may omit controlled production inputs. Production materialization and freeze require donated intake plus dataset selection.
- Use red-green-refactor for every parser, branch, and validation rule. Preserve unrelated worktree changes.
- Run Tasks 1–4 commands from `backend/` unless a step explicitly says repository root.

---

### Task 1: Strict selection artifact and freeze-audit intake mode

**Files:**
- Create: `backend/finetune/dataset_selection.py`
- Modify: `backend/finetune/corpus_io.py`
- Create: `backend/tests/test_dataset_selection.py`
- Modify: `backend/tests/test_corpus_io.py`

**Interfaces:**
- Produces `load_intake(path: Path, *, mode: Literal["generation", "freeze_audit"] = "generation") -> list[IntakeRecord]`.
- Moves the single `lineage_id(story_id: str, char_id: str) -> str` helper into `dataset_selection.py`; `build_dataset.py` imports it so existing `bd.lineage_id` callers keep working.
- Defines `SYNTHETIC_INTAKE = Path(__file__).with_name("corpus_synthetic.json")`.
- Produces `load_dataset_selection(path: Path) -> DatasetSelection`, `selection_sha256(path: Path) -> str`, and `candidate_report(bundles: Sequence[RunBundle]) -> list[dict[str, object]]`.
- Produces `select_dataset_bundles(bundles: Sequence[RunBundle], synthetic_intake: Sequence[IntakeRecord], donated_intake: Sequence[IntakeRecord], selection: DatasetSelection, selection_hash: str) -> tuple[list[RunBundle], DatasetSelectionAudit]`.
- Produces `prepare_dataset_bundles(bundles: Sequence[RunBundle], donated_intake_path: Path | None, selection_path: Path | None, *, synthetic_intake_path: Path = SYNTHETIC_INTAKE) -> tuple[list[RunBundle], DatasetSelection | None, DatasetSelectionAudit]`.
- `DatasetSelectionAudit` carries sorted selected/excluded donated IDs, `{primary_story_id: reason}`, and exact-byte selection SHA-256.

- [ ] **Step 1: Write failing intake-mode tests**

Add to `test_corpus_io.py`:

```python
def test_generation_intake_still_rejects_withdrawn_donor(tmp_path):
    records = donated_candidates()
    records[-1]["withdrawal_state"] = "withdrawn"
    with pytest.raises(ValueError, match="cannot enter generation"):
        load_intake(write_intake(tmp_path, records))


def test_freeze_audit_accepts_withdrawn_donor_without_weakening_batch_rules(tmp_path):
    records = donated_candidates()
    records[-1]["withdrawal_state"] = "withdrawn"
    loaded = load_intake(write_intake(tmp_path, records), mode="freeze_audit")
    assert loaded[-1].withdrawal_state == "withdrawn"
    assert len(loaded) == 15
```

Run from `backend/`:

```powershell
uv run pytest tests/test_corpus_io.py -k "withdrawn or freeze_audit" -v
```

Expected RED: `load_intake` has no audit mode or still rejects the withdrawn record.

- [ ] **Step 2: Implement the smallest context-aware intake change**

Use Pydantic `ValidationInfo` context from `load_intake`; direct `IntakeRecord.model_validate()` calls and the default loader remain generation-strict:

```python
IntakeMode = Literal["generation", "freeze_audit"]


def load_intake(path: Path, *, mode: IntakeMode = "generation") -> list[IntakeRecord]:
    if mode not in ("generation", "freeze_audit"):
        raise ValueError(f"unknown intake mode: {mode}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = [
        IntakeRecord.model_validate(item, context={"allow_withdrawn": mode == "freeze_audit"})
        for item in payload
    ]
    # Retain all existing duplicate/provenance/allocation guards.
    return records
```

The model validator accepts `withdrawal_state="withdrawn"` only when `allow_withdrawn` is true. Do not add a second intake model or add withdrawal state to `IMMUTABLE_INTAKE_FIELDS`.

Run:

```powershell
uv run pytest tests/test_corpus_io.py -v
```

Expected GREEN: all current intake tests still pass.

- [ ] **Step 3: Write failing strict-selection parser tests**

Create `test_dataset_selection.py` with this valid payload and mutations:

```python
VALID_SELECTION = {
    "hard_negatives_frozen_at": "2026-08-24T10:00:00+08:00",
    "hard_negative_matches": [
        {"reference_char_id": "syn-001:c0", "target_char_id": "syn-007:c0"}
    ],
    "donated_replacements": [
        {
            "primary_story_id": "don-001",
            "backup_story_id": "don-011",
            "reason": "withdrawal",
            "approved_at": "2026-08-24T11:00:00+08:00",
            "evidence_ref": "restricted-record-017",
        }
    ],
}
```

Assert strict rejection of unknown fields, naive/future timestamps, duplicate reference mappings, self-pairs, duplicate primary replacement, reused backup, invalid reason, and blank evidence. Assert:

```python
assert selection_sha256(path) == hashlib.sha256(path.read_bytes()).hexdigest()
```

Run:

```powershell
uv run pytest tests/test_dataset_selection.py -k "selection" -v
```

Expected RED: module import fails.

- [ ] **Step 4: Implement strict models and exact-byte hashing**

Use `ConfigDict(extra="forbid")`, aware completed timestamp validators, and this closed reason type:

```python
ReplacementReason = Literal[
    "withdrawal",
    "deidentification_failure",
    "terminal_pipeline_failure",
    "inadequate_character_yield",
]


class HardNegativeMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference_char_id: str
    target_char_id: str


class DonatedReplacement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    primary_story_id: str
    backup_story_id: str
    reason: ReplacementReason
    approved_at: datetime
    evidence_ref: str


class DatasetSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hard_negatives_frozen_at: datetime
    hard_negative_matches: list[HardNegativeMatch]
    donated_replacements: list[DonatedReplacement]


@dataclass(frozen=True)
class DatasetSelectionAudit:
    selected_donated_stories: list[str]
    excluded_donated_stories: list[str]
    replacement_reasons: dict[str, str]
    selection_sha256: str | None
```

`DatasetSelection` owns duplicate/self guards. Cross-corpus role/species/style checks belong in `select_dataset_bundles` and `validate_hard_negative_matches`, not the JSON parser.

- [ ] **Step 5: Write failing membership and candidate-report tests**

Build compact bundle/intake helpers. Cover:

```python
def test_candidate_report_lists_only_same_species_style_candidates():
    report = candidate_report([
        bundle("syn-a", "a", species="fox", style="cel", split="train"),
        bundle("syn-b", "b", species="fox", style="cel", split="train"),
        bundle("syn-c", "c", species="bear", style="cel", split="train"),
        bundle("syn-d", "d", species="fox", style="gouache", split="train"),
    ])
    row = next(item for item in report if item["reference_char_id"] == "syn-a:a")
    assert row["reference_image"] == "syn-a/ref.png"
    assert [item["target_char_id"] for item in row["candidates"]] == ["syn-b:b"]
    assert row["candidates"][0]["scene_count"] == 1
```

For `select_dataset_bundles`, assert:

- every production bundle matches a current intake `story_id` and `intake_sha256`;
- empty replacements select exactly ten primaries;
- one valid same-style backup replaces one primary;
- withdrawn selected primary without replacement fails;
- withdrawn backup, role drift, cross-style replacement, reused backup, missing selected bundle, wrong reason, or final membership other than ten with 4/3/3 fails;
- unselected completed backups appear only in the audit exclusion list.

Run:

```powershell
uv run pytest tests/test_dataset_selection.py -k "candidate_report or dataset_bundles" -v
```

Expected RED: the report and membership functions are absent.

- [ ] **Step 6: Implement one deterministic report and membership audit**

Candidate JSON is sorted by qualified lineage ID and contains only `reference_char_id`, canonical reference path, species, style, and candidates with target ID/path/natural-scene count. It never fetches annotations or verdicts.

`select_dataset_bundles` validates all production bundle digests, computes `primaries - replaced primaries + backups`, checks current withdrawal/role/style/reason/evidence/time state, then returns selected bundles and audit. It does not mutate or delete assets.

`prepare_dataset_bundles` checks `run_metadata["fixture"]`: all-fixture returns every bundle without inputs; production requires both paths, loads checked-in synthetic intake plus donated `freeze_audit` intake, loads selection, and delegates. Mixed fixture state fails.

The production call is exactly:

```python
synthetic = load_intake(synthetic_intake_path)
donated = load_intake(donated_intake_path, mode="freeze_audit")
selection = load_dataset_selection(selection_path)
selected, audit = select_dataset_bundles(
    bundles, synthetic, donated, selection, selection_sha256(selection_path)
)
return selected, selection, audit
```

- [ ] **Step 7: Verify and commit Task 1**

```powershell
uv run pytest tests/test_corpus_io.py tests/test_dataset_selection.py -v
uv run ruff check finetune/corpus_io.py finetune/dataset_selection.py tests/test_corpus_io.py tests/test_dataset_selection.py
git add -- finetune/corpus_io.py finetune/dataset_selection.py tests/test_corpus_io.py tests/test_dataset_selection.py
git diff --cached --check
git commit -m "feat(research): validate dataset selection inputs"
```

---

### Task 2: Exact manual hard negatives and read-only candidate CLI

**Files:**
- Modify: `backend/finetune/dataset_selection.py`
- Modify: `backend/finetune/build_dataset.py`
- Modify: `backend/tests/test_dataset_selection.py`
- Modify: `backend/tests/test_finetune_dataset.py`

**Interfaces:**
- Produces `validate_hard_negative_matches(bundles: Sequence[RunBundle], selection: DatasetSelection, annotation_rows: Sequence[dict[str, object]], pilot_pair_ids: set[str]) -> dict[str, str]`.
- Changes `constructed_records(records: list[ManifestRecord], matches: dict[str, str]) -> list[ManifestRecord]` to consume only a validated mapping.
- Adds mutually exclusive CLI mode `--candidate-report`.

- [ ] **Step 1: Replace adjacency tests with failing exact-mapping tests**

```python
def test_constructed_negatives_use_every_natural_target_scene():
    records = [
        manifest_record("ref", "story-a:a", "ref/a.png", "scene/a.webp"),
        manifest_record("target-1", "story-b:b", "ref/b.png", "scene/b-1.webp"),
        manifest_record("target-2", "story-b:b", "ref/b.png", "scene/b-2.webp"),
    ]
    made = bd.constructed_records(records, {"story-a:a": "story-b:b"})
    assert [row.images for row in made] == [
        ["ref/a.png", "scene/b-1.webp"],
        ["ref/a.png", "scene/b-2.webp"],
    ]
```

Also fail on missing reference records, target without included natural train records, or duplicate constructed pair IDs. `build_dataset(add_constructed=True)` without a validated mapping must fail instead of falling back to combinations.

Run:

```powershell
uv run pytest tests/test_finetune_dataset.py -k "constructed" -v
```

Expected RED: the current code uses adjacent combinations and one target scene.

- [ ] **Step 2: Implement mapped construction**

Remove `itertools.combinations` and `styles_by_char`. Index natural train records by lineage. For each sorted mapping, take the reference image from the reference lineage and emit one constructed record per natural target scene. Preserve `char_id=reference_id`, `split="train"`, `pair_type="constructed"`, `same_character=False`, `label=True`, and the existing deterministic rationale/reason.

Add `hard_negative_matches: dict[str, str] | None` to `build_dataset`. If construction is enabled and the mapping is `None`, raise `ManifestError("hard-negative selection is required")`.

```python
if add_constructed:
    if hard_negative_matches is None:
        raise ManifestError("hard-negative selection is required")
    records += constructed_records(records, hard_negative_matches)
```

- [ ] **Step 3: Write failing cross-corpus mapping/time tests**

Parameterize `validate_hard_negative_matches` failures for missing/excess reference, unknown target, self-pair, non-synthetic/non-train character, different species, different style, missing canonical reference, and target without a finalized natural scene.

Use annotation `created_at` to assert:

- no non-pilot annotation permits an aware completed freeze timestamp;
- pilot annotation before freeze is ignored;
- earliest non-pilot annotation earlier than freeze fails;
- missing, malformed, naive, or future non-pilot timestamps fail closed.

Expected ordering:

```python
selection.hard_negatives_frozen_at <= min(non_pilot_created_at)
```

- [ ] **Step 4: Implement eligibility/time validation without reading outcomes**

Index all synthetic train characters by `<story_id>:<char_id>`. Require exact mapping coverage, case-normalized nonblank species equality, exact style equality, and at least one finalized target scene containing the target. Resolve annotation IDs only to distinguish pilot/non-pilot and compare `created_at`; never read label values, failure reasons, or judge output.

Return the mapping only after the full loop succeeds:

```python
matches = {
    item.reference_char_id: item.target_char_id
    for item in selection.hard_negative_matches
}
if set(matches) != set(train_characters):
    raise ManifestError("every synthetic training reference requires exactly one hard-negative match")
return matches
```

- [ ] **Step 5: Add and test the CLI mode**

Add `--candidate-report` to the current mutually exclusive group. Default `--data` becomes `data/judge/corpus`. The branch loads completed bundles and prints stable indented JSON. Patch `get_supabase_client`, annotation fetchers, and freeze to raise in the test; none may be called.

```powershell
uv run pytest tests/test_finetune_dataset.py tests/test_dataset_selection.py -k "constructed or candidate_report or hard_negative" -v
uv run ruff check finetune/build_dataset.py finetune/dataset_selection.py tests/test_finetune_dataset.py tests/test_dataset_selection.py
```

- [ ] **Step 6: Commit Task 2**

```powershell
git add -- finetune/dataset_selection.py finetune/build_dataset.py tests/test_dataset_selection.py tests/test_finetune_dataset.py
git diff --cached --check
git commit -m "feat(research): freeze manual hard negative matches"
```

---

### Task 3: Select before remote materialization and immutable freeze

**Files:**
- Modify: `backend/finetune/materialize_pairs.py`
- Modify: `backend/finetune/freeze_dataset.py`
- Modify: `backend/finetune/build_dataset.py`
- Modify: `backend/tests/test_materialize_pairs.py`
- Modify: `backend/tests/test_finetune_dataset.py`

**Interfaces:**
- Adds `--donated-intake` and `--selection` to materialize/freeze CLIs.
- Changes `freeze_dataset(data_dir, out_dir, *, donated_intake_path=None, selection_path=None, synthetic_intake_path=SYNTHETIC_INTAKE)`.
- Expands `FreezeReport` with selected/excluded donated IDs, replacement reasons, and selection hash.

- [ ] **Step 1: Write failing materialization boundary tests**

Patch `prepare_dataset_bundles`, `_materialize`, and `get_supabase_client`. Assert preparation receives all completed bundles and both paths; `_materialize` receives only selected bundles. When preparation raises `ManifestError`, assert Supabase is never constructed. Keep direct `materialize(bundles, supabase)` unchanged.

Run:

```powershell
uv run pytest tests/test_materialize_pairs.py -k "selection or controlled_inputs" -v
```

- [ ] **Step 2: Filter before the first remote call**

Add optional path flags, load bundles, and call `prepare_dataset_bundles` before `get_supabase_client()`. Catch `CorpusError` and `ManifestError` through the existing nonzero CLI path. No automatic remote deletion is introduced; later withdrawal cleanup stays under the approved retention procedure.

```python
bundles = load_completed_bundles(args.data)
selected, _, _ = prepare_dataset_bundles(
    bundles, args.donated_intake, args.selection
)
summary = _materialize(selected, get_supabase_client(), BUCKET, args.data)
```

- [ ] **Step 3: Write failing freeze-selection tests**

Extend production fixture helpers with valid current `intake_sha256`. Assert:

- omitted controlled inputs fail before annotation fetch;
- unselected backup and withdrawn/replaced primary contribute no copied asset, annotation requirement, manifest record, or count;
- annotation rows for excluded bundles are ignored, while unknown rows outside all bundles still fail;
- selected stories still require complete annotation truth;
- validated mappings create all and only mapped target-scene negatives;
- production donation allocation is exactly 4/3/3, never 5/5/5;
- `freeze_report.json` records sorted selected/excluded IDs, reasons, and exact selection SHA-256.

- [ ] **Step 4: Apply selection before every downstream operation**

After `load_completed_bundles`, call `prepare_dataset_bundles`. All bundle validation, asset preflight/copy, pair map, annotation consensus, record construction, counts, and pinned versions receive only selected bundles. IDs belonging to excluded bundles may be discarded from fetched annotations; genuinely unknown IDs still fail.

Expand the report compatibly:

```python
selected_donated_stories: list[str] = Field(default_factory=list)
excluded_donated_stories: list[str] = Field(default_factory=list)
replacement_reasons: dict[str, str] = Field(default_factory=dict)
selection_sha256: str | None = None
```

Validate hard-negative mapping/time before `build_dataset`, then pass the validated dict. Fixture freeze uses an explicit empty mapping and needs no controlled input.

```python
matches = {} if selection is None else validate_hard_negative_matches(
    selected_bundles, selection, annotations, pilot_pairs
)
records = build_dataset(
    [(bundle.memory, bundle.split, bundle.provenance) for bundle in selected_bundles],
    out_path=staged / "manifest.jsonl",
    annotation_rows=annotations,
    adjudicator_ids=adjudicators,
    pilot_pair_ids=ignored_pairs,
    image_root=Path("assets"),
    hard_negative_matches=matches,
)
```

- [ ] **Step 5: Wire freeze CLI and verify**

Pass `--donated-intake` and `--selection` into `freeze_dataset` as keyword arguments. Add an exact-call CLI assertion.

```powershell
uv run pytest tests/test_corpus_io.py tests/test_dataset_selection.py tests/test_materialize_pairs.py tests/test_finetune_dataset.py tests/test_finetune_manifest.py -v
uv run ruff check finetune/corpus_io.py finetune/dataset_selection.py finetune/materialize_pairs.py finetune/build_dataset.py finetune/freeze_dataset.py tests/test_corpus_io.py tests/test_dataset_selection.py tests/test_materialize_pairs.py tests/test_finetune_dataset.py
```

- [ ] **Step 6: Commit Task 3**

```powershell
git add -- finetune/dataset_selection.py finetune/materialize_pairs.py finetune/freeze_dataset.py finetune/build_dataset.py tests/test_dataset_selection.py tests/test_materialize_pairs.py tests/test_finetune_dataset.py
git diff --cached --check
git commit -m "feat(research): bind freeze to current donor selection"
```

---

### Task 4: Canonical paths, preregistration amendment, and runbook

**Files:**
- Modify: `backend/finetune/build_corpus.py`
- Modify: `backend/finetune/materialize_pairs.py`
- Modify: `backend/finetune/build_dataset.py`
- Modify: `backend/finetune/manifest.py`
- Modify: `backend/finetune/to_llamafactory.py`
- Modify: `backend/finetune/train_qlora.yaml`
- Modify: `backend/tests/test_finetune_corpus.py`
- Modify: `backend/tests/test_finetune_manifest.py`
- Modify: `backend/tests/test_finetune_llamafactory.py`
- Modify: `backend/tests/test_research_integrity.py`
- Modify: `docs/product/PREREGISTRATION_OBJ4.md`
- Modify: `docs/capstone/research_runbook.md`
- Modify: `docs/specs/research-corpus-operations.md`
- Modify: `docs/specs/judge-finetune.md`

**Interfaces:**
- Mutable defaults become `data/judge/corpus`.
- Initial named training freeze is `data/judge/freezes/obj4-v1`.
- Real-artifact tests require explicit `STORYBUDDY_JUDGE_FREEZE_DIR`; ordinary tests never discover/open a held-out freeze.

- [ ] **Step 1: Write failing path tests**

```python
assert build_corpus.DATA_DIR.as_posix().endswith("data/judge/corpus")
assert materialize_pairs.DATA_DIR == build_corpus.DATA_DIR
assert local_image_path("judge-01/ref.png", "ref") == (
    "data/judge/corpus/ref/judge-01_ref.png"
)
```

Change the `dataset_artifacts` session fixture to skip unless `STORYBUDDY_JUDGE_FREEZE_DIR` is set, then read every artifact only from that exact directory. Add a helper test that root `data/judge` is never selected implicitly.

Run the focused assertions and confirm they fail against current root defaults.

- [ ] **Step 2: Align defaults without adding a pointer artifact**

Set `build_corpus.DATA_DIR`, `materialize_pairs.DATA_DIR`, `manifest.DATA_ROOT`, and `build_dataset --data` to the corpus subdirectory. Set `to_llamafactory` defaults and `train_qlora.yaml dataset_dir` to `data/judge/freezes/obj4-v1`. Keep the Batch 3 base-revision placeholder unchanged.

Run:

```powershell
uv run pytest tests/test_finetune_corpus.py tests/test_finetune_manifest.py tests/test_finetune_llamafactory.py tests/test_research_integrity.py -v
```

Expected: deterministic checks pass; real artifacts skip without the explicit environment variable.

- [ ] **Step 3: Append the dated preregistration amendment**

Under `PREREGISTRATION_OBJ4.md` §12, add `2026-08-24 — Intake-assigned splits and fail-closed backup replacement`. State that zero held-out results, donated corpus entries, study labels, and fine-tunes existed at amendment time. Explicitly supersede—without deleting or silently editing—the earlier seeded-assignment sentence and the 2026-08-22 instruction to report imbalance. State the implemented rules: intake-assigned propagated splits and freeze failure unless a vacated slot has one approved unused same-style backup preserving 10 stories and 4/3/3.

- [ ] **Step 4: Update the existing runbook with the exact sequence**

Retain all unchecked governance gates. Add, from `backend/`:

```powershell
uv run python -m finetune.build_corpus --fixture --limit 1 --out <temporary-fixture-directory>
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --limit 3 --max-usd 1.50 --price-per-call <pinned-conservative-price>
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --max-usd 25 --price-per-call <same-pinned-price>
uv run python -m finetune.build_corpus --corpus ../data/judge/intake/donated.json --out ../data/judge/corpus --max-usd 25 --price-per-call <same-pinned-price>
uv run python -m finetune.build_dataset --candidate-report --data ../data/judge/corpus
uv run python -m finetune.materialize_pairs --data ../data/judge/corpus --donated-intake ../data/judge/intake/donated.json --selection ../data/judge/intake/dataset_selection.json
uv run python -m finetune.build_dataset --reconcile-only
uv run python -m finetune.build_dataset --freeze --data ../data/judge/corpus --donated-intake ../data/judge/intake/donated.json --selection ../data/judge/intake/dataset_selection.json --out ../data/judge/freezes/obj4-v1
```

Mark angle-bracket values as operator inputs, not copy-ready literals. State that `obj4-v1` is immutable; a legitimate pre-training change uses a new named directory and a deliberate config update. Add the five visual comparison dimensions, hard-negative freeze-before-annotation gate, replacement evidence rule, test-unopened rule, three-seed validation-only development, and one-time held-out evaluation. Do not create a second guide.

- [ ] **Step 5: Reconcile specs and scan contradictions**

Update only truthful implementation names/status in the two owning specs. Do not mark governance, paid smoke, training, or held-out evaluation complete.

```powershell
rg -n "data/judge/(runs|manifest\.jsonl|train\.json|val\.json|test\.json)|dataset_dir: data/judge$|seeded assignment|achieved imbalance" backend docs
git diff --check
```

Expected: historical split/imbalance hits remain visible only with the amendment that supersedes them; no live training command consumes mutable `data/judge`.

- [ ] **Step 6: Commit Task 4**

```powershell
git add -- finetune/build_corpus.py finetune/materialize_pairs.py finetune/build_dataset.py finetune/manifest.py finetune/to_llamafactory.py finetune/train_qlora.yaml tests/test_finetune_corpus.py tests/test_finetune_manifest.py tests/test_finetune_llamafactory.py tests/test_research_integrity.py ../docs/product/PREREGISTRATION_OBJ4.md ../docs/capstone/research_runbook.md ../docs/specs/research-corpus-operations.md ../docs/specs/judge-finetune.md
git diff --cached --check
git commit -m "docs(research): align canonical dataset workflow"
```

---

### Task 5: Zero-cost proof, full verification, review, and cleanup

**Files:**
- Modify: `tasks/todo.md`
- Delete after successful completion: `docs/specs/plans/2026-08-24-dataset-validity-safeguards.md`

**Interfaces:**
- Produces only verification evidence and the final task outcome.

- [ ] **Step 1: Run focused verification**

Run from `backend/`:

```powershell
uv run pytest tests/test_corpus_io.py tests/test_dataset_selection.py tests/test_finetune_corpus.py tests/test_materialize_pairs.py tests/test_finetune_dataset.py tests/test_finetune_manifest.py tests/test_finetune_llamafactory.py tests/test_research_integrity.py -v
uv run ruff check .
```

- [ ] **Step 2: Run a zero-cost fixture and candidate report**

Use one explicit temporary directory:

```powershell
$batch2Fixture = Join-Path $env:TEMP "storybuddy-batch2-fixture"
if (Test-Path -LiteralPath $batch2Fixture) { Remove-Item -LiteralPath $batch2Fixture -Recurse -Force }
uv run python -m finetune.build_corpus --fixture --limit 1 --out $batch2Fixture
uv run python -m finetune.build_dataset --candidate-report --data $batch2Fixture
uv run pytest tests/test_finetune_dataset.py -k "writes_complete_immutable_artifacts" -v
```

Expected: one fixture story, zero paid images, `usd_high=0.000`, valid report JSON, and fixture freeze passing without production control files.

- [ ] **Step 3: Run full backend verification**

```powershell
uv run pytest
```

Expected: all deterministic tests pass; only documented environment-dependent RLS, provider-smoke, and opt-in real-artifact tests skip/deselect.

- [ ] **Step 4: Review against standards and both specs**

Use `superpowers:requesting-code-review` against fixed base `49cec25f0c04218aaa3b6acfff8e4864450af787`. Review Standards and Spec separately. Fix each confirmed Critical or Important finding with a failing regression first, then rerun Steps 1–3.

- [ ] **Step 5: Record outcome and delete this disposable plan**

Record exact test counts, Ruff, fixture image/USD totals, review outcome, and what remained unverified in `tasks/todo.md`. Explicitly state that no paid call, real donor intake, held-out evaluation, or live database/Storage mutation ran. Residual gates are genuine institutional approvals and Batch 3 model/toolchain/evaluation work.

```powershell
Set-Location ..
git rm -- docs/specs/plans/2026-08-24-dataset-validity-safeguards.md
git diff --check
git add -- tasks/todo.md
git commit -m "chore(research): close dataset validity batch"
```

## Completion boundary

Batch 2 is complete when the strict selection artifact controls hard negatives and donated membership before materialization/freeze, mutable and immutable paths are separate, the frozen preregistration is visibly amended, and deterministic verification is green. It does not authorize real donated intake or paid generation, and it does not make QLoRA ready: institutional approvals and Batch 3 pins/evaluation remain stop gates.
