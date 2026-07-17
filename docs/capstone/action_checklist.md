# StoryBuddy — Action Checklist (what to do / confirm)

> **Working tracker — not manuscript.** A flat, scannable list of everything that needs a **decision, a
> confirmation, or a verification** before the capstone is safe. Reasoning and options for each item live in
> `design_decisions_and_risks.md` (R1–R6); this file is just *"what do I do, what does it block, what happens
> if I skip it."* Update the Status column as you go.

**Legend — Type:** 🔍 verify · 🧑‍🏫 confirm with adviser · 🛠️ do it · ⏳ waits on something else.
**Status:** ☐ not started · ◐ in progress · ☑ done.

---

## A. Before ANY doc becomes a Word document (citation integrity)

| # | What to do | Blocks / needed for | If ignored | Type | Status |
|---|---|---|---|---|---|
| A1 | Open `arxiv.org/abs/2604.01973` (NearID). If it 404s / isn't NearID, find the real source for the "VLM judges conflate category & identity" claim, or delete the citation. | Related Work; ADR-004's rationale | **Fabricated citation in an IEEE paper** — the most damaging integrity failure possible at defense. | 🔍 | ☐ |
| A2 | Confirm the **"79.6% human agreement"** figure inside the DreamBench++ PDF (`arxiv.org/abs/2406.16855`). Reword if the number isn't there. | ADR-004; model_finetuning.md L7 | A specific quantitative claim a reviewer can check and find wrong. | 🔍 | ☐ |
| A3 | Confirm QLoRA `arXiv:2305.14314` resolves (it does). | Methods citation | Low risk; still confirm. | 🔍 | ☐ |
| A4 | Verify the 3 Related-Work IDs before citing (ConsiStory 2402.03286 · StoryDiffusion 2405.01434 · The Chosen One 2311.10093). | Related Work paragraph | Citing an unverified ID. | 🔍 | ☐ |
| A5 | After A1–A2, apply the corrected gap wording + fixed citations to the **frozen** docs (`ADRs.md` ADR-001/ADR-004, `RESEARCH_PROTOCOL.md`, `ROADMAP.md`) so they match the manuscript. Log ADR edits as a one-line factual-correction changelog. | Consistency between manuscript and authoritative docs | Manuscript and source-of-truth disagree — a project-rule violation and a defense inconsistency. | 🛠️ | ☐ |

---

## B. Confirm with adviser BEFORE the pre-registration is timestamped

*(These get harder to change once data collection starts — lock them first.)*

| # | What to confirm | Blocks / needed for | If ignored | Type | Status |
|---|---|---|---|---|---|
| B1 | **R1 — add the 3rd ablation arm** (`reference-only`, no judge/regen). Owner-accepted 2026-07-13. | The claim that the judge+regeneration loop *specifically* works | You can only claim "whole pipeline beats naive," and a panelist calls OFF a strawman. | 🧑‍🏫 | ◐ |
| B2 | **R3 — make character-recovery co-primary** for RQ5 (keep plot recall as secondary). | RQ5's headline result being sensitive to what the pipeline fixes | Likely null on the pre-registered primary while the real effect hides in the secondary. | 🧑‍🏫 | ☐ |
| B3 | **R2(b) — one reader reads several *different* stories** (never the same one twice), counterbalanced. | RQ5 statistical power | RQ5, your outcome of record, stays underpowered → an uninterpretable null. | 🧑‍🏫 | ☐ |
| B4 | **§6.4 ISO/IEC 25010** — confirm the required standard + evaluator profile (already flagged ⚠️ in methodology). | Software-quality evaluation | Wrong instrument administered; not fixable after the fact. | 🧑‍🏫 | ☐ |
| B5 | Confirm your **actual final-defense date** and check Ethics Stage 1's "months" fits inside it. | The whole RQ6 track (R4) | You discover in month 4 that the fine-tune can't finish. | 🧑‍🏫 | ☐ |
| B6 | **R7 — image-only RQ5 comprehension sessions** (captions stripped; owner-accepted 2026-07-13; draft in RESEARCH_PROTOCOL §7). Decide together with B2/B3 — all three reshape the same instrument. | RQ5 measuring the visual channel at all | Both recall outcomes can be answered from the caption text, identically in both arms → uninterpretable null on the outcome of record. | 🧑‍🏫 | ◐ |
| B7 | Approve the **pre-registration drafts merged 2026-07-13**: test-set access policy + malformed-output rule (judge-finetune §7.5/§7.1), checkpoint-selection rule (§6.4), DreamBench++ binarization (§7.4), major-character definition (RESEARCH_PROTOCOL §7). | RQ6/RQ5 pre-registration integrity | Each is a researcher degree of freedom a reviewer can find. | 🧑‍🏫 | ◐ |
| B8 | **Questionnaire content validation** (extends B4) — name the **expert-validator panel** (who + how many, e.g. 3–5) and confirm the **CVI threshold + interpretation scale** (dept may have a house standard). Basis: `research_instruments.md` → *Content and face validity*; methodology §6.4. | Software-quality questionnaire being reportable as valid | You report a mean score from an instrument never shown to measure the ISO/IEC 25010 characteristics it claims. | 🧑‍🏫 | ☐ |
| B9 | **Evaluator N + pilot group** — confirm the target count of ISO-25010 evaluators (IT practitioners + teachers) and reserve a **separate pilot group held out from the reported sample**, so Cronbach's α (floor ≥ 0.70) is stable and pilot/reported samples don't overlap. Basis: `research_instruments.md` → *Reliability pilot*; methodology §6.4. | Reportable internal-consistency figure | α computed on a tiny or overlapping sample is unstable/invalid; not fixable after administration. | 🧑‍🏫 | ☐ |

