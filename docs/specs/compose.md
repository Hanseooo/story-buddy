# Feature Spec — compose

**Status:** built · bab3351 · **Phase:** 1 · **Owner node:** `backend/pipeline/compose.py`
**Derived from:** MASTER_SPEC §2 (system map) · **Rationale:** ADR-003, ADR-010, ADR-013, ADR-024,
ADR-025, ADR-028

## 1. Purpose

The graph's terminal gate. It asserts the run produced a shippable book, emits the one per-book
record, and produces no artifact.

**There is nothing to assemble.** MASTER_SPEC §2's `compose / export` row reads *"passed scenes +
captions → storybook + PDF in Storage"*, and both halves of that are owned elsewhere: the PDF is
`export-pdf` (Phase 2, ADR-013), and the page sequence already exists — `story_memory.py:129-131`
makes `scenes[]` insertion order the contract and deliberately refuses a `Scene.order` field
because it would be a second source of truth. A page is a `Scene`: image plus verbatim caption,
nothing else (USER_FLOW §4.7, ADR-013). Building a derived `pages[]` block would create exactly
the duplicate the contract rejects.

What is left is the invariant no other node is positioned to check — *is there a book at all, and
is every page in it real* — and the terminal log line that says how the book came out.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `scenes[].final_image_ref`, `scenes[].attempts[].image_ref`, `.passed`,
  `.vlm_verdict`, `cost.image_count`, `cost.regen_count`
- **Writes:** nothing. `compose` returns `{}` on every path that returns at all.
- **Invariants:**
  1. **No state write.** The partial return is always `{}`. `compose` is the one node that reads
     the whole book and changes none of it.
  2. **No effects.** No provider call, no Storage, no DB — therefore **no helper**, which is why
     MASTER_SPEC §6 rule 1 names this node as its example of a node that needs none.
  3. **A book reaching `END` has ≥ 1 scene, every scene has a `final_image_ref`, and every scene
     has a `caption`.** This node is where that becomes true or the job fails
     (`kid-flow-book-persistence.md` §4.2 — a page is an image plus a verbatim caption, ADR-013).
  4. Purity ⇒ idempotent re-entry at zero cost (CC-10).

`contracts/` is **untouched** by this spec.

## 3. Position in the system map

```
consistency_check ──► route_after_check ─ none remain ──► compose ──► END
```

`compose` owns **no** conditional edge — ADR-003's branch points are moderation, consistency, and
ADR-029's reveal, and this is none of them. It is reached two ways, both through
`route_next_scene`: the normal tail (every scene finalized) and ADR-024's empty-`scenes[]` case at
the loop head, where `segment` produced nothing and there is no loop to enter. **The second path
is the reason the gate exists** — it is the only way a zero-page book reaches the terminal.

Phase 2 inserts output-image moderation between `consistency_check` and `compose` (MASTER_SPEC §2,
ADR-011). That is a new predecessor and changes nothing here; see §8 for the gate tightening it
brings.

## 4. Behavior & edge cases

**Happy path.** Three steps, no branches worth naming:

1. Assert the book is non-empty and every scene is finalized.
2. Classify each page by the attempt that won.
3. Log the per-book summary; return `{}`.

