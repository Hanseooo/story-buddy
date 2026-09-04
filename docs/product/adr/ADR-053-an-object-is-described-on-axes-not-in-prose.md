# ADR-053 — An object is described on axes, not in prose

**Status:** Accepted (2026-09-03) · **supersedes ADR-052 D1** (the permanence rule as a prompt
sentence) and **replaces ADR-052 D4**'s render shape · **keeps ADR-052 D2, D3 and D5** unchanged
(`Scene.object_states`, `segment` ownership, no judge change) · **amends ADR-023** (`StoryObject`
gains three list fields and loses `description`) · **extends ADR-040** and ADR-035 surface 5 ·
**does not amend ADR-004, ADR-010, ADR-025, ADR-028, ADR-034, ADR-047, ADR-049, or ADR-050** ·
no judge-prompt, provider, or pipeline-shape change

## Context

ADR-052 shipped in `8f9b79e` and its verification re-probe was run the same day. Half of it worked
and half of it did not, and the half that failed did so for a reason that invalidates the premise it
was built on.

**What worked.** `Scene.object_states` did exactly what D2 specifies. `segment` wrote
`plain and brown and a little dusty` on s0/s1/s2, `partially painted with white sampaguita flowers`
on s3, and `fully painted with white sampaguita flowers` on s4, and `build_prompt` rendered each
state on its own page. Nothing below changes that mechanism.

**What failed.** `analyze` put the plot event back into the permanent description anyway:

```json
{"obj_id": "obj0", "name": "bamboo fan",
 "description": "A plain, brown, slightly dusty bamboo fan that belonged to Lola's mother.
                 It is later painted with white sampaguita flowers by Mila and Tala."}
```

The run manifest records `extraction_prompt_version = 5`, `scene_prompt_version = 3`,
`code_commit = 8f9b79e`. The new wording (`analyze.py:195`) was in the prompt the model read. It was
ignored. The page then asserted both states at once and the generator resolved the contradiction the
way generators do — **s0 and s1 each show two fans**, one plain and dusty in Mila's hand, one
flowered in Tala's. s1 carries `passed=True`, exactly as ADR-047 predicts: both states are in the
constraints, so both are satisfiable.

### The permanence rule has never worked, on either surface

ADR-052 D1 copied the permanence wording that locations already had, on the premise that it worked
there. Across all 41 object and location descriptions in every bundle on disk — from
`corpus-abandoned-2026-08-30` through both `syn-901` probes — **34 violate it**:

| bundle | field | stored description |
|---|---|---|
| smoke-a/syn-001 | `rock` | `a heavy rock used to flatten Bok-Bok's tail` |
| smoke-a/syn-002 | `Eraser` | `A school supply eaten by Mopsi.` |
| smoke-a/syn-002 | `Library book` | `A book partially eaten by Mopsi.` |
| smoke-a/syn-003 | `the flower bed` | `garden area below the post office roof, damaged by Grindle's jump` |
| smoke-f/syn-001 | `pond` | `A body of water near the barn, mentioned as the direction of the wind.` |
| probe/syn-901 | `bamboo fan` | `…It is later painted with white sampaguita flowers…` |

The rule names *damage* explicitly and the model wrote `damaged by Grindle's jump`. It names *use*
explicitly and the model wrote `used to flatten` in five separate bundles. A sentence in a prompt is
not an enforcement mechanism at this surface.

**The defect is already in the corpus, not just in the probe.** `Library book` is
`A book partially eaten by Mopsi` — an object whose appearance changes mid-story, described in its
final state, on every page. The 30-story run will hit this without `syn-901`'s help.

### Why the obvious fixes are all wrong, measured rather than argued

- **A rejecting validator quarantines stories instead of repairing them.** `providers.py:300-315`
  grants exactly one blind re-ask on a `ValidationError`: the same prompt, at `temperature=0`
  (`providers.py:320`), with no feedback about what failed. At a 34-in-41 violation rate that is a
  corpus-wide quarantine, not a fix.
- **Truncating to the first sentence destroys real detail.** Three barn descriptions put permanent
  facts in sentence two — `A barn with a roof… The barn has a fence nearby.`
- **Deleting the field, the ADR-040 move, destroys real detail.** Strip the narrative clauses and
  **35 of 41** still carry appearance: `wooden`, `stone building with a roof`,
  `with a creek behind it`. The field earns its place; its *shape* does not.
- **A clause stripper is the brittleness ADR-052 predicted.** A prototype over the real 41 got 34
  strips but ate `next to the creek` out of `A pen built by Marisol next to the creek for Mopsi`,
  and missed every sentence-initial case (`Used to decorate the fan.`,
  `caused by Grindle's failed jump attempt`).

### The cause is the free-prose slot, and that is measurable

