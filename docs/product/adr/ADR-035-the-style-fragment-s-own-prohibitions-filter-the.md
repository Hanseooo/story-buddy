# ADR-035 — The style fragment's own prohibitions filter the description: rendering properties are the style's jurisdiction, not the subject's

**Status:** Accepted (2026-08-11) · **extends ADR-007** ("style rides the canonical reference") from the *image*
to the *prompt text* · does not amend ADR-022, which keeps sole ownership of the fragments · does not amend
ADR-013, which keeps `caption = text_excerpt` verbatim · transient projection only → **no schema change, no
`schema_version` bump**

**Context:** ADR-034 named this as the first of *"two upstream defects deliberately left open"* and declined to
decide it there. With the gate now working it stops being a quality wart and becomes a recurring cost.

Production job `b9506307` (2026-08-11, `comic` preset), character `c1`:

```
description.colours   = ["glowing"]
style.prompt_fragment = "...flat spot colours, ben-day halftone dot shading, limited palette,
                         no gradients, no glow"
```

`"glowing"` is a lighting property, not a hue. It reached `colours` because that is the closest axis `analyze`
has, and **nothing anywhere reconciles an extracted attribute against the fragment the same prompt then applies.**
The scene prompt `build_prompt` emits for `s1` asserts it twice and forbids it once:

```
Image 1 is Ana. Image 2 is the star. Use them only as references... draw each character exactly once.

Ana - girl; ...
the star - star; glowing; tiny; secondary character      <- _describe, from description.colours
Ana found a tiny glowing star...                         <- text_excerpt, ADR-013 verbatim
bold comic-book illustration, ... no gradients, no glow  <- the style fragment
```

**This is why issue #23's star did not close when the reference clause did.** `REFERENCE_CLAUSE` fixed the
duplicated *girl* because Ana's reference looked like the prose and the clause only had to stop compositing. No
clause can bind the noun *"tiny glowing star"* to an image that is visibly not one. The edit model resolves the
contradiction per scene: reference wins (`s3`), prose wins and the reference is discarded (`s1` — a *different*
star in Ana's hand), or **both entities get drawn** (`s4`, 7/7 draws).

**What ADR-034 changed about the urgency.** Before the gate worked, an unsatisfiable attribute was invisible at
the gate and only surfaced downstream. Now the judge can *legitimately* contradict `glowing` on all three draws,
so this character exhausts its full draw budget on **every job** and ships the same best-of reference anyway. We
converted a quality defect into a recurring spend. Confirmed on re-judging under `JUDGE_PROMPT_VERSION = 3`:
`attributes_present` still reports `"glowing"` for a flat teal image, so the judge is not a backstop here either.

**The finding that made a deterministic fix viable.** Every preset states its own prohibitions, in its own
fragment text:

| preset | prohibitions stated in the fragment |
|---|---|
| `cel` | no gradients, no glossy highlights, no airbrushing |
| `comic` | no gradients, no glow |
| `gouache` | no outlines, no gradients, no glossy highlights |

So the forbidden-rendering list does **not** have to be hand-maintained. This is the objection that killed the
species word-list at `char_bible.py:74-77` — *"it needs a word list that is wrong the first time a child writes
something not on it"* — and it does not apply here: this list is **closed by the fragment**, not by the space of
things children write, and a new preset arrives carrying its own.

### Decision

1. **Prohibitions are derived from the active style fragment**, by reading its `no <term>` clauses. Not
   hand-listed, so ADR-022 keeps sole ownership and a new preset needs no code change.
2. **Filtering applies to the three list axes only** — `colours`, `body_features`, `clothing`. **Never
   `species`** (`analyze.py:22-26` makes it required precisely so the judge always has something to check; an
   empty description makes acceptance vacuous). **Never `notes`**, which is free prose and already excluded from
   the judge (ADR-034 follow-on) and from chips.
   > **Superseded in part by the second 2026-08-12 amendment below.** `notes` *is* filtered, all-or-nothing. The
   > justification above named the two surfaces where `notes` does not appear and missed the two where it does.
3. **Removal is word-level within an entry**, and an entry is dropped only if nothing survives. `"glowing eyes"`
   becomes `"eyes"`, not nothing — dropping the whole entry would discard a real subject fact to remove a
   rendering one.
4. **The projection is transient.** `StoryMemory` keeps the child's words verbatim; only the rendered prompt and
   chip text drop them. Nothing is destroyed, the filter is reversible if the style changes, and there is no
   contract change. `build_prompt`'s invariant 2 (*never invents detail beyond `text_excerpt` and the populated
   axes*) is untouched — filtering removes, it never invents.
