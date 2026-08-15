# ADR-037 — Trade book length for a third scene attempt inside one truthful 55-image envelope

**Status:** Accepted (2026-08-15; owner approved the design and the written spec) · **amends
ADR-010** (one corrected scene retry → two) · **amends ADR-012** (500–800 words → 300) · **amends
ADR-025 Decision 4** (the paid-image coefficient includes output moderation) · **does not amend
ADR-003, ADR-004, ADR-024, ADR-028, or ADR-029** · no contract or schema change

**Context:** S5 of `pipeline-consistency-docket.md` couples three numbers that cannot be chosen
independently: book length, page count, and corrected scene attempts. The owner accepts a shorter
book to buy one additional targeted attempt: at most 300 words, at most 10 scenes, and at most three
consistency attempts per scene.

The existing breaker arithmetic is not truthful. `IMAGE_BUDGET = MAX_SCENES * 2 + 15` funds the
initial scene draw and ADR-010's one consistency redraw, but `output_mod` has a third paid scene
path: one softened redraw after a classifier flag. That node discards `generate_and_store`'s
`paid` boolean, writes no `Cost`, and checks no breaker. With 15 scenes, the current graph can
therefore spend 60 images while recording and claiming a ceiling of 45:

```text
15 scenes × (1 initial + 1 consistency retry + 1 moderation retry) + 15-image prelude = 60
```

The omission is not merely observability drift. ADR-025 defines `cost.image_count` as the
domain-level money backstop, checked before spend. A paid path outside it means the breaker does not
perform its accepted job.

**Decision:**

1. **Input and page ceilings become 300 words and 10 scenes.** `MAX_STORY_WORDS = 300` is enforced
   in the frontend and at the backend trust boundary. The frontend keeps blocking over-cap
   submission; the backend keeps its existing paragraph → sentence → hard-cut fallback for stale or
   direct requests. `MAX_SCENES = 10` remains one constant shared by the segmentation instruction
   and deterministic merge. `MIN_SCENES = 3` and `MIN_SCENE_WORDS = 12` do not move.
2. **A concretely failed scene gets two corrected retries: three consistency attempts total.** A
   pass or unchecked result still finalizes immediately. Concrete failures on attempts 1 and 2
   route through the existing `regenerate → consistency_check` edge. Attempt 3 finalizes through
   the existing lexicographic best-of rule. There is no stop-on-non-improvement branch and no new
   edge, cursor, counter, failure reason, score, or model call type.
3. **Corrections accumulate.** `regenerate` continues correcting from `last.prompt or scene.prompt`.
   Attempt 3 carries the first correction and appends the second. Two correction layers are a
   bounded consequence of the chosen cap; no aggregation or deduplication mechanism is added
   without evidence that the bounded repetition is harmful.
4. **The breaker funds every structurally legal paid image.** A permitted moderation redraw does
   not compete with consistency retries for an undersized shared pool. `output_mod` checks the
   breaker before its redraw, retains the `paid` result, and increments `cost.image_count` only
   when fal was called. The formula is:

   ```python
   IMAGE_BUDGET = MAX_SCENES * 4 + 15   # 10 * (1 initial + 2 consistency + 1 moderation) + 15 = 55
   ```

5. **The recursion formula follows loop depth, not image count.** Three consistency attempts take
   `generate → check → regenerate → check → regenerate → check → output_mod`, or seven super-steps.
   The moderation redraw occurs inside `output_mod` and adds no graph visit. The existing 17-step
   prelude is unchanged:

   ```python
   RECURSION_LIMIT = MAX_SCENES * 7 + 17   # 10 * 7 + 17 = 87
   ```

6. **Judge and classifier calls remain outside `Cost`.** They are real latency and provider costs,
   but no runtime policy consumes a call counter. Adding a contract field solely to make the number
   observable would widen the frozen inter-module contract without strengthening the paid-image
   breaker. Revisit when a concrete cap, budget, or reporting consumer exists.

**Why 300 rather than 250 words:** ten scenes at the joint maximum average 30 caption words. Moving
to 250 would further restrict the child's story without evidence that 25 rather than 30 words is
the quality boundary. The deterministic merge—not division by word count—still enforces ten pages,
so 300 is the smaller product restriction that supports the chosen trade.

**Consequences:**

- The declared worst-case paid-image ceiling becomes **55**, below the current graph's unaccounted
  structural maximum of 60 while adding one consistency attempt.
- The declared graph-depth ceiling becomes **87**, below today's 92 because the page reduction
  outweighs the two added per-scene super-steps.
- ADR-010's former latency/cost consequence changes from two attempts per scene to three. Its
  targeted-correction and best-of principles remain intact.
- ADR-012's no-summarization and boundary-clamp principles remain intact; only its numeric range is
  superseded.
- ADR-036's frozen table and prose name the then-current 45-image/92-step values. Those historical
  statements remain visible but are superseded by this ADR; the implementation's live docs must
  point here rather than silently repeating the old numbers.
- A 300-word story can still contain more than ten distinct visual beats. The deterministic merge
  remains the actual page ceiling; shorter input only limits the resulting density.
- No evidence yet shows that attempt 3 improves visual consistency. The product may use the bounded
  attempt, but no visual-quality or population-level claim follows without separate Tier B evidence.

**Alternatives:**

- **Keep a hard 45-image shared pool and let legal retries compete.** Rejected: a moderation redraw
  could reach a valid safety path and then fail on a budget deliberately too small to fund it. The
  breaker should catch runaway behavior, not make the allowed graph probabilistically incomplete.
- **Keep 15 scenes and fund all current retries.** Rejected for S5: correcting the existing omission
  alone requires `15 * 3 + 15 = 60` images and does not buy the requested third consistency attempt.
- **Use 12 scenes and three attempts.** Rejected: full structural funding requires
  `12 * 4 + 15 = 63`, above both the selected 55 ceiling and the current graph's real maximum of 60.
- **Use 250 words.** Rejected absent evidence: the ten-scene merge already bounds pages, and 300 is
  less restrictive while keeping the joint-maximum mean at 30 words per caption.
- **Stop when `_rank` does not improve.** Rejected: one non-improving redraw is a noisy observation,
  not proof that the last bounded correction cannot pass. Pass and unchecked remain the early exits.
- **Rebuild attempt 3 from the original prompt.** Rejected: it discards the first known correction.
  The existing cumulative path is already bounded and needs no new merge policy.
- **Count judge/classifier calls in `Cost` now.** Deferred: it changes the shared contract but has no
  enforcement or reporting consumer. Add it with the policy that uses it.
