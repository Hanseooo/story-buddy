# ISO/IEC 25010:2023 readiness audit

> **Snapshot:** 2026-08-24 at commit `9794c06f41669d35706be6cceb31eb3afb7f7ca6`  
> **Audience:** project owner, capstone advisers/evaluators, maintainers, and implementation agents  
> **Status:** readiness assessment and remediation guide; not a certification or canonical phase-status document  
> **Disclosure:** this is the public-safe edition. It intentionally omits reproduction details for sensitive findings involving child-derived data. Track those details privately.

## Executive conclusion

StoryBuddy cannot yet support a defensible claim that it “passes ISO/IEC 25010.” The current edition of the
standard defines a product-quality model, not a universal pass/fail checklist. A defensible project claim needs:

1. a declared product scope and quality requirements;
2. project-specific measures and acceptance thresholds;
3. evidence collected against those thresholds; and
4. treatment of every material risk discovered during evaluation.

StoryBuddy has a strong maintainability foundation and unusually explicit architecture, safety, and research
documentation. Its deterministic automated checks were green at this snapshot. Those strengths do not offset
two release-blocking confidentiality/safety concerns, an exposed direct dependency advisory, several reliability
and correctness gaps, and missing empirical evidence for performance, compatibility, accessibility, and
operational reliability.

The accurate claim today is:

> StoryBuddy has been assessed for readiness against the ISO/IEC 25010:2023 product-quality model. It is
> **not yet ready for a pass/conformance claim**. Maintainability is comparatively mature; security and safety
> contain release blockers; the remaining characteristics are partly implemented but not sufficiently measured.

## 1. What “pass ISO/IEC 25010” means here

### 1.1 Standard and terminology

This audit uses **ISO/IEC 25010:2023**, which defines nine product-quality characteristics:

- functional suitability;
- performance efficiency;
- compatibility;
- interaction capability;
- reliability;
- security;
- maintainability;
- flexibility; and
- safety.

This matters because summaries based on ISO/IEC 25010:2011 commonly describe eight characteristics and use
“usability” and “portability” where the 2023 model uses the broader terms “interaction capability” and
“flexibility.” ISO/IEC 25023 provides quality-measure concepts, while ISO/IEC 25040:2024 provides an evaluation
framework. Neither supplies one universal release grade that every product automatically passes.

Accordingly, this document uses **readiness** rather than certification language. Final thresholds must be
approved by the project owner and, where they affect the study, the research adviser before results are claimed.

### 1.2 Rating vocabulary

| Rating | Meaning in this audit |
|---|---|
| **Blocked** | A confirmed issue makes a positive readiness claim unsafe or misleading. |
| **Partial** | Relevant implementation exists, but a gap or missing evaluation prevents a complete claim. |
| **Insufficient evidence** | The repository does not contain a repeatable measure and accepted threshold. |
| **Comparatively strong** | Controls and evidence are materially better developed, but not certified. |
| **Out of scope** | Explicitly excluded by an approved product/research decision, not merely unfinished. |

“Not found” means only “not demonstrated in the inspected repository and commands.” It does not prove absence in
an uninspected deployment or external system.

## 2. System and study context

StoryBuddy is both a child-facing storybook application and a capstone research artifact. The deployed design is
a Next.js/React frontend, FastAPI API, RQ worker, deterministic LangGraph pipeline, Supabase data/auth/storage,
Redis queue, and open-weight model providers. The product turns a child’s story into a moderated illustrated
storybook. That makes confidentiality, moderation ordering, PII handling, access control, failure behavior, and
research-data governance first-class quality requirements rather than optional hardening.

Canonical context used by this audit:

- [`AGENTS.md`](../../AGENTS.md) for locked decisions, invariants, commands, and current implementation notes;
- [`MASTER_SPEC.md`](../MASTER_SPEC.md) for the end-to-end architecture and cross-cutting concerns;
- [`PRD_v2.md`](../product/PRD_v2.md) for promised product behavior;
- [`ROADMAP.md`](../product/ROADMAP.md) for phase gates and explicit de-scope options;
- [`ADRs.md`](../product/ADRs.md) and individual ADRs for accepted decisions;
- [`methodology.md`](methodology.md) and [`research_direction_and_goals.md`](research_direction_and_goals.md)
  for study claims and measures; and
- [`functional-verification-matrix.md`](../specs/functional-verification-matrix.md) for the planned functional
  verification instrument.

