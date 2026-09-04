# ADR-049 — The scene-constraint judge returns structured contradictions, not free-text labels

**Status:** Accepted (2026-09-02; owner accepted the design and the smoke-run evidence) ·
**amends ADR-004** (the scene-constraint judge's output shape; identity judging, reason-then-score,
and the 2-reference cap are untouched) · **extends ADR-047** (which fixed the judge's *input*; this
fixes its *output*) · **does not amend ADR-010, ADR-028, ADR-037, ADR-046, or ADR-048** ·
**no `StoryMemory` or contract change** — `Attempt.scene_contradictions` stays `list[str]` ·
node-local boundary schema change plus `SCENE_CONSTRAINT_PROMPT_VERSION` 3 → 4

**Context:**

ADR-047 stopped correction clauses from reaching the constraint judge as checkable requirements. A
paid smoke run on `syn-001` (2026-09-02, `data/judge/corpus-smoke-b`, USD 0.81, 26 images, 7 scenes,
21 attempts) confirms that worked: of **89** contradictions emitted across the run, **0** contain
`TEXT_CLAUSE` language. The input contamination is gone.

The run also shows it changed no outcome. **0 of 7 scenes passed.** Every scene ran to ADR-037's
third attempt. The reason is a second, independent defect in the same judge, on the other side of
the call.

`SCENE_CONSTRAINT_PROMPT` (v3) asks for two separable things:

> First describe every observed difference from those constraints. Then list each contradiction
> separately. Every contradiction must name the subject and the violated requirement.

`SceneConstraintVerdict` gives the first a field (`differences_observed: str`) and the second a
field (`contradictions: list[str]`), but nothing in the schema distinguishes them. The judge fills
`contradictions` with both. From this run, unmodified:

```text
Bok-Bok: Has a face, but the constraints state it has no face.      <- a contradiction
Bok-Bok: Tail is curved, but the constraints state it is bent.      <- a contradiction
Quill - Viewpoint: three-quarter                                    <- a label
Quill - framing: medium shot                                        <- a label
Quill - Visual direction: Quill looks around with all three amber
  eyes curious and focused                                          <- a restated constraint
```

The last three assert no violation. They name a checked axis and its expected value — the judge
reporting what it checked, in the field reserved for what failed.

`consistency_check` cannot tell the difference:

```python
concrete_failure = (...) or bool(scene_contradictions)
```

Any non-empty list is a concrete failure, so a label costs a paid retry exactly as a real violation
does. Measured on this run:

