# ADR-055 — A prompt change is measured by rate, not read off a page

**Status:** Accepted (2026-09-03) · **amends ADR-054 D1** (the rule moves inside the field it
constrains) · **retires ADR-054's Verification section** and its Context claim about which scenes
duplicate · **extends ADR-048** (`SEGMENT_PROMPT_VERSION` 1 → 3) · **does not amend ADR-023,
ADR-035, ADR-040, ADR-047, ADR-052 or ADR-053** · no judge-prompt, provider, `StoryMemory` field,
or pipeline-shape change

## Implementation status, stated up front

**D1 and D2 of this ADR are already committed** (`fc3046a`), before this ADR was written. That
inverts the project's own rule that a decision is accepted before it is implemented. It happened
because ADR-054 said its rule "does not prescribe wording", so re-placing the same sentence read
as implementation rather than decision — but the version bump and the retirement of ADR-054's
verification criterion are decisions, and they shipped in the same commit. Recorded here rather
than quietly folded in. Reverting `fc3046a` is one `git revert`; the measurement below stands
either way.

## Context

ADR-054 D1 added one rule to `segment` and predicted it would stop a shared object being drawn
twice. It was implemented as a bullet of its own in the prompt's rule list (`2a87044`) and probed
(`probe_out4`, USD 0.21, `code_commit=2a87044`, 7 images, 0 failed).

**The probe appeared to pass and did not.** Four of the five pages carried one fan, including `s1`
and `s4`, the two scenes ADR-054 exists to fix. But their directions came back **byte-identical to
the pre-fix run** — `Mila and Tala shake the bamboo fan`, `Mila and Tala fan Lola with the
decorated bamboo fan`. The rule changed nothing, so the pages could not be evidence for it.

### Why a page cannot verify a prompt change

The pipeline supplies no seed. `providers.text_to_image` (`:352`) and `providers.edit_image`
(`:381`) both accept one and nothing in the graph passes it, so every draw is an independent
sample from a different seed. Two runs of the same story differ for reasons that have nothing to
do with the change under test. ADR-054's own Verification section — *"read the pages, not the
verdicts. One fan on every page"* — is therefore not a test. It was satisfied by noise on the
scenes it targeted and violated on a scene it did not.

The fixed-seed arms in ADR-054's Evidence were sound precisely because they held the seed and
varied only the prompt. The mistake was carrying that conclusion into an unseeded pipeline run.

### The rule measured properly

Text-only, no image spend: the same story, the same rosters, `SEGMENTATION_PROMPT` as the only
variable, N = 8 segmentations per arm, counting every `key_action` that names two or more of the
scene's present characters together with the fan, and asking whether it resolves who holds it
(`docs/product/evidence/scripts/seg_ab3.py`, ~20 s per repetition):

| arm | directions resolving the holder |
|---|---|
| no rule (control) | 5 / 24 (21%) |
| ADR-054 D1 as a standalone bullet | 9 / 31 (29%) |
| the same sentence inside the `key_action` definition | **14 / 29 (48%)** |

The scoring is a substring heuristic and is imprecise in the conservative direction: it marks
`Tala fans Lola with the decorated bamboo fan` unresolved although it names a single actor. Every
classified direction is printed by the script so the count can be re-checked by hand.

A rule stated as one bullet among sixteen is nearly invisible to a 24B model. The same sentence
placed inside the definition of the field it constrains roughly doubles the rate over control.

### The residual, and a counterexample ADR-054 did not predict

Two things survive.

**One construction resists every arm.** `Mila and Tala fan Lola with the decorated bamboo fan`
came back verbatim in 4 of 4 control repetitions, 4 of 4 bullet repetitions, and 6 of 8 inline
repetitions. Prompting is not moving it.

**Duplication is not exclusive to plural-subject directions.** ADR-054's Context asserted that
*"every duplicating scene is a plural subject with a verb that requires holding the object"*. In
`probe_out4`, `s0` drew two fans from a **single-actor** direction: `Tala pulls the bamboo fan
from behind the rice bin` with `pose_expression` = `Tala holds the fan up`.
`render_visual_direction` (`segment.py:51-55`) concatenates the two, so the rendered direction
names the object twice. That claim of ADR-054's is false as stated, and the double-mention is an
untested second trigger.

