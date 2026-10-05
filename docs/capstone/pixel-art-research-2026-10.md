# Pixel-art preset: desk research for C3-13

Researched 2026-10-06. Scope: whether the current generators can draw pixel art, published LoRAs and their fal price, the "fake pixel art" clean-up problem, what pixel art does to identity judging, prompt wording that fits the house fragment convention, and a trial design for [C3-13](../product/ROADMAP.md) / [#98](https://github.com/Hanseooo/story-buddy/issues/98). No paid calls, no image generation, no preset or prompt change. The trial runs after Objective 4, with spend approved first. Every external source was checked 2026-10-06 and is listed under [Sources](#sources) as [Pn].

Evidence classes, as in the [image-model screen](image-model-research-2026-10.md):

- **Fact**: documented licence, schema, price or spec on the owner's page, or a measured value from this repository.
- **Vendor claim**: a model, LoRA or tool owner reporting its own quality results.
- **Inference**: my reasoning from the facts. Not measured.
- **Unknown**: not published, or the page could not be read.

## What the repository already shows

### Current conventions a pixel preset has to fit

Read from the code:

- A preset is one comma-separated fragment in `STYLE_PRESETS` (`backend/app/config.py:156`). `cel` is `settings.default_style_fragment`. The API default is `gouache` (`backend/app/main.py:173`), so #98's proposal to replace `cel` replaces a non-default preset.
- `test_no_preset_utters_a_term_the_negative_prompt_suppresses` (`backend/tests/test_config.py:30`) fails any fragment that names a `NEGATIVE_PROMPT` term as a whole word.
- Every `no <term>` clause in a fragment also becomes a description filter. `style_prohibitions` reads the words after `no`, and `_permitted` drops any description word that shares a 4+ character prefix with one of them (`backend/pipeline/prompt_optimizer.py:35-55`). A clause like `no smooth shading` would strip "smooth" from a child's "smooth unbroken front surface".
- The `comic` note in `config.py` records that a halftone screen on the character's body tints by dot density, so one fill reads as two colours to `wrong_colour`, and that halftone dots are the expected `text_free` false positive. Dithering is the pixel-art equivalent (inference).

### The one pixel-art book: syn-007

The pipeline gate audit names syn-007 s4-3 as pixel art under `cel` (`pipeline-gate-audit-2026-09.md:349`). Reading `data/judge/corpus/runs/syn-007/memory.json` and the stored images shows it is more than one page:

- **Cause (inference, strongly suggested)**: the story's second character is a "sprite" (fairy sense). The canonical reference for Halo (`ref-c1-1.png`) came back as a video-game sprite: blocky outline, two square eyes, flat background. The model read the homonym. The prompt never asked for pixel art.
- **Spread (fact)**: the pixel look reached 11 of the 13 judged scene attempts. The judge's `differences_observed` or `scene_contradictions` say "pixelated" or "pixel art" on each of those 11. The style escape came from one reference and was inherited by the pages, which is the `config.py` note's warning about one reference deciding every page.
- **Judge behaviour (fact)**: 11 of 13 attempts got `same_character: False` and 12 of 13 got `style_match: False`. The judge saw the style and treated it as a difference. s4-3 shipped as the scene's final image with `same_character: False` (capped best-of).
- **Description loss (fact)**: Halo's reference verdict lists two contradictions: square eyes against "smooth unbroken front surface", and "solid, opaque purple form" against "see-through". Translucency did not survive the sprite rendering.
- **Fake pixels (fact, rough measurement)**: on the reference, colour-change run lengths along rows cluster at 18–23 px, not one integer step, and the 1024×768 PNG has 33,410 distinct colours. The page s4-3 clusters at 4–10 px with 80,382 colours. Real pixel art at this size would have one cell size and a palette of tens of colours. The reference and its page do not share a grid. Method: absolute luminance difference > 40 between neighbouring pixels on every 8th row, histogram of gaps. It is an indicator, not a grid detector.

This is one story and one model reading of a word. It shows the generators reach the look unprompted. It does not show they hold a consistent grid.

## Stated facts

### Can the current models draw pixel art from prompting alone?

| Source | What it says about pixel art | Class |
|---|---|---|
| Qwen-Image card [P1] | "a wide range of artistic styles. From photorealistic scenes to impressionist paintings, from anime aesthetics to minimalist design". Pixel art is not named. | Vendor claim |
| Qwen-Image tech report [P2] | Training data has a "Design" category covering "artistic styles". No mention of pixel art, 8-bit or 16-bit in the report text. | Fact (absence) |
| Qwen-Image-Edit card [P3] | Style transfer is a supported edit ("such as Studio Ghibli"). Pixel art is not named. | Vendor claim |
| Qwen-Image-Edit-2511 card [P4] | "integrates selected popular LoRAs directly into the base model". The example given is lighting. No pixel-art LoRA is named as integrated. | Vendor claim |
| Qwen's 2512 prompt rewriter [P5] | Lists "pixel art style" only as a **font style** for rendered text. | Fact |

No vendor page shows pixel-art output for Qwen-Image or Qwen-Image-Edit-2511. The only evidence that prompting alone reaches the look is syn-007 above.

### Published pixel-art LoRAs

Found by searching Hugging Face for "pixel" under each base model's adapter tree [P6], then reading each card. Download counts are last-month figures from the HF API.

| LoRA | Base | Licence | Trigger | Training data stated | Fit for StoryBuddy |
|---|---|---|---|---|---|
| `prithivMLmods/Qwen-Image-2512-Pixel-Art-LoRA` [P7] | Qwen-Image-2512 | Apache-2.0 | "Pixel Art" | 50 images, captions by DeepCaption-VLA-7B. Image source not stated. | Text-to-image only. Base is 2512, not the `qwen-image` the pipeline calls. |
| `artificialguybr/PIXELART-REDMOND-QWENIMAGE` [P8] | Qwen-Image-2512 | Apache-2.0 | "Pixel Art, PixArFK" | Not stated | Same base mismatch. Card describes "8-bit and 16-bit inspired" output. |
| `JOYUNGI/nwpxstyle-qwen-image-lora` [P9] | Qwen-Image-2512 | Apache-2.0 | "nwpxstyle." | 31 AI-generated anime illustrations | Author: "barely transfers to other subjects". Excluded. |
| `svntax-dev/pixel_portrait_lora_v1-lora` [P10] | Qwen-Image | CreativeML OpenRAIL-M (use-based restrictions) | none | Not stated; 512×512 | Card: "downscale by a factor of 8" for pixel-perfect output, and quality may drop above 512×512. Portraits only. |
| `damnthatai/Game_Boy_Camera_Pixel_Style_Qwen` [P11] | Qwen-Image | Apache-2.0 | "g4m3b0yc4m3r4" | Not stated | Game Boy Camera photo look; card examples prompt Nintendo characters. Excluded. |
| `svntax-dev/pixel_spritesheet_4walk_combat_32x48_v1` [P12] | Qwen-Image-Edit-2511 | Apache-2.0 | none | Not stated; 768×768 | Draws 32×48 animation spritesheets, "downscale by a factor of 4". Wrong task. |

`PixelSmile/PixelSmile` matches the search but is facial-expression editing, not pixel art [P13].

No pixel-art **style** LoRA was found for Qwen-Image-Edit-2511, the model that draws every referenced page. A text-to-image LoRA would restyle only the canonical references, and pages would inherit the style through the reference images, as syn-007's did.

### Do the fal endpoints accept LoRAs, and at what price?

From each endpoint's queue OpenAPI schema and model page [P14–P18]:

| Endpoint | `loras` field | `negative_prompt` | Published price | Per 1024×768 output |
|---|---|---|---|---|
| `fal-ai/qwen-image` (current reference model) | **Yes**: "up to 3 LoRAs and they will be merged together"; each `{path, scale}`, scale 0–4, default 1; path is "URL or the path to the LoRA weights" | Yes | $0.02/MP, rounded up to the nearest MP [P14] | $0.020. The page does not say whether a LoRA changes the price. |
| `fal-ai/qwen-image-edit-2511` (current page model) | **No** | Yes | $0.03/MP [P15] | $0.0236–$0.030 |
| `fal-ai/qwen-image-edit-2511/lora` | **Yes**, same 3-LoRA wording; also `image_urls`, steps default 28, guidance 4.5, acceleration `regular` | Yes | $0.035/MP (`endpointBilling` price 0.035) [P16] | $0.0275 exact, $0.035 if rounded up. Rounding and input billing not stated. |
| `fal-ai/qwen-image-2512/lora` | Yes | Yes | $0.035/MP [P17] | $0.0275–$0.035 |
| `fal-ai/qwen-image-2512` | No | Yes | $0.02/MP | $0.020 |

So the current reference endpoint already takes LoRAs at no stated surcharge. A page-side LoRA needs the separate `/lora` edit endpoint, which `REFERENCE_FIELD` does not list today, and costs 17% more per MP.

### Fake pixel art and clean-up

The problem, as named by tool authors: diffusion output imitates pixel art without its structure. Pseudo-pixels vary in size, sit off a regular grid, and carry blur, anti-aliasing and soft gradients inside cells [P19]. syn-007's reference shows all three.

Documented clean-up approaches:

| Method | Source | What it does | Detail loss stated | Class |
|---|---|---|---|---|
| Pixelated Image Abstraction (Gerstner et al., NPAR 2012) | [P20] | Jointly solves a low-resolution superpixel mapping and a reduced palette from a high-resolution image. User study and pixel-artist interviews found it beat naive downsample-and-quantise. | Designed to abstract, so small features are merged by intent | Fact (peer-reviewed) |
| Pixel Art Fixer (Retro Diffusion, MIT licence) | [P19] | Three grid detectors vote on cell size (autocorrelation, run-length soft-GCD, self-similarity), then each cell takes a centre-weighted vote over k-means-quantised labels and is coloured from the mean of the original pixels with the winning label. Output is meant to be enlarged with nearest-neighbour only. | "a too-fine grid subdivides losslessly; a too-coarse one destroys detail", so it prefers the finer step. Fails on "cells under about 3 px, or heavy dithering". | Method: fact. Accuracy: vendor claim |
| Pixel Art Fixer benchmark | [P19] | On its own pixel-bench (100 source images, 43 distortions, 4,300 inputs): exact native size 77%, within 1 px 84%, grid alignment 94%, mean CIELAB difference ~1.6 when the size is right. PixelDetector 4% exact, naive baseline 2%. | n/a | Vendor claim. Measured by the tool's owner on synthetic damage of real pixel art, not on diffusion output. |
| PixelDetector (Astropulse, MIT) | [P21] | Downscales and restores resized or JPEG-damaged pixel art; `--max` palette colours default 128. Algorithm not documented in the README. | Not stated | Fact (README) |
| Naive nearest-neighbour or fixed-integer downscale | [P19] | Assumes one global integer cell from origin 0. | Slices through cells when the grid drifts. | Tool author's claim |
| Downscale by a fixed factor (LoRA cards) | [P10, P12] | Authors tell users to divide by 8 or 4 to reach "pixel-perfect" output. | Not stated | Fact (card instruction) |

**Does clean-up destroy small identity details?** No source measures identity-detail survival. What follows is inference:

- syn-007's reference has ~20 px cells on a 1024-wide image, about a 51×38 native grid. Halo's eyes are about 2×3 cells. A feature smaller than one cell (an eyebrow, a freckle, a thin spoon handle) has nothing to survive in.
- Centre-weighted voting keeps a feature only when it covers most of a cell. Thin outlines and one-cell marks are the parts most likely to flip.
- Palette quantisation can merge two close colours (two purples, skin and a tan shirt). Pixel Art Fixer limits this by using the quantised palette only for placement, not output colour [P19]. A plain k-means palette swap does not.
- The reference and its page do not share a cell size (20 px against 4–10 px in syn-007). Clean-up snaps each to its own grid, so it cannot make them match. It removes blur. It does not add consistency.
- Clean-up is free offline compute and can be tested on the trial's outputs without a second generation.

### Pixel art and identity judging

No paper was found that measures VLM accuracy on stylised pixel-art characters, or same-character judgement across pixel-art images. The closest published evidence measures pixelation and low resolution as corruption of photographs:

| Paper | Finding | Relevance |
|---|---|---|
| Analysing the Robustness of VLMs to Common Corruptions, arXiv:2504.13690 (2025-04-18) [P22] | LLaVA-1.5 only. ImageNet-C pixelate (downsample then upsample) at severities 1→5: TextVQA 51%→45%, GQA about 51%→45%. "pixelation equally degrades the visual quality of object features and textual elements." | One old model. Pixelation of photos, not art drawn on a grid. |
| LR0.FM, arXiv:2502.03950 (ICLR 2025) [P23] | 10 foundation models, 66 backbones, 15 datasets: zero-shot classification declines as resolution falls; larger models are more robust; models fine-tuned at higher resolution are less robust to low resolution. | Classification, not pairwise identity. |
| VLM-RobustBench, arXiv:2603.06148 (2026-03-06) [P24] | Qwen, InternVL, Molmo and Gemma families. Largest drops come from resampling and geometric distortions ("upsample", elastic), up to 34 pp on MMBench. | Includes the two judge families. Resampling artefacts matter, which bears on the resize below. |
| The Last Visible Pixel (FineSightBench), arXiv:2606.07861 (2026-06-05) [P25] | Recognition of letters, shapes and objects at 4–48 px: "perception saturates around 12px", reasoning stays weak at larger sizes. | A rough floor for how small a feature can be and still be seen. |

How the two judges see a 1024×768 page (fact):

- **Production judge, Gemma-3-27B**: the encoder "takes as input square images resized to 896 x 896", and the report says this causes "small objects disappearing" for non-square images unless Pan & Scan is used [P26]. 1024×768 is non-square.
- **Objective 4 judge, Qwen3.5-9B fine-tune**: `backend/finetune/image_preprocessing.py:47` shrinks any image above `image_max_pixels=262144` with Pillow's default filter. For RGB input that is bicubic (Pillow 12.3.0, read from source). 1024×768 becomes 591×443, a factor of 0.577. A 20 px pseudo-pixel becomes 11.5 px, so cell edges no longer land on whole pixels and are blurred. A palette-mode (`P`) PNG would instead be resized with nearest-neighbour, because Pillow forces it for modes `1` and `P`.

Inference on #98's two hypotheses:

1. **"Easier to keep consistent"**: plausible for coarse traits. Fewer cells and fewer colours leave the generator fewer ways to vary hair shape or clothing. No source measures it.
2. **"Harder to judge"**: supported indirectly. At ~20 px cells, eye shape, face shape and small markings are a few cells each. After the Qwen3.5 resize they are about 12 px wide, which is the FineSightBench saturation point. Pages can look consistent because there is less left to disagree about. The judge and a person would then accept real drift, which shows up as false accepts, not as a lower failure rate.
3. **Out of distribution**: the Objective 4 test set has 5 gouache, 5 cel and 5 cut_paper stories (#98). The fine-tuned judge has never seen pixel art in training or evaluation. syn-007 suggests the prompted judge reads pixelation as a style difference.

### Prompt wording

No official Qwen guidance on pixel-art prompting was found. The LoRA cards give only trigger words ("Pixel Art") [P7, P8]. "16-bit" and "8-bit" appear only as LoRA marketing [P8]. Qwen's own rewriter associates "pixel art style" with text fonts [P5].

Candidate fragment in the house shape (inference, untested):

```
pixel art storybook illustration, large square pixels on one regular grid, flat colour in every pixel, limited palette, crisp dark one-pixel outlines, simple readable shapes, no gradients, no dithering, no anti-aliasing, no glossy highlights
```

Why each choice:

- **"pixel art storybook illustration"** leads with the medium, like the other three presets. It avoids "sprite", "video game", "8-bit" and "16-bit". syn-007 shows "sprite" alone pulled in a game look. Game vocabulary plausibly also pulls in score counters, health bars and menus, which are lettering the negative prompt only partly covers.
- **"one regular grid", "flat colour in every pixel"** state the property that fake pixel art lacks. Whether Qwen honours them is unknown.
- **No pixel count** ("64 pixels wide"). No source shows Qwen-Image follows a resolution instruction, and the right cell size is a trial variable, not a constant.
- **`no dithering`** for the same reason `comic`'s halftone was scoped off the character: density-based shading makes one fill read as two colours to `wrong_colour`, and the text check may read it as marks.
- **`no` clauses name only rendering words.** Each one also filters descriptions. `no gradients` and `no glossy highlights` already exist in other presets. `no anti-aliasing` and `no dithering` will not collide with ordinary description words. Avoid `no blur` (strips "blurry") and `no smooth ...` (strips "smooth").

**NEGATIVE_PROMPT conflicts**: none. No current term (`text, letters, words, writing, signage, labels, captions, subtitles, watermark, signature, speech bubbles, speech balloons, comic panels, 3d render, photorealistic`) appears in the candidate, so `test_no_preset_utters_a_term_the_negative_prompt_suppresses` would pass. "3d render" pushes away from voxel art, which is wanted. Not covered: game interface elements (HUD, health bar, score). Do not add them before the trial counts how often they appear. Adding terms changes every preset, because the negative prompt is global.

## Unknown or could not verify

- Whether Qwen-Image or Qwen-Image-Edit-2511 can hold one integer grid across a reference and its pages. No vendor sample, no paper.
- Whether a Qwen-Image-2512 LoRA loads on the August `qwen-image` checkpoint the pipeline uses. No card states compatibility.
- Whether fal charges more on `fal-ai/qwen-image` when `loras` is set, and whether `/lora` endpoints round up or bill input images.
- Whether fal's `loras.path` accepts a Hugging Face repo id or only a direct weights URL.
- Training-image provenance for every LoRA above. None states a source, and one is trained on AI-generated images.
- Any measurement of identity-detail survival through grid snapping or palette reduction.
- Any VLM benchmark on stylised pixel art or on same-character judgement across pixel art.

## Implications for the C3-13 trial

Run after Objective 4 is reported and spend is approved. Not before: a pixel preset changes the product the evaluation describes.

### Design

1. **Arms**: `cel` (as #98 proposes) against a prompt-only pixel fragment. Same stories, same seeds where fal accepts one, same code commit. Prompt-only keeps one variable: no LoRA, no new endpoint, no `REFERENCE_FIELD` change. Treat LoRAs as a second trial only if the prompt-only arm fails on style adherence, since no edit-side pixel-style LoRA exists.
2. **Stories**: 6 synthetic stories, not from the Objective 4 test set. Pick ones whose characters carry small, checkable details: a marking, an accessory, a stated part count, a colour pair. At least two should have two referenced characters. 6 × 5 scenes ≈ 30 pages per arm.
3. **Offline third arm, no generation cost**: run the pixel arm's references and pages through a grid detector (Pixel Art Fixer, MIT) and re-score them.
4. **Fix before generating**: the fragment text, the detail checklist per character, the counting rule for lettering and game-interface marks, and the scoring rules below. Decide the `code_commit` pin first; the campaign note says a mid-run fix breaks provenance.

### Measures

| Measure | How | Why |
|---|---|---|
| Style adherence | Share of references and pages a person calls pixel art; detected cell size and colour count per image; whether a page's cell size matches its reference's | syn-007 showed mixed and drifting grids |
| Reference fidelity to description | Human checklist of each description attribute on each canonical reference, per arm | Halo lost "see-through" and gained eyes |
| Page-to-reference consistency | Human same/different labels under the labelling rulebook, by the current C3 labelling arrangement. Style cannot be hidden, so record that labellers knew the arm. | #98's main claim |
| Small-detail survival | Per pre-listed detail: present, absent, or unjudgeable at page scale. Repeat on the clean-up arm. | #98's main risk |
| Judge agreement | Production judge verdicts against the human labels per arm; report false accepts and false rejects separately, plus `style_match` and `wrong_colour` rates | Pixel art may hide drift as false accepts |
| Lettering and interface marks | Count with the fixed rule | Game vocabulary may summon UI text |
| Cost and retries | fal balance deltas and attempts per scene per arm | A style that fails the judge more buys more retries |

Decide on these numbers, not on "looks better", as #98 already states.

### Cost estimate

Using the synthetic-corpus mix from the [image-model screen](image-model-research-2026-10.md#implications-for-the-c3-10-screen): 7.6 text-to-image calls and 11.2 edit calls per book (18.8 total), output-only billing.

| Arm | Text-to-image | Edit | Per book | 6 books |
|---|---|---|---|---|
| `cel` baseline | qwen-image $0.020 | edit-2511 $0.0236–$0.030 | $0.42–$0.49 | $2.50–$2.93 |
| Pixel, prompt-only | same | same | $0.42–$0.49 | $2.50–$2.93 |
| Clean-up arm | offline | offline | $0 | $0 |
| Later LoRA arm (if run) | qwen-image + LoRA $0.020 (surcharge unknown) | edit-2511/lora $0.0275–$0.035 | $0.46–$0.54 | $2.76–$3.26 |

Prompt-only trial: **about $5.00–$5.90** for 12 books. Worst case at `IMAGE_BUDGET` 55 calls × $0.030 = $1.65 per book is $19.80. A cap of about $8 covers the expected case plus retries; size it after reading the fal dashboard on the first book. Judge calls on OpenRouter are not included.

## Sources

All checked 2026-10-06.

- [P1] Qwen-Image model card — https://huggingface.co/Qwen/Qwen-Image
- [P2] Qwen-Image Technical Report, arXiv:2508.02324 (searched for "pixel", "8-bit", "16-bit", "retro") — https://arxiv.org/html/2508.02324v1
- [P3] Qwen-Image-Edit model card — https://huggingface.co/Qwen/Qwen-Image-Edit
- [P4] Qwen-Image-Edit-2511 model card — https://huggingface.co/Qwen/Qwen-Image-Edit-2511
- [P5] Qwen-Image repository, 2512 prompt rewriter — https://github.com/QwenLM/Qwen-Image/blob/main/src/examples/tools/prompt_utils_2512.py
- [P6] Hugging Face model search API, `search=pixel` with `base_model:adapter:` filters for Qwen-Image, Qwen-Image-2512, Qwen-Image-Edit-2509 and Qwen-Image-Edit-2511 — https://huggingface.co/api/models?search=pixel&filter=base_model:adapter:Qwen/Qwen-Image
- [P7] prithivMLmods/Qwen-Image-2512-Pixel-Art-LoRA — https://huggingface.co/prithivMLmods/Qwen-Image-2512-Pixel-Art-LoRA
- [P8] artificialguybr/PIXELART-REDMOND-QWENIMAGE — https://huggingface.co/artificialguybr/PIXELART-REDMOND-QWENIMAGE
- [P9] JOYUNGI/nwpxstyle-qwen-image-lora — https://huggingface.co/JOYUNGI/nwpxstyle-qwen-image-lora
- [P10] svntax-dev/pixel_portrait_lora_v1-lora — https://huggingface.co/svntax-dev/pixel_portrait_lora_v1-lora
- [P11] damnthatai/Game_Boy_Camera_Pixel_Style_Qwen — https://huggingface.co/damnthatai/Game_Boy_Camera_Pixel_Style_Qwen
- [P12] svntax-dev/pixel_spritesheet_4walk_combat_32x48_v1 — https://huggingface.co/svntax-dev/pixel_spritesheet_4walk_combat_32x48_v1
- [P13] PixelSmile/PixelSmile — https://huggingface.co/PixelSmile/PixelSmile
- [P14] fal model page and OpenAPI, qwen-image — https://fal.ai/models/fal-ai/qwen-image and https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/qwen-image
- [P15] fal model page and OpenAPI, qwen-image-edit-2511 — https://fal.ai/models/fal-ai/qwen-image-edit-2511 and https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/qwen-image-edit-2511
- [P16] fal model page and OpenAPI, qwen-image-edit-2511/lora — https://fal.ai/models/fal-ai/qwen-image-edit-2511/lora and https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/qwen-image-edit-2511/lora
- [P17] fal model page and OpenAPI, qwen-image-2512/lora — https://fal.ai/models/fal-ai/qwen-image-2512/lora and https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/qwen-image-2512/lora
- [P18] fal OpenAPI, qwen-image-2512 — https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/qwen-image-2512
- [P19] Retro Diffusion, Pixel Art Fixer README (MIT) — https://github.com/Retro-Diffusion/pixel-art-fixer
- [P20] Gerstner, DeCarlo, Alexa, Finkelstein, Gingold, Nealen, "Pixelated Image Abstraction", NPAR 2012 — https://gfx.cs.princeton.edu/pubs/Gerstner_2012_PIA/index.php
- [P21] Astropulse, pixeldetector README (MIT) — https://github.com/Astropulse/pixeldetector
- [P22] Analysing the Robustness of Vision-Language-Models to Common Corruptions, arXiv:2504.13690 — https://arxiv.org/html/2504.13690v1
- [P23] LR0.FM: Low-Res Benchmark and Improving Robustness for Zero-Shot Classification in Foundation Models, arXiv:2502.03950 — https://arxiv.org/abs/2502.03950
- [P24] VLM-RobustBench, arXiv:2603.06148 — https://arxiv.org/abs/2603.06148
- [P25] The Last Visible Pixel: Probing Fine-Scale Perception in Vision-Language Models, arXiv:2606.07861 — https://arxiv.org/abs/2606.07861
- [P26] Gemma 3 Technical Report, arXiv:2503.19786 (vision encoder and Pan & Scan section) — https://arxiv.org/html/2503.19786v1

Local evidence inspected: `backend/app/config.py`, `backend/app/main.py`, `backend/providers.py`, `backend/pipeline/prompt_optimizer.py`, `backend/tests/test_config.py`, `backend/finetune/image_preprocessing.py`, `backend/finetune/train.py`, `data/judge/corpus/runs/syn-007/memory.json`, `data/judge/corpus/ref/syn-007--restart-1f310b863b844f9cad101d50fa80062b_ref-c1-1.png`, `data/judge/corpus/scene/syn-007--restart-1f310b863b844f9cad101d50fa80062b_s4-3.png`, `docs/capstone/pipeline-gate-audit-2026-09.md`, GitHub issue #98. No code, config, label or corpus file changed.
