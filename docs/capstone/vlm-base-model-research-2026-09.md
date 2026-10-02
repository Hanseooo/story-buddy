# VLM fine-tuning base selection

Researched 2026-09-30. Scope: choose a trainable consistency-judge base before training, using official documentation and repository configuration. No model calls, additional quality comparisons, or held-out data inspection were performed for this note. The owner subsequently accepted [ADR-061](../product/adr/ADR-061-qwen3-5-9b-as-the-objective-4-judge-base.md) and the dated [Objective 4 amendment](../product/PREREGISTRATION_OBJ4.md); the technical evidence limits below still apply.

## Decision supported by this research

**Inference:** Qwen3.5-9B is a credible replacement candidate with strong published general visual benchmarks. Qwen3-VL-8B-Instruct is a credible alternative with fewer architecture and response-mode changes. Neither is proven better at StoryBuddy character identity classification by the official sources. General benchmarks alone cannot establish the task winner.

**Protocol boundary:** [ADR-018](../product/adr/ADR-018-fine-tune-the-consistency-judge-qwen2-5-vl-7b-qlora.md) and the [2026-08-14 preregistration](../product/PREREGISTRATION_OBJ4.md) fixed Qwen2.5-VL-7B before labels existed. Labels and exploratory VLM predictions now exist. ADR-061 changes that base **after registration** and preserves the original wording in the dated amendment. The base-versus-tuned endpoint must be described as postregistration amended. The [small provider pilot](pipeline-gate-audit-2026-09.md#c3-09-exploratory-provider-pilot--2026-09-30) neither establishes that Qwen3.5 would fine-tune better than Qwen2.5 nor isolates Qwen3.5 from OpenRouter routing effects.

## Verified technical facts

| Base | License | Two-image input | Training support | Migration considerations |
|---|---|---|---|---|
| Qwen2.5-VL-7B-Instruct | Apache-2.0 | Official multi-image example | Original recipe used 4-bit bitsandbytes LoRA and `qwen2_vl` | Original registered base; repository code now uses ADR-061 pins. Qualification remains pending under the [runbook](research_runbook.md#qwen35-host-qualification). |
| Qwen3-VL-8B-Instruct | Apache-2.0 | Official Qwen3-VL repository demonstrates two images in one user message | Pinned LLaMA-Factory source includes `qwen3_vl` and `qwen3_vl_nothink` with its multimodal plugin | New processor/template and image token accounting; official resize granularity changes from 28 to 32 |
| Qwen3.5-9B | Apache-2.0 | Official chat template iterates over image items; pinned trainer uses the Qwen3-VL multimodal plugin | Pinned trainer includes `qwen3_5` and `qwen3_5_nothink`; release explicitly supports Qwen3.5 | Hybrid Gated DeltaNet/attention architecture; thinking is on by default and requires deliberate direct-answer configuration |

Licenses and model descriptions: [Qwen2.5 model card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct), [Qwen3-VL model card](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct), [Qwen3.5 model card](https://huggingface.co/Qwen/Qwen3.5-9B). Multi-image and resize behavior: [Qwen3-VL official repository](https://github.com/QwenLM/Qwen3-VL), [Qwen3.5 official chat template](https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/chat_template.jinja). Training templates: [LLaMA-Factory template source at the repository's exact pin](https://github.com/hiyouga/LLaMA-Factory/blob/7af909522a951e3ad9f022ea6f88b6755257eaa5/src/llamafactory/data/template.py), [multimodal plugin source at the same pin](https://github.com/hiyouga/LLaMA-Factory/blob/7af909522a951e3ad9f022ea6f88b6755257eaa5/src/llamafactory/data/mm_plugin.py), [v0.9.5 release](https://github.com/hiyouga/LLaMA-Factory/releases/tag/v0.9.5).

**Verified distinction:** The newer families already have templates in the exact pinned trainer commit `7af909522a951e3ad9f022ea6f88b6755257eaa5`. Saying that a trainer upgrade is inherently necessary would be incorrect. Template presence and framework QLoRA support establish an available training path, not proof that StoryBuddy's complete recipe runs successfully. [Pinned trainer README](https://github.com/hiyouga/LLaMA-Factory/blob/7af909522a951e3ad9f022ea6f88b6755257eaa5/README.md).

## Hardware and evidence limits

The recipe inspected during this research in `backend/finetune/train_qlora.yaml` set two images through the exported dataset, maximum 262144 pixels per image, cutoff length 2048, batch size 1, gradient checkpointing, rank 16 and 4-bit bitsandbytes quantization. The 16–20 GB estimate was for the original 7B recipe and is not measured evidence for Qwen3.5.

**Inference:** 8B and 9B quantized bases are plausible candidates for a 24 GB GPU, but neither has a verified 24 GB fit for these two-image batches here. Weight size does not include vision activations, optimizer state, adapter gradients or kernel workspaces. Processor token counts and architecture differ. The trainer's generic estimated QLoRA memory table cannot establish two-image VLM training fit. [Pinned trainer hardware estimates](https://github.com/hiyouga/LLaMA-Factory/blob/7af909522a951e3ad9f022ea6f88b6755257eaa5/README.md).

Qwen3.5's official card reports broad visual-understanding improvements and benchmark results including spatial, VQA and hallucination tasks. It does not report StoryBuddy's same-character/different-character task or a controlled post-LoRA result against the registered 7B base. Its strongest benchmark evidence makes it a reasonable selection candidate, not a measured winner for this project. [Official Qwen3.5 results](https://huggingface.co/Qwen/Qwen3.5-9B).

## Minimum migration work after acceptance

ADR-061 pins the selected Hugging Face revision. Align `train.py`'s strict base/template assertions, training YAML, evaluation loader and relevant specifications. Preserve the study's held-out split. Check that both images survive preprocessing and the 2048-token cutoff under the selected direct-answer template, then qualify one actual training step on the intended GPU before the full run. These are compatibility checks, not another quality comparison campaign.

Local evidence inspected for the research: `docs/specs/judge-finetune.md`, `backend/finetune/train_qlora.yaml`, `backend/finetune/train.py`. No training, smoke test or deployment was run as part of this research. For subsequent migration and qualification status, use the [research runbook](research_runbook.md#qwen35-host-qualification).
