# ADR-054 — A shared object needs a named holder in the direction

**Status:** Accepted (2026-09-03) · **extends ADR-052 D3** (`segment` is the sole author of
per-scene visual state) · **amends ADR-023** (`StoryObject`/`Scene` untouched; a new
`SEGMENT_PROMPT_VERSION` is recorded in the corpus manifest) · **extends ADR-048** (a prompt change
bumps a recorded version — `segment`'s prompt has never had one) · **does not amend ADR-035,
ADR-040, ADR-047, ADR-049, ADR-050 or ADR-053** · no judge-prompt, provider, contract-field, or
pipeline-shape change

## Context

ADR-053's verification probe removed the two-state fan and left a second defect visible underneath
it: `s1` and `s4` of `syn-901` each render **two bamboo fans** where the story has one. Both fans
agree with each other — both unpainted on `s1`, both painted on `s4` — so this is not the state
contamination ADR-052 and ADR-053 removed. It is a different failure that the state defect was
masking.

The exposure is corpus-wide, not a `syn-901` quirk: **23 of the 72 scenes across all 14 bundles on
disk have two or more characters present and at least one object present.**

### The obvious fix was measured and it does not work

`prompt_optimizer` states cardinality for characters twice — `REFERENCE_CLAUSE`'s per-subject "draw
each character exactly once" (`:226`) and `SUBJECT_COUNT_CLAUSE`'s whole-canvas count (`:243`) — and
states nothing at all for objects. The symmetric repair is obvious, and `prompt_optimizer.py:239`
even records why the second clause exists: *"residual duplication is compositing, and a canvas-level
assertion is the only shape that can contradict it."*

Both forms were tested on `s1`, the reliable reproducer, at two fixed seeds, with only the prompt
varying (`scratchpad/dup_probe.py`, `dup_probe2.py`):

| arm | prompt addition | fans at seed 11 / 22 |
|---|---|---|
| control | — | 2 / 2 |
| per-object | `Draw each object named above exactly once.` | 2 / 2 |
| canvas count | `This illustration contains exactly one bamboo fan.` | 2 / 2 |

**Eight images, eight duplicates.** The analogy to the character fix is wrong, and the reason it is
wrong is the finding: character duplication is a compositing artifact, which a count can contradict,
but here the direction *itself* asks for two. `Mila and Tala shake the bamboo fan` describes two
people each shaking a fan. A count sentence does not override an action the same prompt is
requesting; it only contradicts it, and the generator resolves the contradiction in favour of the
action.

### The direction is the lever, and that is measurable

The scene cut inside one story says the same thing. Every duplicating scene is a plural subject with
a verb that requires holding the object; every non-duplicating one either has a single actor or
marks the object as shared:

| scene | `key_action` | fans |
|---|---|---|
| s0 | Tala pulls the bamboo fan from behind the rice bin | 1 |
| s2 | Lola points at the bamboo fan while talking | 1 |
| s3 | Mila and Tala paint the bamboo fan **together** | 1 |
| s1 | Mila and Tala shake the bamboo fan | **2** |
| s4 | Mila and Tala fan Lola with the decorated bamboo fan | **2** |

Rewriting only `key_action`, same prompt and same seeds (`scratchpad/dup_probe3.py`):

| arm | rewritten `key_action` | fans at seed 11 / 22 |
|---|---|---|
| named holder | Tala holds the one bamboo fan and shakes it while Mila watches the falling rain | **1 / 1** |
| explicit share | Mila and Tala together shake the one bamboo fan they are both holding | 1 (merged face) / **1** |

Sixteen images, ~USD 0.38 total. The two arms that fix it are the two that resolve who is holding
the object; the two that fail are the two that assert a number without resolving it.

### `segment`'s prompt has no version, and this change needs one

`build_corpus.py:500-504` records `extraction_prompt_version`, `reference_judge_prompt_version`,
`scene_prompt_version`, `judge_prompt_version` and `scene_constraint_prompt_version`. There is no
`segment_prompt_version` anywhere in the repository. Every other prompt in the pipeline is a pinned
freeze key and this one is not, so a change to it is currently invisible to the manifest — two runs
with materially different directions would be indistinguishable inside one corpus.

## Decision

1. **`segment`'s rule list gains one constraint.** After the existing holding rule at
   `segment.py:127` — which already says *"Do not infer holding, carrying, or transfer relations…
   When physical interaction matters, state it directly in key_action"* — `key_action` must resolve
   the holder whenever more than one listed character acts on the same object: name the single
   character who holds it, or state that they share the one object. Both forms are measured above;
   the rule permits either and does not prescribe wording.

2. **`SEGMENT_PROMPT_VERSION` is introduced at 1 and recorded in the manifest,** alongside the five
   versions `build_corpus.py:500-504` already writes. It starts at 1 rather than 2 because no
   earlier value was ever recorded; runs predating this ADR are identified by `code_commit`, which
   is the only key that distinguishes them.

3. **Nothing is added to the scene prompt.** The objects block, `REFERENCE_CLAUSE` and
   `SUBJECT_COUNT_CLAUSE` are unchanged, and no object-cardinality clause is introduced —
   both candidate forms were measured at 0 for 8.

4. **`_DESCRIPTION_PLACEHOLDERS` gains the null family** — `null`, `nil`, `n/a` — which
   `analyze.py:147` has always applied on the `owner_name` path. A JSON null written as the *word*
   reached the page verbatim (`Lola, human, null, human, human face, plain clothes`). `unowned`
   stays out: it answers who owns a thing, not what it looks like. This is a bug fix carried here
   because it lands in the same commit and the same freeze keys, not a decision.

5. **No judge change.** `FailureReason` gains no term, `subjects_unique` is not promoted to a gate,
   and the judge prompt is untouched. See Rejected alternatives.

## Consequences

- **`segment` produces different directions for the same story**, so this splits a corpus exactly
  as `code_commit` does. It must land before the next campaign, never during one.
- **Directions get slightly longer and more explicit about staging.** That is the intended effect:
  the pipeline currently emits physically unresolvable frames and the generator picks the resolution.
- **The fix is unverifiable by the pipeline itself.** `FailureReason` has no duplication term, and
  the judge prompt explicitly scopes uniqueness away from objects — *"count only {name} itself, not
  other things of the same kind that the scene simply contains"* (`consistency_check.py:61`). A
  passing verdict on a two-fan page is expected, so the check is the page, as it was for ADR-053.
- **A named holder binds an object to a character**, which the reference images may then contradict:
  in the `holder` arm the fan was drawn in Mila's hand though the direction named Tala. Object
  duplication is fixed; object-to-character binding is not, and is now the visible defect underneath.
- The single-holder form makes a staging choice the story may not state. That choice was already
  being made — silently, by the generator, in favour of duplicating the object.

## Rejected alternatives

**An object-cardinality clause in the scene prompt, in either form.** Rejected on measurement: 0 of
8. This is the alternative the codebase's own prior art pointed at, and the reason it fails is the
reason this ADR exists.

**Gating `subjects_unique`.** The contract comment at `story_memory.py:173` blocks gating on "a
measured duplicate rate"; that rate is now **6 False in 151 verdicts (4%)** across every bundle on
disk. Still rejected: on `s4` the judge returned `subjects_unique=True` against two visibly
duplicated characters, so it misses the case in hand, and gating it would buy paid redraws on a
signal of unknown precision. This is precisely the `text_free` mistake, ungated on 2026-09-02 after
111 of 121 failed draws proved to be false positives (`consistency_check.py:341-350`).

**Adding a duplication term to `FailureReason`.** Rejected for now: the taxonomy is a closed
contract with one home, imported by the judge schema, the regen controller and the finetune tooling
(ADR-028). Widening it to detect a defect this ADR removes at the source is a detection patch ahead
of evidence that the source fix is insufficient.

**Rewriting `key_action` in `prompt_optimizer` instead.** Rejected: it would parse and rewrite the
direction `segment` authored, which is a second author of the same field and the shape ADR-052 D3
exists to prevent.

## Evidence

- Sixteen probe images at two fixed seeds: `scratchpad/dupprobe/`, generated by
  `scratchpad/dup_probe.py` (control and per-object clause, s1 and s4),
  `dup_probe2.py` (canvas count) and `dup_probe3.py` (direction rewrites). ~USD 0.38.
- The bundle the defect was found in: `scratchpad/probe_out3/runs/syn-901/`
  (`code_commit=11485e7`, USD 0.21, 7 images, 0 failed).
- Exposure count (23 of 72 scenes), placeholder survey and the `subjects_unique` rate: computed over
  all 14 bundles under `data/judge/**/runs/*/memory.json` plus both scratchpad probes.
- These paths are session scratch and are not durable — the same caveat ADR-053 records.

## Verification

Re-run the `syn-901` probe (~USD 0.21) and read the pages, not the verdicts. **One fan on every
page**, including `s1` and `s4`. Check that `s4` renders three distinct characters rather than Mila
and two Talas, and that no prompt contains the word `null`.

## Observations recorded but not decided

**`complete_visual_profile` counts entries, not information.** `analyze.py:52` requires three
discriminators across two axes and counts list length, so Lola passed the gate on the strength of
the literal string `null`. With D4 applied she has `colours: []`, `body_features: ['human', 'human
face']`, `clothing: ['plain clothes']` — which still passes, and still carries nothing a generator
can draw her from. This is the same defect as the long-deferred `"plain clothes"` observation, now
with a measured consequence: a text-only character with no discriminating axes was rendered as a
copy of a referenced one.

**Four of 32 character rows across all bundles have no reference image.** Those are the rows at risk
of being cloned, and the count is small enough that reference coverage is a plausible alternative
lever to a stronger completeness gate.

**Object-to-character binding is unsolved and now visible.** ADR-053 already recorded that
`red hair tie` extracts as its own object with `colours: ['red']` while Tala renders with full red
hair; the `holder` arm adds the converse — a named holder the generator ignored. Both are the same
missing binding between a named entity and the thing attached to it.
