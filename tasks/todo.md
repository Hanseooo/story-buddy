# Current Task: Objective-4 dataset readiness engineering

- [x] Revalidate the earlier readiness audit against current HEAD.
- [x] Separate external governance gates from engineering readiness work.
- [x] Compare staged, combined and documentation-first approaches; obtain approval for staged delivery.
- [x] Record and self-review the Batch 1 corpus-integrity design.
- [x] Obtain owner review of the written Batch 1 design.
- [x] Write and self-review the disposable TDD implementation plan for Batch 1.
- [x] Execute and verify Batch 1 in a separate implementation cycle.
- [x] Design and implement Batch 2 dataset-validity safeguards.
  - [x] Revalidate hard-negative, withdrawal, role, split and path blockers against current HEAD.
  - [x] Approve the full canonical-dataset boundary and manual frozen hard-negative mapping.
  - [x] Approve the controlled selection artifact, fail-closed validation and canonical path flow.
  - [x] Record and self-review the Batch 2 design in the owning research specs.
  - [x] Obtain owner review of the written Batch 2 spec.
  - [x] Write the disposable TDD implementation plan.
  - [x] Implement and verify Batch 2.
- [x] Close verified Batch 2 review findings.
  - [x] Bind copied bundle metadata to its current intake record.
  - [x] Apply the hard-negative freeze timestamp gate to all non-pilot annotations.
  - [x] Reject withdrawal replacements for active primaries.
  - [x] Clarify that hard-negative selection covers reference-bearing characters.
  - [x] Run focused tests, backend lint, and the full backend suite.
- [x] Close the final Batch 2 reproducibility findings.
  - [x] Add a failing regression for freezing the exact selection artifact.
  - [x] Copy and hash-verify `dataset_selection.json` inside the immutable freeze.
  - [x] Reconcile the runbook with the preregistered Rung-D second-read exception.
  - [x] Run focused and full verification, review, and commit only Batch 2 files.
- [ ] Design and implement Batch 3 training/evaluation execution.
- [ ] Finalize the existing research runbook as the sole operator guide.

## Success criteria

Zero-cost fixture work proves exact-boundary completion, fail-closed quarantine and auditable recovery without
resetting spend; immutable intake bytes bind every corpus bundle; dataset freeze enforces the preregistered
negative/selection rules; training and evaluation fail closed on missing pins or premature test access; and
the canonical runbook contains the complete executable sequence without duplicating another permanent guide.

## Batch 2 Outcome — Dataset Validity Safeguards

Implemented and verified in Tasks 1–5:
- **Strict selection artifact & fail-closed donor replacement:** `DatasetSelection` (`dataset_selection.json`) controls primary donors (4 Gouache, 3 Cel, 3 Cut-paper) and documented backup replacements with matching art styles and valid non-blank justifications.
- **Intake mode separation:** `corpus_io.load_intake` supports `mode="generation"` (rejecting withdrawn stories) vs `mode="freeze_audit"` (accepting them to locate and audit exclusions).
- **Frozen manual hard negatives:** Cross-character train-split pairs validated for same species, same style, >=1 finalized target scene, and `hard_negatives_frozen_at` preceding all non-pilot annotations.
- **Pre-materialization bundle filtering:** `prepare_dataset_bundles()` filters and validates bundles before any Supabase client initialization or remote network calls in `materialize_pairs.py` and `freeze_dataset.py`.
- **Immutable freeze reporting:** `FreezeReport` captures `selected_donated_stories`, `excluded_donated_stories`, `replacement_reasons`, and `selection_sha256`.
- **Self-contained selection audit:** The immutable freeze snapshots the exact `dataset_selection.json` bytes, verifies their SHA-256 against the validated selection, and rejects annotation timestamps that do not strictly follow the hard-negative freeze.
- **Canonical workspace paths:** Root `data/judge` references separated into `data/judge/corpus`, `data/judge/intake`, and `data/judge/freezes/obj4-v1`.
- **Preregistration amendment & runbook:** Added 2026-08-24 dated amendment to `PREREGISTRATION_OBJ4.md` §12 superseding earlier seeded assignment/imbalance clauses; updated `research_runbook.md` with the 8-step pipeline.

Verification:
- Focused tests: 218 passed, 7 skipped in `test_corpus_io.py`, `test_dataset_selection.py`, `test_finetune_corpus.py`, `test_materialize_pairs.py`, `test_finetune_dataset.py`, `test_finetune_manifest.py`, `test_finetune_llamafactory.py`, `test_research_integrity.py`.
- Full backend suite: 1,139 passed, 80 skipped (RLS/remote DB), 6 deselected smoke tests, 0 failed (`uv run pytest`).
- Backend lint: `uv run ruff check .` passed with 0 errors.
- Frontend suite: 380 passed across 42 files (`pnpm lint && pnpm test`).
- Zero-cost fixture: 1 story completed, 0 paid images spent, `usd_high="0.000"`, valid candidate report JSON, fixture freeze passed without production files.
- Final senior code review: 0 Critical and 0 Important issues; ready to merge after the strict timestamp-boundary regression was added.
- Review follow-up: bundle metadata now matches intake fields, timestamp gating sees every non-pilot annotation,
  active primaries cannot cite withdrawal, the exact selection artifact is frozen and hash-verified, the Rung-D
  exception is explicit, and the owning spec names reference-bearing characters explicitly.
- Confirmed no live provider, paid Fal call, real donor intake, live database/Storage mutation, or `.env` access occurred.

## Batch 1 Outcome — Research Corpus Integrity

Implemented and verified in Tasks 1–3:
- **Intake binding:** `intake_sha256()` computes canonical SHA-256 over immutable intake fields (excluding mutable `withdrawal_state`), persisted in `run_metadata` and re-verified on bundle load and resume.
- **Paid-call boundary & quarantine:** The shared `_fal_event_sink` rejects attempts past the draw limit before submission (`StoryBudgetStopped`), and `run_story()` explicitly outputs `completed`, `budget_stopped`, or `quarantined` (`resume_exhausted`, `billing_uncertain`, `invalid_terminal`, `intake_mismatch`).
- **Quarantine recovery:** `--resume-quarantined <story_id>` and `--acknowledge-uncertain-billing <story_id>` validate checkpoint state and intake digest, record UTC acknowledgment timestamp, and preserve all attempted spend at the pinned conservative price.

Verification:
- Focused tests: 76 passed (36 in `test_corpus_io.py`, 40 in `test_finetune_corpus.py`).
- Full backend suite: 1,084 passed, 80 intentionally skipped (RLS/remote DB tests requiring live credentials), 6 deselected smoke tests, 1 pre-existing Starlette deprecation warning.
- Backend lint: `uv run ruff check .` passed with 0 errors.
- Zero-cost CLI fixture: 1 story completed, 0 images spent, `usd_high="0.000"`, and valid bundle reference in `build_state.json`.
- Confirmed no live provider, paid Fal call, live database mutation, or `.env` access occurred.
- Remaining blockers: Batch 2 dataset-validity safeguards (construct train negatives, split lineage guards, freeze report) and Batch 3 training/eval execution.

---

# Current Task: Storybook deletion implementation planning

- [x] Explore storybook ownership, UI surfaces, job/worker lifecycle, database relationships, checkpoints, Storage objects, telemetry, and governing decisions.
- [x] Resolve who may delete which storybooks and whether deletion is hard, soft, or staged.
- [x] Compare safe deletion designs and obtain owner approval for the selected data lifecycle.
- [x] Record the approved architecture in ADR-044 and reconcile D-J's decision surfaces.
- [x] Write and self-review the durable feature spec.
- [ ] Write and self-review the TDD-first implementation plan under `docs/specs/plans/`.

## Success criteria

The approved plan names every affected persistence layer and user surface; prevents cross-classroom deletion,
worker resurrection, orphaned Storage/checkpoint data, and silent loss of required research/audit evidence; and
provides exact red-green tests plus live Supabase verification without changing runtime code or external data.

