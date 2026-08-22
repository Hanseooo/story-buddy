# Feature Spec — Research Corpus Operations

**Status:** draft · **Phase:** 2.5 · **Owner:** `backend/finetune/`
**Derived from:** `judge-finetune.md`, `annotation-surface.md`, `PREREGISTRATION_OBJ4.md`, ADR-026, ADR-027

## 1. Purpose

Define the auditable path from consented, de-identified stories to a frozen Objective-4 dataset without
creating a second image-generation pipeline. The existing production graph remains the only Fal caller.

Success means that every training or evaluation pair can be traced to an approved story, an exact pair of
hashed image bytes, two independent annotations and any required adjudication; a rerun performs no duplicate
paid draw or upload; and cumulative Fal spend cannot exceed USD 30.

## 2. Binding research boundaries

- Synthetic stories supply train and validation. Donated stories supply held-out test only.
- Split by character lineage, never by pair. Constructed negatives are train-only and require no new image.
- Donated material cannot enter the pipeline until guardian consent, child assent, manual PII redaction and
  independent redaction review are recorded.
- Raw submissions and the identity-to-receipt ledger never enter the repository, Supabase research storage,
  logs, checkpoints or model artifacts.
- The closed annotation taxonomy cannot change after real annotation begins.
- Annotators, training and evaluation consume the same hashed asset bytes.
- The held-out donated test is opened only after training configuration and checkpoint selection are frozen.
- Every story declares exactly one selectable ADR-042 style ID: `cel`, `gouache` or `cut_paper`. Its
  canonical references and scenes remain in that style; legacy-only `comic` is excluded.

## 3. Artifact ownership

| Artifact | Canonical home | Required contents |
|---|---|---|
| Identity/consent ledger | Ethics-approved restricted store, outside StoryBuddy | Contact record ↔ random receipt code; consent/assent evidence |
| Story intake | Checked-in synthetic JSON or de-identified controlled donated JSON | Opaque `story_id`, text, declared roster, provenance/split/role, frozen style, and donated-only approvals |
| Corpus run | `data/judge/` (gitignored) | Completed `StoryMemory`, split/provenance, run metadata, telemetry and asset hashes |
| Research assets | Private Supabase Storage | PNG canonical references and WebP q≈82 scenes per ADR-027 |
| Pair queue | `research_pairs` | Opaque deterministic pair ID and two private Storage paths; no provenance exposed to annotators |
| Labels | `annotations` | Two independent ordinary labels and adjudicator label only on disagreement |
| Frozen dataset | `data/judge/` plus controlled snapshot | Manifest, split files, statistics, hashes, exclusions and pinned run configuration |

## 4. End-to-end flow

### 4.1 Consent and sanitized intake

Each donor receives a random receipt code. Withdrawal is supported by that code until dataset freeze. After
freeze, a withdrawal excludes the story from future training, but the materials must disclose that an
already-trained model cannot selectively unlearn one example.

The intake validator rejects a donated record unless all approval fields are affirmative. Primary versus
backup test stories is selected before generation or model outcomes are observed. A backup may replace a
primary only for withdrawal, unusable/de-identification failure, terminal pipeline failure or inadequate
character yield under a recorded rule—never because the judge performs poorly.

Both sources use one JSON-list contract; stories are data, not Python edits. Synthetic input is the checked-in
`backend/finetune/corpus_synthetic.json`. Donated input is a separately controlled, gitignored JSON file that
contains only redacted text and research metadata. It never contains a name, contact detail, receipt code or
raw submission. The minimum record shape is:

```json
[
  {
    "story_id": "syn-001",
    "text": "De-identified story text...",
    "declared_characters": ["Quill", "Bok-Bok"],
    "declared_non_human": ["Quill", "Bok-Bok"],
    "provenance": "synthetic",
    "split": "train",
    "candidate_role": "not_applicable",
    "style_preset_id": "cel"
  }
]
```

Donated records additionally require affirmative `guardian_consent`, `child_assent`,
`manual_pii_redaction` and `independent_redaction_review`, plus `withdrawal_state` and a selection-freeze
timestamp. Synthetic records must not fabricate those donated-only fields. `declared_non_human` must be a
subset of `declared_characters`; names are fictional roster labels from the already-redacted story, not donor
identities. After generation, the declared roster is reconciled case-insensitively with the final
`StoryMemory.characters`. A missing, unexpected or differently classified character quarantines the story
for manual review before pair materialization; it is never silently rewritten after seeing judge output.

### 4.2 Style allocation and control

Style is a nuisance variable to control, not the fine-tune target. The 30 synthetic stories are frozen as 24
train and 6 validation stories, with 8 train and 2 validation stories in each of `cel`, `gouache` and
`cut_paper`. Assignment considers character diversity before any paid generation and never changes in
response to generated quality or judge behavior.

The 15 donated candidates are assigned five per style before generation. The 10 primary slots are allocated
4 Gouache, 3 Cel and 3 Cut-paper; the five backups are 1 Gouache, 2 Cel and 2 Cut-paper. Gouache receives the
extra primary slot because it is the product default (ADR-042), not because of generated outcomes.
A replacement fills the same style slot when an eligible backup exists. If it cannot, report the achieved
imbalance; do not restyle an already generated character or select by outcome. If all backups are admitted to
increase held-out power before labeling, the resulting 15-story candidate set is 5/5/5.

Constructed negatives must match `style_preset_id`. Overall held-out performance remains primary. Per-style
metrics are pre-declared exploratory diagnostics because the held-out character count is too small for strong
style-specific claims.

### 4.3 Corpus generation