| Measurement | Value |
|---|---|
| Attempts | 21 |
| Scenes passed | **0 of 7** |
| Attempts with **clean identity** blocked solely by `contradictions` | **5** |
| Contradictions carrying `TEXT_CLAUSE` language (ADR-047's defect) | 0 of 89 |

"Clean identity" means `same_character`, `anatomy_intact`, `style_match`, `subjects_unique` and
`text_free` all true **and** `failure_reasons` empty. `s0` attempt 2 is the plainest case: the
identity judge — the mechanism Objective 3's character-consistency claim rests on — found nothing
wrong, and the page was failed by `Quill - Viewpoint: three-quarter` and one more line of the same
kind.

**This is one story and is not a rate.** `syn-001` is the most adversarial story in the synthetic
set (a three-eyed hedgehog and a tin rooster specified with no face). 21 attempts is enough to show
the defect occurs and is not enough to size it.

**Why the prompt alone is not the fix.** v3 already asks for the shape it is not getting. The prose
demand *"every contradiction must name the subject and the violated requirement"* is present and
ignored. This project has now spent two ADRs learning the same lesson from the other direction:
ADR-034 derived reference acceptance from a list rather than asking for a boolean, and ADR-047
rejected string-matching what a field boundary already answers. Prose asks; schema enforces.

**Decision:**

1. **A contradiction becomes a structured object at the judge boundary.** `SceneConstraintVerdict`
   carries `contradictions: list[Contradiction]`, where `Contradiction` has `subject: str`,
   `required: str`, and `observed: str`. A bare axis label cannot be expressed in that shape: it has
   no `observed` to put against a `required`. Both new types stay **node-local** in
   `consistency_check.py` per ADR-023's D-F rule, exactly as `SceneConstraintVerdict` and
   `SceneVerdict` already do.
2. **The frozen contract is untouched.** `Attempt.scene_contradictions` remains
   `Optional[list[str]]`. Each `Contradiction` renders to one string on the way into Story Memory.
   No schema version bump, no checkpoint invalidation, no migration.
3. **`SCENE_CONSTRAINT_PROMPT_VERSION` goes 3 → 4** and the prompt is rewritten to describe the
   structured shape. The version is recorded per bundle (`build_corpus.py:482`) and pinned by
   `freeze_dataset.py`, so runs before and after this change are distinguishable in the record and
   are not silently pooled.
4. **`providers._assert_field_order` covers the new type.** Field order stays reason-then-score
   (ADR-004): `subject`, `required`, `observed` — the observation last, so the model states the
   requirement before judging against it.
5. **No change to `concrete_failure`.** It keeps reading `bool(scene_contradictions)`. The list is
   now trustworthy, so the gate does not need loosening. Loosening a gate to tolerate bad input
   would hide the next defect of this kind instead of surfacing it.
6. **No claim is made that this makes scenes pass.** The dominant failure in this run is elsewhere
   (see Escape hatch). This decision removes one of two blockers and is expected to reduce paid
   retries; whether any page then passes is not asserted and must be measured.

**Consequences:**

- A page the identity judge accepts is no longer failed by the constraint judge restating its
  checklist. On this run that describes 5 of 21 attempts.
- Correction clauses derived from contradictions (`correct_prompt`, `regenerate.py:71`) stop
  carrying instructions built from non-violations, so retries that do happen correct real faults.
- Retry spend should fall. The magnitude is unmeasured and no figure is committed here.
- `SCENE_CONSTRAINT_PROMPT_VERSION` 3 bundles and version 4 bundles are not comparable on
  contradiction counts. Nothing in `data/judge/` is a frozen dataset yet, so nothing is invalidated;
  `corpus-smoke-b` is a throwaway diagnostic directory.
- One more judge round-trip is **not** added. The call count is unchanged.

**Alternatives:**

- **Tighten the v3 prose and bump to v4 without changing the shape.** Rejected. v3 already contains
  the instruction being ignored, and the smoke run is direct evidence that prose does not bind this
  judge's output discipline. It is also unverifiable without another paid run.
- **Filter malformed entries in `consistency_check` with a string heuristic.** Rejected. It requires
  guessing at contradiction phrasing in code, drifts from the prompt, and is precisely what ADR-047
  refused when it chose a field boundary over string-matching.
- **Relax `concrete_failure` to ignore `scene_contradictions` unless identity also failed.**
  Rejected. Composition violations are real and are the only thing standing behind Section C of the
  validation instrument; a page can be a correct character doing the wrong action in the wrong
  place. This would make the constraint judge advisory and quietly delete that check.
- **Promote `Contradiction` into `contracts/story_memory.py`.** Rejected. ADR-023's D-F rule puts a
  shape used by exactly one node beside that node, and a contract change would force a schema
  version bump and checkpoint migration for a boundary detail.

**Escape hatch:** The **dominant** failure in this run is not addressed here. **16 of 21 attempts
failed `text_free`** — the image model rendered lettering into the page, and `TEXT_CLAUSE` is not
suppressing it. That is a generation defect, not a judging one, and it is the largest single
obstacle to any page passing. It needs its own investigation and its own ADR; fixing the
contradictions field without it will reduce wasted retries but will not by itself produce a passing
book.

Two further items stay open and unaddressed: ADR-046's second escape-hatch question (whether
corrected retries should exist in their current form — after this run they have still never rescued
a page), and `syn-001`'s tin-rooster pathology, where the character spec states the rooster has no
face, `char_bible` draws a species-appropriate rooster per the extraction prompt's own rule, and
every scene then contradicts its own reference. The v3 extraction prompt was written to fix that and
has not.
