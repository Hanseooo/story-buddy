# ADR-057 — Hard-negative coverage is best-effort; the species and style match is not

**Status:** Accepted (2026-09-03) · **removes an unpreregistered rule from
`validate_hard_negative_matches`** · **preserves both rules `PREREGISTRATION_OBJ4.md:564` actually
commits to** · **requires a preregistration amendment (append-only)** · no freeze-key, provider,
`StoryMemory` field, prompt, or pipeline-shape change

## Context

Phase C was rehearsed for USD 0 against the real `corpus-smoke-h` bundles before the ~USD 25
generation campaign. `build_dataset --candidate-report` runs clean and emits well-formed JSON, and
every `candidates` list came back empty. `validate_hard_negative_matches` then hard-failed:

```
train characters requiring a hard-negative match: 4
  syn-001:c0     species='hedgehog'     style=cel       scenes=5
  syn-001:c1     species='tin rooster'  style=cel       scenes=4
  syn-002:c0     species='human'        style=gouache   scenes=5
  syn-002:c1     species='sheep'        style=gouache   scenes=4

legal pairings found: 0 / 4 characters
FAIL -- ManifestError: every synthetic training reference requires exactly one hard-negative match
```

Projected across all 24 synthetic train stories, **26 of 30 train characters have no legal partner**
(cel 0/10, gouache 2/10, cut_paper 2/10). Only humans repeat within a style, and cel has exactly one.
This is a projection, not a count: species is extracted at generation time, and `'tin rooster'` shows
the extractor keeps modifiers, so exact-equality matching may yield fewer rather than more.

Steps 09 and 13 both consume `dataset_selection.json` and both run **after** the campaign. Left
unfixed, the campaign buys a corpus that cannot produce a dataset, with the repair sitting behind a
pinned `code_commit`.

### The failing rule was never preregistered

`PREREGISTRATION_OBJ4.md:564`, in full:

> **Frozen manual hard negatives:** cross-character constructed negative pairs in the training split
> are selected and frozen in `dataset_selection.json` before non-pilot annotations begin, matching
> character species and art style.

That commits to two properties: **frozen before annotation**, and **matched on species and style**.
It states nothing about coverage. `§3.3:147` adds only that constructed negatives are train-only.
ADR-018:36 ("hard negatives are free") is an argument about labour cost, not about universality.

The `set(matches.keys()) != set(train_characters.keys())` check
(`finetune/dataset_selection.py:361`) entered in `3ababcd` alongside the two preregistered rules,
with a one-line commit message and no spec citation. **It is a strictness instinct in a validator,
not an implemented commitment.**

### Why the corpus cannot satisfy it

Two requirements pull against each other, and nothing in the repo reconciles them. A
character-consistency corpus wants **distinctive** characters, which is what makes a consistency
failure legible to the expert instrument and is what was written: a gecko, a paper crane, a
two-spouted kettle, a storm cloud on nine raindrop feet. A hard negative wants **species
collisions**, because a constructed negative is only hard when two characters could be confused.
`candidate_role` is `not_applicable` on all 30 synthetic stories, consistent with the corpus never
having been authored to supply cross-character negatives.

This is a design tension, not a bug. Neither side is wrong; they were decided at different times and
never reconciled.

## Decision

1. **Hard-negative coverage is best-effort.** The completeness rule at `dataset_selection.py:361-362`
   is replaced by a membership check: every `reference_char_id` in the selection must be a synthetic
   training character, but a training character with no eligible partner may carry no hard negative.
   A partial mapping is a valid, freezable selection.

2. **The species and style match is unchanged, and is not negotiable under this ADR.** Species
   equality (`:372`), style equality (`:379`), the self-pair ban, and the target's
   at-least-one-finalized-scene requirement (`:384`) all stay exactly as written. These are what
   `PREREGISTRATION_OBJ4.md:564` and the 2026-08-22 amendment commit to, and they are the entire
   reason a constructed pair is *hard*.

   **The two comparisons are not written the same way, and this ADR does not level them.** Species is
   compared **case-insensitively** (`.casefold()` on both sides, and the same in `candidate_report`);
   style is compared as a **raw string, no casefold**. That asymmetry is pre-existing and probably
   unintentional, but changing either one is a matching-rule change, which this Decision forbids.
   Recorded so a future reader does not "fix" it as a typo.