This audit is a commit-pinned snapshot. It does **not** add another “current phase” authority; follow the status
surface defined in `AGENTS.md` for live phase and probe status.

## 3. Audit method and boundaries

The review combined:

- requirements traceability across the PRD, roadmap, ADRs, specs, capstone documents, and public policy pages;
- static inspection of frontend, backend, worker, pipeline, contracts, migrations, and tests;
- automated lint, build, unit-test, and production-dependency checks;
- comparison with the nine ISO/IEC 25010:2023 characteristics; and
- a distinction between implementation defects, unverified controls, missing measurement evidence, and features
  whose scope is unresolved.

The audit did not run paid provider calls, a live Supabase isolation suite, field usability sessions, load tests,
cross-browser/device trials, disaster-recovery exercises, or capstone participant evaluation. Those remain
evidence gaps, not presumed failures unless a separate confirmed defect is listed.

## 4. Product-scope decisions required before scoring

ISO/IEC 25010 does not require narration or PDF export by name. Whether they affect StoryBuddy’s functional
completeness depends on StoryBuddy’s own approved requirements. The repository currently promises both.

| Capability | Current evidence | Audit classification | Smallest honest resolution |
|---|---|---|---|
| Narration/read-aloud | Accepted in ADR-020; described in the PRD, methodology, privacy notice, and functional matrix; contract scaffolding exists, but end-to-end behavior is not implemented or demonstrated. | **Required but not demonstrated** if current scope is retained. It affects functional suitability and interaction capability/accessibility. Narration quality is not a research outcome variable. | Implement and verify it, or approve a superseding scope decision and reconcile every affected product, policy, research, and test document. |
| PDF export | Accepted in ADR-013 and promised by the PRD, roadmap phase gate, terms, methodology, and functional matrix; implementation is absent. ADR-027 says generation is on demand and the PDF is not stored. | **Required but not demonstrated; eligible for formal de-scope.** The roadmap permits cutting it, but no approved cut was found. | Implement on-demand export, or approve a superseding ADR that invokes the roadmap de-scope rung and reconcile all promises and instruments. Do not invent PDF persistence tests that contradict ADR-027. |

Useful trace points include ADR-020, ADR-013, ADR-027, PRD sections describing the slideshow and MVP, the Phase 2
exit criteria in the roadmap, and the functional-verification matrix’s narrated/exported-book scenario.

Until this decision is recorded, agents must not silently mark either capability optional, nor implement either
as an incidental change: both cross public behavior and accepted architecture.

## 5. Characteristic readiness matrix

| ISO/IEC 25010:2023 characteristic | Snapshot rating | Basis |
|---|---|---|
| Functional suitability | **Partial** | The core moderated illustration pipeline and most user flows exist. Narration/export remain promised but undemonstrated; the functional verification matrix is not yet an executed instrument. |
| Performance efficiency | **Insufficient evidence** | Cost and retry ceilings exist, but no approved latency, throughput, resource, or concurrency thresholds were found with repeatable results. |
| Compatibility | **Insufficient evidence** | Integration contracts and provider smoke tests exist, but supported browser/device combinations and live service interoperability are not demonstrated end to end. |
| Interaction capability | **Partial** | Child and teacher flows, loading/error surfaces, and accessibility intent exist. Keyboard/modal, reduced-motion, responsive, and assistive-technology behavior need systematic verification. Narration is unresolved. |
| Reliability | **Partial** | Checkpointing, bounded retries, deterministic tests, and explicit failure states are strengths. Queue recovery, error interpretation, concurrent research work claims, and recovery exercises have gaps. |
| Security | **Blocked** | The audit confirmed confidentiality-boundary issues involving child-derived content and a high-severity advisory affecting a direct framework dependency. Exact sensitive mechanics are intentionally excluded here. |
| Maintainability | **Comparatively strong / partial** | Locked ADRs, contract-first modules, provider seams, tests, and clear commands support changeability and analysability. Documentation drift and incomplete operational evidence prevent a stronger claim. |
| Flexibility | **Partial** | Environment-overridable model IDs, provider seams, responsive UI intent, and resumable work help adaptability. Deployment portability, scale behavior, and replacement exercises are unproven. |
| Safety | **Blocked** | Moderation and child-safety controls are deeply designed, but confirmed confidentiality issues and an output-correction path that can bypass the full intended consistency assurance prevent a positive claim. |