## ADR review / outcome

ADR-044 selects child-owned hard deletion for quiescent `complete`, `failed`, and `awaiting_confirm` jobs.
Deletion stays behind authenticated FastAPI, uses `worker_finished_at` as the no-producer barrier, moves the row
to `deleting`, and delegates idempotent Storage/checkpoint/Langfuse/row cleanup to existing RQ. Direct browser
DELETE policies, teacher per-book deletion, soft-delete metrics retention, and in-flight cancellation are out.

ADR verification passed: required sections and escape hatch are present; ADR numbering is unique through 044;
the index target resolves; D-J has no open backlog row; placeholder, runtime-change, and targeted diff checks are
clean. No application tests ran because this session changed decision documentation only. The feature spec and
implementation plan remain pending and must be authored in a fresh session per the architecture-session gate.

## Feature-spec outcome — 2026-08-24

Drafted `docs/specs/storybook-deletion.md` from accepted ADR-044. It fixes the per-book boundary,
quiescence/CAS rules, immediate RLS revocation, four-store cleanup order, retry semantics, UI states,
deterministic tests, live Supabase proof, and explicit retention limits. Owner review is pending;
the implementation plan remains blocked until the spec is approved.

---

# Current Task: ISO/IEC 25010 readiness audit and remediation guide

- [x] Re-verify promised product and capstone scope, especially narration and PDF export.
- [x] Write a comprehensive, evidence-backed, AI-agent-friendly readiness audit.
- [x] Separate confirmed blockers, conditional scope gaps, evidence gaps, and rejected findings.
- [x] Create one sanitized public GitHub umbrella issue without disclosing sensitive mechanics.
- [x] Verify document links, issue content, diff hygiene, and record the outcome.

## Success criteria

The audit uses the ISO/IEC 25010:2023 nine-characteristic model, distinguishes implementation defects from
unproven evaluation claims and optional scope, gives agents exact constraints and verification gates, and
publishes only a sanitized public issue. Narration and export are classified from canonical project sources
rather than assumed to be universal ISO requirements.

## Review / outcome

Created `docs/capstone/iso_iec_25010_readiness_audit.md`, a commit-pinned ISO/IEC 25010:2023 readiness report with
system/study context, nine-characteristic matrix, scope gates, public/private finding groups, rejected findings,
remediation workstreams, an Objective-5 instrument gate, an agent ticket contract, and evidence limitations.
Narration and PDF export are both required but undemonstrated under current accepted sources; PDF is eligible for
formal de-scope only through a new superseding ADR and full promise/instrument reconciliation.

Created public umbrella issue `#68` (`ISO/IEC 25010:2023 readiness program and evidence gates`) with the
`documentation` label. A disclosure review replaced sensitive mechanics with opaque private work IDs; the public
document and issue retain only safe classifications and exit criteria. Verification confirmed all 11 local
Markdown links resolve, forbidden sensitive-mechanics patterns are absent, issue #68 is open with corrected ADR
wording, and `git diff --check` reports no patch errors. Application tests were not rerun for this docs-only change;
the audit records the earlier green deterministic baseline and explicitly states that raw logs/live integration
evidence were not retained or run in this step.

---

# Current Task: Expert-evaluation decision brief HTML artifact

- [x] Explore the existing research artifact, Cobalt Playroom design language, canonical evaluation docs, and recent changes.
- [x] Clarify whether the artifact is a researcher decision brief, an administration-ready instrument, or both: include both, with the instrument marked pending adviser approval.
- [x] Compare artifact approaches and obtain approval for the recommended structure and visual direction.
- [x] Write and self-review the approved design document.
- [x] Follow the owner's instruction to implement immediately without another planning round.
- [x] Build and verify the standalone HTML artifact.

## Success criteria

Researchers can understand StoryBuddy's current evaluation design, the implemented pipeline, what CANVAS /
ContinuityEval can and cannot support, the evidence and limitations behind that judgment, the recommended
next actions, and any decisions requiring adviser approval. The artifact must remain honest about unresolved
methodological and documentation gaps and must not silently change a frozen ADR or research instrument.

## Review / outcome

Created the standalone root artifact `expert_evaluation_decision_brief.html`. It combines the research decision,
implemented StoryBuddy pipeline, exact-questionnaire transfer test, source-by-source evidence ledger, CANVAS /
ContinuityEval review, use/adapt/reject recommendations, edge cases, procedure, printable Tool B draft, coding guide,
approval gates, and linked references. Tool B is explicitly marked pending adviser/content review; the artifact does
not change the accepted methodology, a frozen ADR, or pipeline behavior.

Verification confirmed all nine required content landmarks, 28 unique IDs, 14 valid internal fragment links, one
`h1`, zero external asset dependencies, zero placeholder markers, and valid inline JavaScript syntax. Headless Chrome
rendered the artifact successfully at 1440 px and 500 px widths; both renders were visually inspected. `git diff
--check -- expert_evaluation_decision_brief.html` reported no whitespace errors. Application tests were not run
because this is an isolated documentation artifact with no application-code or dependency changes.

---

# Current Task: Expert-evaluation literature and pipeline-context review

- [x] Map the capstone objectives, methodology, expert-evaluation instruments, and implemented pipeline.
- [x] Delegate a read-only review of ContinuityEval and related expert-evaluation literature.
- [x] Compare the paper's constructs and prompts with StoryBuddy's research questions and outputs.
- [x] Report citation/adaptation guidance, instrument recommendations, and pipeline implications.

## Success criteria

The report accurately traces the current code and canonical capstone documents, distinguishes product
control signals from research outcome measures, assesses whether and how ContinuityEval may be cited or
adapted, and proposes the smallest defensible expert-evaluation design without changing code or frozen ADRs.

## Review / outcome

ContinuityEval is a useful cited source for continuity vocabulary and optional open-ended probes, but it is
not a drop-in expert-validation instrument: it is a VLM autorater for storyboard frame transitions. Its
hair/body rubric is human-centric, its prop denominator can conceal disappearances, and its validation prose
and Table 14 disagree on whether 100 or 50 transitions were sampled. StoryBuddy's accepted Objective-3 design
remains a three-validator, five-criterion open-ended interview analysed by content analysis; the repository
currently describes that instrument but contains no administerable question form.

Recommended minimum: operationalize one open-ended question per existing criterion, borrowing ContinuityEval's
visible-evidence, viewpoint/occlusion, recurring-character, recurring-prop and recurring-setting concepts without
adding a numeric score. Keep the runtime judge out of the outcome measure. No pipeline change is justified by
this literature review; cross-frame runtime checks would require a separate ADR/design session if expert evidence
later shows a repeated failure. Verification was read-only apart from this tracker update: canonical docs, graph,
contract and judge prompts were traced; arXiv metadata, CC BY 4.0 license, formulas and validation figures were
checked against arXiv. No application tests or paid/provider calls were run.

---

# Current Task: Research corpus review fixes

- [x] Verify the spend-cap and retry-asset findings against code, tests, specs, and issues.
- [x] Add a failing two-invocation regression test for completed-bundle spend.
- [x] Add a failing restart regression test for known failed-call spend.
- [x] Persist and restore campaign telemetry with pinned-price validation.
- [x] Resolve the retry dataset-composition choice with the owner, then fix it test-first.
- [x] Run focused tests, backend Ruff/full pytest, and record the outcome.

## Success criteria

Sequential corpus-build processes include completed and unfinished Fal attempts before reserving a
new story, never exceed the configured campaign ceiling, and reject invalid or price-drifted billing
state. Retry-containing bundles materialize under the owner-selected dataset policy. The two
maintainability-only findings remain unchanged.

## Outcome