3. **The achieved constructed-pair count is reported, not targeted.** Whatever the campaign yields is
   written into the dataset statistics and the writeup. It is not a threshold, nothing fails on it,
   and no selection decision may be made after seeing it. This follows the 2026-08-22 amendment's own
   precedent: *"the achieved imbalance is reported without restyling or outcome-based selection."*

4. **If the training negatives prove thin, the remedy is induced drift, not relaxed matching.**
   Deliberately induced drift (weaker reference conditioning, higher temperature) to harvest natural
   negatives is already pre-committed, train-split-only, at `§3.3:147` item 3 and ADR-018:162. It is
   in bounds without a further amendment. **Relaxing the species or style match to recover coverage
   is out of bounds** — see Rejected alternatives for why it is worse than useless.

5. **This requires a preregistration amendment, appended not edited.** §12 is append-only. The
   amendment records that the completeness rule was code-only, that both preregistered match rules
   survive, and the state at amendment time. The four standing conditions still hold: zero held-out
   results seen, donated stories not in the corpus, zero study labels collected, no fine-tune
   trained. **The amendment must land before any non-pilot annotation**, because
   `dataset_selection.py:413` requires `hard_negatives_frozen_at` to precede every non-pilot
   annotation row.

6. **`candidate_report` is not changed.** It already lists eligible partners per character and
   returns an empty list when there are none. Under Decision 1 an empty list is a legitimate outcome
   to record rather than an error to resolve, so the report becomes the evidence for the achieved
   count in Decision 3.

## Consequences

- **The campaign is unblocked without spending anything to find out.** The blocker was found before
  the money, which is the whole reason the rehearsal happened first.
- **Constructed training pairs drop by roughly an order of magnitude**, from about 135 (30 references
  x ~4.5 target scenes) to about 18 (4 references x ~4.5). This is the real cost of this ADR and it
  is not hidden. The projection above bounds it; the campaign settles it.
- **The primary endpoint cannot be affected.** `manifest.py:validate_manifest` rejects
  `pair_type == "constructed"` outside `train`, and `constructed_records` (`build_dataset.py:195`)
  filters to the train split. Validation and test keep the deployment distribution by construction,
  so this is a training-composition change only.
- **The human-labelled negatives carry more of the load.** Constructed pairs are auto-labelled
  (`same_character=False`, `failure_reasons=[different_face]`). ADR-018's own reasoning is that the
  *positives* are the expensive and noisy side; discrimination is learned from real annotated drift.
  That was always true and is now more visibly true.
- **A future reader will find fewer constructed pairs than the design implies and must not read it as
  a bug.** That is what this ADR and the amendment exist to prevent.

## Rejected alternatives

**Relax the matching rule — drop style equality, or normalize species.** Rejected twice over.
Measured insufficient: even ignoring style entirely, only the 5 humans in the whole corpus collide,
so it does not restore coverage. Worse, it inverts the purpose. Without species equality a
constructed pair is a hedgehog reference against a tin-rooster scene, and the training signal becomes
*"different species implies different character"* — a shortcut that cannot transfer to the held-out
donated test split, where the failures are drift **within** one character. It buys coverage by
degrading every negative into an easy one, and it breaks a preregistered commitment to do it.

**Change the corpus so species repeat within a style.** Rejected on proportionality and on research
integrity. Style reassignment cannot fix it: only 5 characters share a species across the entire
corpus *ignoring* style, so manufacturing collisions requires rewriting story text. That changes
`intake_sha256` and makes the corpus a new hashed input; it means authoring stories to serve a
negative-mining rule, which is the outcome-directed corpus change the preregistration exists to
prevent; it spends the whole generation budget again; and it trades away the property that serves
**Objective 3**, since distinctive characters are what make a consistency failure legible to the
expert instrument. Homogenising the cast to feed the judge's training set damages the thing the judge
is being trained to measure.

**Keep completeness and hand-author matches that violate species or style.** Not possible, and should
not be. The validator would reject them, and defeating it would put a fabricated pairing into a
frozen research artifact.

**Downgrade the failure to a warning.** Rejected. A validator that warns is a validator that gets
ignored at the exact moment it matters. The rule is either right or it is removed; this ADR removes
the one that was never committed and keeps the two that were.

**Say nothing and discover it after the campaign.** Rejected. This is the option the rehearsal
existed to eliminate.

## Evidence

`docs/product/evidence/phase-c-rehearsal-2026-09-03.md`, with
`docs/product/evidence/scripts/rehearse_selection.py`, which is re-runnable from its committed
location and costs nothing. It loads the real bundles, greedily builds the best legal pairing, and
calls `validate_hard_negative_matches`.