```python
"""The graph's terminal gate (spec `docs/specs/compose.md`).

No provider call, no I/O, no helper (MASTER_SPEC §6 rule 1) — the book IS `scenes[]` in
segmentation order, so there is nothing to assemble. What is left is the invariant no other
node is positioned to check, and the one per-book record the run emits.
"""
import logging

from contracts.story_memory import Scene, StoryMemory

log = logging.getLogger(__name__)


def _outcome(scene: Scene) -> str:
    """How the page that shipped got there: passed / failing / unchecked.

    Matched by `image_ref`, not by position: ADR-010's best-of may ship attempt 1 or attempt 2,
    and the Storage paths are per-attempt (`{story_id}/{scene_id}-{n}.png`), so the match is
    unique. A `final_image_ref` with no matching attempt cannot happen — `consistency_check`
    derives it from one — and counts as `unchecked`, because it carries no verdict either way.
    """
    winner = next((a for a in scene.attempts if a.image_ref == scene.final_image_ref), None)
    if winner is None or winner.vlm_verdict is None:
        return "unchecked"
    return "passed" if winner.passed else "failing"


def compose(state: StoryMemory) -> dict:
    if not state.scenes:
        raise ValueError("compose: no scenes — there is no book to compose")

    unfinalized = [s.scene_id for s in state.scenes if s.final_image_ref is None]
    if unfinalized:
        # Unreachable while `route_next_scene` is correct, and that is the point: a routing
        # regression fails the job HERE rather than shipping a book with a blank page.
        raise ValueError(f"compose: scenes not finalized: {unfinalized}")

    uncaptioned = [s.scene_id for s in state.scenes if not s.caption]
    if uncaptioned:
        raise ValueError(f"compose: scenes without a caption: {uncaptioned}")

    outcomes = [_outcome(s) for s in state.scenes]
    # CC-5: the only per-book terminal record the run produces.
    log.info(
        "compose: pages=%d passed=%d failing=%d unchecked=%d image_count=%d regen_count=%d",
        len(outcomes), outcomes.count("passed"), outcomes.count("failing"),
        outcomes.count("unchecked"), state.cost.image_count, state.cost.regen_count,
    )
    return {}
```

**What the gate does *not* fail.** Everything the upstream nodes deliberately ship:

| Case | Behavior |
|---|---|
| **Zero scenes** | `raise ValueError` → `run_job.py`'s handler writes job `failed`. Reachable today: empty/whitespace input (`segment.py:143`) or `repair` clamping every range away, with no `input_gate` length check until Phase 2's `length-guard`. A book with no pages is not a book, and ADR-025 forbids shipping a partial one. |
| **A scene with `final_image_ref is None`** | Same raise. Unreachable by construction — `route_next_scene` only routes here when none remain — so this is an invariant assertion, not a handled case. It is cheap, and the alternative is a book with a blank page and no signal. |
| **A page that shipped a *failing* best-of image** | **Ships.** ADR-010's best-of fallback is the designed outcome, and ADR-028 sets the same policy for references: never a placeholder, never a failed job. Counted as `failing` in the summary. |
| **A page that went unchecked** (`vlm_verdict is None`) | **Ships.** A judge or Storage outage means *the check failed, not the artifact* (ADR-025, `consistency_check.py:157-161`). Counted as `unchecked`. |
| **A scene whose characters had no canonical reference** | **Ships.** It reaches here with `vlm_verdict is None` and lands in `unchecked` — `judge_attempt` returns `[]` for empty subjects. Nothing about a missing reference is this node's to fail (`character-bible` §5). |
| **Re-entry after a lost checkpoint** | Re-runs the assertions and re-logs. Pure, zero cost, no re-pay (CC-10). |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-3 Cost control** — *reports*, does not enforce. `cost.image_count` and
      `cost.regen_count` land in the summary line so a book's spend is legible without replaying
      the trace. The ADR-025 D4 breaker itself lives in `generate_scene` and `regenerate`, where
      the spending happens; a breaker at the terminal would trip after the money was gone.
- [x] **CC-5 Observability** — the one per-book record. Per-scene facts already exist in
      `consistency_check`'s line and in `attempts[]`; what did not exist anywhere is a *book*-level
      row. `functional-verification-matrix` (Tool A) is an offline script over tracing exports and
      its Picture-Book-Production criterion is scored **per book**
      (`evaluation_instruments_brief.md:91`) — this line is what it reads.
- [x] **CC-10 Checkpointing / resumability** — pure and effect-free, so re-execution after a lost
      checkpoint is free and cannot double-charge. The strongest form of the tick, by doing nothing.
- [ ] **CC-9 Failure states = success states** — **partially satisfied, and not by this node.**
      The raise reaches `run_job.py:41` and becomes `{status: failed, error: str(exc)}`. ADR-025
      Decision 5's `jobs.failure_reason` enum column **does not exist** (already flagged unowned by
      `image-generator` §8), so the kid-facing screen has only a dev-only `error` string to branch
      on. Flagged in §8, not absorbed.