The spend guard now restores completed-bundle and unfinished-story telemetry, persists each Fal
event through an atomic state-file replacement, retains the campaign total across invocations, and
fails closed on invalid counters or pinned-price drift. Pair construction now follows the canonical
finalized-scene policy: rejected retries remain in `StoryMemory` provenance, while only each scene's
`final_image_ref` is uploaded and annotated.

Both spend regressions and the retry-materialization regression failed on the old behavior and pass
after the fixes. Focused corpus/annotation verification passed 99 tests with 7 intentional skips;
full backend verification passed 1,069 tests with 80 skips and 6 deselected smoke tests; Ruff passed.
The existing Starlette/httpx deprecation warning remains. Frontend checks and paid provider smoke
tests were not run because no frontend, model, provider, or external-service behavior changed.

---

# Current Task: Research corpus operations design

- [x] Explore corpus, annotation, telemetry, ethics, storage ADR, and training context.
- [x] Clarify consent status, donated-test role, budget, storage posture, and pilot disposition.
- [x] Compare corpus-generation approaches and obtain approval for the staged diversity-first design.
- [x] Present and obtain approval for architecture, failure/cost controls, phases, and artifacts.
- [x] Write the canonical corpus-operations spec and consent/assent draft.
- [x] Update and verify the self-contained research-strategy HTML artifact.
- [x] Self-review all written artifacts for drift, ambiguity, placeholders, and broken links.
- [x] Commit the approved design documentation; ask the owner to review it before implementation planning.

## Success criteria

The written design provides an end-to-end, fail-closed lineage from consent through one-time evaluation;
preserves ADR-027's Supabase/PNG-reference/WebP-scene decision; caps Fal spend at USD 30; prevents pilot,
split, identity and byte-provenance leakage; and clearly separates ethics drafts from approved materials.

## Review outcome

Added the canonical `research-corpus-operations` spec, an explicitly unapproved guardian-consent/child-assent
draft, and a pointer from the existing ethics document. Updated the root HTML artifact to remove stale R2,
USD-20, 50–100-pair pilot and predictive-superiority claims. Independent review aligned pilot deletion with
the canonical spec and confirmed the missing `StoryMemory` materialization and queue bridge as implementation
gaps rather than claiming the existing scripts are end-to-end.

Verification: `git diff --check` passed; stale-claim grep returned no matches; the HTML parser confirmed 14
cards, balanced tags and the current title. The in-app browser render check was unavailable because its bridge
could not start, so visual rendering remains unverified. No code tests were run because this change is
documentation-only. Consent/assent administrative blanks are deliberate and the draft is marked do-not-use
until adviser, ethics and participating-school approval.

---

# Current Task: Annotation implementation review verification

- [x] Trace each review finding through specs, migrations, server actions, exporter, and tests.
- [x] Reject findings that conflict with intentional architecture; record the evidence.
- [x] Add failing regression tests for every confirmed behavior defect.
- [x] Apply the smallest fixes and update the owning annotation spec where behavior changes.
- [x] Run focused red/green checks and full frontend/backend verification.
- [x] Record the outcome, unverified external state, and residual risks.

## Success criteria

Dataset export hard-fails on incomplete or invalid non-pilot annotation states; adjudication accepts
only two independent ordinary labels; annotation ordering satisfies the documented per-annotator
randomization rule; signed-URL failures cannot present a labelable broken pair; and intentional
service-role access remains no broader than the approved blinded-queue design.

## Outcome

Confirmed and fixed the exporter hard-fail regressions, ordinary-annotator eligibility checks,
whole-queue deterministic ordering, signed-URL failure handling, and swallowed queue/status read or
write errors. Kept the authenticated server-action service-role seam: ordinary annotation RLS cannot
read the second annotator's row, while the server must compute pair consensus without exposing those
rows to either annotator.

The second-pass investigation found and fixed an additional blocker: Supabase returns at most 1,000
rows by default, but `fetch_annotations()` made one unpaginated request for a campaign expected to
produce 1,500–2,000+ rows. The exporter now reads stable ordered pages until exhausted, with a
1,001-row regression test and the annotation spec updated.

Verification: frontend focused action tests passed 42; full frontend suite passed 380 tests across
42 files; production build/type-check passed. Backend focused exporter tests passed 26; full backend
suite passed 973 tests, skipped 80 environment-dependent cases, and deselected 6 smoke tests. Frontend
lint and backend Ruff passed. Remote Supabase migration/RLS state remains unverified because the DB
integration tests require `SUPABASE_DB_URL` and skipped locally.

---

# Current Task: Production visual-output regression follow-up

- [x] Read project guidance, lessons, current pipeline/specs, production prompts/logs, and recent commits.
- [x] Delegate focused investigations of prompt flow, PII pseudonymization, and recent history/style changes.
- [x] Confirm the earlier comparison run and intended product priority with the owner.
- [x] Compare 2–3 root-cause fixes and obtain design approval before implementation.
- [x] Update the owning spec and self-review it.
- [x] Obtain written-spec approval from the owner through the current implementation request.
- [x] Write and execute a disposable implementation plan after the design gates passed.

## Success criteria

The approved design prevents one actor from surviving as both a character and object, stops
ownership or interaction from becoming an invented physical-holder instruction, preserves mandatory
PII protection, and treats comic-style quality as a measured variable rather than an assumed cause.

## Spec review outcome

Updated `docs/specs/visual-prompt-reliability.md` to drop explicit parenthetical actor aliases in
full, make `objects_present` explicit per frame, remove node-local object-event/holder carry-forward,
and preserve physical interactions only in the selected visual action. The exact Jamie/Bolt story
in explicitly selected Gouache remains the paid regression check.

## Implementation review outcome

The follow-up implementation now adds explicit selected-frame object rules to the segmentation
provider prompt, reuses the rendered direction once per scene, and adds deterministic coverage for
the prompt boundary plus a local Jamie/Bolt contract-shaped scene fixture. The exact production
story text is not present in the repository, so no exact Tier-B reproduction or paid Gouache call
was fabricated or run; that acceptance gate remains open.

The requested style-policy change cannot be included in this implementation: ADR-022 freezes three
selectable presets and Cel as the flagship default. Logged D-O in
`docs/product/DECISION_BACKLOG.md` for a dedicated superseding-ADR session. Presidio remains enabled;
canonical-reference timeout policy and raw-before-redaction storage remain separate follow-ups.

Verification: focused analyzer/segment tests passed (152); `uv run ruff check .` passed; full backend
tests passed (906 passed, 71 skipped, 6 deselected, one pre-existing Starlette/httpx warning); and
`git diff --check` passed. The exact production Tier-B gate is not complete because the story input is
not in the repository and no paid provider call was run.

---

# Current Task: Production analyze alias regression

- [x] Reproduce the exact Leo/object alias failure and trace the pre/post-merge behavior.
- [x] Identify the smallest fix that preserves the frozen StoryAnalysis boundary and prompt invariants.
- [x] Add a regression test that fails on the current code.
- [x] Implement the root-cause fix and update the affected feature spec if behavior changes.
- [x] Run focused tests, backend lint/full tests, and report residual risk.

## Success criteria

An extraction response containing a character plus an explicit object alias no longer kills a job,
the duplicate entity cannot reach downstream state, and the deterministic suite proves the behavior.

## Outcome

The merged validator rejected the model's known `the robot (Leo)` response, and the provider's
single unchanged re-ask repeated the invalid payload. `StoryAnalysis` now drops exact character
duplicates and drops a trailing parenthetical character alias in full.
Updated `story-analyzer.md` and `visual-prompt-reliability.md` to describe normalization.

Verification: TDD red run failed 3 tests on the old behavior; focused analyzer tests passed 49;
`uv run ruff check .` passed; `uv run pytest` passed 903 tests, skipped 71, deselected 6, with one
pre-existing Starlette warning; `git diff --check` passed.

Residual risk: implicit semantic aliases such as character `Leo` plus object `the robot` remain
intentionally unresolved because they cannot be merged deterministically without false positives.

