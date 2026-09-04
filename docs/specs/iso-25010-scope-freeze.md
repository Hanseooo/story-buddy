# Design — ISO/IEC 25010 scope freeze and issue #68 decomposition

**Status:** approved (owner, 2026-09-04) · **Date:** 2026-09-04
**Derived from:** issue #68, `docs/capstone/iso_iec_25010_readiness_audit.md` (snapshot
`9794c06f`), `docs/product/ROADMAP.md` §de-scope ladder, `docs/product/DECISION_BACKLOG.md`
§"Considered and rejected as deferrals", ADR-013, ADR-020, ADR-027
**Produces:** ADR-058, four replacement issues, and the close of #68

---

## 1. The problem with #68 as written

Issue #68 asks for an ISO/IEC 25040-style evaluation program: approved measures, thresholds,
environments, owners, and dated reproducible evidence for every claimed characteristic — work
groups 3 and 4, plus most of the exit criteria. That includes load tests, browser/device
matrices, disaster-recovery exercises, and clean-environment portability runs.

The capstone never claimed that. Objective 5 is a **perceived-quality Likert questionnaire**
administered to designated software-quality evaluators over five selected characteristics,
reported as weighted means and SD with a CVI gate and Cronbach's α floor
(`methodology.md` §6.3, `research_instruments.md` §D). `methodology.md` §6.4 already states in
bold that a 4.5/5 mean is not evidence the consistency loop works, and `research_instruments.md:175`
already labels the result "**Perceived software quality** — explicitly *not* output quality or
classification performance."

The audit itself says the same thing from the other side (§7): ISO does not independently require
narration or export, and "a large test count is not an ISO pass." It rates the project honestly
and declines to certify. Nothing downstream of that requires the program.

**Position:** the evaluation program is out of scope. What remains is the work that would be
real whether or not ISO/IEC 25010 had ever been mentioned.

## 2. What survives from the audit

Four things, in dependency order.

| # | Item | Audit origin | Why it is real |
|---|---|---|---|
| 1 | Public policy pages assert unshipped features | §6 Group E | `terms/page.tsx:45` and `privacy/page.tsx:30,32` state PDF download and Chatterbox narration as fact. Neither exists in the codebase. Legal surface, child-facing product. |
| 2 | Narration and PDF export scope | §4, work group 1 | Promised across the PRD, roadmap, master spec, policy pages, methodology, and Tool A; implemented nowhere. Blocks the Objective 5 instrument. |
| 3 | `PRIVATE-25010-01..04` + the dependency advisory | §6 Group A | Child-data confidentiality, retention, diagnostics leakage, deployed access-control state. Adjacent to Ethics Stage 1. |
| 4 | B1–B4 correctness gaps | §6 Group B | Ordinary defects with ordinary fixes. B5 is dropped — §5.1. |

Group E's Objective 5 instrument/model mismatch is folded into item 2: the questionnaire's
functional-suitability item cannot be finalised until scope is frozen, because it names the cut
features by name.

## 3. Scope decision

**Narration and PDF export are both cut from the evaluated product scope.**

### 3.1 PDF export

`ROADMAP.md:372` already carries the pre-authorised cut: rung 3, "PDF export — the
out-of-container escape hatch; slideshow still works." ADR-058 invokes that rung explicitly.

**ADR-058 supersedes only the export half of ADR-013.** ADR-013 is "Caption source **and** PDF
export"; its caption decision — the child's verbatim post-redaction text, no LLM rewrite — is
independent and survives untouched. ADR-013 is not edited; ADR-058 names which half it retires.

ADR-027 stays untouched. It specifies on-demand generation with no stored PDF, so there was never
a stored-PDF control to remove, and none must be invented to test.

### 3.2 Narration

Narration is **not** a de-scope rung. It is CC-6 = Accessibility in the cross-cutting concerns
registry (`MASTER_SPEC.md:264`), and cutting it is retiring the project's only named accessibility
mechanism beyond "large targets; minimal text".

`DECISION_BACKLOG.md:440-444` already recorded the exact terms under which this cut is permitted:

> Deferring it narrows a reported evaluation row and drops an accessibility claim — a documented
> cost, not a free win. **Defer only as a deliberate trade, with the Tool A row narrowed in the
> same change.**

ADR-058 is that deliberate trade, and narrowing the Tool A row in the same change is a hard
requirement of it (§3.3 below), not a follow-up.

CC-6 is **narrowed, not retired**: it becomes "large targets; minimal text", and ADR-058 records
that the accessibility surface got smaller and why. ADR-020 is superseded outright.

