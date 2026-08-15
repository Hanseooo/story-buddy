# StoryBuddy — Action Checklist (what to do / confirm)

> **Working tracker — not manuscript.** A flat, scannable list of everything that needs a **decision, a
> confirmation, or a verification** before the capstone is safe. Reasoning and options for each item live in
> `design_decisions_and_risks.md` (R1–R6); this file is just *"what do I do, what does it block, what happens
> if I skip it."* Update the Status column as you go.

**Legend — Type:** 🔍 verify · 🧑‍🏫 confirm with adviser · 🛠️ do it · ⏳ waits on something else.
**Status:** ☐ not started · ◐ in progress · ☑ done.

**Numbering note (2026-07-25).** The manuscript now uses **Objective 1..5**, not RQ1–RQ6 (ADR-008, revised
2026-07-25). Objective 3 = expert validation, Objective 4 = fine-tuned judge classification (precision/
recall/F1), Objective 5 = ISO/IEC 25010. Items below that existed only for the now-dropped reader-
comprehension study (RQ5), the Tier-1/Tier-2 respondent tiers, or the Fun Toolkit are marked retired, per the
same convention already used for B1.

---

## A. Before ANY doc becomes a Word document (citation integrity)

| # | What to do | Blocks / needed for | If ignored | Type | Status |
|---|---|---|---|---|---|
| A1 | Open `arxiv.org/abs/2604.01973` (NearID). If it 404s / isn't NearID, find the real source for the "VLM judges conflate category & identity" claim, or delete the citation. | Related Work; ADR-004's rationale | **Fabricated citation in an IEEE paper** — the most damaging integrity failure possible at defense. | 🔍 | ☐ |
| A2 | Confirm the **"79.6% human agreement"** figure inside the DreamBench++ PDF (`arxiv.org/abs/2406.16855`). Reword if the number isn't there. | ADR-004; model_finetuning.md L7 | A specific quantitative claim a reviewer can check and find wrong. | 🔍 | ☐ |
| A3 | Confirm QLoRA `arXiv:2305.14314` resolves (it does). | Methods citation | Low risk; still confirm. | 🔍 | ☐ |
| A4 | Verify the 3 Related-Work IDs before citing (ConsiStory 2402.03286 · StoryDiffusion 2405.01434 · The Chosen One 2311.10093). | Related Work paragraph | Citing an unverified ID. | 🔍 | ☐ |
| A5 | After A1–A2, apply the corrected gap wording + fixed citations to the **frozen** docs (`docs/product/adr/ADR-001-image-generation-model-qwen-image-edit-open-weight.md` / `docs/product/adr/ADR-004-consistency-via-vlm-as-judge-control-loop-human-ratings.md`, `RESEARCH_PROTOCOL.md`, `ROADMAP.md`) so they match the manuscript. Log ADR edits as a one-line factual-correction changelog. | Consistency between manuscript and authoritative docs | Manuscript and source-of-truth disagree — a project-rule violation and a defense inconsistency. | 🛠️ | ☐ |

---

## B. Confirm with adviser BEFORE the pre-registration is timestamped

*(These get harder to change once data collection starts — lock them first.)*

| # | What to confirm | Blocks / needed for | If ignored | Type | Status |
|---|---|---|---|---|---|
| B1 | ~~R1 — add the 3rd ablation arm~~ **MOOT (2026-07-20)** — the ablation itself is dropped (ADR-008); there's no arm structure left to decide. | — | — | — | ✗ retired |
| B2 | ~~Plot-vs-character co-primary outcome choice~~ **RETIRED (2026-07-25)** — this was the pre-pivot RQ5 reader-recall study's primary-outcome decision. RQ5 does not exist in the manuscript; Objective 3 uses an open-ended interview + content analysis, not a scored recall outcome. | — | — | — | ✗ retired |
| B3 | ~~One reader reads several *different* stories, to improve recall-estimate precision~~ **RETIRED (2026-07-25)** — the reader-recall study (RQ5) this was sizing is dropped entirely; there is no reader pool to design an assignment for. | — | — | — | ✗ retired |
| B4 | **Objective 5 — ISO/IEC 25010** — confirm the required standard + the five applicable characteristics (Functional Suitability, Performance Efficiency, Usability, Reliability, Security), and that the software-quality evaluators are a **separate pool from the Objective 3 expert validators** (already flagged ⚠️ in methodology). | Software-quality evaluation | Wrong instrument or wrong respondent pool administered; not fixable after the fact. | 🧑‍🏫 | ☐ |
| B5 | Confirm your **actual October defense date** and check Ethics Stage 1's "months" fits inside it. Objective 4 (the judge) reports **precision/recall/F1 against human labels**, with an optional secondary comparison to base/prompted baselines (R3; `design_decisions_and_risks.md`). The October deliverable is a pilot run on fixtures, explicitly illustrative; full-corpus results land after Ethics Stage 1 (roadmap §0.8). | The whole Objective 4 track (R3) | You discover in month 4 that the fine-tune can't finish, with no fixture-pilot fallback prepared. | 🧑‍🏫 | ☐ |
| B6 | ~~Image-only comprehension sessions (captions stripped)~~ **RETIRED (2026-07-25)** — the reader-comprehension study (RQ5) this instrument belonged to is dropped entirely; there is no comprehension session left to strip captions from. | — | — | — | ✗ retired |
| B7 | Approve the **pre-registration drafts merged 2026-07-13**: test-set access policy + malformed-output rule (judge-finetune §7.5/§7.1), checkpoint-selection rule (§6.4), DreamBench++ binarization (§7.4), major-character definition (RESEARCH_PROTOCOL §7). | Objective 4 pre-registration integrity | Each is a researcher degree of freedom a reviewer can find. | 🧑‍🏫 | ◐ |
| B8 | **Instrument confirmation** — (1) the **Objective 3 expert-validator panel is now fixed by the manuscript**: the Dean/Professor of the Arts college, one Arts student/intern, one Education student/intern (purposive selection, not a generic 3–5) — confirm names/availability. (2) Confirm the **Objective 5 ISO/IEC 25010 questionnaire's** content-validity threshold (CVI) and the **Table 4 interpretation bands** (4.20–5.00 Excellent · 3.40–4.19 Very Good · 2.60–3.39 Good · 1.80–2.59 Fair · 1.00–1.79 Poor). Basis: `research_instruments.md` → *Content and face validity*; methodology §6.4. | Both instruments being reportable as valid | You report an expert-validation or ISO-25010 result from an instrument/panel never confirmed against the manuscript's spec. | 🧑‍🏫 | ☐ |
| B9 | **Evaluator N + pilot group** — confirm the target count of ISO-25010 evaluators (IT practitioners + teachers) and reserve a **separate pilot group held out from the reported sample**, so Cronbach's α (floor ≥ 0.70) is stable and pilot/reported samples don't overlap. Basis: `research_instruments.md` → *Reliability pilot*; methodology §6.4. | Reportable internal-consistency figure for Objective 5 | α computed on a tiny or overlapping sample is unstable/invalid; not fixable after administration. | 🧑‍🏫 | ☐ |