---

# Current Task: Visual-prompt reliability implementation

- [x] Plan 1: Analysis & Segmentation (explicit alias boundary, structured drawable moment, deterministic later-moment merge).
- [x] Plan 2: Prompt Construction (visual-only `build_prompt` without `text_excerpt` or notes, version bump to 2).
- [x] Plan 3: Clean-Base Retries & Verification (clean-base retries, exact contradiction deduplication, integration graph test, live spec reconciliation).
- [x] Run full deterministic test suite and ruff checks.
- [ ] Tier-B quality check (offline/manual product validation, pending live paid runs).
- [ ] Obtain user/owner approval per §9.

## Success criteria

Scene prompts are visual-only, retries derive from the immutable clean `Scene.prompt` base plus only the latest verdict, exact duplicate contradictions are deduplicated in first-seen order, the 3-attempt graph order and economics remain unchanged, and all live specs are reconciled.

## Outcome

Implemented clean-base retries in `backend/pipeline/regenerate.py`, extracted `correction_clauses` with exact first-seen contradiction deduplication in `backend/pipeline/prompt_optimizer.py`, and proved the unchanged 3-attempt graph shape and economics in `backend/tests/test_graph.py`. Reconciled `regeneration-controller.md`, `spend-and-retry-economics.md`, `visual-continuity.md`, `pipeline-consistency-docket.md`, and `visual-prompt-reliability.md`.

---

# Current Task: ADR-040 — scene prompts exclude narrative notes

- [x] Read D-M, ADR-039, ADR-035, the proposed visual-prompt spec, current prompt flow, and tests.
- [x] Audit direct and semantic references with a delegated read-only repository scan.
- [x] Stress-test removal against thin descriptions, unreferenced characters, retries, targeted
      redraws, legacy checkpoints, and frozen-contract constraints.
- [x] Compare retaining notes, heuristically filtering them, splitting the schema, and removing
      them from newly assembled scene prompts.
- [x] Present the strengthened decision and obtain owner approval.
- [x] Write ADR-040, add its index row, remove D-M, and unblock the visual-prompt spec.
- [x] Self-review the ADR and changed documentation for contradictions, stale gates, and placeholders.
- [x] Verify the documentation diff, link target, numbering, and frozen/runtime file boundaries.
- [x] Commit the ADR session.

## Success criteria

ADR-040 makes typed appearance axes and canonical references the only character-identity authority
in newly assembled scene prompts, while `Scene.visual_direction` owns the drawable moment. It
preserves the frozen schema, targeted redraw behavior, stored legacy prompts, and runtime code; it
explicitly amends ADR-039 Decision 4 and ADR-035's scene-note filtering assignment.

## Outcome

ADR-040 accepts D-M for newly assembled scene prompts. It keeps `notes` in the frozen contract but
removes their normal image-prompt authority, preserves direct ADR-029 targeted attributes and stored
legacy prompts, and records thin typed descriptions as an upstream extraction miss rather than a
reason to restore prose. The visual-prompt spec is unblocked but remains a draft awaiting owner
review; no runtime code or frozen ADR file changed.

Documentation verification on 2026-08-16: `git diff --cached --check` passed; the ADR index target
exists; ADR files end sequentially at ADR-040; D-M is absent from the decision backlog; and the
staged frozen/runtime boundary check returned no paths. Code tests were not run because this session
changes Markdown only.

---

# Current Task: Visual-prompt reliability design

- [x] Read project guidance, lessons, current pipeline/specs, recent commits, Fal prompts, and worker logs.
- [x] Delegate recent-change, capstone/judge, and end-to-end pipeline diagnosis.
- [x] Clarify product priority, paid validation size, prompt source, retry policy, moderation
      replacement policy, angle-aware identity posture, and the one-moment rule.
- [x] Compare three approaches and select the staged robustness program.
- [x] Present and obtain approval for the S1 architecture/data flow.
- [x] Write `docs/specs/visual-prompt-reliability.md` with failure modes, edge cases,
      deterministic tests, and the three-story Tier-B check.
- [x] Log ADR-039's scene-notes conflict as D-M and the moderation replacement gap as D-N.
- [x] Self-review the written spec for placeholders, contradictions, ambiguity, and scope.
- [x] Commit the design documentation.
- [ ] Ask the user to review the written spec after D-M resolution and before implementation planning.

## Success criteria

The written design preserves verbatim captions and story-appropriate camera angles while giving Fal
one visual authority, rebuilding retries from the immutable clean base, and adding no runtime code,
schema, model-call site, successful-path call, retry loop, or architectural decision inline. Every
blocked decision is explicit.

## Outcome

The draft S1 spec defines a visual-only scene prompt, structured one-moment segmentation,
explicit actor/object-alias boundary handling, and clean-base latest-only retry corrections. It preserves
verbatim captions, story-appropriate rear/profile/overhead views, the three-attempt cap, graph shape,
and raw judge evidence. The self-review caught and fixed a merge inconsistency: the later selected
 moment now also owns visible cast, visible objects, and explicit location. Node-local holder events
 are removed rather than merged or replayed. ADR-040 now resolves D-M and removes narrative notes
 from newly assembled scene prompts; D-N separately owns moderation-replacement checking.

---

# Current Task: Pipeline Consistency Docket — S2 Design

- [x] Read project guidance, lessons, the docket, S1 carry-forward constraints, current code/specs, and recent commits.
- [x] Reconcile S2 status and spot-check binding constraints against the current implementation.
- [x] Clarify S2 purpose, scope, constraints, and success criteria one question at a time.
- [x] Propose 2–3 approaches with trade-offs and a recommendation.
- [x] Present the S2 design in reviewable sections and obtain approval.
- [x] Record the approved closure in the canonical docket; do not create a duplicate S2 spec.
- [x] Self-review the written closure for placeholders, contradictions, ambiguity, and scope.
- [x] Extract and confirm S2 binding constraints, then update the docket status.

## Outcome

S2 was waived as a separate deliverable because `docs/specs/visual-continuity.md` already owns and
implements the approved behavior. The docket now records BC-7…BC-12, marks S2 `WAIVED`, and makes
S3/S4 `READY`. No implementation changed and no visual-quality claim was made.

---

# Current Task: Pipeline Consistency Docket — S3 Design

- [x] Explore S3 context: project guidance, docket, relevant specs/code, recent commits.
- [x] Offer the visual companion only if a genuinely visual question arises. Not needed for the
      conceptual composition-vs-identity decision.
- [x] Clarify S3 purpose, constraints, and success criteria one question at a time.
- [x] Propose 2–3 mechanisms with trade-offs and a recommendation.
- [x] Present the S3 design in reviewable sections and obtain approval.
- [x] Write the approved S3 spec in `docs/specs/` and commit it (`ea20d92`).
- [x] Self-review the written spec for placeholders, contradictions, ambiguity, and scope.
- [ ] Ask the user to review the written spec. Awaiting response.
- [ ] Record and confirm S3 constraints in the docket; stop before implementation planning.

---

# Current Task: Reference Pipeline Hardening

- [x] Diagnose character prompt contamination and the Supabase reference timeout.
- [x] Confirm PII pseudonymization remains unchanged.
- [x] Obtain approval to implement both independent fixes with delegated agents.
- [x] Create the implementation plan in `docs/specs/plans/2026-08-15-reference-pipeline-hardening.md`.
- [x] Implement and review Task 1: character-reference prompt fidelity.
- [x] Implement and review Task 2: signed reference URL delivery.
- [x] Draft ADR-039 and add its index row in a dedicated ADR session.
- [x] Obtain explicit human acceptance of ADR-039 before retaining the conflicting prompt behavior.
- [x] Review the combined blast radius and run backend pre-merge verification.
- [x] Record commands, results, unverified external behavior, and residual risks below.

## Outcome

