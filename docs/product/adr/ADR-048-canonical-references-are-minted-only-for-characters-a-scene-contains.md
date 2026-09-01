# ADR-048 — Canonical references are minted only for characters a scene contains

**Status:** Accepted (2026-09-01) · **amends ADR-004** (which characters reach a reference draw;
the 2-reference cap, the per-character judge call, and reason-then-score are untouched) · **does not
amend ADR-010, ADR-028, ADR-037, ADR-046, or ADR-047** · no `StoryMemory`, contract, schema,
provider, or graph-shape change · one condition in `char_bible`

**Context:**

`analyze` caps the roster at 3 and `char_bible` mints a canonical reference for the first 2
(ADR-004). Neither node asks whether a character appears in the book.

`segment` runs **before** `char_bible` (`graph.py:115`), so `Scene.characters_present` is already
populated when the selection is made. A character no scene contains is never drawn into a page, is
never a subject of the identity judge (`consistency_check` builds `subjects` from
`characters_present`), and never reaches `compose`. Its reference is bought and never read.

This is observed, not hypothetical. Across every recorded run under `data/judge/**/runs/*/`:

| Measurement | Value |
|---|---|
| Characters extracted | 15 |
| Never present in any scene | 1 |
| Never present **and** paid for a canonical reference | **1** |

The one case is `syn-003`'s *"the gardener"*, whose entire appearance in the source story is
*"...and the gardener never figured out what happened."* It does not speak, decide, or move on its
own intent, so it fails the extraction prompt's own agency rule (`analyze.py`, v2). It cost one of
that story's eight images and occupied a reference slot; `the pigeons`, present in 2 scenes, got no
reference because the ADR-004 cap was already spent.

**This is a 1-in-15 measurement and is not a rate.** Five distinct stories, two corpora, two code
commits. It is sufficient to show the class of waste occurs and insufficient to size it.

**Why the extraction prompt is not the fix.** The defect originates there — v2 already added the
agency rule after a probe found *"the hill"*, *"the river"* and *"the jar of pickles"* in
`characters[]`. But `EXTRACTION_PROMPT` is on v4, and v3 and v4 each fixed one thing and broke
another: v3's ungated faceless wording contradicted its own reference spec and burned 25 image
calls on a story the judge never passed; v4's "neutral" was simultaneously instructed and banned,
hard-failing stories on contract validation after two billed text calls. A fifth version bumps
`extraction_prompt_version`, changes extraction for every story, and is justified by n=1. It is not
taken here.

**Reconciliation is not the backstop it appears to be.** `reconcile_declared_roster`
(`corpus_io.py:106`) deliberately does not require roster equality — its docstring records that a
strict probe quarantined 22 of 30 synthetic stories, because whether a bit player has agency is a
judgement the author and the model can read differently. Extra extracted names pass. The real
quarantine risk is **displacement**: a spurious entry ranked above a declared character pushes it
past `REFERENCED_CHARACTERS = 2` and the story fails on *"declared name not in the reference
slice"*. `syn-003` passed only because `Grindle` was declared alone. This ADR reduces displacement's
blast radius without relying on reconciliation to catch it.

**Decision:**

1. **`char_bible` mints a reference only for a character some scene contains.** The selection
   becomes the ADR-004 cap, then the existing already-referenced filter, then presence.
2. **Presence is filtered AFTER the cap, never before.** The existing cap-then-filter order is
   load-bearing and its reason is recorded in the code: filtering first slides the 2-slot window
   onto `c2` and produces three canonical references. A post-cap filter can only shrink the
   selection, so ADR-004's cap holds by construction.
3. **An empty union falls back to today's behaviour.** `Scene.characters_present` defaults to an
   empty list (`story_memory.py:185`) and `segment` never forces it non-empty, so "no character
   appears anywhere" cannot be distinguished from "the segmenter did not populate the field".
   When no scene names anyone, every capped character is minted exactly as before. Filtering on an
   empty union would strip every reference in the book and silently skip the reveal.
4. **`reveal` is left alone.** It projects exactly the characters that carry a reference and
   already fails toward progress on an empty list (`reveal.py:84` — it returns `{}` rather than
   pausing, so no child is parked on a confirm button). A cast member absent from the book no
   longer appears on the reveal screen, which is the intended consequence, not a regression.
5. **`docs/specs/character-bible.md` records the new selection rule** alongside invariant 1.

**Consequences:**

- A reference that provably cannot be read is not bought. Direction is lower spend inside the
  unchanged ADR-037 55-image envelope; the magnitude is unmeasured and no rate is claimed.
- Output quality cannot fall. The dropped reference is, by the selection rule itself, one no page
  is drawn from and no identity judgement uses.
- Displacement still costs a reference slot — a spurious character ranked in the top 2 that *does*
  reach a scene is still minted. This ADR removes the waste, not the extraction defect.
- One test is added and one existing behaviour gains its first test (the empty-union fallback was
  previously unpinned).

**Alternatives:**

- **Bump `EXTRACTION_PROMPT` to v5 and tighten the agency rule.** Rejected on evidence, not on
  principle: n=1 against a prompt whose last two versions each caused a worse failure than the one
  they fixed. Revisit when the donated corpus exists and the rate is measurable.
- **Make `reconcile_declared_roster` require roster equality.** Rejected. Already tried and
  recorded: it quarantined 22 of 30 stories.
- **Drop absent characters from `state.characters` in `analyze` or `segment`.** Rejected. It
  destroys extraction's record of what it found, breaks reconciliation's ability to report what was
  extracted, and puts a roster mutation in two more nodes. The reference is the cost; drop the
  reference, keep the record.
- **Filter presence before the ADR-004 cap.** Rejected — this is the exact bug the existing
  cap-first comment was written to prevent.

**Escape hatch:** The extraction defect is untouched and will resurface as displacement the moment a
story declares two characters and the model ranks a bare noun phrase second. The donated intake file
does not exist yet (`data/judge/intake/` holds only raw text; `load_intake` requires 15 records), so
the declared rosters that would trigger it have not been authored. When they are, a v5 extraction
prompt becomes measurable and is its own ADR.