## 6. Findings grouped for action

### Group A — Private release blockers (P0)

The review confirmed multiple child-data confidentiality, data-minimization, and access-control risks. Public
detail would create unnecessary exposure, so this document assigns opaque tracking IDs only. The owner must create
the corresponding access-restricted records before remediation begins.

| Private ID | Public classification | Status | Owner | Public-safe exit criterion |
|---|---|---|---|---|
| `PRIVATE-25010-01` | Child-derived content confidentiality boundary | Confirmed | Security/privacy owner | The affected boundary is private by default; prior exposure is contained; production verification is recorded privately. |
| `PRIVATE-25010-02` | Collection, redaction, and retention boundary | Confirmed | Product owner + privacy architect | Stored data matches an approved minimization/retention decision; existing affected data is dispositioned; live behavior is privately verified. |
| `PRIVATE-25010-03` | Operational diagnostic minimization | Confirmed | Backend/operations owner | User-readable state contains only stable non-sensitive errors; restricted telemetry retains the diagnostics operators need. |
| `PRIVATE-25010-04` | Checkpoint/access-control deployment state | Requires live verification and remediation as indicated | Database/security owner | Every deployed checkpoint object has the approved isolation posture, and startup/deployment fails closed on drift. |

Do not place source locations, affected identifiers, reproduction steps, screenshots, sample data, advisory
mechanics, or production links for these items in public commits or issues.

#### Public dependency release blocker

The production dependency audit reported an applicable high-severity condition in a direct framework dependency.
Upgrade to a patched compatible release, run the complete frontend verification suite, regression-test the
middleware/auth boundary, and retain advisory specifics with the restricted security record.

### Group B — Correctness and reliability decisions (P1)

#### B1. Final-asset assurance provenance is incomplete across replacement paths

The current evidence does not establish that every replacement of an already evaluated output receives the same
required assurance before delivery. This weakens the meaning of the final verdict.

- **Decision needed:** route corrected output back through the consistency check or formally redefine the verdict
  and document the residual risk.
- **Constraints:** preserve ADR-003 deterministic routing, bounded retries, image-budget accounting, and the
  per-scene moderation order.
- **Verification:** a deterministic graph test must prove every final delivered image has the required moderation
  and consistency evidence.

#### B2. Initial queue-enqueue failure lacks complete compensation

If initial background-job enqueueing fails after job creation, the durable job record can remain in a misleading
state. Define and test one recovery behavior: atomically fail the job with a stable code, or provide a safe,
idempotent re-enqueue path.

#### B3. Client-side data errors can be misclassified as absence

The job subscription/data hook can collapse backend/query failures into a “not found” interpretation. Preserve the
difference between missing, unauthorized, transient, and terminal failure so the UI and operators can respond
correctly.

#### B4. Teacher mutations do not consistently verify HTTP success

Some teacher-facing actions can proceed as if successful without checking `Response.ok`. The minimum repair is a
shared existing request pattern or direct per-call checks with visible failure state—whichever matches current
code without introducing a new abstraction.

#### B5. Research annotation claims are not atomically reserved

The annotation queue’s claim behavior is vulnerable to concurrent workers selecting the same work. Resolve this at
the database boundary with an accepted migration/transaction design; do not paper over it with client state.

#### B6. Live checkpoint isolation is not demonstrated

Treat this as `PRIVATE-25010-04`. Define a fail-closed deployment/runbook rule and test the resulting live policy
state without publishing the database mechanics.

#### B7. Product deletion does not yet demonstrate complete data deletion

Treat deletion coverage as part of `PRIVATE-25010-02`: define and verify the lifecycle across every persistence
layer, including protection for active resumable work. This is a privacy/security requirement, not cosmetic
cleanup; keep affected storage mechanics in the restricted record.

### Group C — Missing evaluation evidence (P1/P2)

These are not all code defects. They are missing proof needed for a quality claim.