ADR-039 was accepted on 2026-08-15. Normal canonical-reference prompts now omit narrative `notes`;
targeted redraws read `ReferenceRetry.attribute` directly and emphasize it unconditionally. Analyzer
guidance requires concrete drawable values instead of placeholders. Scene prompts intentionally keep
`notes`, PII pseudonymization is unchanged, and no contract, graph, model, provider, or moderation
ordering changed.

Scene generation now gives fal a fresh 300-second Supabase signed URL for each canonical reference
instead of downloading the full asset through the worker and re-uploading it to fal. URL ordering,
private Storage paths, checkpoint compatibility, and idempotent resume behavior are preserved.

Verification from `backend/` on 2026-08-15:

- `uv run ruff check .` — passed.
- `uv run pytest` — 853 passed, 71 intentionally skipped, 6 deselected; one existing Starlette
  deprecation warning.
- Focused changed surface — 267 passed.
- `git diff --check` — clean.

Repository pre-merge verification also passed: `pnpm lint` and `pnpm test` from `frontend/`, with
34 test files and 269 tests passing. The first frontend test attempt hit the 120-second command
timeout without a result; the isolated retry completed successfully in 31.5 seconds.

Not verified locally: a paid live fal request fetching a private Supabase signed URL. The deterministic
tests prove URL creation, freshness, and ordering but cannot prove fal's external fetch. Remaining
product risk: prompt adherence is probabilistic, and scene prompts still receive narrative `notes` by
ADR-039's deliberately narrow scope. No population-level quality claim is made from the single repro.

---

# Current Task: Pipeline Consistency Docket — S4 Design

- [x] Explore S4 context: project guidance, docket, relevant specs/code, and recent commits.
- [x] Reconcile S4's stale null-location question against the already-built carry-forward behavior.
- [x] Clarify S4's artifact, persistence, transient-change, gating, and failure decisions one at a time.
- [x] Propose alternatives with trade-offs and a recommendation.
- [x] Present the S4 design in reviewable sections and obtain approval.
- [x] Write the approved S4 spec at `docs/specs/setting-consistency.md`.
- [x] Self-review the written spec for placeholders, contradictions, ambiguity, and scope.
- [x] User approved the written spec.
- [x] Record and confirm S4 constraints in the docket; stop before implementation planning.

## Outcome

S4 chose a frozen text-only location canon in the existing `Location.description`, retained the
existing carry-forward and prompt order, and routes permanent setting mismatches through the
existing scene-constraint retry path. The approved spec is `docs/specs/setting-consistency.md`;
BC-13…BC-18 are confirmed, S4 is `DONE`, and S5 is `READY`. No implementation or paid model run
occurred, and no visual-quality claim was made.

---

# Current Task: Sanitize placeholder character canon before image generation

- [x] Add regression tests for placeholder values at the canonical and scene prompt boundaries.
- [x] Preserve the ADR-039 permissive contract while projecting blank/placeholder values out of prompts.
- [x] Add an age-appropriate torso-clothing instruction for human/humanoid reference renders.
- [x] Run focused and full backend verification.

## Success criteria

No literal `unspecified`, `none`, `unknown`, or `neutral` value reaches a canonical or scene prompt.
The persisted contract remains backward-compatible, valid descriptions remain unchanged, and no
new terminal failure path or model/image call is introduced.

## Outcome

Implemented `CharacterDescription.without_placeholders()` and applied it to canonical-reference,
judge, reveal, scene, and correction prompt projections. Canonical references now explicitly ask
human/humanoid subjects to wear age-appropriate torso-covering clothing. The initially proposed
terminal validator was rejected because ADR-039 freezes a permissive contract and forbids turning
imperfect extraction into a new child-facing terminal failure; the final fix stays within that ADR.

Verification: `uv run ruff check .` passed; `uv run pytest` passed 861 tests, 71 skipped, 6
deselected, 1 existing Starlette warning. Focused character/prompt/contract tests passed 258 tests
after the final regression addition. `git diff --check` passed.

---

# Current Task: Visual-prompt reliability implementation plan

- [x] Read the project instructions, lessons, master spec, target feature spec, affected module specs, and current runtime/test surfaces.
- [x] Split the implementation plan into sequential extraction/segmentation, prompt-construction, and retry/verification plans.
- [x] Write the three disposable plans under `docs/specs/plans/` with exact files, interfaces, TDD steps, verification commands, and live-doc reconciliation.
- [x] Self-review the plans for target-spec coverage, placeholder instructions, signature consistency, and repository hygiene.

## Success criteria

The plan is executable in order without changing the frozen contract or architecture. It names the
existing seams, keeps deterministic tests separate from Tier-B product validation, and includes the
required final grep, full backend verification, owner-approval gate, and disposable-plan cleanup.

## Outcome

Created:

- `docs/specs/plans/2026-08-16-visual-prompt-reliability-1-analysis-segmentation.md`
- `docs/specs/plans/2026-08-16-visual-prompt-reliability-2-prompt-construction.md`
- `docs/specs/plans/2026-08-16-visual-prompt-reliability-3-clean-base-retries-verification.md`

Plan-only validation passed: `git diff --check`; placeholder scan found no `TBD`, `TODO`, or vague
test-stub instructions. No runtime tests were run because implementation was not requested in this
turn.

---

# Current Task: Visual-prompt reliability review fixes

- [x] Read `AGENTS.md`, `CLAUDE.md`, `tasks/lessons.md`, the review artifact, the target spec, the affected lettering spec, and the current implementation/tests.
- [x] Verify the three spec-facing review findings against the current tree.
- [x] Add failing regression assertions for explicit anti-montage guidance and surviving contradiction count.
- [x] Apply the two runtime fixes and update `docs/specs/lettering-suppression.md`.
- [x] Run targeted tests, backend lint/tests, and final diff/spec checks.
- [x] Record the outcome and delete the disposable review-fix plan.

## Success criteria

`SEGMENTATION_PROMPT` explicitly names montage, split-panel, duplicate-character, and impossible-pose prohibitions; regeneration logs the number of unique current contradictions; lettering suppression documents immutable-base/latest-verdict-only corrections; and backend verification is green.

## Outcome

Implemented the three review fixes: `SEGMENTATION_PROMPT` now explicitly prohibits montage, split
panel, duplicate character, and impossible pose outputs; `regenerate` logs the surviving unique
contradiction count; and lettering-suppression §4.4 documents immutable-base/latest-attempt-only
corrections without `last.prompt` or accumulated correction history.

Verification on 2026-08-16:

- Red/green targeted checks: both new assertions failed against the old behavior, then passed after
  the fixes.
- `uv run pytest tests/test_segment_node.py tests/test_regenerate_node.py -q` — 136 passed.
- `uv run ruff check .` — all checks passed.
- `uv run pytest` — 903 passed, 71 skipped, 6 deselected, 1 existing Starlette deprecation warning.
- Frontend pre-merge checks: `pnpm lint` passed; `pnpm test` — 34 files and 279 tests passed.
- `git diff --check` — clean; stale code-expression grep returned no matches.

Residual risk: no paid Tier-B visual-quality validation was run; contract, graph, provider calls, and
retry policy remain unchanged.

---

# Current Task: Visual-prompt reliability follow-up implementation

- [x] Read and critically review the project instructions, target spec, implementation plan, and affected code/tests.
- [x] Add failing analyzer and segmentation regression tests.
- [x] Implement alias dropping and remove object lifecycle propagation.
- [x] Update the story-analyzer, scene-segmentation, and visual-continuity specs.
- [x] Run focused tests, backend lint/full verification, strict greps, and review the diff/spec alignment.
- [x] Run or document the Tier-B Jamie/Bolt reproduction and remove the disposable plan.

## Success criteria

Explicit parenthetical character aliases are dropped, `objects_present` is explicit per frame,
object ownership does not invent visibility or holder relations, all deterministic checks pass, and
the affected specs match the runtime behavior.

