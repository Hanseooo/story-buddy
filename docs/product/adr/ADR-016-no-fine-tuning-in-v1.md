# ADR-016 — No fine-tuning in v1

**Status:** ⚠️ **Superseded by ADR-018 (2026-07-10b).** An external requirement now mandates that the
project fine-tune a model. **This ADR is retained, not deleted, because its reasoning was correct and
is now load-bearing in the opposite direction:** it eliminates identity and style as fine-tuning
targets, which is precisely the argument for why the *judge* is the right one. Read ADR-018 with this
one open. The trigger conditions and the dataset-sourcing analysis below remain live.

**Context:** Moving to open weights (ADR-015) raised the question of whether the system must now
fine-tune a model. There are exactly two candidate targets: **character identity** and **art style**.
Neither has been requested; both are commonly assumed to be necessary when leaving a proprietary
image model. That assumption is what this ADR exists to settle.

**Decision:** **No fine-tuning in v1.** Character identity comes from training-free multi-reference
conditioning (ADR-001). Art style comes from the fixed style constant carried by the canonical
character reference (ADR-007).

**Rationale:**

- **Identity — blocked by latency, not cost.** A per-character LoRA or DreamBooth run is cheap
  (3–20 images, 30–60 minutes on a ~$0.49/hr rented RTX 4090). But a child *invents* a character at
  write-time: there is no dataset to train on and no 40-minute budget inside a 1–3 minute flow.
  Training-free alternatives that *are* fast (IP-Adapter, InstantID, PuLID) are **face-embedding
  based** and their own documentation calls animal and fantastical characters unstable — precisely
  the case StoryBuddy promises (PRD §1). Reference conditioning via the image model itself has none
  of these problems and is already the mechanism the pipeline is built around.
- **Style — already solved by ADR-007.** A style LoRA buys a *proprietary house style*. v1 requires
  *a* consistent style, and the canonical reference is generated **in** that style, so every scene
  conditioned on it inherits the style for free. Adding a LoRA would add a training artifact, a
  dataset-licensing problem, and a model-version dependency, for no user-visible gain.

**Consequences:** No GPU is needed. No dataset must be sourced or licensed. Phase 1 stays about the
pipeline — which is the contribution — rather than about training infrastructure. Fine-tuning is named
in the paper as Future Work, with the cost and the sourcing constraints already scoped (below).

**Trigger to revisit — reopen this ADR if either condition is met:**

- **(a)** The Phase 0.5 spike or Phase 1 eval shows human-judged character consistency on **non-human**
  characters is unacceptable with reference conditioning alone, **and** the FLUX.1 Kontext [dev]
  fallback (ADR-001) also fails. *Note: even then, a style LoRA is not the fix — identity is the
  failing variable. The correct response is a different base model, not training.*
- **(b)** Style drift across scenes is flagged by expert validators as a top-3 defect in Phase 3.
  *This* is what a style LoRA fixes.

**If reopened, the scoped cost (style LoRA):** 20–60 curated images, ~1000–3000 steps, 1–3 hours on a
rented RTX 4090 (~$0.45–0.49/hr) or A100 (~$1.50/hr), via **ai-toolkit** (Ostris) or **kohya_ss**.
**Roughly $1–10, one-time.** Our 8–16GB GPU **cannot** train Qwen-Image (needs 24–48GB) — rent, don't buy.

*The expensive part is the dataset, not the GPU:*
- **Project Gutenberg** illustrations — US public domain for pre-1929 works only, no illustration index
  (manual book-by-book vetting), and US public-domain status does not clear EU/UK life+70 rules.
- **Smithsonian Open Access** — 2.8M+ CC0 images, the cleanest source. Filter on the explicit CC0 tag.
- **Flickr Commons** — "no known copyright restrictions" is an institutional best-effort statement,
  not a legal guarantee. Accept only explicit CC0/PDM.
- **Synthetic bootstrap** — generate ~1000 images, hand-curate ~100, train on those. Established
  practice, and **not** model collapse: collapse ("model autophagy disorder") requires repeatedly
  training on *unfiltered* self-output. One human-curated round is not that.

**Alternatives:** Per-character LoRA at runtime — rejected on latency, permanently. Style LoRA in v1 —
rejected as speculative (ADR-007 already delivers style consistency; build it only if raters say it
didn't). Fine-tuning as a research contribution — explicitly not requested; the contribution is the
pipeline (PRD §3), and adding a training claim would dilute that focus, not strengthen it.