---

## C. Do now — independent of everything else (critical path)

| # | What to do | Blocks / needed for | If ignored | Type | Status |
|---|---|---|---|---|---|
| C1 | **Submit Ethics Stage 1** (story donation). Include the one sentence: *donated stories may be used to build and evaluate an AI model* — **plus** the withdrawal-cutoff clause **and** the bundled adult-rater protocol (drafts merged into RESEARCH_PROTOCOL §9, 2026-07-13). | Corpus → RQ1/RQ4/RQ5 stimuli → RQ6 training data; Tier-1 rating sessions | The single longest pole. Every result waits on it; the consent clauses have **no retroactive fix**; without the adult protocol, "Tier 1 stands alone" still has an unfiled dependency. | 🛠️ | ☐ |
| C2 | Adopt the **value-proposition framing** (`value_proposition.md`) in the Intro/Discussion; keep refusing creativity (Trap A) and "visuals beat text" (Trap B). | The "so what?" defense question | You drift into an unmeasurable or already-known claim and lose the "why this matters" exchange. | 🛠️ | ☑ (doc written; adopt in manuscript) |
| C3 | Present **R1–R9 as known risks** at the proposal defense — do not try to solve them first. | Proposal defense posture | Looks like you missed weaknesses the panel then "discovers." | 🛠️ | ☐ |
| C4 | **Stand up CI** (pytest + vitest workflows in `.github/`; add the manifest split-disjointness guard when it exists). | "CI must stay green" (CLAUDE.md §3), the char-leakage guard (judge-finetune §10) | The testing bright line has no fence — both rules are currently aspirations; `.github/` does not exist. | 🛠️ | ☐ |
| C5 | **Surface the moderation-routing finding to the ADR process**: verified 2026-07-13 that neither Qwen3Guard-Gen nor Granite Guardian is routable on OpenRouter (only `llama-guard-4-12b` and `gpt-oss-safeguard-20b` are). Decide: run the pair on the worker (RAM budget) or amend ADR-011's backstop. | Phase-2 moderation stack; probe 4's second classifier | Probe 4 runs one classifier while ADR-011 claims two; the gap is discovered during Phase 2 instead of now. | 🧑‍🏫 | ☐ |

---

## D. Do AFTER the Phase 0.5 probes run

| # | What to do | Waits on | Then it unblocks | Status |
|---|---|---|---|---|
| D1 | Take the first **effect-size estimate + inter-rater α** from Probe 1's rating dress-rehearsal. | Probe 1 (kill criterion) passing | **R2** — compute the required RQ5 reader N (probably the binding N of the study). | ☐ |
| D2 | If **Quill fails** but Pip passes: record it as the product's boundary — a *finding*, not a failure. Decide scope deliberately. | Probe 1 result | The Discussion/Limitations framing; possibly narrows scope. | ☐ |
| D3 | Read **Probe 2** (seed determinism). If either endpoint fails to reproduce, drop the reproducibility claim from RQ2's method or change provider — don't keep the claim silently. | Probe 2 result | RQ2 reproducibility wording; R1 arm structure (m1 cross-endpoint caveat). | ☐ |
| D4 | Run **Probe 4** (Filipino/Taglish moderation, both directions) before Phase 2 ships. | Phase 2 build | Child-safety gate; blocks classroom use if it misses. | ☐ |

---

## One-glance priority

1. **C1 (ethics) + A1–A2 (citations)** — start today; both are on the critical path and neither waits on anything.
2. **B1–B5** — one adviser meeting, before any data is collected.
3. **A4–A5 + Related Work** — before the first Word export.
4. **D1–D4** — as the probes complete.