## Outcome — 2026-08-17

Implemented in commits `a639495`, `8d51b34`, and `58dfa14`:

- `StoryAnalysis` now drops an explicit parenthetical character alias object in full.
- `segment` no longer accepts object lifecycle events, carries owned objects forward, or appends
  derived holder relations; `objects_present` is explicit per frame.
- Updated the three affected module specs and replaced lifecycle assertions with deterministic
  per-frame tests.

Verification:

- Red tests failed against the old behavior, then focused analyzer/segment tests passed: 149.
- `uv run ruff check .` — passed.
- `uv run pytest` — 903 passed, 71 skipped, 6 deselected; one existing Starlette warning.
- Strict greps and `git diff --check` reviewed clean for runtime lifecycle leakage.

Tier-B Jamie/Bolt reproduction was not run: the exact production story is not checked into the
repository. No `.env` or secret file was read, and no live paid provider call was made. The
remaining risk is unmeasured behavior on that external reproduction.

---

# Current Task: Character-bible consistency and art-style ADR session

- [x] Trace the exact PII redaction, analysis, character-bible, prompt, and reference-generation flow.
- [x] Reconcile the Jamie/Bolt/Leo repro with recent visual-prompt reliability changes.
- [x] Clarify the intended handling of fictional character names: consistency first; do not disable Presidio.
- [x] Compare minimal consistency options for PII, character canon, prompt generation, and reference acceptance.
- [x] Resolve the separate art-style policy in ADR-042 without mixing it into ADR-041.
- [x] Present the hardened no-second-LLM design and obtain owner approval to draft it.
- [x] Write and self-review the proposed canonical ADR/spec; request owner acceptance before implementation.

## Success criteria

The design identifies the evidenced source of the Bolt-to-Leo mutation, keeps child-safety guarantees,
gives image generation one stable non-human character identity, and selects an art-style policy with
a reproducible validation method. No runtime, frozen ADR, schema, provider, or model change occurs
before explicit owner approval.

## Character-consistency design outcome

Drafted `docs/specs/canonical-character-consistency.md` and proposed ADR-041. The design keeps
Presidio and the existing analyzer call, adds transient body-plan/face-interface structure folded
into `body_features`, removes direct name concatenation from fresh canonical draw/judge projections,
and replaces reveal's empty name chip with `overall physical appearance`. It adds no runtime code,
provider/model call, persisted contract field, graph change, retry, or style decision.

Independent review tightened the legacy predicate, targeted-restatement rule, child-facing chip
bound, placeholder/species validation, PII limitation, Objective-4 distribution versioning, and
fail-open decision ownership. It rejected a deterministic name-string scrubber because names such as
`Blue`, `Star`, and `Bolt` can be legitimate visual facts.

Documentation verification: `git diff --check` passed; ADR-041 is indexed as Proposed; D-P and D-Q
record the deferred full-scene alias and reference-failure policies. No backend/frontend tests or
paid Tier-B images were run because this is a documentation-only design session. D-O art-style
policy is independently resolved by ADR-042; implementation and Cut-paper validation remain pending.

---

# Current Task: D-O selectable-style ADR

- [x] Read ADR-022, the style-presets spec, current picker/API/worker compatibility flow, historical
      preset evidence, and production notes.
- [x] Decide hard retirement for new Comic jobs while preserving existing Comic execution.
- [x] Make Gouache the immediate new-job default without changing legacy null→Cel behavior.
- [x] Select Cut-paper collage as the provisional replacement candidate.
- [x] Freeze a three-book, zero-style-family-miss promotion gate.
- [x] Draft ADR-042, update the ADR index, remove D-O, and reconcile affected live specs.
- [x] Self-review and verify the documentation change.
- [ ] Ask the owner to review ADR-042 before implementation or paid candidate validation.

## Success criteria

ADR-042 distinguishes selectable from compatibility-supported presets, preserves every existing
Comic/null job, names one exact Cut-paper candidate fragment, and prevents that candidate from
becoming public before its paid three-book gate passes. This session changes no runtime behavior.

## Outcome

ADR-042 is accepted as the policy decision. It makes Gouache the target new-job default, hard-retires
Comic from new creation while retaining historical execution, and freezes Cut-paper collage as the
only provisional replacement. Promotion requires three frozen production-equivalent books, the
accepted picker sample, zero style-family misses, intact identity/anatomy, and owner acceptance.

Documentation verification on 2026-08-17: all twelve ADR requirement assertions passed; the
placeholder scan returned none; D-O has no open backlog row and points to ADR-042 as resolved; the
ADR index target exists; `git diff --check` passed; and the changed-path check found no runtime,
frontend, or migration files. Code tests and paid image calls were not run because this session is
documentation-only.
---

# Current Task: Canonical-character consistency implementation plan

- [x] Read AGENTS.md, CLAUDE.md, lessons, MASTER_SPEC §5–§6, ADR-041, the target spec, linked module specs, and current code/tests.
- [x] Map the cross-module work into analyzer, reference/reveal, and integration/documentation/Tier-B slices.
- [x] Write three TDD-first disposable plans under docs/specs/plans/.
- [x] Self-review plan coverage, placeholders, signatures, paths, and whitespace.
- [x] Obtain/confirm owner approval for the target feature spec before runtime implementation.
- [x] Execute the three plans in order and delete them after implementation, verification, and Tier-B retention.

## Success criteria

The plans are executable without changing Story Memory, graph shape, providers, model choice, retry policy, or failure posture; every behavior has a red-green test path; live specs and status surfaces are reconciled; and the Tier-B gate is explicit and honest.

## Implementation outcome

Implemented across three plans and verified:
- `analyze` incorporates required transient `body_plan` and `face_or_interface` morphology folded into `body_features`, with 120-code-point limits, single-line / non-placeholder validation, and `EXTRACTION_PROMPT_VERSION = 1`.
- `char_bible` removes direct name concatenation from fresh normal and targeted canonical reference draw and judge projections (`JUDGE_PROMPT_VERSION = 6`), maintaining legacy fallback only when all visual axes are empty.
- `reveal` empty-chip fallback uses `overall physical appearance` instead of the character name; standalone morphology chips are preserved.
- Added deterministic integration regression in `test_canonical_character_consistency.py`.
- Reconciled `canonical-character-consistency.md` (built), `story-analyzer.md`, `character-bible.md`, `kid-flow-pause-lifecycle.md`, `visual-prompt-reliability.md`, and `ADRs.md`.
- Deterministic verification: 935 passed, 71 skipped, 6 deselected; ruff clean; git diff --check clean.

---

# Current Task: ADR-042 selectable-style policy implementation

- [x] Add failing backend tests for the separate creation allowlist, Gouache new-job default, Comic rejection, and historical worker compatibility.
- [x] Implement the backend creation allowlist and Gouache default without changing `STYLE_PRESETS` execution compatibility.
- [x] Add failing frontend tests for the two-card Gouache-default picker and legacy-null retry preservation.
- [x] Implement the picker and retry boundary changes.
- [x] Reconcile current style behavior in the feature spec, Master Spec, workflow, user flow, and PRD.
- [x] Run focused red/green checks, full backend/frontend verification, and stale-surface review.
- [x] Delete the disposable implementation plan and record the outcome.

## Success criteria

New jobs store Gouache when style is omitted or null, accept Cel and Gouache, reject Comic, and
show only Cel/Gouache with Gouache selected. Historical Comic rows still execute, historical null
rows still resolve to Cel, Cut-paper remains offline-only, and all required checks are green.

## Outcome — 2026-08-17