5. **It is applied at every surface that renders a description axis**, all five:

   | surface | why it must be filtered |
   |---|---|
   | `char_bible.reference_prompt` (draw) | where the self-contradicting reference is born |
   | `char_bible._describe(notes=False)` (judge) | otherwise the gate re-rolls on an unclearable contradiction — the 3-draw burn |
   | `prompt_optimizer._describe` (scene) | `s1`'s assertion, the wrong-star case |
   | `prompt_optimizer.correct_prompt` `values["colours"]` | today it answers `wrong_colour` with *"match the reference's exact colours: glowing"*, reinforcing the side that is not in the reference (issue #24) |
   | `reveal._chips` | a child can tap **"glowing"** and spend an ADR-029 retry tap on a redraw that cannot succeed |

   One pure helper in `prompt_optimizer` (already the home of the pure prompt-construction helpers, and it imports
   only `app.config` and `contracts`, so `char_bible` and `reveal` importing it introduces no cycle).

**When the child's words and the style collide, the style wins and the attribute is dropped from the prompt.**
That is the load-bearing choice here, stated plainly. It follows ADR-007 — style rides the reference — and it is
the only side that can win, because the fragment is what the generator actually obeys today. The child's word
survives in `StoryMemory` and in their own story text; what it loses is the power to contradict the picture.

### Consequences

- The reference becomes *satisfiable*, which is the precondition for every other measurement. The rate ADR-028
  put at *"roughly 42%"* was measured through a prompt that asked for and forbade the same thing; until this
  lands, generator quality and prompt contradiction are not separable.
- **Do not reach for ADR-001's `fal_image_model` seam before this.** Swapping the model first would measure the
  wrong variable.
- Per-preset behaviour is correct rather than uniform: `glowing` is dropped under `comic`, and **kept under
  `cel`**, which never forbids it.

**What this does not fix — five limits, stated rather than discovered later:**

1. **The `text_excerpt` still says it.** ADR-013 freezes `caption = text_excerpt` verbatim and the excerpt reaches
   the prompt unchanged, so `s1` still contains the word *"glowing"* once. The conflict drops from three
   assertions to one, and — the part that matters — the *reference* stops contradicting it. This ADR does not
   claim the prose conflict is gone.
2. **It does not fix the anti-anthropomorphising guard** (ADR-034's defect 2): `ref-c1-1.png` also has legs and a
   face, which is independent of this. **The star needs both fixes.** This one is landing alone deliberately, so
   the next measurement has one variable in it.
3. **Prefix matching is a heuristic** (`"glowing"`.startswith(`"glow"`)), and derivation only removes what a
   fragment *states*. An attribute that is merely hard for a flat style but not explicitly forbidden still gets
   through. Over-dropping fails soft (an attribute goes unasserted); the status quo fails hard (a prompt that
   contradicts itself).
4. **A style-forbidden word inside `species` still reaches both prompts.** Decision 2's carve-out is
   unconditional, so `species = "glowing orb"` under `comic` is described to the generator *and* to the judge.
   Accepted: `analyze.py:22-26` makes species required precisely so acceptance is never vacuous, and stripping it
   would trade a describable contradiction for an undescribable character. The judge can at least *see* this one
   and contradict it, which is the ordinary ADR-034 path.
5. **Filtering can make a description "thin".** `reference_prompt`'s test is
   `if not (colours or body_features or clothing)`, and the filter can empty all three — prod's `c1` goes from
   `star; glowing; tiny` to `star, a friendly children's picture-book character`. That is the intended
   degradation (nothing drawable survived, so the neutral floor is right), but it was a *consequence* rather than
   a decision and it moves acceptance toward vacuous, which is the same pressure limit 4 names.
6. **A style-forbidden `notes` is dropped whole, so its permitted words go with it.** Added by the second
   2026-08-12 amendment. `"glows softly in the dark"` under `comic` contributes nothing rather than
   `"softly in the dark"` — the word-level rule of Decision 3 is right for short noun phrases and wrong for a
   sentence, which it leaves as a mangled fragment the generator still has to reconcile. Accepted because `notes`
   is emphasis, not an axis the gate measures: ADR-034 removed it from the judge prompt, so dropping it cannot
   make acceptance vacuous the way dropping a visual axis would.

### Amendment (2026-08-12) — species is filtered in **chip scope**

Decisions 2 and 5 conflicted on one cell, found while auditing the retry path. Decision 2 says *never `species`*;
Decision 5 lists `reveal._chips` as a filtered surface, and its stated reason — *"a child can tap **"glowing"** and
spend an ADR-029 retry tap on a redraw that cannot succeed"* — applies to a forbidden word inside `species` exactly
as it does to one inside `colours`. Decision 2 won that cell by default, and it was the wrong reading:

```
species="glowing orb", colours=["blue"], preset=comic

chips offered:  ['glowing orb', 'blue']          <- the child is handed the unfixable term
draw prompt:    the orb - glowing orb; blue; glowing orb
style:          ... no gradients, no glow
```

A tapped chip becomes `char_bible._mint_targeted`'s `notes`, and `notes` is unfiltered by the same Decision 2. **Two
carve-outs composed into a bypass**, reachable on a fresh post-fix job — not, as first suspected, only on an
in-flight one holding pre-amendment chips. `main.confirm_job` validates the tap against the stored chips, so it
waved it through: the validator's input was the thing that was wrong.

**Resolution: `species` is word-filtered where it is OFFERED, never where it is DESCRIBED.** `permitted_words` in
`prompt_optimizer`, called by `_chips` only. Decision 2 is unchanged everywhere it was actually reasoned about —
`filtered_description` still never touches `species`, so the draw and judge prompts keep it (limit 4 above stands)
and acceptance cannot go vacuous. What the child loses is a button that promised something no redraw could deliver.
An all-forbidden species now offers no chip and falls through to the existing name fallback (invariant 4).

**One thing deliberately not changed.** `_mint_targeted`'s `if retry.attribute not in prompt` re-injection branch
is **unreachable**, and has been since the commit that introduced it — the line above writes the attribute into
`notes`, and `_describe(notes=True)` always renders `notes`. It is pinned by a test rather than deleted because it
is a trap, not merely dead: it is dead *only while `notes` and `retry.attribute` are both unfiltered*, and the
obvious follow-on fix — filtering the tapped attribute — would reanimate it into a clause that re-appends the term
the filter had just removed. The test names the correct response (delete the branch, do not repair it).

**How we will know it worked.** Re-run the same story under `comic` and check three things: `c1`'s reference no
longer carries an unsatisfiable attribute into the judge; the gate stops re-rolling `c1` to the 3-draw cap; and
`s1`/`s3`/`s4` are inspected for the star. A residual star defect after this is attributable to the guard or the
generator, which is exactly what landing it alone buys.

### Amendment (2026-08-12b) — `notes` is filtered, all-or-nothing

Raised in review of the branch carrying the amendment above. Decision 2 justified the `notes` carve-out as *"free
prose and already excluded from the judge (ADR-034 follow-on) and from chips"* — and both clauses are true and
both are beside the point. The judge and the chips are not where this ADR's defect lives. `notes` reaches the two
surfaces that *are*:

| surface | line |
|---|---|
| `char_bible.reference_prompt` → `_describe(notes=True)` — the draw prompt | `char_bible.py:275` |
| `prompt_optimizer._describe` → `build_prompt` — the scene prompt | `prompt_optimizer.py:108` |

**This is strictly worse than limit 4's `species` carve-out, not equivalent to it.** Limit 4's whole acceptance
argument is *"the judge can at least see this one and contradict it"*. ADR-034 removed `notes` from the judge, so
for `notes` that argument is specifically false: a forbidden term there is asserted to the generator and invisible
to the gate. And `notes` is unconstrained model output — `EXTRACTION_PROMPT` never mentions the field, while strict
`json_schema` forces every property into `required`, so the model fills it with prose of its own choosing. Prod's
value was `"secondary character"`; `"glows softly in the dark"` is the same draw from the same distribution.

Structurally the same shape as the leak the first amendment closed — a Decision 2 carve-out composing into a
bypass — one axis over. **Unproven rather than observed:** no prod instance of a rendering word landing in `notes`.
Fixed anyway, because the residue is unbounded (any prose) and the fix is three lines.

**Resolution: `_kept_whole` in `prompt_optimizer`, wired into `filtered_description`.** If any word of `notes` is
forbidden, the whole string is dropped; otherwise it survives untouched. Word-level (Decision 3's rule) is right
for a short noun phrase and wrong for a sentence — see limit 6.

**Two things this deliberately does not disturb.**

- **`_mint_targeted` is unaffected.** It sets `notes` *after* the filter runs
  (`filtered_description(...).model_copy(update={"notes": retry.attribute})`), so the tapped attribute overwrites
  whatever `_kept_whole` did. The unreachable re-injection branch above stays unreachable and the trap does not
  reanimate — that needs filtering `retry.attribute` itself, which the chip-scope amendment already made
  unnecessary.
- **The `comic` re-measurement stays single-variable.** This changes a prompt only when `notes` actually contains
  a forbidden word. Prod's `"secondary character"` is forbidden by no preset, so on the measurement job the
  rendered prompts are byte-identical to what they would have been without this amendment.
