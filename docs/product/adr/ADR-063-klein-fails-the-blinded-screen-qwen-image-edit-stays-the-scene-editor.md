# ADR-063 — klein fails the blinded screen; Qwen-Image-Edit stays the scene editor

**Status:** Accepted (2026-10-08) · closes ADR-062's candidacy · leaves ADR-001 unchanged · changes no production setting, the reference generator, the judge, or the registered Objective 4 corpus

## Context

ADR-062 named `fal-ai/flux-2/klein/4b/base/edit` the candidate scene editor. Production would change
only after a blinded rate screen, a judge recheck, a contract check and a follow-up ADR. That ADR's
evidence came from scenes picked because Qwen had failed on them. It warned that some regression to
the mean was expected.

The blinded screen ran early, as an exploratory check
([model probes, blinded klein screen](../../capstone/model-probes-2026-10.md)). Its sample, scoring
and pass rule were committed before the first paid call (`1e870b8`):

- 30 random synthetic scenes, 15 with one reference and 15 with two.
- Each scene's stored Qwen first attempt against one new klein draw from the same prompt.
- Images shown as A and B, sides set by a hash. All 60 scored and saved before the key was opened.
- klein passes only if it draws fewer duplicate-or-extra pages than Qwen, and its identity-or-style
  pages exceed Qwen's by at most 3.

| Per 30 pages | Qwen | klein |
|---|---|---|
| Duplicate or extra (major) | 4 | 4 |
| Identity (major) | 3 | 10 |
| Style (major) | 0 | 0 |
| Lettering | 2 | 0 |
| Action | 2 | 8 |
| No defect of any kind | 20 | 13 |

Both rules fail. The duplicate counts tie. Identity misses the margin by 4 pages, not by one. Qwen's
duplicate rate here (13%) equals the stage audit's, and klein's is the same. The two editors failed
on different scenes, sharing only one. The earlier probes' gap came from the scene selection.

## Decision

1. **Qwen-Image-Edit stays the scene editor.** `fal_image_edit_model` remains
   `fal-ai/qwen-image-edit-2511`. ADR-001 stands as written.
2. **klein's candidacy is closed.** ADR-062's remaining gates (judge recheck, contract check) are not
   run. The screen is recorded as exploratory, but a fail this wide closes the question: running the
   formal gate after Objective 4 would spend money confirming an advantage the screen did not find.
3. **Duplicates are an open defect, not one awaiting an editor swap.** The defense reports a 13%
   major duplicate rate. Changing the editor does not lower it, measured on two editors.
4. **Any future editor candidate passes the same screen first.** Same sampling, same blinding, same
   two rules, with its own seed string, before an ADR names it a candidate. A failure-picked probe
   may motivate a screen but never stands in for one (ADR-055).

## Consequences

- No code, setting or corpus changes. Objective 4 is unaffected; no klein image entered its corpus.
- ADR-062's gates and timing no longer apply. Its record of the probes stays as the motivation that
  was tested.
- The duplicate fixes that do not depend on the editor stay open: body-count phrases in the
  direction, and cast members past the two-reference cap. Each needs its own measured change.
- klein drew no invented lettering against Qwen's 2. At n = 30 that is not a finding to act on.
- The screen's script and protocol can be reused for the next candidate at about $0.02 a scene.

## Alternatives considered

- **Run ADR-062's formal gates after Objective 4 anyway.** Rejected. The screen found no duplicate
  advantage to confirm and a clear identity cost.
- **Cascade: klein only where Qwen draws a duplicate.** The arms failing on different scenes is what
  a cascade would use. Rejected: the trigger is the judge's `subjects_unique`, which misses and
  over-flags duplicates (the best-of ranking review). klein's identity losses would also come with
  every retry.
- **More klein draws per page, keep the best.** Rejected. Without a reliable picker this is the
  cascade's problem, and a human picker does not scale to a product.
- **Scenes from a text-to-image generator, with no reference.** Rejected on measured evidence.
  Phase 0.5 Probe 1 drew each scene from the description alone, through the reference generator
  (`providers.text_to_image`). The invented character Quill kept identity on 40% (Run 2) and 30%
  (Run 3) of those, against 70% and 80% with the reference (`docs/product/PHASE_05_RESULTS.md`).
  The fox cub scored the same either way, but many corpus characters are invented: a sock dragon,
  a gargoyle, an egg-shaped robot. ADR-001's reference-conditioned design exists for this case.
