# ADR-062 — FLUX.2 klein 4B base is the candidate scene editor, not yet the production one

**Status:** Accepted (2026-10-08) · would amend ADR-001's scene-editor choice only after the gates in Decision 2 pass · changes no production setting, the reference generator, the judge, or the registered Objective 4 corpus

## Context

Duplicate characters are the largest major page defect a change can still fix. The October stage
audit found a major `duplicate_character` on 28 of 221 pages (13%). The larger `reference_inherited`
count is mostly stated body counts, which ADR-056 records as a limitation, and the count screen
found no reference model that fixes them.

The [October model probes](../../capstone/model-probes-2026-10.md) ruled out the cheaper fixes:

- **Prompt and data.** Every page prompt already says "draw each character exactly once". Of the 13
  duplicate pages without a group direction, 8 come from the editor itself: a character drawn at
  both ends of a move, or twice for no visible reason. No prompt or data change reaches more than
  2 of the 13 (the duplicate-cause review).
- **Best-of ranking.** Shipping the attempt the judge did not flag for duplicates helped one scene
  and hurt another (the best-of ranking review).
- **Text model.** No open-weight candidate beat Mistral (the text-model trial).

The scene editor did reduce duplicates. `fal-ai/flux-2/klein/4b/base/edit` (Apache-2.0,
`image_urls` up to 4, has `negative_prompt`) was given each scene's stored first-attempt prompt and
the same references, in 12 scenes where `fal-ai/qwen-image-edit-2511` shipped a duplicate. It drew
18 of 24 draws without a duplicate or extra character. On the second round's 6 scenes, 2 or 3 of
the 16 stored Qwen attempts were clean. The first round's 4 control scenes kept identity on 8 of 8
draws.

That evidence is weak in known ways:

- The scenes were picked because Qwen failed, so some regression to the mean is expected.
- There was one rater, and the arms were not blinded.
- Qwen's retries had corrected prompts; klein had only the first.
- klein lost the cut-paper style on syn-024 and drifted in colour on syn-004. It also drew one
  clothed General Lint, and the wrong character acting in both syn-002 draws.
- It still copies characters when the prompt invites it: a body-count phrase ("all four jaws") or a
  cast member past the two-reference cap.

The production judge was prompted and checked on Qwen pages only. The Objective 4 judge is trained
and evaluated on a registered Qwen corpus. ADR-061 point 5 and ROADMAP C3-10 both say a new image
distribution needs the judge rechecked before a product swap.

## Decision

1. **The candidate.** `fal-ai/flux-2/klein/4b/base/edit` is the selected candidate to replace
   `fal-ai/qwen-image-edit-2511` as `fal_image_edit_model`, the scene editor only. The reference
   generator stays `fal-ai/qwen-image`: the count screen found nothing better, and under ADR-001
   style is decided at the reference. The distilled `klein/4b/edit` is not the candidate, because
   it has no `negative_prompt` and fal would silently drop the lettering ban.
2. **The gates.** Production does not change until all of these pass:
   - **Blinded rate screen** (ADR-055). Random synthetic scenes, not failure-picked, stratified by
     zero, one or two references. Both editors draw from the same prompts, and arm labels stay
     hidden until scoring is saved. Scored by the audit's defect types: duplicate or extra
     character, identity drift, style escape, invented lettering, action mismatch. The pass rule
     and sample size are written down before the first paid call. klein must lower the
     duplicate-or-extra rate without raising identity drift or style escape beyond that pre-set
     margin.
   - **Judge recheck.** On the screen's klein pages, the production judge's verdicts are compared
     with the human scores. The judge must catch klein's defects at least as well as it catches
     Qwen's on the same scenes.
   - **Contract.** A `REFERENCE_FIELD` row checked against fal's openapi. A verified two-reference
     scene that conditions on both. How the endpoint reports a safety flag (HTTP 422 or a black
     image), and the pipeline handling that form. All 32 probe calls returned
     `has_nsfw_concepts: [False]`, which proves nothing about detection.
   - **A follow-up ADR** records the screen result and makes the swap, or rejects it.
3. **Timing.** The gates run after the Objective 4 result. Before the defense, Qwen stays the
   shipped editor, and duplicates are reported as an open defect with this ADR as the evidenced
   next step. klein images never enter the registered Objective 4 corpus.

## Consequences

- The defense can name a measured lever for the largest fixable defect, without claiming a
  production improvement that has not been made.
- If the swap ships, Objective 4's result describes a judge on Qwen pages. Whether it holds on
  klein pages is the judge-recheck gate's question, not an assumption.
- Cost goes down or stays flat. klein base edit is $0.009 per megapixel of input and output, with
  inputs resized to 1 MP: about $0.016 to $0.027 per page with one or two references. The baseline
  book costs about $0.42 to $0.49, per the 2026-10-06 desk research. Probe wall times were 7 to
  14 s per call.
- The screen costs money that the October USD 2 cap no longer covers. Its spend cap is set when it
  is scheduled.
- Prompt-invited copies need their own fixes whichever editor ships: body-count phrases in the
  direction, and cast members past the two-reference cap.

## Alternatives considered

- **Swap before the defense on the probe evidence.** Rejected. The evidence is failure-picked,
  unblinded and has one rater. The style drift is unmeasured. The judge has never seen a klein page.
- **Keep Qwen and fix duplicates in the prompt.** Rejected for now. The prompt already asks for each
  character once, and the duplicate-cause review found no prompt or data change reaching more than
  2 of 13 pages.
- **OmniGen2** (ADR-001's rung 1). Not chosen: ADR-001 measured it fusing characters into scene
  objects at a 20–25% floor.
- **FLUX.2 klein 9B.** Non-commercial licence. ADR-015 permits it only as a fallback, and nothing
  measured favours it.
- **An auto-cascade** (Qwen first, klein on a judge duplicate flag). Rejected. The judge's
  `subjects_unique` misses and over-flags duplicates (the best-of ranking review), so the trigger
  is unreliable.
