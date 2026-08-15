# Feature Spec — Functional Verification Matrix (Tool A)

**Status:** draft · **Phase:** 3 · **Owner node:** `backend/eval/functional_verification.py` (offline script, not a pipeline node)
**Derived from:** MASTER_SPEC §4 (eval harness), §5 (CC-5) · **Rationale:** ADR-004 (non-circularity), ADR-026 (no dashboard), ADR-010 (best-of fallback)

> Read `docs/capstone/evaluation_instruments_brief.md` §3 first — this spec is its operational form. It answers
> Objectives 1–2: did each pipeline stage run and emit valid output.

---

## 1. Purpose

A **script over tracing exports** that computes a per-functional-category success rate from Langfuse traces
of fixture-story runs, and hands the resulting table to the manuscript. It is not a UI and it does not add a
new database table — `MASTER_SPEC.md:217` already commits the eval harness to "offline scripts + tracing
exports," and CC-5 (`MASTER_SPEC.md:246`) already requires every trace to carry gen time, regen count, cost,
and VLM score. Tool A only had to be *specified*; the data layer already existed.

**A dashboard was considered and rejected.** The output is a table pasted into the manuscript a handful of
times, not a thing anyone watches live — the same argument ADR-026 makes against a metrics dashboard for the
annotation surface, restated here because this is where that data actually lives.

---

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

This script writes nothing to `StoryMemory` and adds no table. It is a pure **consumer** of already-emitted
traces.

- **Reads:** Langfuse trace exports for fixture-story runs — per-node status, gen time, regen count, cost,
  VLM verdict (CC-5) — plus the terminal `StoryMemory` snapshot per run (for schema validity checks against
  `story-memory-contract.md`).
- **Writes:** a CSV/table of per-category success rates. No production data, no new schema.
- **Invariants:** every row it reports traces back to a fixture-story run, never a real child's story — see
  §4 on why that keeps this instrument outside ethics clearance.

---

## 3. Position in the system map

Not a LangGraph node. It runs **after** a batch of fixture stories has been processed through the full
Phase-1/2 pipeline, reading their trace exports:

```
fixture stories ──► pipeline (unmodified) ──► Langfuse traces (CC-5) ──► functional_verification.py ──► table
```

It owns no conditional edge — it observes edges the pipeline already took (moderation pass/fail, consistency
pass/fail, ADR-003) and tallies their outcomes; it never influences routing.

---

## 4. Behavior & edge cases

**Happy path:** run N fixture stories through the pipeline (unmodified, no special "eval mode"), export their
traces, then for each of the six functional categories below count `Successful ÷ Total × 100`.

| Functional category | Modules | Pass = | Unit |
|---|---|---|---|
| Input validation & moderation | Input gate (safety + PII redaction) | Story cleared/blocked correctly, schema-valid Story Memory seed emitted | per story |
| Story analysis | Story Analyzer | Entities/coreference extracted into schema-valid Story Memory | per story |
| Scene structuring | Scene Segmentation, Story Memory | Story converted to sequential scenes, Story Memory still schema-valid | per story |
| Visual planning | Character Bible, Style Preset, Prompt Optimizer | Character refs + style + structured prompt produced, all schema-valid | per scene |
| Scene generation & refinement | Image Generator, Consistency Judge, Regeneration | **Consistency loop ran to a terminal state and a shippable page was produced** (incl. best-of fallback) | per scene |
| Picture book production | Compose, TTS narration, Export | Scenes assembled + narrated + exported as a complete book | per book |

**Formula:** `Success Rate = Successful ÷ Total × 100`. *(An earlier draft had this inverted, which would
produce ≥100% — the script must not repeat that.)*

**The unit matters and must be stated in the output table.** Per-story categories and per-scene categories use
different denominators (e.g. 10 stories vs. ~150 scenes); reporting them side by side without labelling the
unit makes the rates look comparable when they are not (`evaluation_instruments_brief.md:103-104`).

**Edge cases:**
- A story blocked at the input gate is **still a Pass** for that category if the block was the *correct*
  outcome for that fixture (a fixture deliberately containing unsafe content that should be blocked) — Pass
  measures "the gate executed and decided correctly," not "the story made it through."
