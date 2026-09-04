# ADR-046 — Clean-base retry is ratified; ADR-037 Decision 3 is superseded

**Status:** Accepted (2026-09-01; owner accepted the ratification) ·
**supersedes ADR-037 Decision 3 and its rejected alternative "Rebuild attempt 3 from the original
prompt"** · **ratifies `visual-prompt-reliability.md` §4.4, shipped 2026-08-16 in `c77d590`** ·
no `StoryMemory`, contract, schema, provider, or graph-shape change · **no code change at all**

**Context:**

ADR-037 Decision 3 reads:

> **Corrections accumulate.** `regenerate` continues correcting from `last.prompt or scene.prompt`.
> Attempt 3 carries the first correction and appends the second.

and its Alternatives section rejects the opposite:

> **Rebuild attempt 3 from the original prompt.** Rejected: it discards the first known correction.

The shipped code does the rejected thing. `backend/pipeline/regenerate.py:40` is
`base_prompt = scene.prompt`, the immutable original. Attempt 3 therefore carries only the
correction derived from attempt 2's verdict, never attempt 2's own correction.

This was not an accident and not silent drift. It was a deliberate reversal, designed and
documented at spec level on 2026-08-16 and shipped in `c77d590`:

- `docs/specs/visual-prompt-reliability.md` §4.4 "Clean-base corrected retries" states the rule
  directly, and invariant 6 restates it: *"Attempt 1 uses `Scene.prompt`; attempts 2 and 3 each use
  `Scene.prompt + latest correction`, never another attempt's prompt."*
- `docs/specs/spend-and-retry-economics.md:124` annotates the change explicitly: *"`regenerate` uses
  the immutable `Scene.prompt` as the clean base for both retries **(amended by
  visual-prompt-reliability)**."*
- `docs/specs/regeneration-controller.md:238` carries it as **Clean-base retry**.
- It is pinned by `backend/tests/test_graph.py::test_three_attempt_graph_ordering_and_clean_base_retries`.

What never happened is ratification. No ADR amends ADR-037 Decision 3, and ADR-037 was never
annotated as superseded on this point — unlike ADR-036, ADR-039, ADR-040 and ADR-041, whose header
lines name their amendments scrupulously. A reader who treats `docs/product/adr/` as the decision
record, which this project's own rules instruct them to do, gets the wrong answer about retry base
selection. This ADR closes that gap and nothing else.

**The evidence, recorded because it bears on the decision:**

ADR-037's consequences section left an open question: *"No evidence yet shows that attempt 3
improves visual consistency."* Local corpus dumps under `data/judge/**/runs/*/memory.json` now
answer it, and the answer is worse than "unproven":

| Measurement | Value |
|---|---|
| Attempts recorded across all runs | 50 |
| Attempts that passed | 2 |
| Passes attributable to a `regenerate` correction retry | **0** |

The two passes are `syn-001` `s0`, which passed on its initial draw, and `syn-002` `s3`, which
passed on attempt 4 — an `output_mod` moderation redraw carrying the
`child-safe, gentle, age-appropriate…` prefix (`output_mod.py:57`) prepended to the **clean** scene
prompt. That redraw discards every correction clause. The only page in the recorded corpus that
recovered late did so on a prompt with the corrections removed.

This evidence does **not** favour the accumulate rule ADR-037 preferred. Accumulation would have
made attempt 3's prompt longer and more self-contradictory, not more effective. It indicates that
the correction mechanism itself is not working, which is a separate question from which base it
builds on, and is deliberately left to a separate ADR (see Escape hatch).

**These numbers must not be quoted as a system pass rate.** They come from three distinct stories
(two counted twice across two corpora) at the most adversarial end of the synthetic set — a
three-eyed hedgehog, a tin rooster specified with *"a smooth, unbroken front surface"* instead of a
face, a six-legged sheep, a stone gargoyle — run under two incompatible configurations
(`corpus-smoke-a` with retries structurally disabled at `scene_attempts: 1`, and
`corpus-abandoned-2026-08-30` at three attempts) on different code commits and extraction prompt
versions. They are sufficient to answer "has a correction retry ever rescued a page in recorded
data" and insufficient for anything else.

