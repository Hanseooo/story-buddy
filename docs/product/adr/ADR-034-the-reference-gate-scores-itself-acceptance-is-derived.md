# ADR-034 — The reference gate scores itself: acceptance is derived from a contradiction list, not asked for as a boolean

**Status:** Accepted (2026-08-11) · **amends ADR-028 Decision 3** — the acceptance *predicate* only; the in-node
loop, the cap of 3 and the best-of fallback are unchanged · **strengthens ADR-004** (reason-then-score) rather
than amending it · additive to `story-memory-contract` §2 → **no `schema_version` bump**

**Context:** ADR-028 Decision 3 amended ADR-007 so the canonical reference is *checked, not assumed*, and
`char_bible.py:6-7` states the node's purpose as *"the gate that makes that failure visible."* Production job
`b9506307` (2026-08-11, `comic` preset) shows the gate passing a reference it had itself just described as
contradictory.

The verdict for `c1` — *"the star - star; glowing; tiny; secondary character"* — verbatim from the LangGraph
checkpoint, which is the only place it survives (`jobs.reveal` carries the chips, not the verdict):

```json
"differences_observed": "The description states the star is 'tiny', but the image depicts the star
   as a significant size relative to the image frame. This is a contradiction.",
"matches_description": true,
"attributes_present": ["star", "glowing", "secondary character"]
```

Three things are wrong here and they are **not the same failure**:

1. **The prose declares a contradiction and the boolean says `true`.** ADR-004's ordering is enforced on the wire
   by `providers._assert_field_order` and it *worked* — the reason was emitted first. Ordering makes the model
   reason before it scores. It does not make the score follow the reasoning. That gap is what this ADR closes.
2. **`attributes_present` contains `"glowing"` for an image that is not glowing, and cannot have been.** The
   `comic` fragment ends `"no gradients, no glow"` while `analyze` had put `"glowing"` in `colours`, so
   `reference_prompt` asked for a rendering property the same prompt's style clause forbade. `"secondary
   character"` is listed too — a `notes` value, not a visual attribute. **`best_draw` ranks candidates by
   `len(attributes_present)`**, so the best-of fallback sorts on this.
3. **The 3-draw loop has never fired.** `cost.image_count` is 11 against 7 scenes with `regen_count` 2 — 9 scene
   draws, therefore **2 reference draws for 2 characters**. Both accepted on the first draw. ADR-028 bought a
   bounded re-roll and production has not used it once, because nothing has ever failed the gate.