`finetune.build_corpus` continues to drive `pipeline.graph.build_graph()` and is the sole corpus Fal caller.
It must materialize, for every completed story:

- the full final `StoryMemory`;
- provenance and assigned split;
- code commit, schema, prompt, model and style identifiers;
- attempted, completed, failed and uncertain-billing paid calls;
- canonical PNG references and finalized WebP q≈82 scenes;
- SHA-256, MIME magic bytes, dimensions and byte length per asset.

A story is complete only when memory, inventory and files reconcile. Completed stories are immutable and
free to resume. Partial stories resume from their LangGraph checkpoint. Untrustworthy checkpoint state is
quarantined rather than silently regenerated or pooled.

### 4.4 Queue materialization

One idempotent command reads completed memories, uploads the exact corpus files to private Supabase Storage
and inserts deterministic opaque `research_pairs`. Existing identical path/hash records are skipped. A
pair-ID, path or hash conflict is terminal. The command does not generate images or labels.

### 4.5 Annotation and adjudication

The existing annotation surface remains authoritative: short-lived signed URLs, blinded ordering, two
different ordinary annotators, immutable first writes and adjudication on disagreement across any complete
label field. A signed-URL or image-load failure makes a pair unlabelable.

Pair status is a cache, not ground truth. Because label insertion and status update are not transactional,
export derives truth from annotation rows and a reconciliation command repairs stale statuses.

### 4.6 Freeze and conversion

One export command loads completed memories, derives consensus, creates train-only constructed negatives,
runs manifest guards, verifies every local asset hash and produces the LLaMA-Factory files. It fails on:

- missing, duplicate or excess ordinary labels;
- unresolved, unnecessary or multiple adjudications;
- missing assets, MIME mismatch or hash mismatch;
- character leakage across splits;
- synthetic test data or constructed validation/test data;
- pair/memory mismatch, duplicate IDs or unknown exclusions.
- absent/unknown style IDs, reference/scene style disagreement, allocation drift or a constructed negative
  whose two characters have different styles;
- unresolved declared-roster versus `StoryMemory.characters` reconciliation.

The freeze report records dataset SHA-256, counts by story/character/split/class/reason, adjudication rate,
exclusions and all pinned software/model/prompt versions.

## 5. Encoding and storage

ADR-027 is binding: Supabase remains the asset store, canonical references remain PNG and scenes are WebP at
approximately quality 82. R2 is not a fallback. Encoding happens exactly once before hashing, upload,
annotation and training. Filename extensions are not trusted; magic bytes and decoded dimensions are checked.

## 6. Spend policy

- USD 25 is the working Fal allocation; USD 30 is the absolute campaign ceiling.
- A zero-cost fixture run must pass first.
- A three-story synthetic smoke run is capped at USD 1.50.
- Pricing is pinned at campaign start and budgeting uses the conservative per-call price.
- A story starts only if its maximum permitted draws fit the remaining reserve.
- A timeout or uncertain billing result stops the campaign for reconciliation; it is not blindly retried.
- The USD 25–30 reserve is released only to finish a story or materially improve character coverage.
- Spend stopping cannot silently change split rules, taxonomy or held-out membership.

## 7. Pilot cleanup

The 17 visual pilot pairs are disposable test data. A privileged cleanup command must support dry-run and an
explicit confirmation. It deletes pilot annotations first, then pilot pair rows, then `research/pilot/*`
objects, and verifies all three counts are zero. Deleting only pair rows is forbidden: `annotations.pair_id`
has no foreign key to `research_pairs`, so orphaned labels could later escape pilot exclusion.

## 8. Training and evaluation handoff

School hardware is preferred only after recording GPU model/VRAM, RAM, storage, OS, driver/CUDA versions and
permitted runtime. A loader plus forward-pass smoke test precedes training. School and cloud paths use the
same frozen dataset and scientific configuration; hardware-only batch/accumulation changes are recorded.

Train seeds 0, 1 and 2, select checkpoints on synthetic validation only, then evaluate the donated held-out
test once under the pre-registered procedure. A confirmed evaluation-code defect permits only the documented
controlled rerun. Deployment remains a separate decision and is not required for Objective 4 to stand.

## 9. Phases and gates

1. Governance: approve consent/assent and receipt process; freeze story/split/style assignments; build and
   verify the bounded pilot cleanup before clearing pilot data.
2. Zero-cost engineering: ADR-027 encoding, corpus persistence, intake validation, queue materialization,
   status reconciliation and freeze CLI pass end-to-end on fixtures.
3. Intake: recontact donors; redact, independently review and freeze 10 primary + 5 backup candidates.
4. Paid smoke: three synthetic stories; measure cost, failures, bytes, latency and signed delivery.
5. Generation: synthetic train/validation, then donated held-out test, within the USD 30 ceiling.
6. Annotation: calibration, dual labels, adjudication and drift check.
7. Freeze: integrity report and adviser sign-off.
8. Training: school first, cloud fallback; three seeds.
9. Evaluation: frozen baselines and one-time donated test; report uncertainty by character cluster.

No phase advances while its gate is unresolved.

## 10. Stop conditions and residual risks

Stop before spending or advancing when consent language lacks approval, a story cannot be confidently
de-identified, the image substrate changes after annotation starts, billing is uncertain, the hard cap cannot
safely finish a started story, or held-out character yield is inadequate for the registered claim.

Residual risks to report rather than hide: WebP and cost projections are not measurements until the paid
smoke; donated character yield is unknown before generation; rare failure reasons may be underpowered; and
school hardware may force the predeclared cloud fallback.
