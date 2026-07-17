# Phase 0.5 — Probe Results

**Status:** ⬜ not run · **Owner:** build track · **Companion:** ROADMAP Phase 0.5

This file is **written before the probes run.** Each section states what the probe tests, what
counts as a pass, and what to do on each way it can fail — *then* leaves a blank for the number.

Pre-committing the shape is the same discipline as pre-registering the analysis plan
(RESEARCH_PROTOCOL §13): you cannot retro-fit a narrative onto a number you have already seen.

Fill in `Result` and `Decision` immediately after each run. Do not edit the `Pass condition`
or `Branches` rows after seeing a number — if one turns out wrong, say so in `Notes` and leave
the original visible.

> **Revised 2026-07-13, before any probe ran** (round-2 review, `docs/capstone/review_round2_2026-07-12.md`):
> probe 1 scaled from 5 to 10 scenes per character (n = 20 per condition) and its tie rule recorded;
> probe 3 gains a raw field-order condition (Pydantic cannot see order); probe 4 probes the
> two-classifier **union** over an expanded ~26-case set, both directions.

---

## Probe 1 — Non-human character consistency ⬜

**THE KILL CRITERION.** Everything downstream is contingent on this.

Two characters: **Pip**, a fox cub (real animal, canonical silhouette, heavily represented in
illustration training data — the *easy* case) and **Quill**, an invented three-eyed lizard-bird
(the case ADR-001 is actually afraid of). **Ten scenes each** (n = 20 items per condition),
generated twice: conditioned on the canonical reference (**ON**) and from the description alone
(**OFF**). Shuffled behind opaque filenames. Every team member scores blind. Nobody opens `key.csv`.

Scoring rules, recorded before any number exists: per-item verdict is the **rater majority; a tie
scores as not-identity** (conservative). The team scorers are not naive raters — they designed the
mechanism and can often infer condition from pose/composition echo — so the κ and effect size this
probe yields are treated as **optimistic bounds** when sizing the Tier-1 load (R2), not as unbiased
estimates.

```
uv run python -m spikes.phase_05 consistency
# ...all four raters fill spikes/out/scores.csv, blind...
uv run python -m spikes.phase_05 tally
```

**Pass condition — both must hold, on the `gouache` preset only:**

| | Threshold |
|---|---|
| Absolute | pipeline-ON identity retained on **≥ 80%** of items |
| Separation | pipeline-ON − pipeline-OFF **≥ 30 points** |

**Branches:**

| Outcome | Meaning | Do this |
|---|---|---|
| Both hold | The reference does the work. ADR-007's mechanism is real. | **Phase 1 opens.** |
| Absolute holds, separation fails | The model draws a good fox with or without the reference. **This is a fail** — the reference is not doing the work, ADR-007 has no measurable effect on this substrate, and **RQ2 has no story.** | Escalate to **FLUX.1 Kontext [dev]** (non-commercial, permitted — ADR-015). Re-run. |
| Both fail | The substrate cannot hold identity. | **Stop and surface it.** A Phase-0.5 finding, not a Phase-3 catastrophe. |
| Pip passes, Quill fails | **Not a defeat.** It maps the product's boundary and it is the most interesting sentence in the paper. | Record it. Decide scope deliberately. Do not paper over it. |

**Result:**

| | ON | OFF | ON − OFF | n |
|---|---|---|---|---|
| Pip | | | | |
| Quill | | | | |
| **Combined (gates)** | | | | |

Inter-rater agreement (κ): ______  ← this is also a dress rehearsal of the Phase 3 instrument (ADR-008).

**Decision:** _____________________________________________

**Notes:**

### Secondary arm — style presets (ADR-022, **does not gate**)

Quill through all three presets, ON only. Second rater column: *"does this read as a
hand-illustrated children's book, or as AI art?"*

**Prediction, recorded before the run.** From ADR-022's tension — *texture defeats the AI look, but line
and silhouette are what hold identity.* `ink` has the strongest line, so it should score highest on identity
and lowest on handmade. `watercolour` has the softest edges, so it should invert: highest handmade, and it is
**the preset most at risk of losing Quill**, because bleeding edges dissolve a silhouette. `gouache` sits
between them; that is why it is `PRIMARY`. A result that contradicts this is a finding about the substrate,
not a scoring error — record it rather than explaining it away.

| Preset | identity (ON) | reads-as-handmade | Verdict |
|---|---|---|---|
| `gouache` | | | |
| `ink` | | | |
| `watercolour` | | | |

Neither number gates Phase 1. But **a preset that cannot hold an invented chimera, or that reads
as generic AI art, is re-authored or dropped before a child sees it** — that is the binding
acceptance condition on ADR-022.

