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

## 3. Artifact ownership

| Artifact | Canonical home | Required contents |
|---|---|---|
| Identity/consent ledger | Ethics-approved restricted store, outside StoryBuddy | Contact record ↔ random receipt code; consent/assent evidence |
| Sanitized intake | De-identified controlled research file | `donation_id`, redacted text, consent/assent, redaction review, provenance, primary/backup, withdrawal state |
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

### 4.2 Corpus generation

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

### 4.3 Queue materialization

One idempotent command reads completed memories, uploads the exact corpus files to private Supabase Storage
and inserts deterministic opaque `research_pairs`. Existing identical path/hash records are skipped. A
pair-ID, path or hash conflict is terminal. The command does not generate images or labels.

### 4.4 Annotation and adjudication

The existing annotation surface remains authoritative: short-lived signed URLs, blinded ordering, two
different ordinary annotators, immutable first writes and adjudication on disagreement across any complete
label field. A signed-URL or image-load failure makes a pair unlabelable.

Pair status is a cache, not ground truth. Because label insertion and status update are not transactional,
export derives truth from annotation rows and a reconciliation command repairs stale statuses.

### 4.5 Freeze and conversion

One export command loads completed memories, derives consensus, creates train-only constructed negatives,
runs manifest guards, verifies every local asset hash and produces the LLaMA-Factory files. It fails on:

- missing, duplicate or excess ordinary labels;
- unresolved, unnecessary or multiple adjudications;
- missing assets, MIME mismatch or hash mismatch;
- character leakage across splits;
- synthetic test data or constructed validation/test data;
- pair/memory mismatch, duplicate IDs or unknown exclusions.

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

1. Governance: approve consent/assent and receipt process; inventory and clear pilot data.
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