Implemented ADR-042 style policy:
- Backend: `SELECTABLE_STYLE_PRESET_IDS` restricts creation API to `{"cel", "gouache"}`; Comic is rejected with 422; new jobs with omitted or null `style_preset_id` store `"gouache"`. Worker retains full `STYLE_PRESETS` mapping (`cel`, `comic`, `gouache`) and resolves legacy null rows to `"cel"`.
- Frontend: Write page style picker displays only Cel ("Cartoon") and Gouache ("Painted"), with Gouache selected by default. Comic sample card is kept on disk for historical compatibility but excluded from the picker. `FailureScreen` retry defaults null `stylePresetId` to `"cel"` to protect legacy books from silent restyling.
- Docs: Reconciled `style-presets.md`, `MASTER_SPEC.md`, `WORKFLOW.md`, `USER_FLOW.md`, and `PRD_v2.md`.
- Verification:
  - Backend: `uv run ruff check .` clean; `uv run pytest` — 938 passed, 71 skipped, 6 deselected, 1 pre-existing warning.
  - Frontend: `pnpm lint` clean; `pnpm test` — 34 test files, 279 passed.
  - `git diff --check` clean.
- Cut-paper collage remains an unpromoted offline candidate fragment for future paid validation per ADR-042; no runtime or schema promotion was performed.

---

# Current Task: Error-page auth recovery and route verification

- [x] Verify the reported route unauthenticated without changing route guards; authenticated reproduction remains dependent on a sanitized signed-in browser state.
- [x] Add failing tests for logout recovery, signout cookie clearing, and role/auth routing gaps.
- [x] Implement the smallest error-page recovery change using the existing `/auth/signout` route.
- [x] Update the owning auth UX spec without changing the auth model or role policy.
- [x] Run focused tests, lint, the full frontend suite, the build, and diff checks.

## Success criteria

The reported route remains governed by the existing middleware contract, error and 404 surfaces offer a safe logout escape hatch, auth/role behavior is covered by deterministic tests, and all required frontend verification is green with no unrelated dirty-worktree changes overwritten.

## Outcome — 2026-08-21

Added native `POST /auth/signout` recovery forms to the root 404, root/global error, student,
classroom, gallery, research metrics, annotate, and adjudicate fallbacks. Added deterministic coverage for the recovery forms,
raw-error non-disclosure, signout redirects and `sb-*` cookie sweeping, safe login redirects, and
teacher/student/researcher role destinations. The reported `/s/c4f346f6-829e-41d3-b642-b0f4ef06bad0`
route still returns `307 → /join?next=...` for a clean unauthenticated request; `/does-not-exist`
returns the StoryBuddy 404. No authenticated reproduction was available in this session.

Verification: focused tests 66 passed, then the final full frontend suite 366 passed across 42 files;
production build succeeded. Targeted changed-file `git diff --check` is clean. Whole-worktree diff
check still reports a pre-existing trailing-whitespace line in
`frontend/app/(research)/adjudicate/actions.ts:145`, which was not changed.

---

# Current Task: Researcher redirect trap

- [x] Reproduce the clean unauthenticated request and trace authenticated role-routing paths without reading secrets.
- [x] Delegate independent read-only traces for login redirects, student-route rendering, and Supabase signout.
- [x] Add failing tests for incompatible `next` targets, profile lookup failure, researcher role routing, and logout recovery.
- [x] Implement the smallest role-aware fixes at login and the existing teacher/student route boundaries.
- [x] Update the owning auth UX spec with role-compatible `next` behavior and failure handling.
- [x] Run focused tests, lint, the full frontend suite, the build, and live smoke checks.

## Success criteria

A researcher cannot be pushed into `/s/<id>` by a stale/incompatible login target or a silent profile
lookup fallback; authenticated teacher-surface resolution routes researchers to `/annotate` or
`/adjudicate`; any student-route fallback has a correct research link and visible logout; and all
required frontend checks are green without overwriting unrelated worktree changes.

## Outcome — 2026-08-21

Root causes were confirmed in separate paths: login honored role-incompatible internal `next`
targets; a failed profile lookup silently fell through to `/s/<userId>`; and the teacher resolver
sent every non-teacher to that student tree. The fixes keep middleware role-blind, constrain `next`
by the resolved role, fail visibly on profile lookup failure, route researchers through the existing
server profile resolver, and add research-specific recovery plus logout to the student fallback.

TDD evidence: the new login/layout/teacher tests first failed for the expected redirects and missing
logout, then passed after the fixes. Final verification: focused auth tests 43 passed; `pnpm lint`
passed; `pnpm test` passed with 371 tests across 42 files; `pnpm build` completed successfully.
HTTP smoke returned `307 /join?next=...` for the clean unauthenticated reported URL, `404` with
`Page 404` for an unknown route, and `303 /login` for `POST /auth/signout`.

The signed-in researcher URL could not be replayed because no sanitized authenticated browser state
was available; the current remote Supabase migration state is also unverified. Whole-worktree
`git diff --check` still reports the pre-existing trailing-whitespace line at
`frontend/app/(research)/adjudicate/actions.ts:145`, which was not changed.
# Research corpus operations implementation planning (2026-08-21)

