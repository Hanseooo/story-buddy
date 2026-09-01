# ADR-050 — The reference judge gets one retry, and an unchecked reference is counted in the record

**Status:** Accepted (2026-09-02; owner approved the design in session before implementation) ·
**amends ADR-025** (retry count at one call site; the accept-unchecked asymmetry itself is
untouched) · **amends ADR-028** (the reference gate's reachability, not its predicate) ·
**does not amend ADR-002, ADR-004, ADR-010, ADR-018, ADR-034, ADR-037, or ADR-049** ·
**no `StoryMemory` or contract change** — `Character.ref_verdict` stays `RefVerdict | None` ·
one additive derived field in `build_corpus` bundle metadata

**Context:**

The 2026-09-02 paid smoke run on `syn-001` (`data/judge/corpus-smoke-b`, USD 0.81, 26 images,
7 scenes, 21 attempts) passed **0 of 7 scenes**. ADR-049 attributed the dominant blocker to
lettering. Reading the seven persisted pages falsifies that:

| Page | `text_free` | Actually on the page |
|---|---|---|
| s0 | False | **"Bok" lettered on the weathervane** — a true positive |
| s1 | True | clean — correct |
| s2, s3, s4, s5, s6 | False | **no text anywhere** |

One true positive, five false positives, and on those five the judge's own `differences_observed`
describes rust mottling on the tin rooster and hatch-mark quills on the hedgehog and never
describes lettering. That is `lettering-suppression.md` §4.6.2's pre-declared failure mode, verbatim
("wood grain, ben-day halftone dots and brush marks can read as writing to a VLM").

It is also **not the blocker**. Counting attempts that would pass with the text gate removed
entirely: **0 of 21**. Every attempt carried contradictions, identity failure reasons, or both.
`text_free` was never once the sole gate. ADR-049's escape hatch is wrong on both counts and this
ADR is the correction of record.

What does block every page:

| Signal | Count |
|---|---|
| `different_face` | 15 of 21 attempts |
| `wrong_body_feature` | 13 of 21 attempts |
| Contradictions naming **Bok-Bok** | **39** of ~89 |

Bok-Bok's stated attributes are *no face*, *standing on one leg*, *metal beak and comb*, *bent
tail*. His accepted canonical reference (`ref/…_ref-c1-1.png`) shows a face with an eye, a fleshy
red comb and wattles, a yellow beak, two scaly legs and a curved tail — four stated attributes
contradicted. Every page inherits it, and the scene judge then correctly reports "Bok-Bok: Has a
face, but should have no face" on all 21 attempts. No page can pass, because each page is measured
against a spec its own reference already violates.

The reference gate exists precisely to catch that. It did not run:

```json
"ref_verdict": null,   // c0 Quill
"ref_verdict": null    // c1 Bok-Bok
```

`null` is reachable through exactly one path (`char_bible.py:293`): `judge` raised, and the
`except Exception` accepted the draw unchecked and returned. **Both references in this run were
never judged at all.** The judge model (`google/gemma-3-27b-it`) has now stalled three observed
times, including the `CALL_TIMEOUT_SECONDS` abort that killed the first attempt at this same run.

Two independent faults compound:

1. **The gate is abandoned after a single transient raise.** The drawn image is already paid for.
   A judge call is ~1.5s and a fraction of a cent against `providers.CALL_TIMEOUT_SECONDS = 120`.
   Giving up the pipeline's highest-leverage check to save that is not a trade; it is a dropped
   check. The first smoke attempt is direct evidence the stall is transient — the identical
   timeout cleared on one unchanged retry.
2. **Nothing reads the signal.** `ref_verdict: null` is honest and is documented as deliberately
   distinguishable from a FAILING verdict, but no consumer distinguishes it. The bundle records
   `ref_retry_count: 0`, which reads as "accepted cleanly on draw one" and here means "nobody
   looked." The defect was found by opening PNGs by hand; nothing in the record surfaced it.

**Decision:**

1. **`mint_reference` retries the reference judge once on the same drawn image, then accepts
   unchecked.** Only after a second raise does control fall through to the existing
   accept-unchecked return. The retry judges the image already in hand — it draws nothing and
   costs no image call.
2. **ADR-025's accept-unchecked asymmetry is unchanged.** The terminal behaviour is identical:
   the artifact exists and is paid for, only the check failed, so the draw ships with
   `ref_verdict=None`. `char_bible.py`'s "do not fix this asymmetry" comment stands and this does
   not fix it — it reduces how often the asymmetry is reached. A judge that is genuinely down
   still yields an unchecked reference, and that is still correct.
3. **Scoped to `mint_reference` alone.** `consistency_check.judge_attempt` keeps one attempt. A
   bad scene is one page and a bad reference is every page — the same asymmetry `MAX_DRAWS = 3`
   already encodes against ADR-010's single scene retry. `_mint_targeted` (ADR-029) is a
   child-initiated single redraw with an unconditional overwrite and is out of scope.
4. **An unchecked reference is counted in the bundle record.** `build_corpus` writes one additive
   `run_metadata` field, `unchecked_references`: the number of characters holding a
   `canonical_ref_image` whose `ref_verdict` is `None`. Derived by reading Story Memory; no new
   call, no contract change, no schema version bump. This run would have written `2`.
5. **No judge-model change and no reference-gate predicate change.** Three stalls from
   `gemma-3-27b-it` is a real signal and a model-selection question governed by ADR-002 and
   ADR-018. It is not smuggled in here. `not verdict.contradictions and verdict.text_free`
   (ADR-034, lettering-suppression §4.2) is untouched.
6. **No claim that this makes pages pass.** A working gate makes Bok-Bok's reference *visible and
   re-rollable* across `MAX_DRAWS = 3`. It does not make the image model able to draw a faceless
   tin rooster, and the run that measures whether three judged draws produce an on-spec reference
   has not happened.

**Consequences:**

- A transient judge stall costs one extra judge call instead of the whole reference gate.
- `unchecked_references` makes "the gate did not run" readable from the bundle without opening
  images. Runs recorded before this change do not carry the field; its absence is not zero.
- Worst-case reference-judge calls per book rise from `MAX_DRAWS` to `2 × MAX_DRAWS` — 3 to 6 for
  a two-character book. Judge calls are text/vision, are not the `IMAGE_BUDGET`, and add no paid
  image call. `CALL_TIMEOUT_SECONDS` bounds each independently, so the worst-case added wall time
  is 120s per stalled draw, inside the ADR-036 1800s job deadline.
- `corpus-smoke-b`'s numbers on contradictions and `text_free` were measured against **unjudged**
  references and are not a baseline for anything. Nothing in `data/judge/` is frozen, so nothing
  is invalidated.
- ADR-049 shipped on a diagnosis this ADR corrects. Its own decision stands on its own evidence
  (5 of 21 attempts had clean identity and were failed by restated checklist axes); only its
  escape-hatch ranking was wrong.

**Alternatives:**

- **Retry the whole draw instead of the judge.** Rejected. It spends a paid image call to fix a
  text-call failure, and the image in hand is not the thing that failed.
- **Raise instead of accepting unchecked after the second failure.** Rejected. That is ADR-025's
  asymmetry, deliberately chosen, and it would kill a whole book to save one unverified
  reference.
- **Retry inside `providers.judge` for every caller.** Rejected. `_bounded` already wraps
  `MAX_RETRIES` SDK attempts in one 120s budget; a second layer there doubles the worst-case wall
  time of every judge call in the pipeline, including the 21 scene calls, to fix a problem
  measured at one call site.
- **Swap the judge model.** Deferred, not rejected — see Decision 5. Three stalls is enough to
  raise the question and not enough to answer it, and answering it here would make this change's
  effect unattributable.
- **Fail the corpus build when `unchecked_references > 0`.** Rejected for now. A count is the
  measurement; a hard gate is a policy decision that needs a rate first, and `corpus_io.py`
  already hard-fails on enough things.

**Escape hatch:** Two items stay open. **`text_free` has a false-positive rate this run puts at 5
of 6 checkable pages** — the pre-declared fallback in `lettering-suppression.md` §4.6.2 is to demote
it to rank-only, a two-line reversal, and the alternative is to make the judge quote the text it
saw so a mottle cannot be expressed (ADR-049's own lesson applied here). It is deferred because it
was measured to change **zero** outcomes on this run, not because it is fine. And **the tin-rooster
pathology is unresolved**: "no face" and "metal beak and comb" may simply be unrenderable by
`fal-ai/qwen-image` for a rooster, in which case the lever is the extraction prompt or the
synthetic story set, not the pipeline. ADR-046's second escape-hatch question — whether corrected
retries should exist in their current form, having still never rescued a page — also stays open.
