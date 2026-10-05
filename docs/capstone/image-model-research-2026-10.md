# Image-model screen: desk research for C3-10

Researched 2026-10-06. Scope: licence, fal endpoint contract, published price, resolution and steps, published consistency evidence, and lettering behaviour for the two production baselines and the two [C3-10](../product/ROADMAP.md) candidates. No paid calls, no image generation, no model swap. Generation stays fixed until Objective 4; any swap needs its own ADR. Every external source below was checked 2026-10-06 and is listed under [Sources](#sources) as [Sn].

Evidence classes used throughout:

- **Fact**: documented licence, schema, price or spec on the owner's page.
- **Vendor claim**: the model's owner reporting its own quality results.
- **Unknown**: not published, or the page could not be read.

## How the baselines are called today

Read from the code, not the docs:

| Call | Endpoint | Arguments sent | Source |
|---|---|---|---|
| Canonical reference, and any scene with no referenced character | `settings.fal_image_model` = `fal-ai/qwen-image` | `prompt`, `negative_prompt` (`NEGATIVE_PROMPT` plus a per-call `negative_extra` for references), `image_size` `{"width": 1024, "height": 768}`, `output_format: "png"`; steps, guidance and acceleration left at fal defaults | `backend/providers.py` `text_to_image`, `_run_fal`; `backend/pipeline/generate_scene.py:49` |
| Scene page with references | `settings.fal_image_edit_model` = `fal-ai/qwen-image-edit-2511` | `prompt`, `image_urls` (from `REFERENCE_FIELD`), `negative_prompt` = `NEGATIVE_PROMPT`, same `image_size` and format | `backend/providers.py` `edit_image`, `_run_fal` |

- At most two characters get a canonical reference (`state.characters[:2]`, `backend/pipeline/char_bible.py:440`), each with up to 3 draws (`MAX_DRAWS`). A scene therefore sends 0, 1 or 2 reference images.
- Per scene: up to 3 consistency-checked attempts plus 1 output-moderation redraw. `IMAGE_BUDGET = MAX_SCENES * 4 + 15 = 55` (`backend/app/config.py:193`).
- `NEGATIVE_PROMPT` is the only channel carrying the lettering ban ("text, letters, words, writing, signage, labels, captions, ..."). The comment above it records that fal **silently drops unknown arguments**.
- `edit_image` refuses any endpoint missing from `REFERENCE_FIELD`. A new edit endpoint needs a row there before it can be called.
- A fal content flag is recognised only as HTTP 422 "flagged by a content checker" (`is_fal_content_flag`). The code reads `images[0].url` and ignores `has_nsfw_concepts`.

1024×768 = 0.786 MP per output image. The synthetic corpus (`data/judge/corpus/runs/syn-*`, 30 bundles) records 1.83 canonical references per book, 5.0 scenes, 11.2 stored scene attempts (0.03 zero-reference, 6.73 one-reference, 4.40 two-reference) and 18.8 attempted fal calls per story ID in `run_metadata.attempted_calls`. Unverified: whether that count also includes abandoned executions for the readmitted stories.

## Stated facts

### Licence and commercial use

| Model | Licence | Restrictions | fal label |
|---|---|---|---|
| Qwen-Image (baseline, refs) | Apache-2.0 [S1] | None beyond Apache-2.0 on the card | "commercial" [S9] |
| Qwen-Image-Edit-2511 (baseline, scenes) | Apache-2.0 [S2] | None beyond Apache-2.0 on the card | "commercial" [S10] |
| FLUX.2 [klein] 4B (candidate, both legs) | Apache-2.0 [S4] | The card's "Out-of-Scope Use" list includes harming minors, deceptive content, NCII, and "fully automated decision making or high risk applications". It also states this list does not restrict or modify the licence [S4]. BFL "encourage[s]" deployers of 4B to add NSFW/protected-content filters. These are required only for the 9B models [S4]. | "commercial" [S11, S12] |
| Qwen-Image-2512 (candidate, refs only) | Apache-2.0 [S3] | None stated on the card | "commercial" [S13] |

fal terms (last updated 2026-09-08) bar using third-party model outputs "to develop, modify, fine-tune, or improve any products or services that compete with those Third Party Materials" [S20]. A consistency judge is not an image generator. Read literally, the clause does not reach the Objective 4 fine-tune. This note does not settle that legal reading.

### Reference images on the edit endpoints

All from fal's queue OpenAPI schema for each endpoint [S14–S18]:

| Endpoint | Field | Stated limit | Model-card guidance |
|---|---|---|---|
| `fal-ai/qwen-image-edit-2511` | `image_urls` (array, required) | **None stated** in schema or API page | 2509 card: "Optimal performance is currently achieved with 1 to 3 input images" [S5]. 2511 card shows a two-image example [S2]. |
| `fal-ai/flux-2/klein/4b/edit` | `image_urls` (array, required) | "A maximum of 4 images are allowed" | BFL overview: up to 4 references for klein [S7] |
| `fal-ai/qwen-image`, `fal-ai/qwen-image-2512` | n/a (text-to-image) | n/a | n/a |

The klein field name matches Qwen's, so the `REFERENCE_FIELD` row would read `"fal-ai/flux-2/klein/4b/edit": "image_urls"`. The schema confirms the name.

### Price on fal

Read from each model page's published pricing text and its embedded `endpointBilling` record [S9–S13]:

| Endpoint | Published price | Billing detail stated | Per 1024×768 output |
|---|---|---|---|
| `fal-ai/qwen-image` | $0.02 per MP | "Images are billed by rounding up to the nearest megapixel." | $0.020 |
| `fal-ai/qwen-image-2512` | $0.02 per MP | "rounded up to the nearest megapixel" | $0.020 |
| `fal-ai/qwen-image-edit-2511` | $0.03 per MP | Rounding and input-image billing **not stated** | $0.0236 exact, $0.030 if rounded up |
| `fal-ai/flux-2/klein/4b` | $0.005 per MP | Rounding not stated | $0.0039–$0.005 |
| `fal-ai/flux-2/klein/4b/edit` | $0.01 per MP | Rounding and input-image billing **not stated** for this distilled endpoint. The sibling `klein/4b/base/edit` page states "$0.009 per megapixel of input and output. Input images will be resized to 1MP" [S19]. | $0.0079–$0.010 output only. Add about $0.01 per reference if inputs are billed like the sibling. |

Repository cross-check: the B5 smoke run measured **$0.027 per image call** from fal balance deltas (`docs/specs/obj4-readiness-audit.md:365`). The same document calls the real price "$0.0157-$0.0236" (line 1231). That range ignores the qwen-image rounding rule stated above, which makes every reference draw $0.020. Drift is flagged here and left uncorrected.

### Resolution, steps, latency

| Model | Resolutions | fal defaults (code sends none of these) | Published latency |
|---|---|---|---|
| Qwen-Image | Card lists 1328×1328, 1664×928, 1472×1140 and others [S1]. fal accepts custom width/height up to 14142 [S14]. | 30 steps, guidance 2.5, `acceleration: "none"` [S14] | None published |
| Qwen-Image-Edit-2511 | Not stated on card. fal output defaults to input size if `image_size` is null [S15]. | 28 steps, guidance 4.5, `acceleration: "regular"` [S15]. Card recommends 40 steps, true CFG 4.0 [S2]. | None published |
| FLUX.2 klein 4B | Card example 1024×1024 [S4]. BFL editing docs state "up to 4MP output" for FLUX.2 [S8]. | 4 steps (range 4–8), no `guidance_scale` field [S16, S17] | Vendor claim: "under 0.5s on modern hardware", ~13 GB VRAM [S4, S6] |
| Qwen-Image-2512 | Card lists 1328×1328, 1664×928, 1472×1104 and others [S3] | 28 steps, guidance 4, `acceleration: "regular"` [S18]. Card recommends 50 steps, true CFG 4.0 [S3]. | None published |

Every fal output schema returns a `timings` object and `has_nsfw_concepts` [S14–S18]. The screen can log both without extra calls.

### negative_prompt support on each fal endpoint

| Endpoint | `negative_prompt` in schema | Default |
|---|---|---|
| `fal-ai/qwen-image` | Yes | `" "` [S14] |
| `fal-ai/qwen-image-edit-2511` | Yes | `""` [S15] |
| `fal-ai/qwen-image-2512` | Yes | `""` [S18] |
| `fal-ai/flux-2/klein/4b` | **No** (also no `guidance_scale`) | n/a [S16] |
| `fal-ai/flux-2/klein/4b/edit` | **No** (also no `guidance_scale`) | n/a [S17] |
| `fal-ai/flux-2/klein/4b/base/edit` (undistilled sibling) | Yes, with `guidance_scale` default 5, 28 steps | `""` [S19] |

Because `_run_fal` always injects `negative_prompt` and fal drops unknown keys, both klein legs as named in C3-10 would run **without the lettering ban and without the reference background ban**, silently. That is a parity break against the baseline, not a model property.

### Safety-flag surface

The `fal-ai/qwen-image`, `qwen-image-2512`, `klein/4b` and `klein/4b/edit` schemas say unauthorised requests are always checked and "images flagged as unsafe are returned as black images" [S14, S16–S18]. The `qwen-image-edit-2511` description omits that sentence [S15]. The pipeline recognises only a 422 flag. Unknown: which form each endpoint actually returns, and whether a black image is billed.

## Vendor claims

| Model | Consistency / multi-reference claim | Benchmarks and who measured |
|---|---|---|
| Qwen-Image (Aug 2025) | Report claims pose edits keep "subject identity and background structure" [S21] | Alibaba's own report [S21]: GEdit-Bench overall 7.56 EN / 7.52 CN, **scored by GPT-4.1**; ImgEdit overall 4.27; GenEval 0.91 (with RL); DPG 88.32; CVTG-2K word accuracy 0.8288; LongText-Bench 0.943 EN / 0.946 ZH. These are the August generation and edit checkpoints, not 2511 or 2512. No identity-consistency benchmark is reported. |
| Qwen-Image-Edit-2511 | "character consistency has been significantly improved", plus "Improved Multi-Person Consistency" fusing "two separate person images into a coherent group shot" [S2] | **No numbers** on the card. The official blog [S22] renders client-side and returned no content to fetch. |
| FLUX.2 klein 4B | "multi-reference editing", "matches or exceeds Qwen's quality at a fraction of the latency and VRAM" [S6] | BFL's own Elo charts across text-to-image, single-reference and multi-reference tasks. Values are in images only, and rater pool and comparison counts are not stated [S6]. No identity metric. |
| Qwen-Image-2512 | Better human realism and text rendering. No reference or identity claims (text-to-image only). [S3] | "over 10,000 rounds of blind model evaluations on AI Arena" (Alibaba's own arena), "strongest open-source model". Elo shown only as an image [S3]. |

None of these measure same-character identity across illustrated pages, which is what StoryBuddy needs.

## Text and lettering behaviour

- **Qwen-Image family (both baselines, 2512)**: text rendering is a design goal. The report's data pipeline deliberately synthesises text "embedding synthetic text into realistic visual contexts" [S21]. The 2512 card lists "Improved Text Rendering" as a headline change [S3]. fal's qwen-image schema notes `acceleration: "high"` "is recommended for images without text" [S14]. Qwen's own 2512 default negative prompt includes "文字模糊，扭曲" ("blurry, distorted text"), which targets *bad* text rather than *any* text [S3].
- **FLUX.2 klein 4B**: the card's limitations say "While the model can output text, text rendered may be inaccurate or subject to distortion" [S4]. BFL attributes typography strength to FLUX.2 [flex], not klein [S7].
- **Evidence of unwanted text**: no vendor source reports unprompted lettering for any of the four. The only evidence is this repository's. `providers.py` records production pages with smeared pseudo-lettering and speech bubbles (2026-08-13). The [selected-page lettering screen](pipeline-gate-audit-2026-09.md#selected-page-lettering-screen--2026-10-06) found one clear invented caption and two softer cases in 16 sampled pages, and showed the `text_free` flag over-fires. That screen also says a count rule must be fixed before a larger screen.

## Other 2026 open-weight multi-reference editors

| Model | Released | Licence | References | fal | Fit |
|---|---|---|---|---|---|
| FLUX.2 [klein] 4B Base | 2026-01-15 [S6, S12] | Apache-2.0 [S23] | Up to 4 on fal [S19] | `fal-ai/flux-2/klein/4b/base/edit`, $0.009/MP input+output [S19] | Same licence as the C3-10 candidate and **has `negative_prompt`**. Worth adding as the parity arm. |
| FLUX.2 [klein] 9B | 2026-01-15 [S6] | FLUX Non-Commercial License [S4, S6] | Up to 4 on fal [S24] | `fal-ai/flux-2/klein/9b/edit` exists [S24] | Non-commercial. The HF card is gated and was not read. |
| HunyuanImage-3.0-Instruct | 2026-01-26 [S25] | Tencent Hunyuan Community License. Does not apply in the EU, UK or South Korea, and above 100M MAU a licence must be requested [S26]. | "A maximum of 3 images" on fal [S27] | `fal-ai/hunyuan-image/v3/instruct/edit`, $0.09/MP [S27] | 80B-parameter MoE [S25] at 3–9× the baseline price. Territory carve-out. |
| Qwen-Image-2.1 | 2026-09-20 [S28] | Qwen Research License, non-commercial only [S28] | Up to 10 [S28]; fal schema `maxItems` 10 [S29] | Schema exists but the model page shows `licenseType: "private"`, compute-second billing at price 0 and enterprise status "pending" [S29]. **Not publicly priced.** | Licence fails the Apache-2.0 bar of the current baselines. fal's `negative_prompt` is "used only when guidance_scale is greater than 1" [S29]. |
| Boogu-Image-0.1-Edit | 2026-06-16 [S30] | Apache-2.0, "research project only" [S30] | "Only support 1 reference image for now" [S30] | `fal-ai/boogu-image/edit` takes a single `image_url` [S31] | Not multi-reference. Excluded. |

## Unknown or could not verify

- Whether `qwen-image-edit-2511` and `flux-2/klein/4b/edit` bill input reference megapixels, and whether they round up. Not stated on either page.
- The Qwen-Image-Edit-2511 blog [S22] returned no readable content (client-side rendered).
- The FLUX.2 [klein] 9B HF card is gated. Its licence is taken from BFL's blog and the 4B card.
- The klein Elo values, rater pool and comparison counts are published only as chart images [S6].
- The fal API page for `flux-2/klein/4b/edit` shows no price. The price came from the model page and its embedded billing record, not a dedicated pricing API (that needs a key).
- How each endpoint actually surfaces a safety flag (422 or black image), and whether a black image is billed.
- The reference-numbering convention klein expects in prompts. The pipeline writes "Image 1 is …" (`prompt_optimizer.py`) and no BFL page checked confirms klein honours it.

## Implications for the C3-10 screen

Verify in the paid run:

1. **Reference count**: both edit endpoints accept two `image_urls`. klein's cap is 4 and Qwen's is unstated. Confirm a two-reference scene actually conditions on both: the omnigen precedent in `providers.py` shows a dropped field yields a confident wrong character.
2. **Negative-prompt parity**: the distilled klein endpoints have no `negative_prompt`. Either record that the klein arm ran with no ban, or add `klein/4b/base/edit` (Apache-2.0, has the field) as a parity arm. Otherwise invented lettering on klein confounds model and missing ban. Count lettering with the rule the lettering screen asks for, fixed before scoring.
3. **Fal defaults differ**: the code sends no steps, guidance or acceleration. `qwen-image` runs `acceleration: "none"`; `qwen-image-2512` and `qwen-image-edit-2511` run `"regular"`. Log the effective defaults per arm, or pin them.
4. **"Reference generation only" is not one switch**: `fal_image_model` also draws every zero-reference scene (`generate_scene.py:49`). That was 1 of 335 stored synthetic scene attempts, but the zero-reference stratum C3-10 asks for runs through it.
5. **Safety surface**: log `has_nsfw_concepts` and check for black images. A flagged black image would pass the current code as a completed, possibly billed draw.
6. **Latency**: use fal's returned `timings`. No vendor latency for the Qwen endpoints is published, and klein's sub-second figure is for local hardware.
7. **Price per completed book**: use the synthetic-corpus mix from above, with the price columns already stated and output-only billing unless noted. Treat the 7.6 non-scene calls per book as text-to-image draws (an assumption). Draw counts are today's. A model that fails the judge more often buys more retries, up to `IMAGE_BUDGET` 55.

   | Arm | Text-to-image leg | Edit leg | Estimated cost per book |
   |---|---|---|---|
   | Baseline | qwen-image $0.020 | qwen-image-edit-2511 $0.0236–$0.030 | **$0.42–$0.49** (B5 measured $0.027 × 18.8 ≈ $0.51) |
   | 2512 refs + baseline edits | qwen-image-2512 $0.020 | unchanged | **$0.42–$0.49**, same price as baseline |
   | klein both legs, output-only billing | $0.0039–$0.005 | $0.0079–$0.010 | **$0.12–$0.15** |
   | klein both legs, inputs billed like the base sibling | as above | + $0.01 per reference | **$0.27–$0.31** |
   | klein t2i + klein base edit | $0.0039–$0.005 | 1 ref $0.016–$0.018, 2 refs $0.025–$0.027 | **$0.25–$0.28** |

   The billing questions in [Unknown](#unknown-or-could-not-verify) set which klein row applies. Read the fal dashboard after the first few calls, before the spend cap is sized.

## Sources

All checked 2026-10-06.

- [S1] Qwen-Image model card — https://huggingface.co/Qwen/Qwen-Image
- [S2] Qwen-Image-Edit-2511 model card — https://huggingface.co/Qwen/Qwen-Image-Edit-2511
- [S3] Qwen-Image-2512 model card — https://huggingface.co/Qwen/Qwen-Image-2512
- [S4] FLUX.2 [klein] 4B model card — https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
- [S5] Qwen-Image-Edit-2509 model card — https://huggingface.co/Qwen/Qwen-Image-Edit-2509
- [S6] BFL blog, FLUX.2 [klein] (dated January 15, 2026) — https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence
- [S7] BFL docs, FLUX.2 overview — https://docs.bfl.ai/flux_2/flux2_overview
- [S8] BFL docs, FLUX.2 image editing — https://docs.bfl.ai/flux_2/flux2_image_editing
- [S9] fal model page, qwen-image — https://fal.ai/models/fal-ai/qwen-image
- [S10] fal model page, qwen-image-edit-2511 — https://fal.ai/models/fal-ai/qwen-image-edit-2511
- [S11] fal model page, flux-2/klein/4b — https://fal.ai/models/fal-ai/flux-2/klein/4b
- [S12] fal model page, flux-2/klein/4b/edit — https://fal.ai/models/fal-ai/flux-2/klein/4b/edit
- [S13] fal model page, qwen-image-2512 — https://fal.ai/models/fal-ai/qwen-image-2512
- [S14] fal OpenAPI, qwen-image — https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/qwen-image
- [S15] fal OpenAPI, qwen-image-edit-2511 — https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/qwen-image-edit-2511
- [S16] fal OpenAPI, flux-2/klein/4b — https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/flux-2/klein/4b
- [S17] fal OpenAPI, flux-2/klein/4b/edit — https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/flux-2/klein/4b/edit
- [S18] fal OpenAPI, qwen-image-2512 — https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/qwen-image-2512
- [S19] fal model page and OpenAPI, flux-2/klein/4b/base/edit — https://fal.ai/models/fal-ai/flux-2/klein/4b/base/edit and https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/flux-2/klein/4b/base/edit
- [S20] fal Terms of Service (last updated 2026-09-08) — https://fal.ai/terms
- [S21] Qwen-Image Technical Report, arXiv:2508.02324 (Tables 3, 8, 10, 11, 12; data synthesis section) — https://arxiv.org/html/2508.02324v1
- [S22] Qwen blog, Qwen-Image-Edit-2511 (**no readable content returned**) — https://qwen.ai/blog?id=qwen-image-edit-2511
- [S23] FLUX.2 [klein] 4B Base model card — https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B
- [S24] fal OpenAPI, flux-2/klein/9b/edit — https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/flux-2/klein/9b/edit
- [S25] HunyuanImage-3.0-Instruct model card — https://huggingface.co/tencent/HunyuanImage-3.0-Instruct
- [S26] Tencent Hunyuan Community License (HunyuanImage-3.0-Instruct repo) — https://huggingface.co/tencent/HunyuanImage-3.0-Instruct/blob/main/LICENSE
- [S27] fal model page and OpenAPI, hunyuan-image/v3/instruct/edit — https://fal.ai/models/fal-ai/hunyuan-image/v3/instruct/edit
- [S28] Qwen-Image-2.1 model card and LICENSE — https://huggingface.co/Qwen/Qwen-Image-2.1 and https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE
- [S29] fal model page and OpenAPI, qwen-image-2.1/edit — https://fal.ai/models/fal-ai/qwen-image-2.1/edit
- [S30] Boogu-Image-0.1-Edit model card — https://huggingface.co/Boogu/Boogu-Image-0.1-Edit
- [S31] fal OpenAPI, boogu-image/edit — https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/boogu-image/edit

Local evidence inspected: `backend/providers.py`, `backend/app/config.py`, `backend/pipeline/generate_scene.py`, `backend/pipeline/char_bible.py`, `backend/pipeline/prompt_optimizer.py`, `data/judge/corpus/runs/syn-*/{run,memory}.json`, `docs/specs/obj4-readiness-audit.md`. No code, config, label or corpus file changed.