- [ ] **CC-1 Moderation ordering** — N/A **today**, and deliberately not faked: nothing writes
      `scenes[].moderation_status`, so a gate on it would assert a field that is always `None`.
      The tightening belongs to `moderation-stack` (§8).
- CC-2 (PII — `input_gate`, upstream), CC-4 (no asset access at all), CC-6, CC-7 (no model call to
  seed), CC-8: **N/A.**

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

`backend/tests/test_compose_node.py`. **No mocks needed** — the node has no effect boundary, which
is the practical payoff of invariant 2.

1. **Zero scenes raises.** `StoryMemory` with `scenes=[]` → `pytest.raises(ValueError)`.
2. **An unfinalized scene raises**, and the message names the offending `scene_id` — the assertion
   is only worth having if it says which page.
3. **A mixed three-page book returns `{}`** and logs `pages=3 passed=1 failing=1 unchecked=1`
   (`caplog`): one page whose winning attempt has `passed=True`, one with a real verdict and
   `passed=False`, one with `vlm_verdict=None`.
4. **Best-of shipping attempt 2 is classified by attempt 2.** A scene with two attempts where
   attempt 1 passed and attempt 2 did not, `final_image_ref` pointing at attempt 2 → `failing=1`.
   This is the assertion that fails if `_outcome` ever regresses to `attempts[-1]` or `attempts[0]`
   instead of matching `image_ref`.
5. **`cost` passes through to the log** — `image_count` and `regen_count` are reported from state,
   not recomputed.

`tests/test_graph_stub.py` already runs the full graph to `compose`; no new graph test — the
existing end-to-end runs now assert against a node that can fail, which is coverage gained for free.

## 7. Eval / quality checks

**N/A.** This node produces no content.

## 8. Linked decisions & open questions

**Depends on:** ADR-003 (no new branch point), ADR-010 + ADR-028 (best-of is a shippable outcome,
not a failure), ADR-013 (a page is image + verbatim caption; the PDF half is `export-pdf`),
ADR-024 (the empty-`scenes[]` path that makes the gate necessary; partial-return convention),
ADR-025 (never a partial book; a raise becomes job `failed`), MASTER_SPEC §6 rule 1 (no helper).

**Handed off — flagged, not absorbed:**

- **The multi-page persistence gap → closed by `kid-flow-book-persistence.md`.** `run_job.py` now
  projects every scene into `jobs.pages`, `frontend/app/book/[jobId]/page.tsx` renders the whole
  array, and this node's invariant 3 gates the caption half of that contract (ADR-013: a page is an
  image plus a verbatim caption). `export-pdf` remains the other consumer of `jobs.pages`.
- **`jobs.failure_reason` (ADR-025 Decision 5) → unowned**, as `image-generator` §8 already
  records. This node adds a second producer of job-level failures with no enum to name itself by.
  Migration `0003` plus a taxonomy map in `run_job.py`. Note the constraint: `FailureReason` in
  `contracts/` is frozen at 7 by ADR-028 and is the *scene identity* taxonomy — this is a different,
  job-level enum, and conflating them would corrupt Objective 4's F1 denominator.
- **Output-image moderation → `moderation-stack`** (Phase 2). When that node lands ahead of
  `compose` and starts writing `scenes[].moderation_status`, the gate should extend to *"every page
  is moderated"* — the CC-1 promise is that no unmoderated image reaches a child, and this is the
  last place to check it. That extension is `moderation-stack`'s to make, in the same change that
  starts writing the field.
- **The PDF/storybook artifact → `export-pdf`** (Phase 2, ADR-013 WeasyPrint). MASTER_SPEC §2's
  `compose / export` row is one row for two nodes; this spec covers only the first.

**No open decisions.** Nothing here needs an ADR — the node adds no branch, no contract change,
no dependency, and no schema change.
