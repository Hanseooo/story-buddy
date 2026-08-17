# ADR-042 — Reliable selectable styles: Gouache default, Comic retired, Cut-paper candidate

**Status:** Accepted (2026-08-17; owner approved) · **resolves D-O** · **amends ADR-022's
exact selectable catalog, flagship default, and preset acceptance policy** · preserves ADR-007's
reference-carried style mechanism · implementation and paid candidate validation pending

**Context:** ADR-022 made `cel`, `comic`, and `gouache` selectable and named Cel the flagship
default. Production observations since then show Comic resolving into materially different visual
families: some jobs look halftone- or doodle-like, while others resemble an older television
cartoon. Because the canonical reference is generated once in the chosen style and conditions the
scene images, this ambiguity can determine the appearance of an entire book. A picker cannot
truthfully promise one look when the same preset name produces either family.

The Phase-0.5 preset results do not prove that Comic is less identity-preserving than Cel or
Gouache. Comic's reported identity result was confounded by a different reference layout, and all
three fragments have since changed. The current Comic fragment is explicitly unmeasured. This
decision therefore treats the repeated production mismatch as an operational product-quality veto,
not as a population-level or capstone finding.

The owner ranks consistency above preset variety, has found Gouache the most consistently
acceptable production preset, and wants a replacement for Comic tested before it becomes official.
Existing Comic jobs must remain resumable, and legacy rows with a null preset must not silently
change style.

**Decision:**

1. **Consistency is the first acceptance criterion for a child-visible preset.** A preset name and
   picker sample must describe one reproducible visual family across canonical references and scene
   images. Visual distinctness and medium character matter only after that condition holds.
2. For new storybooks, the selectable catalog becomes **Gouache and Cel**, and **Gouache is the
   default**. The picker selects Gouache initially. An omitted or null style on a new API request is
   canonicalized to `gouache` before the job row is inserted.
3. **Comic is hard-retired from new creation.** It is removed from the picker, and an explicit
   `style_preset_id="comic"` on a new `POST /storybooks` request is rejected at the API boundary.
   Hiding the card alone is insufficient because it would leave the public contract able to create
   a retired preset.
4. **Comic remains runtime-compatible for existing work.** Its current identifier and fragment stay
   available to the worker, the database constraint continues to accept `comic`, and stored rows,
   references, prompts, attempts, and checkpoints are not rewritten or redrawn. A historical row
   with `style_preset_id = null` continues to resolve to Cel; changing that fallback would silently
   restyle a legacy job.
5. Selection eligibility and execution compatibility are separate policies. The implementation
   uses the smallest explicit allowlist needed at the creation boundary while retaining the
   existing execution lookup. It does not introduce a versioned preset registry, status model, or
   plugin framework.
6. **Cut-paper collage is the sole provisional replacement candidate.** Its frozen candidate
   fragment is:

   > flat cut-paper storybook collage, clean simplified shapes with crisp cut edges, flat layered
   > colour areas, limited warm palette, subtle paper fibre texture, no outlines, no gradients, no
   > glossy highlights, no dimensional shadows

   The candidate is not added to the public API, database constraint, worker catalog, picker, or
   sample-card manifest merely so it can be tested. The offline product-validation path supplies
   the fragment directly.
7. The candidate is tested on three frozen stories using the current production image models,
   provider paths, prompt construction, moderation, consistency control, and retry limits. The set
   contains: one human-led story, one non-human-led story, and one multi-character story. Review the
   canonical references and every scene attempt, not only each selected winner. Generate the one
   proposed picker sample through the same current text-to-image path and exact fragment before
   scoring; it is part of the reviewed evidence rather than a later marketing approximation.
8. **Promotion requires zero style-family misses across all three books.** Every reviewed image must
   remain recognizably in the promised cut-paper family: simplified flat layered shapes, crisp cut
   edges, limited colour areas, and subtle paper texture, without switching to cel animation,
   doodle, television-cartoon, photoreal, 3D-craft, or another rendering family. The selected
   references and final pages must also preserve identity-defining traits and intact anatomy, and
   all three jobs must complete inside the existing image and recursion budgets.
