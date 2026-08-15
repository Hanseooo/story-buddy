# ADR-022 — Selectable art-style presets (three, prompt-fragment based)

**Status:** Accepted (2026-07-10) · **amends ADR-007**

**Acceptance condition (binding).** The presets must not read as generic AI art, must look creative, and must
hold character identity across scenes. See "The aesthetic constraint" below — it is a design requirement with
a measurement attached, not a preference.

**Context:** ADR-007 froze v1 to a single fixed art style and named selectable styles a "clean Future Work
item" (ROADMAP Phase 4). The product owner now wants **at least three presets**, because letting the author
choose how their story looks is one of the few places this product gives a child ownership rather than
output — and author benefit is a stated product goal (PRD §2).

The question raised was whether a preset should be driven by a **prompt fragment** or by a **reference image
in that art style.** ADR-007 already answers it, and the answer was easy to miss: **style is carried by the
canonical character reference.** The char-ref is generated once *in* the chosen style; every scene is a
reference-conditioned edit of that image, so it inherits identity and style through the same mechanism. The
style fragment is belt-and-suspenders. **A preset is therefore a different constant, not a different
mechanism.** Nothing in the pipeline shape changes.

**Decision:**

- A preset is a **named prompt fragment in config** — `style_presets: dict[str, str]`, three entries, one of
  which is today's constant. **No new node, no new model, no new API call, no additional image.**
- **Style is chosen once, before canonical-reference generation, and frozen for the life of the storybook.**
  A style that can change mid-book breaks regeneration: a targeted retry would re-draw one page in a new
  style, and `wrong_style` would fire on a correct image.
- **Story Memory gains `style_preset`.** This is a contract change (CLAUDE.md §2): schema, affected specs,
  and every consumer move in the same change.
- **The judge only ever compares a reference against a scene within one preset.** It never compares across
  styles. So `wrong_style` keeps its meaning, and the fine-tune's training data is not split three ways —
  it gains visual diversity within a single task.
- **Reject the style-exemplar-image route** (IP-Adapter / style-transfer from a reference artwork).

**Why the exemplar image is rejected, in order of weight:**

1. **Provenance.** An art-style exemplar has to come from somewhere. Scraped artwork is a copyright and
   ethics problem in a child-facing product whose defensibility rests on an open-weight, clean-provenance
   argument (ADR-015). A *generated* exemplar is a prompt fragment with extra steps.
2. **Redundancy.** The char-ref already anchors style. A second style-conditioning image adds a channel that
   duplicates one we have.
3. **Unverified substrate.** Conditioning `qwen-image-edit-2511` on *two* images (character + style exemplar)
   is not something Phase 0.5 probes or ADR-001 records. It would add a new unknown for no gain.
4. Extra cost and latency on every image.

**Choosing the three.** Style presets must be visually distinct *and* identity-preserving. Strong line and
silhouette carry identity across scenes; heavy texture and photorealism destroy it — and non-human characters
are the fragile case (ADR-001).

- Authored **2026-07-21** (resolving the open question below): **(1) bold comic-book with ben-day halftone**
  (`comic`, the gating primary), **(2) flat cel-shaded cartoon** (`cel`, the flagship default kids see first),
  **(3) flat gouache storybook** (`gouache`). All three are strong-line + flat-fill. `watercolour` was
  considered and **dropped** — soft bleeding edges dissolve an invented silhouette, the fragile non-human
  case. `comic` is the gating primary because it is the *representative-middle* substrate — line-forward
  enough to hold identity, but textured enough (halftone) that the no-reference baseline can't fake the
  separation gate; gating on the *most* reproducible style (`cel`) would make that gate too lenient. `cel`
  and `gouache` are identity-checked in the non-gating secondary arm, so neither ships unvalidated.
- **Do not offer photorealistic or 3D-render styles.** Highest identity drift, uncanny on invented creatures,
  and photoreal imagery of child-authored characters worsens the moderation surface for no pedagogical gain.

**The aesthetic constraint — and the tension inside it.**

"Looks AI-generated" is not vague; it is a specific and nameable default that diffusion models fall into:
airbrushed gradients, plastic sheen, hyper-saturation, symmetrical perfection, glow and bokeh, uniform
over-detail. The antidote is equally specific — **name a traditional medium and its physical artifacts**:
paper grain, visible brush and ink edges, a limited palette, deliberate asymmetry, flat fills rather than
gradients. Prompt fragments state the medium; they do not state "beautiful," "8k," or "highly detailed."

**But this pulls directly against consistency, and that must be said out loud.** Painterly texture and
imperfection are what defeat the AI look. Strong line and flat silhouette are what preserve identity across
scenes (ADR-001; non-human characters are the fragile case). Maximize one and you erode the other.

**The resolution is why the recommended three are what they are:** put *identity* in the line and *character*
in the fill. A clean cel or comic ink line holds the silhouette, the eye count, the scarf; a halftone screen
or gouache grain kills the airbrushed sheen. Styles that carry identity *in the texture* — impressionist, painterly,
photorealistic — are the ones to refuse.

**This is measured, not asserted.** Probe 1's blind scoring sheet gains one item alongside identity:
*"Does this read as an intentionally hand-drawn illustration, or as generic AI art?"* It does **not** gate — the kill
criterion stays on identity — but a preset that scores badly is re-authored or dropped before a child sees
it, and the number goes in the paper.

**Consequences:**

- **Phase 0.5 gains a secondary arm:** run Quill (the invented chimera) through all three presets.
  ~20 extra images, ~$0.80. **It does not gate.** The kill criterion stays on the primary style — but a
  preset that cannot hold Quill is deleted before a child ever sees it, not after.
- Three presets are three substrate risks. This measures them instead of assuming them.
- Expert validators will see mixed styles across stories. **Record the preset per story** and report it as a
  covariate. **Do not claim a preset effect** — N is nowhere near enough, and it is not an RQ.
- ⚠️ **Fine-tune.** Training data now spans three styles. Because every pair is within-style, this is
  diversity rather than a three-way split. **Do not attempt per-preset results.** No power.
- PRD flow gains a style-picker step before generation: three large sample cards, not a dropdown.
- Marginal cost: **zero.** Presets are strings.

**Alternatives:**

- **Keep one fixed style** (ADR-007 as written) — simplest and cheapest. Rejected: it removes the clearest
  author-agency affordance in the product, at near-zero implementation cost to keep.
- **Style exemplar image / IP-Adapter** — rejected above.
- **Style LoRA** — ADR-016 trigger (b) still governs: only if raters flag style drift. Not now, and a preset
  is not a reason to revisit it.
- **Let the child describe any style freely** — rejected. An unbounded style space destroys the meaning of
  `wrong_style`, makes the judge's training distribution unbounded, and makes moderation unpredictable.

**Open questions:**

- ~~The three exact prompt fragments.~~ **Resolved 2026-07-21:** authored as `cel` / `comic` / `gouache`
  in `backend/spikes/phase_05.py`; probed by Phase 0.5's secondary arm. `comic` is the gating primary;
  `cel` is the flagship default.
- Does the teacher lock one preset per classroom, or does each child choose? A product question (ADR-017's
  teacher-owner model makes either possible). Not blocking; decide at Phase 2.
