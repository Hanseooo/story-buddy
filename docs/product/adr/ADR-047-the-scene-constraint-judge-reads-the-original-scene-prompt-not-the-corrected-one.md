# ADR-047 — The scene-constraint judge reads the original scene prompt, not the corrected one

**Status:** Accepted (2026-09-01; owner accepted the design and the failing test) ·
**amends ADR-004** (the scene-constraint judge's input, not its existence or its reason-then-score
shape) · **does not amend ADR-010, ADR-028, ADR-037, or ADR-046** · no `StoryMemory`, contract,
schema, provider, or graph-shape change · one-line node change plus one test

**Context:**

`consistency_check.py:277` calls the judge seam as:

```python
identity_verdicts, composition = judge_attempt(
    attempt.image_ref, subjects, attempt.prompt or scene.prompt or ""
)
```

The third argument becomes `SCENE_CONSTRAINT_PROMPT.format(constraints=...)`
(`consistency_check.py:191`), whose instruction to the judge is *"Check it only against the exact
scene constraints below"* and *"A contradiction is a stated requirement the page violates."*

On attempt 1 `attempt.prompt` equals `scene.prompt`, so the two readings agree. On a corrected
retry they do not. `regenerate` builds `attempt.prompt` as `scene.prompt` plus clauses appended by
`correct_prompt`, and those clauses are then handed back to the judge as **stated requirements the
page must satisfy**. The lettering-suppression clause is the clearest case:

```python
TEXT_CLAUSE = "every surface in the picture is blank and unmarked"   # prompt_optimizer.py:378
```

Appended to fix a page that rendered text, it arrives at the constraint judge as a rule that every
surface in the picture is blank — which a drawn house with windows and a door violates. The
correction that was meant to rescue the page becomes the reason the page fails. The style fragment,
already carried by `scene.prompt`, is delivered twice on attempt 3 for the same reason.

`scene_contradictions` is not advisory. `consistency_check` computes:

```python
concrete_failure = (... ) or bool(scene_contradictions)
```

so a contradiction manufactured this way forces another paid retry, which appends another clause,
which the judge then checks as another requirement.

ADR-046 recorded the outcome: across 50 recorded attempts, 2 passed and **0 passed on a
`regenerate` correction retry**. The one late pass came from `output_mod`'s moderation redraw, which
rebuilds from the clean scene prompt and discards every correction clause. This ADR names the
feedback loop as the strongest candidate cause. It does not claim to have proven causation — the
recorded corpus is three stories under two incompatible configurations (ADR-046) and cannot carry
that claim.

The defect is reproducible without any of that. A failing test now pins it:
`tests/test_consistency_check_node.py::test_the_constraint_judge_is_given_the_original_scene_prompt_not_the_corrected_one`
constructs a scene whose second attempt carries `TEXT_CLAUSE` and asserts the judge is given the
original prompt. It fails with the corrected prompt, verbatim clause included.

**Decision:**

1. **The constraint judge reads `scene.prompt`.** `consistency_check.py:277` becomes
   `scene.prompt or attempt.prompt or ""`. The fallback order is reversed rather than dropped: it
   preserves today's behaviour for the unreachable case where `scene.prompt` is unset on attempt 1,
   and it cannot reintroduce the loop, because `regenerate` hard-fails when `scene.prompt` is None
   (`regenerate.py:38`) so no corrected attempt can exist without it.
2. **The constraint set is the story's, not the controller's.** `Scene.prompt` is the immutable
   record of what the story fixed. Correction clauses are instructions to the image model about how
   to redraw; they are not facts about the scene and are not checkable requirements. Nothing the
   controller appends may enter the constraint list.
3. **This is the same provenance rule ADR-046 ratified for `regenerate`, applied to the judge.**
   Retries derive from the immutable `Scene.prompt`; from this ADR, so does the judging of them.
   Both arms of the loop now read one base.
4. **No change to identity judging.** `judge_attempt`'s first two arguments, the per-character
   `JUDGE_PROMPT` calls, the worst-wins fold, `GATING_REASONS`, `_rank`, and `max_scene_attempts`
   are untouched. Section D of the validation instrument is defended by the identity judge, and this
   ADR does not weaken it.
5. **`docs/specs/consistency-checker.md` §135 is corrected in the same change.** ADR-046 Decision 5
   made it state the current provenance; this ADR changes that provenance, so the sentence changes
   with it.

**Consequences:**

- A corrected retry is judged against the same constraints its first attempt was. Retry N and
  retry N+1 become comparable, which they are not today.
- Contradictions manufactured by the controller's own clauses stop forcing paid retries. Expected
  direction is fewer retries per scene, therefore lower spend inside the unchanged ADR-037
  55-image envelope. **No pass-rate improvement is claimed.** Whether corrections work at all is
  ADR-046's second escape-hatch item and remains open.
- Real contradictions are unaffected: they are violations of `scene.prompt`, which is still the text
  the judge checks.
- One test is added. No existing test changes, because no existing test asserted this provenance —
  which is why the defect shipped.

**Alternatives:**

- **Filter correction clauses out of the corrected prompt before judging.** Rejected. It needs a
  list of known clause strings kept in sync with `correct_prompt` in a second file, and it is
  string-matching what a field boundary already answers. The original prompt is available; use it.
- **Keep the corrected prompt and teach `SCENE_CONSTRAINT_PROMPT` to ignore redraw instructions.**
  Rejected. It spends a prompt-version bump and a judge round-trip on asking a VLM to sort
  requirements from instructions, when the caller already knows which is which.
- **Stop passing constraints on retries at all.** Rejected. It would leave corrected attempts
  unchecked against the story's own facts, so a retry could drift off the scene and pass.
- **Leave it and lower `max_scene_attempts` instead.** Rejected. That hides the loop by giving it
  less room to run, costs the third attempt ADR-037 bought with 200 words and 5 pages, and is a
  product change where a provenance fix is available.

**Escape hatch:** `Scene.prompt` still contains the style fragment (`build_prompt` invariant 1), so
the constraint judge is checking the page against styling language on every attempt, not only on
retries. This ADR removes the doubling on attempt 3 but not the base inclusion. Narrowing the
constraint text to only the story-fixed facts — characters, objects, location, visual direction —
is a larger change to `build_prompt`'s output contract and requires its own ADR. ADR-046's second
escape-hatch item, whether corrected retries should exist in their current form, also remains open
and is not answered here.