**Decision:**

1. **Clean-base retry is the accepted rule.** `regenerate` derives every corrected attempt from the
   immutable `Scene.prompt` plus corrections from the latest attempt's verdict only. Prior
   corrections are not accumulated. This ratifies the shipped behaviour; **no code changes.**
2. **ADR-037 Decision 3 is superseded**, along with its rejected alternative "Rebuild attempt 3 from
   the original prompt", which is now the accepted mechanism. ADR-037's Decisions 1, 2, 4, 5 and 6
   are untouched, as are its word and page ceilings and its budget arithmetic.
3. **ADR-037 gains a header annotation** naming this ADR, so a reader arriving at ADR-037 first is
   not misled. `docs/product/ADRs.md` gains the index row.
4. **The three specs are already correct and are not rewritten.** `visual-prompt-reliability.md`
   §4.4, `spend-and-retry-economics.md:124` and `regeneration-controller.md:238` describe the
   shipped rule accurately. They gain a pointer to this ADR so the ratification is findable from
   either layer.
5. **`docs/specs/consistency-checker.md` gains one missing statement.** It declares
   `constraint_prompt: str = ""` as a bare parameter (§112, §135) and never says where the value
   comes from. The answer is `consistency_check.py:277` — `attempt.prompt or scene.prompt or ""`.
   Documenting it is in scope here because it is the same retry-provenance question; changing it is
   not.
6. **No claim is made that three attempts improve output.** ADR-037's open question is recorded as
   answered-negative for the correction path in the evidence above. `max_scene_attempts` stays at 3
   pending the separate decision below; lowering it would be a product change with its own budget
   and page-count consequences.

**Consequences:**

- The ADR layer stops disagreeing with the code and with three specs. An examiner tracing retry
  behaviour reaches one answer regardless of which layer they start from.
- ADR-037's open evidence question is closed in the record rather than left implicitly open.
- Nothing in the running system changes. There is no migration, no checkpoint invalidation, no
  contract version bump, and no test to rewrite — the pinning test already asserts the ratified
  behaviour.
- The measured ineffectiveness of correction retries becomes a written, dated fact that a follow-up
  decision can build on instead of rediscovering.

**Alternatives:**

- **Change the code to match ADR-037 (accumulate corrections).** Rejected. It would replace a
  deliberately designed, spec-documented, test-pinned mechanism with one that was superseded for
  stated reasons — prompt accumulation and contradictory instruction growth — and the recorded
  evidence gives no reason to expect longer corrected prompts to perform better. It would also be a
  live code change made to satisfy a bookkeeping inconsistency.
- **Annotate ADR-037 in place and mint no new ADR.** Rejected. `AGENTS.md` requires a new file plus
  an index row to change a locked decision; editing a frozen ADR's decision text is the thing the
  freeze exists to prevent.
- **Fold the correction-mechanism fix into this ADR.** Rejected. Base selection and whether
  corrections work at all are separate decisions with different evidence and different blast
  radius. Bundling them would put a code change behind a bookkeeping ratification.
- **Leave it alone; the specs are correct and the code works.** Rejected. The project's stated rule
  is that `docs/product/adr/` is the decision record. An unratified reversal is exactly the defect
  that rule exists to catch, and it is cheap to close now and expensive to explain at a defence.

**Escape hatch:** Two decisions are deliberately left open and each requires its own ADR with owner
acceptance before implementation:

1. **The constraint-judge feedback loop.** `consistency_check.py:277` passes the *corrected* prompt
   as the constraint list, so appended correction clauses become checkable scene constraints. The
   lettering-suppression clause `TEXT_CLAUSE` (`prompt_optimizer.py:378`) has been observed
   generating contradictions about a house's windows and doors, and attempt 3 receives the style
   fragment twice. This manufactures paid retries and is the strongest candidate cause of the zero
   rescue rate above.
2. **Whether corrected retries should exist in their current form**, given that none has rescued a
   page in recorded data. Changing `max_scene_attempts`, the correction clause set, or removing the
   `regenerate` node are all product changes with budget, page-count and ADR-010 consequences.