**Scope.** The 0/4 failure is measured on real generated bundles. The 26-of-30 figure is a projection
from declared story text, because species is extracted at generation time and the exact strings are
not knowable until the campaign runs. The direction is not in doubt.

## Verification

A test-first change, and small:

1. **Red:** a test asserting that a selection covering a strict subset of train characters validates.
   It must fail against current `dataset_selection.py:361` with `ManifestError: every synthetic
   training reference requires exactly one hard-negative match`.
2. **Green:** replace the set-equality check with the membership check in Decision 1.
3. **One existing test inverts, and it is weaker than its name.**
   `test_validate_hard_negative_matches_rejects_missing_or_excess_reference`
   (`tests/test_dataset_selection.py:617`) is named for both directions but asserts only the
   *missing* one — it omits `syn-002:c2` and expects a raise. Decision 1 makes exactly that case
   legal, so the test inverts to an assertion that a partial mapping validates.
   **The *excess* direction has no test today**, and the set-equality check is the only thing
   catching it (`target_id not in train_characters` guards targets, not references). Replacing that
   check therefore requires a new test that a `reference_char_id` outside the synthetic training
   set still raises. Deleting the old test without adding it would silently drop the only guard on
   a reference that does not exist.
4. **Unchanged and re-run, not rewritten:** the species-mismatch, style-mismatch, self-pair,
   target-without-scenes, and annotation-timestamp tests must all still pass, along with
   `test_validate_hard_negative_matches_success`, whose full-coverage mapping stays valid.
5. **Re-run the rehearsal.** `rehearse_selection.py` against `corpus-smoke-h` must stop raising on the
   completeness rule. The script needs no edit — it already prints the achieved count and already has
   a pass branch; the only thing that changes is which branch it takes. Still USD 0.

**Outcome (2026-09-03).** Implemented as specified. The membership check sits first in the match loop,
before the species lookup, because an unknown `ref_id` would otherwise be a `KeyError` rather than a
`ManifestError`. Both new tests were confirmed red against unmodified source for the intended reasons
(the partial mapping rejected by the completeness rule; the excess reference raising the *wrong*
message because no guard existed). Phase C suite: **144 passed**, up from 143 because one test split
into two, none lost. The rehearsal reports `PASS -- a valid selection exists` on an empty mapping,
which is correct: `corpus-smoke-h` genuinely has 0 legal pairings. No downstream change was needed —
`constructed_records({})` returns `[]`, and `build_dataset`'s guard rejects only `None`.

**What would reopen this:** a corpus that actually supplies same-species, same-style partners at
scale. That is a Phase D corpus decision, not a validator decision.

## Observations recorded but not decided

**Species matching is brittle against an extracted field.** `char.description.species` is written by
`analyze`, not declared at intake, and it carries modifiers (`'tin rooster'`). Casefolding does not
help with that: two roosters still fail to match on `'tin rooster'` vs `'rooster'`. Under Decision 1
that costs coverage rather than failing the freeze, so it is no longer campaign-fatal, but it means
the achieved count may be lower than the projection. Not fixed here: normalizing the field is a
matching-rule change and Decision 2 forbids one.

**The self-pair ban at `:368` is unreachable.** `DatasetSelection.validate_selection_integrity`
(`:81-83`) rejects self-pairs at the pydantic layer, so a `DatasetSelection` carrying one cannot be
constructed and the validator's own check never fires through any real call path. Decision 2 keeps it
as written, but the enforcing check is the model validator, and that is where
`test_selection_rejects_self_pairs` points. Belt and braces, not the gate.

**A reference with zero finalized scenes passes this validator and fails later.** The
`scene_count >= 1` rule at `:384` is applied to the *target* only, so a reference character with a
canonical image but no finalized scenes validates here and then raises `reference character {id} has
no natural training records` inside `constructed_records`. Pre-existing, and Decision 1 makes it
*less* likely to fire rather than more: the old completeness rule forced every train character to be
a reference, including zero-scene ones. Not a regression, not touched.

**`candidate_role` is `not_applicable` on all 30 synthetic stories.** The field exists and the corpus
never used it. Whether it was intended to carry exactly this selection role is unknown, and nothing
in `finetune/` reads it.

**Phase C past step 09 is still unrehearsed.** `freeze_dataset` and `to_llamafactory` were never
reached because this blocker sits upstream of both. Finishing that rehearsal is still free and is
still worth doing before the campaign.
