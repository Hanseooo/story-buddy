# Task Log

Updated 2026-07-10. Phase 0 done. Everything below is contingent on Phase 0.5.

## Active

### NOW — Phase 0.5 (blocks everything)

The code half is committed. **The probes are the point, and they have not run.**
They need `OPENROUTER_API_KEY` + `FAL_KEY`, and probe 1 is human-scored.

- [ ] `uv run python -m spikes.phase_05 consistency` → verify: ~22 images land in `spikes/out/`, ~$0.80
- [ ] All four team members score `spikes/out/scores.csv` **blind**. Nobody opens `key.csv`.
- [ ] `uv run python -m spikes.phase_05 tally` → verify: **the kill criterion.**
      Pass needs *both*: ON ≥ 80% identity retained, **and** ON − OFF ≥ 30 points.
      Absolute-but-no-separation is a fail — the reference isn't doing the work and RQ2 has no story.
- [ ] `uv run python -m spikes.phase_05 seed` → verify: PASS on **both** endpoints (CC-7)
- [ ] `uv run python -m spikes.phase_05 structured` → verify: judge PASSes **with two images**
- [ ] `uv run python -m spikes.phase_05 moderation` → verify: no MISS in either direction.
      **Release gate for Phase 2.**
- [ ] One page written per probe. Green-light Qwen-Image-Edit, or record an ADR amendment naming the fallback.

**ADR-022 accepted — do these two before running probe 1, or you run it twice:**

- [ ] **Author the three style fragments.** Flat gouache · bold ink + cel shading · watercolour with ink line.
      Name the *medium and its physical artifacts* (paper grain, brush edges, flat fills, limited palette).
      Never "beautiful", "8k", "highly detailed". No photoreal, no 3D render.
- [ ] **Extend `spikes/phase_05.py`:** secondary arm runs Quill through all three presets (~20 images, ~$0.80),
      and `scores.csv` gains a second rater column — *"hand-illustrated children's book, or AI art?"*
      **Neither gates.** The kill criterion stays on identity.

**If Pip (fox) passes and Quill (invented chimera) fails:** that is a finding, not a defeat. It maps the
product's boundary. Record it, decide scope, don't paper over it.

### NOW — research track (parallel; does not wait for the spike)

- [ ] **File Ethics Stage 1 (story donation).** The long pole. RESEARCH_PROTOCOL §9.
- [ ] Stage-1 consent form **must** state donated stories may be used to build and evaluate an AI model.
      **Draft language is written for you — RESEARCH_PROTOCOL §9.** Paste it in, adapt to the board's
      template. No retroactive fix exists: collect first and you re-consent everyone or delete the data.
- [ ] Start participant outreach. Private school or learning centre first; a public school needs an SDO permit.
- [ ] **Corpus target is 50 stories; ask for 60–70.** Set by the fine-tune's 33/5/12 character-disjoint
      split, not by the ablation. Characters are statistical power for RQ6's *secondary* endpoints — the
      Gemma comparison and the non-human slice, where the contribution lives — and the corpus is closed by
      Phase 2.5. **Unfixable later.** RESEARCH_PROTOCOL §8.
- [ ] One researcher, one day: survey what public child-narrative corpora actually exist. Most candidates
      turn out to be L2-learner essays or published books. This is the corpus insurance.
- [ ] **Write and timestamp the pre-registered analysis plan before a single label is collected.**
      RQ2 + RQ6 success criteria, the primary endpoint, δ = 3, the claim ladder. ADR-018 amendment (a).
      This is the only thing separating a pre-declared ladder from a moved goalpost.
- [ ] Show the adviser the claim ladder **before** results exist. RQ6's gate is now "beats the un-fine-tuned
      base" — near-certain, and the standard fine-tuning ablation. Get that agreed in writing now, because
      agreeing to it after seeing numbers is worthless.

### NEXT — Phase 1

- [ ] `story-memory-contract` spec, then the schema → verify: freezes MASTER_SPEC §3; Pydantic round-trips.
- [ ] Design the **failure-reason taxonomy** here (`judge-finetune.md` §4). Shared by the regeneration
      controller and the Phase-2.5 annotators. Extending it later invalidates every collected label.
- [ ] Nodes: analyzer → segmentation → char_bible → prompt_optimizer → image_generator →
      consistency_check (prompted Gemma via `providers.judge()`) → regenerate

### LATER

- **Phase 2** — moderation stack, **Filipino PII recognizers**, classroom auth (ADR-017), sharing +
  reflections (ADR-021), Story Map, Kokoro narration (ADR-020), export, teacher gate.
  **Check worker RAM at the start of this phase, not the end.**
- **Phase 2.5** — judge fine-tune. **Read `docs/specs/judge-finetune.md` §0 first — it is the ten-step
  order of operations.** The product ships with the *prompted* judge; this phase swaps one part.
  Blocked on: Ethics Stage 1 → corpus → a Phase 1 run over it → one labelling weekend.
  **Do not label before Phase 0.5 passes.** Nothing to download; the dataset is manufactured (§5).
- **Phase 3** — ablation, Tier-1 harness + RQ5 comprehension instrument, Tier-2, metrics export.

---

## Completed

### 2026-07-10 — direction revision (classroom setting, peer sharing, judge fine-tune)

**Code.** `providers.py` gained `judge()` — a multimodal path it did not have, without which Phase 1's
`consistency_check` could not have been written. The Phase 0.5 spike gained a fourth probe (Filipino/
Taglish moderation) and two fixes. 19 tests green (was 17); ruff clean.

**Docs.** Five new ADRs (017 classroom setting · 018 judge fine-tune · 019 vLLM serving · 020 Kokoro ·
021 sharing), five amended (004, 008, 009, 011, 015), one superseded-but-retained (016). PRD → v2.2.
ROADMAP rewritten with a de-scope ladder and a two-stage ethics track. Two new docs:
`docs/product/RESEARCH_PROTOCOL.md` and `docs/specs/judge-finetune.md`.

**Three things the revision surfaced that were in no document:**

1. **Tier 1 was silently blocked on Tier 2.** The corpus is real child writing; those children are the
   Tier-2 participants. ADR-008's insurance policy did not actually exist. Fixed by splitting the ethics
   submission (Stage 1 donation / Stage 2 system use).
2. **Presidio leaks Filipino PII by default** — on exactly the case ADR-011 calls "the expected case."
3. **Probe 3 tested the judge with a text-only call.** It would have passed while the judge was broken.