- [x] Read the approved design and writing-plans instructions.
- [x] Map existing corpus, annotation, storage, and integrity seams.
- [x] Write the test-first implementation plan under `docs/specs/plans/`.
- [x] Self-review the plan against every approved spec requirement.
- [x] Create bounded GitHub issues with explicit manual/code gates (#54-#65).
- [x] Verify links, issue state, diff hygiene, and commit the planning artifacts.

## Success criteria

- Every design requirement maps to an executable task or explicit human gate.
- No new provider, datastore, dependency, schema, or public contract is introduced.
- Paid execution is blocked behind zero-cost tests, consent approval, and dollar caps.
- Issues are independently reviewable and ordered by stop gates.

## Review / outcome

- Plan covers governance, intake, immutable corpus persistence, exact image encoding/hashing, Fal spend and uncertain billing, pair materialization, annotation reconciliation, freeze guards, pilot cleanup, storage telemetry, paid smoke, annotation, training, and one-time evaluation.
- Existing Objective-4 epic #53 now links issues #54-#65 and no longer directs a donated training corpus or stale image-count budget.
- No application code, data, database, provider configuration, or paid service was changed or invoked.

---

# Current Task: Research corpus operations tasks 1–5

- [x] Task 1: Validate sanitized intake and document governance gates.
- [x] Task 2: Persist immutable run bundles and add zero-cost fixture mode.
- [x] Task 3: Enforce dollar-denominated spend reserves and uncertain-billing quarantine.
- [x] Task 4: Materialize exact assets and blinded pair rows idempotently.
- [x] Task 5: Reconcile annotation truth and freeze immutable dataset artifacts.
- [x] Run focused checks, full backend verification, two-axis code review, and commit all work.

## Success criteria

Tasks 1–5 of `docs/specs/plans/2026-08-21-research-corpus-operations.md` match the approved spec,
use test-first seams, pass focused and full backend checks, receive standards/spec review, and are
committed on the current feature branch. Tasks 6 onward remain unchanged.

## Review / outcome

Task 4 now preflights immutable PNG/WebP inventory, existing private Storage bytes, and complete
`research_pairs` rows before mutation; uploads are idempotent and database failure rolls back only
objects created by that invocation. Task 5 derives queue status from annotation rows, supports
bundle-declared exclusions, revalidates exact local assets, enforces split/style/duplicate guards,
and installs only byte-identical immutable freeze artifacts with pinned run versions.

Review fixes made the freeze self-contained, persisted and revalidated declared rosters before
materialization and freeze, counted constructed pairs under their reference story, qualified
story-local character IDs for corpus-wide lineage guards, and split annotation truth/freeze concerns
out of the manifest builder. Final focused Task 4–5 tests passed 61. Full backend Ruff passed; full
backend pytest passed 1057, skipped 80 environment-dependent tests, and deselected 6 provider smoke
tests. Frontend lint passed and all 380 tests across 42 files passed. Both final standards and spec
reviews were clean after fixes. The zero-cost fixture reported `images_spent=0`, `usd_high=0.000`, and
persisted all required commit/model/prompt/config pins. No paid provider call or remote Supabase write
was made; live Storage, RLS, and database state remain unverified locally.

---

# Current Task: Research corpus operations tasks 6–7

- [x] Task 6: Add dry-run-first, confirmed pilot cleanup with exact ordered deletion.
- [x] Task 7: Align storage telemetry with PNG references, WebP scenes, and Supabase-only reporting.
- [x] Run focused checks, full verification, two-axis code review, and commit all work.

## Success criteria

Tasks 6–7 of `docs/specs/plans/2026-08-21-research-corpus-operations.md` match the approved spec,
use test-first seams, pass focused and full checks, receive standards/spec review, and are committed.
Task 8 remains an explicit human/paid operational sequence and is not executed automatically.

## Review / outcome

Task 6 uses paginated Supabase reads, recursively enumerates only the literal `research/pilot/`
Storage prefix, deletes annotations before pairs before objects, requires the exact confirmation,
and verifies all three scopes are empty. Focused verification: 8 tests passed; Ruff passed.

Task 7 measures PNG references and quality-82 WebP scenes separately, verifies format and dimensions,
reports only Supabase storage/egress headroom, and writes zero-cost output under `.scratch/`. The owning
judge spec now points to the corpus-operations spec for live counts/costs, and MASTER_SPEC records the
existing research modules as built. Focused verification: 5 tests passed; Ruff passed; the stale scan
found only negative test assertions and an unrelated CVPR URL substring, not operational guidance.

Final verification: backend Ruff passed; backend pytest passed 1066 with 80 environment-dependent skips
and 6 provider smoke tests deselected; frontend ESLint passed; frontend Vitest passed 380 tests across 42
files; `git diff --check` passed. Inline Standards and Spec reviews were clean after adding regression
coverage for Supabase delete calls that raise instead of returning an error-bearing response.

---

# Current Task: Objective-4 corpus style and story-input gap closure

- [x] Inspect the locked selectable-style catalog and existing corpus input path.
- [x] Obtain explicit owner acceptance of `cut_paper` under ADR-042's escape hatch.
- [x] Decide explicit per-story style assignment and one JSON-list input contract.
- [x] Freeze synthetic and donated style allocations before paid generation.
- [x] Define declared roster validation and post-run `StoryMemory` reconciliation.
- [x] Amend the preregistration before any held-out result, study label, or fine-tune exists.
- [x] Run repository-wide contradiction and placeholder checks.
- [x] Commit the documentation-only change and request owner review.

## Success criteria

Canonical docs use `cel`, `gouache`, and `cut_paper`; explain exactly how a story is entered; prevent style
from becoming an identity shortcut; keep all allocation choices outcome-blind; and give the implementation
plan deterministic validation and sequencing checks. No code, corpus data, paid call, or external store changes.

## Review / outcome

Owner acceptance is recorded as ADR-042's dated escape-hatch amendment without claiming the waived paid
validation passed. Canonical research docs now freeze one strict JSON-list input contract, roster
reconciliation, 24/6 synthetic splitting with 8/2 per style, 5/5/5 donated candidate coverage, and
within-style pairing. Historical ADR statements remain visible.

Verification: `git diff --check` passed; the added JSON example parsed; `research_strategy.html` parsed and
its tags balanced; changed-line placeholder scan was empty; repository scan found no live `paper_cut`,
single-style, or obsolete 50-story claim in the owning corpus documents. Application tests were not run
because no runtime, data, schema, or UI behavior changed.
# Current Task: Research corpus integrity code review

- [x] Pin `290bc6e...HEAD` and verify the four-commit diff is non-empty.
- [x] Run independent Standards review against repository rules and smell baseline.
- [x] Run independent Spec review against `docs/specs/research-corpus-operations.md`.
- [x] Validate findings against the diff and record the review outcome.

## Success criteria

Report Standards and Spec findings separately with actionable file/line references, preserving the
existing working tree and making no implementation changes.

## Review / outcome

Standards review found no hard violations and one advisory Divergent Change concern in the 693-line
corpus runner. Spec review found three recovery defects: unresolved attempted calls can restart without
uncertain-billing acknowledgment, checkpoint contents are not bound to intake, and a billing
acknowledgment is lost after re-quarantine. Focused verification passed 76 tests; these three crash and
recovery cases are not covered by that suite.
# Current Task: Verify corpus recovery review findings

- [x] Trace persisted telemetry, checkpoint validation, and acknowledgment state end to end.
- [x] Add one failing regression test for each confirmed recovery defect.
- [x] Apply the smallest fail-closed fixes; leave the advisory file split alone.
- [x] Run focused tests, backend Ruff, and record the outcome.

## Success criteria

Crash-window attempts require uncertain-billing acknowledgment, recovered checkpoints match immutable
intake fields, and billing acknowledgments survive re-quarantine without refactoring unrelated runner code.

## Review / outcome

All three Spec findings reproduced with focused tests and were fixed in the existing runner. In-progress
state now carries the intake digest; unmatched attempted-call telemetry becomes `billing_uncertain` before
restart; checkpoint story/text/style must match intake; and billing acknowledgment survives subsequent
state writes and quarantine. The advisory module split was deliberately left alone as unrelated refactoring.

Verification: all four regressions failed before their fixes and passed afterward; `uv run ruff check .`
passed; full backend pytest passed 1088, skipped 80 environment-dependent
tests, and deselected 6 provider smoke tests. No paid provider or remote database call ran.

# Current Task: Close Objective-4 corpus integrity Batch 1

- [x] Add failing regressions for malformed persisted telemetry and untrusted in-progress restarts.
- [x] Reject malformed telemetry and mismatched intake/checkpoints before any graph or provider call.
- [x] Run focused tests, full backend verification, and a zero-cost fixture.
- [x] Review and commit only the Batch 1 implementation, tests, and task outcome.

## Success criteria

Malformed persisted billing counters fail closed through the supported corpus error path; all existing
recovery safeguards remain green; the zero-cost fixture completes without paid calls; and the complete
Batch 1 change is committed without touching unrelated working-tree files.

## Review / outcome

Batch 1 now fails closed on non-integer or missing persisted billing counters, crash-window attempts without
a terminal billing event, changed intake bytes, and stale or invalid LangGraph checkpoints. Uncertain-billing
acknowledgments remain auditable across re-quarantine. The approved smoke policy remains unchanged: a story
that exhausts its assigned allowance halts the smoke before another paid call.

TDD evidence: each new malformed-state and restart regression failed before its fix and passed afterward.
Final verification: 84 focused corpus tests passed; `uv run ruff check .` passed; full backend pytest passed
1092, skipped 80 environment-dependent tests, and deselected 6 provider smoke tests. The zero-cost fixture
completed one story with zero paid attempts and `usd_high="0.000"`. Independent re-review found no remaining
Critical or Important findings. No provider call, paid draw, live database mutation, or `.env` access occurred.

# Current Task: Objective-4 dataset validity Batch 2

- [x] Revalidate hard-negative, withdrawal, candidate-role, preregistration, and path blockers.
- [x] Approve the full canonical-dataset boundary and manual same-species/same-style mapping.
- [x] Approve the controlled selection artifact, fail-closed replacement rules, and canonical paths.
- [x] Record and self-review the durable design in the two owning specs.
- [x] Obtain owner approval of the written Batch 2 specification.
- [x] Write and self-review the disposable TDD implementation plan.
- [x] Execute the plan inline, verify it, review it, and delete it after completion.

## Success criteria

Production materialization and freeze consume the current donated intake plus one strict selection artifact;
withdrawn and unselected donated bundles cannot enter the dataset; every synthetic training reference uses
one manually frozen same-species/same-style target and all of that target's eligible natural train scenes;
mutable and immutable paths are distinct; the frozen preregistration is amended visibly; and all deterministic
checks pass without paid calls, real donor data, held-out evaluation, or live research mutations.
