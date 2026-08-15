# ADR-007 — Style as a fixed constant carried by the character reference

**Status:** Accepted · **amended by ADR-022 (2026-07-10)** — one constant becomes three selectable presets.
The *mechanism* below is unchanged and is the reason presets are cheap: style rides the character reference.
ADR-022 also **removes the optional style-anchor image** on provenance grounds. · **amended by ADR-028
(2026-07-29)** — the assumption below that the reference is correct *because it was generated from the
description* is falsified (3 off-spec draws in 4, Probe 1 Run 2 setup). `char_bible` now checks the reference
against the description and re-rolls, capped at 3 draws. The mechanism is otherwise unchanged.

**Context:** v1 uses a single fixed art style. Generating a "style bible" per story is unnecessary, and style drift across images is a real risk with text-only prompting.

**Decision:** Author the style **once** as a constant: a hand-tuned prompt fragment + optional fixed style-anchor image. Because the canonical character reference is generated *in that style*, every scene conditions on that reference and inherits **both identity and style**; the style fragment is belt-and-suspenders.

**Consequences:** "Style Bible Generator" collapses into config; character and style consistency ride the same mechanism; cleaner consistency evaluation. Selectable styles become a clean Future Work item.

**Alternatives:** Per-story generated style, selectable styles, fine-tuned/LoRA style — all deferred; unnecessary complexity for a single fixed v1 style.
