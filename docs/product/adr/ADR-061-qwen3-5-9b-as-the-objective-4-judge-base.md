# ADR-061 — Qwen3.5-9B as the amended Objective 4 judge base

**Status:** Accepted (2026-09-30) · amends ADR-018's base-model decision and the Objective 4 preregistration · does not change the production judge or authorize training before qualification

## Context

ADR-018 and the 2026-08-14 preregistration fixed `Qwen/Qwen2.5-VL-7B-Instruct` before study labels existed. Labels, a registered dataset freeze, and a small exploratory Qwen3.5 provider screen now exist. The study owner prefers to fine-tune the newer Qwen3.5-9B base before the October defense. This is a **postregistration model change**, even though the exploratory screen used synthetic training pairs and no held-out performance result is recorded in the project documents.

[Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) is an Apache-2.0 vision-language model. The repository's exact [LLaMA-Factory pin](https://github.com/hiyouga/LLaMA-Factory/blob/7af909522a951e3ad9f022ea6f88b6755257eaa5/src/llamafactory/data/template.py) includes `qwen3_5` and `qwen3_5_nothink` multimodal templates. Neither fact establishes that this project's two-image QLoRA recipe fits on a 24 GB GPU or improves character-identity classification. The [24-pair pilot](../../capstone/pipeline-gate-audit-2026-09.md#c3-09-exploratory-provider-pilot--2026-09-30) measured prompted provider behavior, not the result of fine-tuning.

## Decision

1. Replace **only the Objective 4 fine-tune base** with `Qwen/Qwen3.5-9B` at revision [`c202236235762e1c871ad0ccb60c8ee5ba337b9a`](https://huggingface.co/Qwen/Qwen3.5-9B/commit/c202236235762e1c871ad0ccb60c8ee5ba337b9a). The mandatory zero-shot comparator becomes the same pinned Qwen3.5 revision, with the same two images, prompt, processor settings, response mode, and decoding as the tuned model. The adapter remains the only difference between those two evaluation arms. The original Qwen2.5 plan remains visible in ADR-018 and the preregistration.
2. Keep the registered character-disjoint split and labels, three seeds, validation-only checkpoint selection, one-read held-out policy, `different_character` F1 analysis, clustered uncertainty analysis, non-human slice, and the prompted Gemma-3 product comparator. Keep the registered freeze as the primary dataset; the 16-pair filtered freeze remains exploratory. Do not use held-out data to select a model, processor, prompt, checkpoint, or fallback.
3. Use a recorded direct-answer/non-thinking mode for the strict verdict schema. The supervised `differences_observed` field remains; disabling a freeform thinking stream does not remove the structured rationale target. Pin the preprocessing configuration **before training**.
4. Before a full run, qualify two-image preprocessing and token limits, one actual QLoRA training step with measured peak memory on the intended host, and contract-valid inference from the base and adapter. If qualification fails, stop for a new owner decision; do not silently fall back to Qwen2.5 or change the frozen dataset.
5. This decision does **not** replace the prompted production judge, reference-description judge, safety classifiers, Mistral text model, Qwen reference generator, or Qwen scene editor. C3's text, reference, edit, and gate failures remain separate investigations. A later image-model change introduces a new training/deployment distribution and needs its own measured decision.

## Consequences

- The base-versus-tuned endpoint is **amended after labels existed**, not the unchanged 2026-08-14 registration. The methods and results must disclose this timing, the existing labels, the ten owner-approved AI-assisted audit labels, the 16 exploratory training omissions, and the 24-pair prompted pilot. Broad model-card benchmarks and that pilot cannot be cited as proof of StoryBuddy improvement.
- The existing Qwen2.5 assertions in the training/evaluation code and the operational recipe require an aligned implementation change before qualification or training. The pinned trainer already has Qwen3.5 templates; an upgrade is not assumed necessary.
- The current 16–20 GB estimate concerns the 7B recipe. GPU size, runtime, and serving compatibility for Qwen3.5 must be measured. The existing product gate still decides whether a tuned judge ships; choosing a newer base is no deployment claim.

## Alternatives considered

- **Run the originally registered Qwen2.5 base:** preserves the strongest preregistration claim and the existing qualified recipe, but does not follow the owner's newer-base preference.
- **Run Qwen3.5 only as a separate exploratory study after Qwen2.5:** preserves the original endpoint but adds a second full run and delays the preferred base past the defense schedule.
- **Swap text, image, and judge models together:** rejected because C3 has not isolated those failure stages; it would change the image distribution and several causal inputs at once.

## Dated preregistration amendment

The [2026-09-30 amendment](../PREREGISTRATION_OBJ4.md) supersedes the Qwen2.5 base, revision, zero-shot comparator, and base-versus-tuned endpoint passages while leaving their original wording visible. It discloses the labels, dataset freeze, and synthetic pilot already seen. The eventual primary result is **postregistration amended**, never the unchanged original endpoint.