## Decision

1. **ADR-054 D1's rule moves inside the `key_action` definition** (`segment.py:134`) and the
   standalone bullet is removed. Measured 14/29 against 9/31 for the bullet and 5/24 for no rule.
   The rule's content is unchanged: name the single character who holds the object, or say the
   characters hold the one object between them.

2. **`SEGMENT_PROMPT_VERSION` goes to 2 for the re-placed rule, and to 3 for D5.** Version 1
   shipped the bullet and is recorded in `probe_out4`'s manifest, so the three are
   distinguishable. **The constant's rule widens**: it is bumped on any change to the direction
   `segment` emits, not only on a change to `SEGMENTATION_PROMPT`. D5 rewrites `key_action`
   without touching the prompt and would otherwise be invisible to the manifest — the exact gap
   ADR-054 D2 was introduced to close, reopened one layer down.

3. **ADR-054's Verification section is retired, and no prompt change is verified by reading an
   unseeded page again.** A prompt change is verified one of two ways:
   - **free, and the default** — hold every input, vary only the prompt, run the node N ≥ 8 times
     and report a rate with the classified outputs printed;
   - **paid, when the claim is about the image** — a fixed-seed arm, the same seeds across arms,
     only the prompt varying, as in ADR-054's Evidence.

   A single unseeded draw is an anecdote in both directions: it cannot confirm a fix and it cannot
   convict one.

4. **ADR-054's causal claim is narrowed.** An unresolved multi-character direction is *one*
   trigger for object duplication, not the only one. The `s0` counterexample is recorded; whether
   naming an object twice in one rendered direction is a second trigger is untested and is not
   decided here.

5. **The residual is not attacked with a third prompt wording.** Two attempts have been measured
   and the failure is concentrated on a construction the model reproduces verbatim. Instead
   `segment` gains a **deterministic normalizer**: a `model_validator(mode="after")` on
   `ExtractedScene`, which is the one object holding `characters_present`, `objects_present` and
   `visual_direction` together. It appends one clause stating that the characters hold the one
   object between them. It never rejects a scene, and it **never invents a single holder** — the
   shared form is the only one derivable from the text. This mirrors ADR-053's normalizing
   validator on `ExtractedObject` and keeps `segment` the sole author of the direction
   (ADR-052 D3).

   **The trigger is a compound subject** — `X and Y <verb> the object`, where both names are in
   `characters_present` and exactly one `objects_present` entry is named — and not merely two
   characters appearing anywhere in the action. That is the symmetric shape measured to duplicate:
   both characters doing the same thing to one object. A looser trigger was written first and two
   existing tests caught it rewriting `Ana hands the wooden sword to Maya`, a transfer that already
   fixes who holds the object and that the clause contradicts. Several objects named in one action
   are left alone: no phrasing stays correct without guessing which one is shared.

   **D5 is not settled by textual resolution.** It counts as fixed only after a fixed-seed image
   arm (~USD 0.20, two seeds, the resisting scene with and without the appended clause) shows the
   fan count drop. The link from resolved text to a single fan on the page was measured at n = 2
   per arm in ADR-054 and is the weakest step in the chain.

## Consequences

- **A second `SEGMENT_PROMPT_VERSION` bump inside one day.** That is the constant doing its job:
  ADR-054 D2 exists so that two runs with different directions are distinguishable, and they now
  are. It must still land before a campaign, never during one.
- **D5 lets `key_action` carry two sentences** where the prompt asks for one action. That is a
  real loosening of the field's definition and it is the price of not depending on model
  compliance.
- **A deterministic clause will sometimes state the obvious**, appending shared holding to a
  direction a reader would already have read that way. Verbosity is the failure mode, and it is
  cheaper than a duplicated object.
- **The defect is still not detectable by the pipeline.** Unchanged from ADR-054: `FailureReason`
  has no duplication term, the judge prompt scopes uniqueness away from objects
  (`consistency_check.py:61`), and `subjects_unique` does not gate. A passing verdict on a
  two-fan page remains expected.