A browser-native `speechSynthesis` read-aloud was considered — ~15 lines, no dependency, no cost,
and no new trust boundary, since the text never leaves the device. It was rejected by the owner on
2026-09-04 in favour of the clean cut. Recorded so the next session does not re-derive it.

### 3.3 This cut reaches Objectives 1–2, not only Objective 5

`functional-verification-matrix.md:65` scores a Tool A category "Picture book production" as
`Compose, TTS narration, Export`, with the success criterion "Scenes assembled + narrated +
exported as a complete book."

Both cut features sit inside a **reported** evaluation row. ADR-058 must narrow that row to
compose-only in the same change. The category does not disappear; its criterion shrinks to
"Scenes assembled as a complete book."

This is the single highest-risk edit in the whole change, because Tool A produces the Objectives
1–2 functional-verification results. Getting it wrong means reporting a success rate against a
criterion the product was never built to meet.

## 4. Reconciliation surface

One change, per work group 1's exit gate: no contradictory promise survives a repository search.

### 4.1 Code

| Site | Change |
|---|---|
| `backend/contracts/story_memory.py:231,233,267` | Remove `NarrationEntry` and the `narration` field. Orphans this change creates, per AGENTS.md §3. |
| `frontend/app/terms/page.tsx:29,45` | Ships ahead of the ADR — see §5.A |
| `frontend/app/privacy/page.tsx:30,32` | Ships ahead of the ADR — see §5.A |

No pipeline node is deleted: `export` was never built.

### 4.2 Product and architecture docs

| Site | Change |
|---|---|
| `docs/product/adr/ADR-058-*.md` | New. The decision. |
| `docs/product/ADRs.md` | Index row for ADR-058. |
| `docs/MASTER_SPEC.md:264` | CC-6 narrowed to "large targets; minimal text". |
| `docs/MASTER_SPEC.md` §2 | `export` leaves the canonical target graph shape; the `compose / export` row becomes `compose`. |
| `docs/MASTER_SPEC.md` §7 | Drop the `narration` and `export-pdf` module rows. |
| `docs/product/PRD_v2.md:71,182,217,238,244-245,266-267,429,433,435,517-518,533-543,598` | Remove narration and export from the feature list, model table, MVP scope, architecture, cost model, and the Story Memory JSON example. §154, §240 and §398's teacher-gate wording keeps "enters the gallery" and drops "or is exported". |
| `docs/product/ROADMAP.md:188,189,196,395` | Phase 2 loses both; the §372 rung-3 row is marked taken. |
| `docs/TECH_STACK.md:28,29,47,53,72,220` | Drop the Chatterbox and Kokoro rows, narration from the fal.ai row and the cost table, and the PDF clause from Storage. |
| `docs/product/DECISION_BACKLOG.md:382,383,440-444,462,544-545` | Close the `narration` and `export-pdf` rows as cut, not deferred. Keep the §440 rejected-deferral note and append the outcome. |
| `docs/specs/compose.md:12-14,183,192,203-204` | `export-pdf` is no longer "the other consumer of `jobs.pages`". |
| `docs/specs/kid-flow-reader-and-wait-states.md:59,536,591,621` | The reader already ships without a play button; the `narration` pointers become "cut, ADR-058". |

### 4.3 Research instruments — adviser-visible

| Site | Change |
|---|---|
| `docs/specs/functional-verification-matrix.md:65` | The §3.3 edit. Hard requirement of ADR-058. |
| `docs/capstone/methodology.md:74,141,152,416` | §141's "Slide composer with expressive TTS narration; PDF export" and §416's functional-suitability item lose the cut features. §74's phase status is corrected. |
| `docs/capstone/research_instruments.md:94` | The item "Does the system do what it claims — analyze, segment, illustrate, narrate, export?" loses `narrate, export`. |
| `docs/capstone/research_direction_and_goals.md` | Feature references reconciled. |
| `docs/capstone/system_architecture.md`, `value_proposition.md`, `ethics_and_safety.md`, `design_decisions_and_risks.md` | Narration and export references reconciled. |
| `docs/diagrams/` (drawio + excalidraw) | Narration/export nodes removed from both pipeline and architecture diagrams. |

`PREREGISTRATION_OBJ4.md` is not touched: Objective 4 has no narration or export dependency.

### 4.4 Verification

`rg -i "narration|read.?aloud|chatterbox|kokoro|\bTTS\b|narrate"` and
`rg -i "pdf|weasyprint"` over `docs/`, `frontend/app`, `frontend/components`, `frontend/lib`,
`backend/` return only historical ADR text and ADR-058's own record. Excluding `.venv/`,
`node_modules/`, and `.worktrees/` — the worktree is another branch's state (AGENTS.md).