| Evidence package | Minimum acceptable artifact |
|---|---|
| Functional suitability | Execute the approved Tool A matrix against the final declared feature scope; retain results and defect disposition. |
| Performance efficiency | Approved p50/p95 latency, queue delay, end-to-end completion, resource/cost, and concurrency thresholds plus a reproducible workload and results. |
| Compatibility | Supported browser/device/service matrix with pass/fail results; include degraded provider and realtime behavior. |
| Interaction capability | Keyboard-only, focus/modal, reduced-motion, screen-reader, responsive, failure/moderation, and child/teacher task checks with accepted criteria. |
| Reliability | Enqueue failure, worker restart, checkpoint resume, provider failure, duplicate delivery/idempotency, and recovery-time exercises. |
| Security/safety | Private remediation evidence for Group A; live RLS/storage isolation results; moderation ordering and corrected-output assurance. |
| Flexibility | Documented deployment assumptions and at least one repeatable clean-environment/replacement exercise for claimed adaptable components. |

The live RLS isolation suite and real-provider smoke tests are intentionally excluded from CI. That is reasonable,
but their absence from this run means their properties are **unverified**, not passing. Record dated pre-deploy
results without exposing credentials or child data.

### Group D — Interaction and performance improvements (P2)

- Verify modal semantics, focus trapping/return, keyboard escape behavior, and background inertness.
- Honor reduced-motion preferences for nonessential animation.
- Exercise every async route’s loading and error surface under realistic latency and failure.
- Avoid loading original/full-resolution assets where bounded thumbnails are sufficient.
- Implement ADR-027’s accepted WebP scene-asset decision, or supersede it; the current scene path and tests still
  encode PNG behavior, leaving the documented payload/storage reduction unrealized.
- Remove avoidable teacher-route hydration waterfalls and duplicate remote reads by following the repository’s
  existing server-layout data-ownership rule.
- Correct the welcome flow that labels privileged teacher signup for “Teacher / Parent”; the PRD treats parents as
  consent-givers, not classroom operators.
- Add end-to-end browser coverage for the highest-risk child, teacher, auth, moderation, and failure flows after
  scope is frozen. Unit/component tests alone do not demonstrate the integrated experience.

### Group E — Documentation and research alignment (P2)

- Resolve the **Objective 5 instrument/model mismatch before CVI, pilot, or administration**. The methodology and
  research instrument currently use five selected labels including “Usability,” while this audit applies the
  ISO/IEC 25010:2023 nine-characteristic model and adviser confirmation is still open. Approve the applicable
  2023 characteristics/subcharacteristics and the actual questionnaire item bank first; do not relabel results
  after collection. See [`methodology.md`](methodology.md), [`research_instruments.md`](research_instruments.md),
  and [`action_checklist.md`](action_checklist.md).
- Resolve narration and export scope once, then update all product, policy, research, and verification references
  in the same change.
- Complete and execute the functional-verification matrix; a draft matrix is not evidence.
- Define measurable thresholds before collecting results so success is not chosen after observation.
- Keep the runtime consistency judge a control signal, not a research outcome measure.
- Preserve pre-registered history with strike-through where project rules require it.
- Correct stale model, node-order, phase, and “built versus planned” statements using the bounded status-surface
  grep process in `AGENTS.md`.
- Make frontend onboarding documentation match the pnpm-only tooling lock and pin the intended pnpm version if the
  project wants reproducible Corepack onboarding.

## 7. Findings deliberately rejected or narrowed

An audit becomes misleading if it turns every possible feature into a defect. The following limits apply:

- **ISO does not independently require narration or PDF export.** They matter because StoryBuddy currently promises
  them. A formally approved de-scope can remove them from functional completeness, but must also reconcile public
  promises and study instruments.
- **Narration expressivity/quality is not a declared research outcome.** Verify functional read-aloud and
  accessibility behavior if retained; do not invent a narration-quality experiment.
- **Stored-PDF controls are not required by the accepted export design.** ADR-027 specifies on-demand generation
  without storing the PDF, so do not add a PDF bucket, persistence, RLS, or signed-URL requirement unless a new ADR
  changes that design.
- **A skipped live integration test is not automatically a failed control.** It is insufficient evidence until a
  dated authorized run proves the deployed property.
- **A large test count is not an ISO pass.** It supports maintainability and regression confidence only for the
  behaviors and environments those tests actually cover.

## 8. Remediation guide and execution order

### Workstream 0 — Contain private blockers

Owner: human maintainer plus an authorized security/privacy reviewer.

1. Open a private incident record for A1, A2, and any affected production data.
2. Contain exposure before adding features.
3. Decide the raw-input/redaction architecture and retention/migration policy in a dedicated ADR session.
4. Upgrade the affected direct dependency and regression-test the auth boundary.
5. Verify production state privately and record dated evidence.