**What it cost downstream (issue #23).** The accepted reference is a flat teal star with legs and a face. Every
scene prompt then re-asserts `glowing; tiny` against it, and the edit model resolves the conflict differently
per scene — same template, same two references, three outcomes:

| scene | text excerpt | result |
|---|---|---|
| s3 | *"Ana decided to help."* — no star noun | reference wins: one teal star, glow painted on |
| s1 | *"found a tiny glowing star"* | description wins: one yellow legless star, reference discarded |
| s4 | *"carried the star… held it toward the sky"* | **both drawn — 7/7 draws**, the reported defect |

Duplication is not a distinct bug; it is one of three ways the model resolves two incompatible specifications for
one entity. This was established by probe, not inference: naming the reference images fixed the *protagonist*
duplication (0/10 draws) and moved the star not at all (7/7), and a clause explicitly forbidding a second star
also moved it not at all (0/4). No prompt change in `generate_scene` can fix it, because the reference and the
description genuinely disagree and the gate whose job was to catch that disagreement reported it and passed.

**Decision:**

### 1. `RefVerdict` gains `contradictions`, and acceptance is computed from it.

```python
class RefVerdict(BaseModel):
    differences_observed: str                                 # ADR-004 free-text reason, still first
    contradictions: list[str] = Field(default_factory=list)   # NEW — the structured reason
    matches_description: bool                                 # the judge's own claim: recorded, NOT the gate
    attributes_present: list[str] = Field(default_factory=list)
```

`char_bible` accepts on `not verdict.contradictions`; `reveal.py:36` uses the same predicate. The model is no
longer *asked* whether the image matches — it is asked to **enumerate** the contradictions, and the boolean the
pipeline acts on is derived from the length of that list. A judge cannot then write *"This is a contradiction"*
and pass, because the sentence and the score are the same object.

Inserted **between** `differences_observed` and `matches_description`, so ADR-004's ordering assertion and
`test_story_memory.py:116` keep passing unchanged, and the emitted sequence becomes free-text reason → structured
reason → claim → attributes. **A new field with a default is additive** (`story-memory-contract` §3), so no
`schema_version` bump, no restart path, and old checkpoints deserialise with an empty list.

### 2. `matches_description` stays, demoted from gate to instrument.

It is kept for three reasons: removing it is a breaking change (`schema_version` bump, restart path, ~10 test
files, `judge-finetune.md` §6.1's round-trip requirement); and keeping it beside the derived predicate makes the
**reason–score inconsistency rate directly measurable**, which is a finding this project is positioned to report
rather than a wart to hide. The field gets a comment saying it is an observation and must not be branched on.

### 3. `best_draw` ranks on contradictions first.

`(fewest contradictions, most attributes_present, earliest)` instead of `(most attributes_present, earliest)`.
The current key is sorting on a list that demonstrably contains hallucinated entries; the new primary key is the
same signal the gate now uses. Still lexicographic, still no scalar — ADR-028 Decision 2's posture, applied to
the schema next door.

### 4. `JUDGE_PROMPT_VERSION` → 3, and the prompt asks for the list.

The v2 wording asks *"First describe any way the image CONTRADICTS a stated attribute. Then say whether the
image matches…"* — v3 keeps the first sentence and replaces the second with an instruction to **list each
contradiction separately, one entry per contradicted attribute, and leave the list empty if there are none.**
Per the existing rule at `char_bible.py:38-42`, the bump is mandatory: what a failure *means* changes.

**Consequences:**

- ⚠️ **The typical-case cost moves toward the worst case.** ADR-028 priced the loop at *"worst case ≈ +$0.14 on a
  $0.30–0.65 book; typical case ≈ $0, since a passing first draw costs one judge call."* The typical case was $0
  because the gate passed everything. A gate that works will re-roll, and the ceiling ADR-028 already approved is
  where books will now land more often. **The cap of 3 is not raised** — that is the containment.
- ⚠️ **ADR-028's 42% figure is invalidated, for the second time.** It was computed against a gate that passes
  self-declared contradictions, so it *understates* the off-spec rate. `ref_verdict_prompt_version` goes to 3 and
  the series restarts — exactly the failure the v2 comment was written to prevent, now working as intended.
- **This does not fix issue #23's star.** With the gate working, this reference is rejected and re-rolled into
  ADR-028's known-bad generator rate. The fix for the *rate* remains the seam ADR-001 names: swap
  `fal_image_model`. Do not read this ADR as closing #23.
- **Two upstream defects are deliberately left open**, named here so they are not rediscovered as this ADR's
  bugs:
  1. **`analyze` puts rendering properties in `colours`** (`"glowing"`), which the style preset may forbid
     outright. Nothing reconciles a story attribute against ADR-022's fragment, and with the gate fixed this
     becomes a character that can never pass. That is the *next* decision, and it is a real one.
  2. **The anthropomorphising guard at `char_bible.py:87-88` does not work** — `ref-c1-1.png` has legs and a
     face, the exact failure the comment at `:69-71` says was caught before. v2's *"contradiction, not
     difference"* framing means unlisted features are by construction invisible to the judge, so the guard has no
     checker. Widening the judge here would re-break what v2 fixed; this needs the draw side, not the gate.
- **Files edited by this decision:** `contracts/story_memory.py`, `pipeline/char_bible.py` (predicate, prompt,
  version, `best_draw`), `pipeline/reveal.py:36`, `docs/specs/story-memory-contract.md` §2/§8,
  `docs/specs/character-bible.md`, and the tests that construct `RefVerdict` positionally.

**Alternatives:**

- **Remove `matches_description` entirely** — rejected on cost, not on principle. It is the cleaner schema and
  leaves nothing to misread, but it is a breaking change to a persisted, finetune-targeted type in exchange for
  deleting a field that Decision 2 turns into a measurement. Revisit if a `schema_version` bump happens anyway.
- **Keep the boolean as the gate and detect inconsistency by string-matching `differences_observed`** — rejected.
  It works on this exact sample (*"This is a contradiction"*) and nowhere else, and it re-introduces the failure
  v2 removed by treating any described difference as a defect.
- **Reuse `VlmVerdict`** — rejected again, for ADR-028's original reasons, which are unchanged.
- **Do nothing; swap `fal_image_model` instead** — rejected as an alternative, accepted as a complement. A better
  generator raises the pass rate but a gate that cannot fail still cannot measure it, and the ADR-028 hit rate is
  a capstone number. The measurement has to be trustworthy before the intervention is worth running.
- **Fix `analyze` so descriptions never contradict the style** — rejected *as this ADR*. It is the deeper fix and
  it is listed above as the next decision, but it is LLM-output shaping with no deterministic guarantee, and it
  would leave the gate still unable to catch the cases it misses.

⚠️ **One honest qualification.** The mechanism is verified — the verdict is quoted from the checkpoint, the draw
arithmetic is closed, and the three downstream outcomes are from 21 draws across four probe arms. What is **not**
measured is whether `google/gemma-3-27b-it` populates a *list* more faithfully than it sets a boolean. It emitted
the right reasoning in prose here, which is the encouraging half; ADR-028 Decision 2's limit 2 applies verbatim to
this field on arrival — **it is a slot, not a validated signal, until Phase 1 checks it against the scorer's
eye.** The difference is that a wrong list is a wrong *answer*, where a boolean contradicting its own prose was a
wrong *instrument*.

---

### Implementation note (2026-08-11) — measured on arrival, and one follow-on decision

The qualification above was tested before this ADR shipped: `ref-c1-1.png` and `ref-c0-1.png` were re-judged under
v3 with no redraw (2 judge calls, 0 image draws). Results are recorded in `character-bible` §"What v3 was measured
to do, and what it was not". Against this ADR's own claims:

- **Decisions 1–4 hold.** The list is populated, the mid-schema insert survives strict `json_schema` and
  `_assert_field_order`, c1 returned two contradictions alongside `matches_description: true` and the gate
  rejected, and the c0 control returned an empty list — no false positive.
- ⚠️ **The gate is probabilistic.** One of two calls on c1 returned an empty list and would have accepted. This
  ADR's *"a wrong list is a wrong answer"* framing stands, but the answer varies between calls on identical input.
- ❌ **The two open upstream defects are confirmed, not merely suspected.** c1's `differences_observed` names *"the
  star with legs and a face"* in prose and does not list it as a contradiction — defect 2 above, verbatim. And
  `attributes_present` still reports `"glowing"` for a flat teal image — defect 1.

**Follow-on carried into this ADR rather than a new one:** the judge prompt no longer receives `notes`
(`_describe(..., notes=False)`; the draw prompt still does). v3 returned *"secondary character - The image does
not provide cues as to this character's role"* as a **contradiction** — a `notes` value, unclearable by any
redraw, which under Decision 1 would exhaust all 3 draws on every job for that character forever. Decision 1
promoted `attributes_present`'s known noise into the gate, so the noise had to be excluded from the gate's input.
Folded in rather than raised as ADR-035 because it is a defect *created by* Decision 1, discovered while verifying
it, and it narrows what the judge measures without changing what acceptance means. `JUDGE_PROMPT_VERSION` stays at
`3`: v3 never produced a persisted verdict, so bumping to 4 would segment an empty series. `reveal._chips` already
drew this exact line, which is the precedent it follows.
