# ADR-011 — Moderation & safety stack (four mechanisms)

**Status:** Accepted · **revised 2026-07-10** — open classifiers become primary · **revised 2026-07-10b**
— the proprietary backstop is removed and replaced with an open one · **revised 2026-07-21c** — text
backstop routed to `gpt-oss-safeguard-20b` on OpenRouter (D-1 resolved: the ADR-011b pair is not
routable). Drivers: ADR-015 (hardened), ADR-017.

**Context:** Child users require moderation of input and output; a child narrating real life will include PII; the image model itself may refuse legitimate mild-peril scenes. One provider does not cover all of this.

Three things changed. First, the open-weight mandate (ADR-015) applies to safety classifiers too — they are on the child-safety critical path, and a paper claiming an open stack cannot quietly depend on a closed one. Second: **the open image model ships no built-in safety filter** (ADR-001). Google's filter used to be a silent second line of defense behind SafeSearch. It is gone. The output-image gate is now the *only* thing between a generated image and a child.

Third, and the reason for revision **b**: ADR-015 was hardened to *no proprietary models at all*, which
deletes the `omni-moderation-latest` backstop from both the text and the image path. Taken naively that
leaves the text gate standing alone. It also collides with ADR-017: the respondents are **Filipino
children**, and **nobody has published Llama Guard's Filipino or Taglish performance.** A gate that is
both unbacked and unmeasured in the respondents' language is not a gate.

**Decision:** **Two independent open classifiers per path, from different vendors, trained on different
data. Either signal flagging fails the content.** Independence is the property that matters; "open"
and "proprietary" were never the axis — vendor diversity was, and it is achievable without a closed model.

1. **Input text** — **`meta-llama/llama-guard-4-12b`** (Apache-2.0, **119 languages**), the **0.6B variant on the
   OpenRouter**, as primary, with **`openai/gpt-oss-safeguard-20b`** (Apache-2.0, open *weights* — not
   the OpenAI API) via **OpenRouter** as the independent backstop. meta-llama/llama-guard-4-12b's multilingual coverage
   closes the Filipino/Taglish hole *by construction*; gpt-oss-safeguard's separate vendor, taxonomy, and
   training data provide the independence `omni-moderation` used to.
   **D-1 resolved (2026-07-21):** neither ADR-011b classifier is routable on OpenRouter (verified
   2026-07-13). The primary was always OpenRouter API, so only the backstop needed a home. Running Granite
   Guardian *also* on the worker adds a 2B model to a 2–3 GB RAM budget (§9); routing to gpt-oss-safeguard
   keeps the worker lean and adds **no new privacy surface** — input already leaves to OpenRouter for
   analysis (ADR-002), and the backstop is **one call per story**, not per scene, so its cost is noise.
2. **PII** — **Presidio** redaction on input before storage/captioning/export. **Its default recognizers
   are English/US-centric and will miss Filipino PII**: spaCy NER misses Filipino names, and
   `Barangay`/`Purok`/`Sitio` address structure and `+63 9xx` mobile formats match no built-in pattern.
   *"Ako si Juan dela Cruz, taga Purok 3, Barangay San Isidro"* is the case this ADR calls expected, and
   the stock configuration leaks it. **Custom Filipino recognizers are a Phase-2 deliverable, not a polish item.**
3. **Output images** — on **every** image, **including the canonical reference before the reveal**:
   - **`qwen/qwen3-vl-32b-instruct`** (ViT-base, 86M, Apache-2.0) — a specialist sexual-content gate, runs on the OpenRouter in milliseconds. No new service.
   - **`google/gemma-3-27b-it`** with a safety rubric via OpenRouter — covers violence, gore, and dangerous content, which the NSFW ViT does **not**. Open-weight (Gemma license, not OSI). A separate call with a separate concern — **never the fine-tuned judge** (ADR-004 amendment b).
   - These two are **complementary, not independent** — they cover disjoint categories. True redundancy on the image path is **ShieldGemma 2 (4B)**, and ADR-019's GPU container makes it affordable for the first time (see Alternatives).
4. **Model self-refusal fallback** — soften-and-retry, then a gentle reframe. Unchanged.
5. **The child's donated story is child-authored input**, entered directly by the child into their own account (ADR-017), and routes through mechanisms 1 and 2 unchanged. Who types it does not lower the bar — the text is a child's narrative and carries a child's PII. No new surface.
6. **The classroom gallery is display-only** (ADR-021) — the approved storybook is the only peer-visible artifact. There is no second child-authored text surface; nothing beyond the story's own moderation pass is needed.

Ordering is unchanged and non-negotiable: input gate → char-ref moderation → output moderation.

**Consequences:**
- No unmoderated generated image reaches a child; PII kept out of stored/exported content; scary-but-innocent stories don't dead-end.
- The primary text classifier and the image NSFW ViT are OpenRouter API on the worker; the text backstop is
  a hosted OpenRouter call (one per story). No GPU, and no extra service to stand up for moderation.
- ⚠️ **Both gates are unverified in Filipino and Taglish until the Phase 0.5 moderation probe runs.**
  A miss on a harmful case is a child-safety hole; a miss on a benign case dead-ends a child's dragon
  fight. The probe tests both directions and is a **release gate for Phase 2**, not a curiosity.
- Open image models refuse *less*, so self-refusal (mechanism 4) will fire more rarely while unsafe output is *more* likely. Budget test cases accordingly; do not read "fewer refusals" as "safer."
- The stack is now end-to-end open-weight with zero proprietary dependencies, which is a claim the paper can actually make.

**Alternatives:**
- **Llama Guard 4 12B** — the previous primary. Demoted: Llama Community License (not OSI-approved), English-centric, and beaten by Granite Guardian on GuardBench. Still a usable fallback.
- **ShieldGemma 2 (4B)** — purpose-built image-safety filter, broadest category coverage. Previously rejected because no hosted provider existed and self-hosting a 4B model was a new operational surface. **ADR-019 stands that surface up anyway for the judge**, so ShieldGemma 2 becomes cheap optional hardening on the image path. It must remain *optional*: image moderation may not hard-depend on the GPU container, because the ROADMAP's de-scope ladder allows dropping it.
- **IBM `Granite Guardian`** — the backstop named in ADR-011b. **Not routable on OpenRouter** (verified
  2026-07-13); usable only self-hosted on the worker, which the RAM budget (§9) doesn't favor. Retained as
  a fallback if gpt-oss-safeguard underperforms on Taglish in the Phase 0.5 probe.
- **OpenAI `omni-moderation-latest`** — removed. Proprietary (ADR-015, hardened). Its independence is replaced by gpt-oss-safeguard-20b, not abandoned.
- **Vision SafeSearch** — dropped: proprietary and paid.
- **LlavaGuard** — research license; unusable.
- **Single-classifier moderation** — rejected. Independence is the whole design; one classifier is one bug away from a child seeing something.