**Exit gate:** no known public path to child-derived content; raw-input handling matches the approved policy;
dependency audit has no unresolved applicable high/critical direct advisory.

### Workstream 1 — Freeze the evaluated feature scope

Owner: product owner and research adviser where study instruments change.

1. Decide narration: retain and implement, or supersede/de-scope.
2. Decide export: retain and implement, or approve a new superseding ADR that formally invokes the roadmap
   de-scope rung. Never edit the accepted ADR in place to reverse it.
3. Reconcile the PRD, ADR index/new ADR if required, roadmap, master spec, methodology, research instruments, public
   policy pages, and Tool A in one change.

**Exit gate:** one approved list of required capabilities, with no contradictory promise in repository search.

### Workstream 2 — Close correctness/reliability gaps

Address B1–B6 as separate, narrowly scoped tickets. Schema, migration, public-interface, auth, and graph-routing
decisions must follow the project’s ADR/spec gates. Each behavioral fix starts with a failing deterministic test
and preserves the contract-first/provider-seam rules.

**Exit gate:** deterministic regression tests pass and the affected specs describe the actual behavior.

### Workstream 3 — Define the evaluation profile

For each retained characteristic/subcharacteristic:

1. name the requirement;
2. name the measure and data source;
3. set the threshold **before** the final run;
4. name the environment/sample/workload;
5. assign an owner and evidence location; and
6. define how failures are dispositioned.

Do not average away a release blocker. Use per-characteristic gates and an explicit rule that unresolved P0
security/safety findings fail release readiness regardless of aggregate score.

For Objective 5 specifically, adviser approval of the applicable 2023 profile and complete questionnaire item bank
is a gate before content validation, pilot testing, or administration.

### Workstream 4 — Execute and package evidence

Run deterministic CI, authorized live isolation/provider checks, functional verification, accessibility/browser
checks, workload tests, recovery exercises, and capstone evaluations. Record command/config version, date,
environment, sample, raw result location, threshold, pass/fail, limitations, and reviewer.

**Exit gate:** another evaluator can reproduce the classification without relying on oral context.

## 9. AI-agent execution contract

Agents implementing this program must:

1. read `AGENTS.md` and `CLAUDE.md`, then the exact feature spec and relevant cross-cutting concerns;
2. treat all accepted ADRs as frozen and open a dedicated ADR session for a required architectural change;
3. keep sensitive Group A details out of public commits, issues, logs, screenshots, and test fixtures;
4. never read or print secret files; use sanitized fixtures and approved live-test procedures;
5. classify work as **confirmed defect**, **scope decision**, **evidence task**, or **documentation reconciliation**
   before editing;
6. grep the entire repository before claiming a feature is absent, unused, or de-scoped;
7. update behavior specs with behavior changes and update the full bounded status surface when a finding changes;
8. mock provider calls in deterministic tests and keep fuzzy quality evaluation out of CI;
9. run the smallest focused test while iterating, then the project-defined verification commands; and
10. report commands, results, skipped checks, deployment verification, and residual risks without converting
    “not run” into “pass.”

### Ticket template

```markdown
## Context
Which requirement, characteristic, and user/data boundary does this ticket concern?

## Classification
Confirmed defect | scope decision | evidence task | documentation reconciliation

## Evidence
Public-safe references only. Put sensitive mechanics in the approved private record.

## Constraints
Relevant ADRs, contracts, provider seams, moderation order, privacy rules, and research constraints.

## Acceptance criteria
- Observable outcome with a predeclared threshold.
- Required deterministic/live/manual evidence.
- Specs and status-surface references reconciled.
- No sensitive data in fixtures, logs, issue text, or screenshots.

## Verification
Exact commands/environment, expected result, and intentionally skipped checks.
```

### Public-safe ticket index

The private IDs above intentionally require the restricted evidence record. The following non-sensitive work is
traceable in the public repository and can be split into narrow tickets.