`uv run ruff check . && uv run pytest` green after the `story_memory.py` edit;
`pnpm lint && pnpm build && pnpm test` green after the policy-page edit.

## 5. Work decomposition

Issue #68 is closed and replaced by four issues. The private findings get no public issue.

**A — Correct the public policy pages.** Ships first, independently, no ADR. `terms/page.tsx` and
`privacy/page.tsx` only. Public accuracy on a child-facing product should not wait on an
architectural decision.

**B — ADR-058 and the reconciliation.** §3 and §4 in one change. The ADR is written and accepted
in its own session per AGENTS.md ("architectural decisions get their own session"). §3.3's Tool A
narrowing is part of this change, not a follow-up.

**C — Direct production dependency advisory.** The audit's public release blocker. Step one is
re-confirming it is still open — `pnpm audit --prod --audit-level high` could not reach the
registry from the authoring environment, so the audit's finding is unverified at this date, not
refuted. Then upgrade to a patched compatible release, run the full frontend suite, and
regression-test the middleware/auth boundary.

**D — Objective 5 evaluation profile.** Reconcile the five characteristic labels to 2023
vocabulary ("Usability" → "Interaction capability"), fix the functional-suitability item after B
lands, and obtain adviser sign-off on the applicable profile and the item bank. Gates CVI, pilot,
and administration. Links `action_checklist.md` B4, B8, B9. **Depends on B.**

**E — Correctness batch.** Separate narrow tickets. Each defect below was re-verified present at
`5dafe70` on 2026-09-04; the audit snapshot is 84 commits old and its findings were not assumed.

| Issue | Audit ref | Site | Fix |
|---|---|---|---|
| E1 | B2 | `backend/app/main.py:122` | Enqueue-failure compensation. The pattern already exists at `main.py:164-171` on the resume path; apply it. |
| E2 | B3 | `frontend/lib/useJob.ts:51-57` | `loadRow` discards `error`, so every failure becomes `classify(null)` → `"not-found"`. Preserve missing / unauthorized / transient / terminal. |
| E3 | B4 | `frontend/app/classroom/[classroomId]/settings/page.tsx:49,69` | PATCH and DELETE discard the response. Check `Response.ok`; use the existing request pattern, no new abstraction for two call sites. |
| E4 | B1 | pipeline | Final-asset assurance provenance. **Investigation first** — ADR-046/047/049/050 landed after the snapshot and may already close it. Trace, then fix or record. |

Each starts with a failing deterministic test and updates its spec in the same change.

### 5.1 B5 (atomic annotation claim) is dropped

The audit's B5 asks for an atomic claim at the database boundary because "the annotation queue's
claim behavior is vulnerable to concurrent workers selecting the same work." It rates the effort
**L** — the largest item in the batch — and it requires a migration and therefore its own ADR.

**The race cannot occur.** `PREREGISTRATION_OBJ4.md:616`: "One rater labels every pair. That rater
is the researcher, and there is no second annotator." Inter-rater κ is "undefined for this dataset
— permanently, not pending" (`:623`); the design reports intra-rater test-retest agreement
instead, where round 2 is the same person again. There is one annotator, one queue, one session.

Concurrency hardening for a single-rater instrument is speculative work on a pre-registered
design that forbids the second rater. Dropped under ponytail rung 1.

**Reopen when:** a second annotator is ever added — which would require a preregistration
amendment, since it changes the reported agreement statistic from test-retest back to inter-rater.

**Private.** `PRIVATE-25010-01..04` go to the restricted record. No source locations,
identifiers, reproduction steps, or production links enter the public repository.

## 6. Explicitly not doing

- Work group 3 — per-characteristic requirements, measures, thresholds, environments, owners,
  evidence locations, and failure dispositions across nine characteristics.
- Work group 4 — latency/queue/concurrency thresholds and runs, browser/device matrices,
  screen-reader and reduced-motion campaigns, provider-failure and recovery exercises,
  clean-environment and component-replacement portability exercises.
- Group D's P2 polish, except items that already hold their own issues (#25–#29).
- Any ISO/IEC 25010 conformance or pass claim, now or in the #68 close comment.

If an adviser later requires a real conformance evaluation, that is a new program, and it opens by
disagreeing with this document on the record.

## 7. Spec footprint

This document is the only new spec. The sub-issues produce no further spec files:

- B's durable artifact is **ADR-058**; this design is its input.
- D changes `methodology.md` and `research_instruments.md` — those *are* the instruments.
- E updates the existing affected specs in place, per "behavior change → update the spec in the
  same change".
- A and C need no spec.

Expected new ADRs: **ADR-058** (this scope cut). E4 may add one if its investigation finds a
routing change is needed; no other ticket in the set touches an ADR-gated decision.