Three arms, same model, same `structured_text` path, `temperature=0`, over syn-001, syn-002 and
syn-901. Only the objects/locations paragraph and the object/location sub-schema differ; characters
and timeline are byte-identical across arms.

| arm | object shape | clean visual fields |
|---|---|---|
| A (today) | `description: str` | **4 / 14** |
| B | `appearance` + `use_and_history` | **12 / 16** |
| C | `materials` / `colours` / `form_features`, no prose slot | **15 / 16** |

Removing the prose slot moves violations from 71% to 6%. The aggregates flatter B, though, and the
per-story cut is the finding: syn-001 and syn-002 come out clean under both B and C, while
**syn-901 — the donated-shaped story — scores 0 of 4 under arm B.** Handed a dedicated
`use_and_history` field, the model filled it correctly *and repeated the change in `appearance`*:

> `appearance: 'Plain, brown, and a little dusty. Later painted with white sampaguita flowers.'`

A second prose slot does not stop the model saying the thing twice. Axes do, for every object in
the sample except the one that genuinely changes.

### The residue, and the rule that removes it

A fourth arm added an explicit `changes_during_story` slot to the axis shape.
`changes_during_story` was filled correctly every time — `tail was bent, then straightened with a
rock`, `eaten by Mopsi`, `half-eaten by Mopsi`, `Painted with white sampaguita flowers, dust
removed`. The axes still leaked on the fan, and only on the fan:

```
materials=['bamboo, paint']  colours=['brown, white (painted flowers)']
form_features=['round, flat, handle, dusty initially, painted with sampaguita flowers']
```

Because the model states the change itself, the leak can be removed by self-consistency instead of
by a list of English words. Over all 66 axis entries the four arms produced, **dropping an entry
that shares two or more stemmed content words with that object's own `changes_during_story` drops
exactly the two leaked entries and touches nothing else.** A threshold of one would have destroyed
`tail that spins`, a genuine permanent feature of the weathervane whose tail is what changes.

## Decision

1. **`StoryObject` carries axes, not prose.** `description: Optional[str]` is replaced by
   `materials: list[str]`, `colours: list[str]`, and `form_features: list[str]`, each
   `default_factory=list`. This mirrors `CharacterDescription`, which has never had this defect
   because it has never had a free-prose slot in the prompt (ADR-040 removed its last one).

2. **`ExtractedObject` gains `changes_during_story: str | None`,** and the extraction prompt states
   the axis rule in the terms the arm-D probe used: an axis entry must be true of the object in
   every picture of the story; a change goes in `changes_during_story`; null when nothing changes.
   The field is a boundary-only slot — it is **not** persisted to `StoryObject` and never reaches a
   prompt. `segment` remains the sole author of per-scene state (ADR-052 D3, unchanged).

3. **A normalizing validator on `ExtractedObject`, never a rejecting one.** In `mode="after"` it
   splits comma-joined entries into atoms (the model emits `'bamboo, paint'` as one entry), drops
   blanks and `_DESCRIPTION_PLACEHOLDERS`, enforces the single-line 120-character bound
   `morphology_is_concrete` already imposes, and drops any atom sharing **two or more** stemmed
   content words with `changes_during_story`. It never raises, so it can never trigger the blind
   re-ask at `providers.py:300-315` and can never quarantine a story.

4. **`filtered_object` filters the three axes through `_filter_axis`,** the way
   `filtered_description` already does at `prompt_optimizer.py:116-118`, and appends
   `Scene.object_states` last as ADR-052 D4 specifies. `build_prompt` renders
   `name, <axes joined>, <state>`, and falls back to `obj.name` alone when nothing survives —
   the branch that exists and is tested today at `prompt_optimizer.py:349`.

5. **Locations are not covered.** `permanent_features` came out clean in every arm and
   `filtered_location` (`prompt_optimizer.py:124`) is the symmetric home for it, but ADR-052 scoped
   locations out and this ADR does not widen that scope. The evidence is recorded below so the
   decision can be taken on it later.

6. **No judge change, no new model call, no pipeline-shape change.** `EXTRACTION_PROMPT_VERSION`
   5→6 and `SCENE_PROMPT_VERSION` 3→4, both recorded into corpus manifests
   (`build_corpus.py:500,502`).

## Consequences

- **Old bundles lose their object descriptions on replay.** `StoryObject` declares no
  `model_config`, so Pydantic's default `extra="ignore"` applies: the eleven persisted
  `memory.json` bundles still deserialize, and their `description` value is silently discarded,
  leaving objects rendering by name alone. Those bundles are finished artifacts, not inputs — no
  corpus record, `intake_sha256`, or annotation depends on the field — so this is accepted rather
  than migrated. A migration would have to invent axes from prose, which is the parsing this ADR
  exists to avoid.