- A trace with a malformed/missing field (schema-invalid `StoryMemory` snapshot) counts as a failure for the
  category that node owns, not a script crash — the script must tolerate partial/incomplete traces from a
  run that itself failed.
- A scene whose consistency loop exhausts its regeneration budget and ships via best-of fallback (ADR-010) is
  a **Pass**, not a Fail and not a judge-approved verdict — see §4.1.

### 4.1 THE CRITICAL RULE: "Pass" ≠ "good"

A Pass means the stage **executed and emitted valid output** — not that the output was high quality.

For **scene generation & refinement** specifically: **Pass = the loop shipped a page**, including a page the
judge flagged and best-of-fell-back on. Pass is **not** "the judge approved it."

> **"Functional completion ≠ output quality"** — Tool B (the expert validation interview) measures quality;
> Tool A measures completion (`evaluation_instruments_brief.md:97-101`).

Defining Pass as *judge-approved* would use the judge to score the outputs it helped produce, which breaks
the non-circularity rule (ADR-004) — the exact reason the judge is never used to grade Objective 3's outputs
either. Tool A cannot quietly become a second judge-scored instrument; it counts execution, full stop.

---

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-5 Observability** — this script's entire input is the trace fields CC-5 already mandates (gen time,
      regen count, cost, VLM score). It adds no new instrumentation; it reads what already exists.
- [x] **CC-7 Reproducibility (seed)** — fixture runs honor `eval.seed`; re-running the script against the same
      trace export set reproduces the same table.
- [ ] CC-1 Moderation ordering — observed, not enforced, by this script (it tallies the outcome of an ordering
      the pipeline already guarantees; see §3).
- [ ] CC-2, CC-3, CC-4, CC-6, CC-8, CC-9, CC-10 — N/A. This is a read-only offline script over existing traces
      of fixture-story runs; it has no user, no cost of its own beyond the fixture runs it reads, and no state
      to checkpoint.

---

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked (fixture-story pipeline runs are already mocked at this tier per MASTER_SPEC §6). Assertions:

- `Success Rate = Successful ÷ Total × 100` never exceeds 100 and never divides by zero (guards the
  known inverted-formula mistake).
- A scene marked `passed=True` via best-of fallback (`Attempt.passed=True`, `vlm_verdict.same_character=False`
  on the shipped attempt) counts as a **Pass** for "Scene generation & refinement" — the regression test for
  §4.1's central rule.
- A schema-invalid terminal `StoryMemory` snapshot for a run counts as a **Fail** for whichever category owns
  the invalidating field, and does not raise an uncaught exception in the script.
- Per-category output rows carry their stated **unit** (`per story` / `per scene` / `per book`) — the table
  never mixes denominators silently.
- The script accepts a trace export fixture with zero runs and reports `0/0` categories as `N/A`, not a
  divide-by-zero crash or a fabricated 100%.

---

## 7. Eval / quality checks (if fuzzy — MASTER_SPEC §6 Tier B)

N/A. Tool A measures functional completion, which is binary per the Pass definitions in §4 — it produces no
content whose *quality* is subjective. (Objective 3's acceptability claim and Objective 4's classification
performance are the fuzzy legs; both live in their own specs, not here.)

---

## 8. Linked decisions & open questions

**Depends on:** ADR-004 (why Pass cannot be judge-approved), ADR-010 (best-of fallback is what makes a
flagged-but-shipped page still a Pass), ADR-026 (why this is a script and not a dashboard).

**Runs on fixture stories, not the donated corpus** — it needs **no ethics clearance** and is valid
October-defense material ahead of the donated-corpus results (`evaluation_instruments_brief.md:80-81`). Real
donated-story traces may also be fed through the same script once collected, but the instrument's validity
does not depend on that — fixture-story runs are sufficient on their own.

**Open — do not guess (CLAUDE.md §1, §7):**

- Exact number of fixture stories per category, and whether "Visual planning" and "Scene generation &
  refinement" report over the same set of scenes or independently sampled ones, is not fixed here — a
  scheduling decision for whoever runs the Phase-3 eval pass, not a schema question this spec answers.
- Whether the script also runs once against the ten primary donated-corpus stories (in addition to fixtures)
  for a second reported table, or fixtures alone are reported, is open — flagged rather than assumed, since
  the donated corpus carries ethics obligations the fixture corpus does not.