| Finding | Public evidence | Owner / effort | Confidence | Required verification and evidence destination |
|---|---|---|---|---|
| Initial enqueue compensation | `backend/app/main.py` request/enqueue flow | Backend / S–M | High | Deterministic failure + ambiguous-delivery/idempotency tests; affected API spec. |
| Job-load error taxonomy | `frontend/lib/useJob.ts`; processing page | Frontend / M | High | Hook/page tests for absent, unauthorized, transient, and terminal states; frontend test output. |
| Teacher mutation HTTP handling | `frontend/app/classroom/[classroomId]/settings/page.tsx` | Frontend / S | High | Non-2xx/network tests and accessible error state; frontend test output. |
| Atomic annotation claim | `frontend/app/(research)/annotate/actions.ts`; annotation migrations/spec | Database + research / L | High | Concurrent transaction/isolation test; migration and research-data integrity note. |
| WebP scene delivery | ADR-027; `backend/providers.py`; `backend/pipeline/generate_scene.py` | Backend / M | High | MIME/byte/path regression tests plus measured payload result; affected node spec. |
| Teacher data waterfall | `frontend/components/TeacherShell.tsx`; classroom page/settings | Frontend / M | High | Request-count/integration evidence and frontend tests; existing server-layout rule. |
| Gallery thumbnails | `frontend/app/s/[profileId]/gallery/page.tsx` | Frontend / M | High | Mobile payload/image-dimension result and visual regression; performance evidence package. |
| Reduced motion | Processing and reader pages; existing `useReducedMotion` precedent | Frontend / S | High | Browser test with reduced-motion emulation; interaction evidence package. |
| Image modal semantics | Reader page and shared research lightbox | Frontend / M | High | Keyboard, focus return/trap, Escape, and screen-reader checks; interaction evidence package. |
| Browser-path coverage | `frontend/package.json`; Vitest configuration | Frontend/test / M | High | Small real-browser matrix covering critical child/teacher/auth/failure paths; CI artifact. |
| Parent/teacher wording | Welcome page and PRD role definitions | Product/frontend / S | High | Copy test/review and product-owner sign-off. |
| pnpm onboarding drift | `frontend/README.md`; tooling lock in `AGENTS.md` | Documentation / S | High | Fresh-clone command check and documentation review. |

Exact line numbers are intentionally not frozen in this snapshot; agents should locate the named flow with `rg`,
trace all callers, and cite the current lines in each implementation ticket.

## 10. Verification evidence at this snapshot

| Area | Command/result |
|---|---|
| Frontend lint | `pnpm lint` — passed. |
| Frontend unit tests | `pnpm test` — 42 files, 380 tests passed. |
| Frontend production build | `pnpm build` — passed, including type checking. |
| Backend lint | `uv run ruff check .` — passed. |
| Backend tests | `uv run pytest` — 1,069 passed, 80 skipped; 6 provider smoke tests deselected. |
| Production dependency audit | `pnpm audit --prod --audit-level high` — unresolved high-severity production dependency findings reported; specifics retained privately. |

These results establish a useful deterministic baseline. They do not cover paid providers, a live database,
deployed access policies, browsers/devices, assistive technologies, performance under load, or real recovery.
The raw command logs were not committed, so the counts above are a dated audit record rather than independently
replayable evidence. A future readiness package must retain CI/run artifacts and environment versions.

## 11. Minimum condition for a future readiness claim

A future report may claim readiness only when all of the following are true:

- feature scope is approved and internally consistent;
- no unresolved P0 security or safety finding remains;
- all applicable direct high/critical dependency advisories are remediated or formally risk-accepted;
- required functional scenarios pass;
- each claimed characteristic has an approved measure, threshold, dated result, and limitation statement;
- live access-control, provider, recovery, browser/accessibility, and workload evidence is current for the release;
- behavior, policies, research instruments, and implementation agree; and
- an independent reviewer can trace every conclusion to evidence.

Anything narrower should be phrased precisely—for example, “the deterministic test suite passed” or “the
selected functional scenarios met their thresholds”—rather than “ISO/IEC 25010 passed.”

## 12. References

- ISO/IEC 25010:2023, *Systems and software engineering — Systems and software Quality Requirements and
  Evaluation (SQuaRE) — Product quality model*.
- ISO/IEC 25023:2016, *SQuaRE — Measurement of system and software product quality*.
- ISO/IEC 25040:2024, *SQuaRE — Quality evaluation framework*.
- StoryBuddy canonical sources listed in §2. Consult licensed/official ISO publications for normative wording;
  this audit paraphrases the model and does not reproduce the standard.

## 13. Tracking

Public umbrella issue: [#68 — ISO/IEC 25010:2023 readiness program and evidence gates](https://github.com/Hanseooo/story-buddy/issues/68).
Sensitive remediation remains in separate access-restricted records.