- **The blast radius is three call sites.** `analyze.py:277` writes the field,
  `prompt_optimizer.py:156` and `:349` read it. Nothing else in `pipeline/`, `finetune/`, `app/`
  or `worker/` touches `StoryObject.description`.
- **`segment`'s prompt wording changes.** `segment.py:125` tells the model a state is a departure
  from "the permanent description"; it becomes a departure from the axes. The rule is unchanged.
- The change lands in `code_commit`, a pinned freeze key, so it must be committed **before** the
  next campaign starts, never during one.
- A new failure mode replaces the old one: the model may split a fact across the wrong axis
  (`paint` as a material). That is a wrong value in a typed list, which is inspectable and
  checkable; the shape it replaces produced an error that was structurally uncheckable.
- **Known residue, stated rather than hidden.** On the fan, `materials: ['paint']` survives the
  drop rule at one shared word, and `form_features: ['dusty initially']` keeps a temporal adverb.
  Neither contradicts a scene state — `dusty` is the before-state the axes are supposed to hold —
  and tightening the threshold to catch them costs `tail that spins`. Measured trade, taken
  deliberately.

## Rejected alternatives

**Keep `description` and add axes beside it.** Rejected: two sources of appearance truth, which is
the failure `contracts/story_memory.py` already names for scene ordering (*"There is deliberately no
`Scene.order` field — it would be a second source of truth"*). The prose slot is the defect; keeping
it keeps the defect.

**Arm B — one prose slot for appearance, one for history.** Rejected on measurement: 0 of 4 clean on
the one donated-shaped story, because the model writes the change in both fields.

**A stronger prompt.** Rejected on measurement: this is the third version of that wording
(`EXTRACTION_PROMPT_VERSION` 4→5 was itself ADR-052 D1) and the violation rate across every bundle
on disk is 34 of 41. `analyze.py`'s own v2 note records the same lesson from the other direction —
a rule the model ignored was fixed by changing the prompt's *structure*, not by restating the rule.

**A rejecting validator with a re-ask.** Rejected: one blind re-ask, same prompt, `temperature=0`.
It cannot repair, and at this violation rate it quarantines the corpus.

**A narrative-clause stripper over the existing prose.** Rejected on measurement: over-strips
(`next to the creek`) and misses every sentence-initial case. ADR-052 called this brittle on
reasoning; the prototype confirms it on data.

## Evidence

- Re-probe bundle: `scratchpad/probe_out2/runs/syn-901/` (USD 0.39, 13 images, 5 scenes, 0 failed,
  `code_commit=8f9b79e`). Pages showing two fans: `scene/…_s0-2.png`, `scene/…_s1-1.png`. The
  pre-ADR-052 bundle is kept beside it at `scratchpad/probe_out/` as the before-image.
- Description survey over all 41 stored descriptions and the clause-stripper prototype:
  `scratchpad/strip_probe.py`, `scratchpad/strip_probe2.py`.
- Arms A/B/C: `scratchpad/slot_experiment.py`. Arm D and its raw output:
  `scratchpad/arm_d.py`, `scratchpad/arm_d.json`.
- Drop-rule measurement over all 66 axis entries: `scratchpad/drop_rule.py`.
- These paths are session scratch and are not durable. The bundles and probe scripts need a home
  before this ADR's evidence can be cited by anything but this document.

## Verification

Re-run the `syn-901` probe (~USD 0.40) and read s0 and s1. **One fan, unpainted, on both**, and a
painted fan on s3 and s4. Two fans on any page means the axes are still carrying the change. The
check is the page, not the verdict — a passing verdict on this failure is what produced it twice.

Assert in the same pass that `changes_during_story` never reaches `scene.prompt`.

## Observations recorded but not decided

**Locations have the identical shape and the evidence is already in hand.** `Location.description`
is one `Optional[str]` rendered raw into the `Setting:` line, and 17 of the 34 surveyed violations
are locations — 17 of the 21 location descriptions on disk
(`A place where Marisol hides Mopsi under the stairs.`). `permanent_features` was
clean in all three arms that used it. Deliberately out of scope here.

**The axis shape re-extracts `red hair tie` as its own object** with `colours: ['red']`, in the arm
that has no prose slot. Tala's tie has bled onto her hair in both probes — full red hair, no tie, on
all five pages of each — and the character axes are where that binding is currently lost. Recorded
as a lead, not a decision. The earlier withdrawal stands unchanged: a colour-type validator on the
`colours` axis would pass `"red hair tie"` and change nothing.

**Axis extraction invents more filler than prose extraction does** — `red door`, `brick building`
on a school the story never describes. The prompt permits filling missing detail once, and stable
invented detail plausibly helps D3, but it can contradict a story and nothing measures that yet.