---

## C. Do now — independent of everything else (critical path)

| # | What to do | Blocks / needed for | If ignored | Type | Status |
|---|---|---|---|---|---|
| C1 | **Submit Ethics Stage 1** (story donation). Include the one sentence: *donated stories may be used to build and evaluate an AI model* — **plus** the withdrawal-cutoff clause **and** the bundled adult-participant protocol (drafts merged into RESEARCH_PROTOCOL §9, 2026-07-13). | Corpus → picture-book generation (Objective 2) → Objective 3 expert-validation stimuli and Objective 4 judge training data | The single longest pole. Every result waits on it; the consent clauses have **no retroactive fix**; without the adult-participant protocol, the expert-validation and judge-annotation tracks each have an unfiled dependency. | 🛠️ | ☐ |
| C2 | Adopt the **value-proposition framing** (`value_proposition.md`) in the Intro/Discussion; keep refusing creativity (Trap A) and picture-superiority/comprehension claims (Trap B). | The "so what?" defense question | You drift into an unmeasurable or already-known claim and lose the "why this matters" exchange. | 🛠️ | ☑ (doc written; adopt in manuscript) |
| C3 | Present **R2–R6 as known risks** at the proposal defense (R1 is moot post-pivot) — do not try to solve them first. | Proposal defense posture | Looks like you missed weaknesses the panel then "discovers." | 🛠️ | ☐ |
| C4 | **Stand up CI** (pytest + vitest workflows in `.github/`; add the manifest split-disjointness guard when it exists). | "CI must stay green" (CLAUDE.md §3), the char-leakage guard (judge-finetune §10) | The testing bright line has no fence — both rules are currently aspirations; `.github/` does not exist. | 🛠️ | ☐ |
| C5 | **Surface the moderation-routing finding to the ADR process**: verified 2026-07-13 that neither meta-llama/llama-guard-3-8b nor Granite Guardian is routable on OpenRouter (only `llama-guard-4-12b` and `gpt-oss-safeguard-20b` are). Decide: run the pair on the worker (RAM budget) or amend ADR-011's backstop. **Resolved 2026-07-21 → ADR-011c:** backstop routed to `gpt-oss-safeguard-20b` on OpenRouter; meta-llama/llama-guard-3-8b stays on the worker. | Phase-2 moderation stack; probe 4's second classifier | Probe 4 runs one classifier while ADR-011 claims two; the gap is discovered during Phase 2 instead of now. | 🧑‍🏫 | ☑ |

---

## D. Do AFTER the Phase 0.5 probes run

| # | What to do | Waits on | Then it unblocks | Status |
|---|---|---|---|---|
| D1 | ~~Take the first effect-size estimate + inter-rater α from Probe 1's rating dress-rehearsal, to size the RQ5 reader N~~ **RETIRED (2026-07-25)** — RQ5 and the Tier-1 rating dress-rehearsal it depended on are both dropped; Probe 1 now only gates Phase 1 opening (see `design_decisions_and_risks.md` Sequencing). | — | — | ✗ retired |
| D2 | If **Quill fails** but Pip passes: record it as the product's boundary — a *finding*, not a failure. Decide scope deliberately. | Probe 1 result | The Discussion/Limitations framing; possibly narrows scope. | ☐ |
| D3 | Read **Probe 2** (seed determinism). If either endpoint fails to reproduce, drop the reproducibility claim from Phase 0.5's method or change provider — don't keep the claim silently. | Probe 2 result | Phase 0.5 reproducibility wording (m1 cross-endpoint caveat). | ☐ |
| D4 | Run **Probe 4** (Filipino/Taglish moderation, both directions) before Phase 2 ships. | Phase 2 build | Child-safety gate; blocks classroom use if it misses. | ☐ |

---

## One-glance priority

1. **C1 (ethics) + A1–A2 (citations)** — start today; both are on the critical path and neither waits on anything.
2. **B4, B5, B7, B8, B9** — one adviser meeting, before any data is collected.
3. **A4–A5 + Related Work** — before the first Word export.
4. **D2–D4** — as the probes complete.