**Decision:** _____________________________________________

---

## Probe 2 — Seed determinism ⬜

Same seed twice, on **both** `edit_image` and `text_to_image`. The ablation seed-matches
pipeline-ON against pipeline-OFF, so both endpoints must reproduce or the comparison is unfair.
Diff the bytes. Replicate has an open, unresolved bug (#334) where seeds are ignored under its
fast path — **verify empirically, do not trust the docs.**

```
uv run python -m spikes.phase_05 seed
```

**Pass condition:** byte-identical output on both endpoints.

**Does not gate Phase 1.**

**Branches:**

| Outcome | Do this |
|---|---|
| Both reproduce | Record against CC-7. Proceed. |
| Either fails | Record against **CC-7**, then choose: drop the reproducibility claim from RQ2's method, or change provider. Do not silently keep the claim. |

**Result:** `edit_image` ______ · `text_to_image` ______

**Decision:** _____________________________________________

---

## Probe 3 — Structured output, in the shape each model is actually called with ⬜

The text model gets text. **The judge gets two images** — because that is the only way the judge
is ever invoked, and OpenRouter's structured-output support is per `(model, provider)` *and* per
modality. A text-only probe of the judge passes while the judge is broken. (This exact bug was
caught and fixed; see `tasks/lessons.md`.)

Also confirms `provider.require_parameters: true` is honored.

```
uv run python -m spikes.phase_05 structured
```

**Pass condition:** strict `json_schema` → Pydantic round-trip succeeds for the text model **and**
for the judge **called with two images**, **and** the raw response emits `differences_observed`
before `same_character` — Pydantic validation is order-insensitive, so the reason-then-score
property (ADR-004) is asserted on the raw text. As of 2026-07-13 `providers._chat` enforces this
order on every structured call; a provider that emits out of schema order now fails loudly instead
of silently voiding the mitigation.

**Does not gate Phase 1** — but Phase 1's `consistency_check` node cannot be written without it.

**Branches:**

| Outcome | Do this |
|---|---|
| Both pass | Proceed. |
| Judge fails on two images | The judge model or provider does not support structured multimodal output. Try another provider for the same model before changing models. Record it. |

**Result:** text ______ · judge (2 images) ______ · `require_parameters` honored ______

**Decision:** _____________________________________________

---

## Probe 4 — Filipino / Taglish moderation ⬜

**Release gate for Phase 2, not Phase 1.** You may build Phase 1 with this still red.

The respondents are Filipino children, the open image model ships **no built-in safety filter**,
and the proprietary backstop is gone (ADR-011 revision b). Nobody has published Llama Guard's
Filipino performance. Run the gate over harmful **and** benign Filipino/Taglish cases and check
**both directions.**

ADR-011's gate is **two independent classifiers — either one flagging fails the content** — so the
probe scores the **union**: harmful must be caught by at least one model, benign by neither. The
~26-case set spans threats, self-harm, bullying, dangerous instructions, abuse disclosure, and
hate (must flag) vs. mild peril, folklore horror, in-story death, and **fictional Filipino names**
(must not flag — the R8 false-positive direction).

⚠️ **Verified 2026-07-13 against the live OpenRouter catalog: neither Qwen3Guard-Gen nor Granite
Guardian is routable there** (only `meta-llama/llama-guard-4-12b` and `openai/gpt-oss-safeguard-20b`
are). This is the pre-declared "routing error is also a finding" branch arriving early: ADR-011's
pair must run on the worker, or the backstop needs an ADR amendment. `moderation_backstop_model`
stays unset until that decision is made.

```
uv run python -m spikes.phase_05 moderation
```

**Pass condition:** no MISS in either direction.

**Branches:**

| Outcome | Meaning | Do this |
|---|---|---|
| No misses | Gate is sound. | Phase 2 may ship. |
| Miss on a harmful case | **A child-safety hole.** | Blocks Phase 2. Add a backstop model or a rule layer. Re-run. |
| Miss on a benign case | Dead-ends a child's dragon fight. Mild peril is the *expected* case. | Blocks Phase 2. Retune thresholds; do not ship a gate that punishes normal children's writing. |
| Routing error | The gate cannot run where it was placed. | **This is also a finding** — it means the gate runs on the worker, not the API process. Record it. |

**Result:** harmful recall ______ · benign false-positive rate ______

**Decision:** _____________________________________________

---

## Exit

Phase 0.5 is done when every section above has a `Result` and a `Decision`, and **one** of:

- a green light for Qwen-Image-Edit, **or**
- a recorded **ADR amendment** naming the fallback that passed.

Then, and only then, update `tasks/todo.md` and open Phase 1.