- **Every measurement in this ADR is single-story.** `syn-901` is the reliable reproducer, not a
  sample. The rates above are evidence about a mechanism, not an estimate of the corpus rate.

## Rejected alternatives

**A third prompt wording.** Rejected on process and evidence: two attempts have now been measured,
which is where guessing is supposed to stop, and the surviving failure is one construction
reproduced verbatim across all three arms.

**Reading `probe_out4` as a pass.** Rejected on the facts: the directions it produced for the two
target scenes are byte-identical to the pre-fix run, so the single-fan pages are attributable to
seed, not to the rule. This is the alternative that was nearly taken.

**An object-cardinality clause in the scene prompt.** Already rejected by ADR-054 on measurement,
0 of 8, and nothing here changes that.

**Swapping `segment` to a larger text model.** It would likely comply, and it changes `text_model`
— a pinned freeze key — plus the per-campaign cost basis for every node that shares it. Out of
proportion to one construction, and untested.

**Rewriting `key_action` in `prompt_optimizer`.** Rejected again for ADR-052 D3's reason: a second
author of a field `segment` owns.

## Evidence

All of it is committed under `docs/product/evidence/`, whose README carries the crosswalk from the
scratch paths ADR-053 and ADR-054 cite — those two are frozen and are not edited.

- `evidence/scripts/seg_ab.py`, `seg_ab2.py`, `seg_ab3.py` — the three-arm text-only A/B, N = 8,
  with every classified direction printed. No image spend.
- `evidence/scripts/seg_verify.py` — the same harness against the shipped code, for D5 step 1.
- `evidence/bundles/probe_out4/` — the ADR-054 verification probe, `code_commit=2a87044`,
  `segment_prompt_version=1`, USD 0.21, 7 images, 0 failed. Its `s0` page is the counterexample;
  the direction that produced it is in the committed `memory.json`, the page itself is not.
- ADR-054's fixed-seed image arms (`evidence/scripts/dup_probe*.py`) remain the evidence that a
  resolved direction yields one fan, at n = 2 per arm.
- The generated images are not committed. See the README for what that does and does not cost.

## Verification

D1 and D2 are verified above and by `backend/tests/test_segment_node.py`.

D5 is verified in two steps, in this order:

1. **Free. Done, passed.** N = 8 against the shipped code: **25 / 25**, against 14/29 for the
   prompt rule alone and 5/24 for no rule. `Mila and Tala fan Lola with the decorated bamboo fan`
   now carries the clause every time (`evidence/scripts/seg_verify.py`).
2. **Paid, ~USD 0.20. Not run.** Two fixed seeds, the resisting scene, the appended clause as the
   only difference. Expected: one fan in both seeds. Step 1 passing while step 2 fails means the
   text is resolved and the generator still duplicates, which would move the defect back to
   `prompt_optimizer` and require its own ADR. **Until step 2 runs, D5 is verified as text and
   unverified as a picture** — which is the distinction D3 exists to enforce.

## Observations recorded but not decided

**D5 matches an object only by its full roster name.** A direction that writes `the fan` where the
roster says `bamboo fan` does not trigger the clause. It appeared in the N = 8 run and was resolved
by other means each time, so the gap is real but unmeasured. Widening it means partial matching,
which risks binding the clause to the wrong object.

**Naming an object twice in one rendered direction** (`key_action` plus `pose_expression`, joined
at `segment.py:51-55`) is the `s0` hypothesis. Untested. It is the cheapest next probe if D5's
step 2 fails.

**`complete_visual_profile` still counts entries, not information** (`analyze.py:52`), and it now
has a second page-level consequence: with ADR-054 D4 applied, Lola is no longer cloned from Tala,
but she renders as a young woman rather than a grandmother in `s2` and `s4`. She has no reference
image and no discriminating axis. Carried forward unresolved from ADR-053 and ADR-054.

**Object-to-character binding remains unsolved.** `probe_out4` `s2` directs `Lola points at the
bamboo fan` and draws the fan in Mila's hand. Third ADR in a row to record it.