9. The validation records the exact fragment, model IDs, provider routes, prompt versions, job IDs,
   every attempt path, selected winners, and the owner's pass/fail judgment without exposing child
   PII. It is targeted product validation, not a preset-effect experiment or a capstone efficacy
   claim. No cross-preset ranking is required.
10. If every gate passes and the owner accepts the recorded evidence, Cut-paper collage may replace
    Comic as the third selectable preset in a later implementation session. Its public identifier
    is `cut_paper`; the picker label is `Paper Cutout`; Gouache remains the default. The same change
    adds the database value, runtime fragment, accepted sample card, API acceptance, specs, and
    deterministic tests. It does not regenerate a different picker sample after validation. No
    further architectural choice is required unless the implementation departs from this decision.
11. If any gate fails, Cut-paper remains unavailable and the public catalog stays at Gouache and
    Cel. No different replacement is substituted automatically; another candidate requires a new
    ADR or an explicit amendment accepted by the owner.
12. A repeated, documented owner observation of a material picker-promise mismatch is sufficient
    to quarantine a child-visible preset. Reintroduction of Comic or any retired preset requires
    the same current-stack, three-book, zero-miss gate and owner acceptance. Historical probe
    rankings alone are insufficient when fragments or production call shapes have changed.

**Consequences:**

- The product temporarily offers two honest choices instead of three unreliable ones. This amends
  ADR-022's minimum-three requirement in favor of consistency.
- Gouache becomes the default only for newly created jobs. Existing books retain their stored or
  legacy-resolved style.
- API selection and worker execution no longer share one identical allowlist, but both still use
  the existing fragments and identifiers; the split exists solely to preserve old jobs while
  rejecting retired styles for new ones.
- No migration is needed to retire Comic. A migration is required only if `cut_paper` passes and is
  promoted, because the existing `jobs.style_preset_id` check constraint enumerates the values.
- The current Comic sample may remain as historical source material, but it is no longer rendered
  in the child-facing picker after implementation. It is not relabeled as Cut-paper.
- The candidate test costs real image calls and remains outside CI. Deterministic tests verify
  catalog, defaulting, rejection, and compatibility behavior; they never assert generated quality.
- A three-book zero-miss result is a product release gate, not proof that Cut-paper will never drift.
  Later production mismatches can trigger the same quarantine policy.
- ADR-022's prompt-fragment mechanism, frozen-per-book selection, within-preset judging, and
  rejection of exemplar images, free-form styles, and style LoRAs remain unchanged.

**Alternatives:**

- **Keep or re-author Comic in public while testing it.** Rejected because children would continue
  selecting a preset whose visible promise is already unreliable.
- **Hide Comic only in the frontend.** Rejected because manually submitted new jobs could still
  create Comic books, contradicting the retirement policy.
- **Delete Comic from every runtime and database surface.** Rejected because existing rows and
  paused checkpoints must resume without being restyled or invalidated.
- **Make Cut-paper official immediately.** Rejected because the same assumption-first path produced
  the Comic problem; the candidate must demonstrate current-stack consistency before exposure.
- **Flat screen-print.** Rejected as the first candidate because ink grain and registration effects
  can alter identity-bearing colours between reference and scene scale.
- **Coloured-pencil storybook.** Rejected as the first candidate because variable sketch lines and
  shading create more identity variance than flat cut shapes.
- **Add active/retired/version metadata to a preset registry.** Rejected as unnecessary machinery
  for one compatibility-retained preset and one gated candidate.

**Escape hatch:** Changing the default, restoring Comic for new jobs, promoting a candidate that did
not pass the gate, weakening the zero-miss rule, or substituting a different candidate requires a
new ADR or an explicit owner-accepted amendment before implementation.
