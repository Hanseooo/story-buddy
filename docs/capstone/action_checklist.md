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
| B1 | ~~R1 — add the 3rd ablation arm~~ **MOOT (2026-07-20)** — the RQ2 ablation itself is dropped (ADR-008); there's no arm structure left to decide. | — | — | — | ✗ retired |
| B2 | ~~R3 — make character-recovery co-primary~~ **RESOLVED (2026-07-20)** — owner decision: plot recall stays primary, character recovery is secondary (RQ5 is one of Objective 3's two output measures; with RQ6 demoted there is no headline comparative study behind it). `RESEARCH_PROTOCOL.md` §7, `ADR-008`, `research_direction_and_goals.md` now say so explicitly. Mention to adviser for the record. | RQ5's headline result being sensitive to what the pipeline fixes | — | 🧑‍🏫 | ☑ |
| B3 | **R2(b) — one reader reads several *different* stories** (never the same one twice), counterbalanced. Reframed 2026-07-20: no longer about between-arm power, but about the precision of RQ5's single-arm recall-rate estimate. | RQ5 estimate precision | RQ5, your outcome of record, stays imprecise → hard to distinguish a weak result from measurement noise. | 🧑‍🏫 | ☐ |
| B4 | **§6.4 ISO/IEC 25010** — confirm the required standard + evaluator profile (already flagged ⚠️ in methodology). | Software-quality evaluation | Wrong instrument administered; not fixable after the fact. | 🧑‍🏫 | ☐ |
| B5 | Confirm your **actual October defense date** and check Ethics Stage 1's "months" fits inside it. RQ6 is **reported descriptively** — the comparison was dropped as a research claim (R4; ADR-008 revised 2026-07-22), so the study has no primary comparative study. The October deliverable is a pilot run on fixtures; full corpus results land after Stage 1 (roadmap §0.8). | The whole RQ6 track (R4) | You discover in month 4 that the fine-tune can't finish, with no fixture-pilot fallback prepared. | 🧑‍🏫 | ☐ |
| B6 | **R7 — image-only RQ5 comprehension sessions** (captions stripped; owner-accepted 2026-07-13; draft in RESEARCH_PROTOCOL §7). Decide together with B2/B3 — all three reshape the same instrument. Unaffected by the ablation drop. | RQ5 measuring the visual channel at all | The recall outcome can be answered from the caption text alone → an uninterpretable result regardless of image fidelity. | 🧑‍🏫 | ◐ |
| B7 | Approve the **pre-registration drafts merged 2026-07-13**: test-set access policy + malformed-output rule (judge-finetune §7.5/§7.1), checkpoint-selection rule (§6.4), DreamBench++ binarization (§7.4), major-character definition (RESEARCH_PROTOCOL §7). | RQ6/RQ5 pre-registration integrity | Each is a researcher degree of freedom a reviewer can find. | 🧑‍🏫 | ◐ |
| B8 | **Questionnaire content validation** (extends B4) — name the **expert-validator panel** (who + how many, e.g. 3–5) and confirm the **CVI threshold + interpretation scale** (dept may have a house standard). Basis: `research_instruments.md` → *Content and face validity*; methodology §6.4. | Software-quality questionnaire being reportable as valid | You report a mean score from an instrument never shown to measure the ISO/IEC 25010 characteristics it claims. | 🧑‍🏫 | ☐ |
| B9 | **Evaluator N + pilot group** — confirm the target count of ISO-25010 evaluators (IT practitioners + teachers) and reserve a **separate pilot group held out from the reported sample**, so Cronbach's α (floor ≥ 0.70) is stable and pilot/reported samples don't overlap. Basis: `research_instruments.md` → *Reliability pilot*; methodology §6.4. | Reportable internal-consistency figure | α computed on a tiny or overlapping sample is unstable/invalid; not fixable after administration. | 🧑‍🏫 | ☐ |

---

## C. Do now — independent of everything else (critical path)

| # | What to do | Blocks / needed for | If ignored | Type | Status |
|---|---|---|---|---|---|
| C1 | **Submit Ethics Stage 1** (story donation). Include the one sentence: *donated stories may be used to build and evaluate an AI model* — **plus** the withdrawal-cutoff clause **and** the bundled adult-rater protocol (drafts merged into RESEARCH_PROTOCOL §9, 2026-07-13). | Corpus → RQ1/RQ4/RQ5 stimuli → RQ6 training data; Tier-1 rating sessions | The single longest pole. Every result waits on it; the consent clauses have **no retroactive fix**; without the adult protocol, "Tier 1 stands alone" still has an unfiled dependency. | 🛠️ | ☐ |
| C2 | Adopt the **value-proposition framing** (`value_proposition.md`) in the Intro/Discussion; keep refusing creativity (Trap A) and "visuals beat text" (Trap B). | The "so what?" defense question | You drift into an unmeasurable or already-known claim and lose the "why this matters" exchange. | 🛠️ | ☑ (doc written; adopt in manuscript) |
| C3 | Present **R2–R9 as known risks** at the proposal defense (R1 is moot post-pivot) — do not try to solve them first. | Proposal defense posture | Looks like you missed weaknesses the panel then "discovers." | 🛠️ | ☐ |
| C4 | **Stand up CI** (pytest + vitest workflows in `.github/`; add the manifest split-disjointness guard when it exists). | "CI must stay green" (CLAUDE.md §3), the char-leakage guard (judge-finetune §10) | The testing bright line has no fence — both rules are currently aspirations; `.github/` does not exist. | 🛠️ | ☐ |
| C5 | **Surface the moderation-routing finding to the ADR process**: verified 2026-07-13 that neither Qwen3Guard-Gen nor Granite Guardian is routable on OpenRouter (only `llama-guard-4-12b` and `gpt-oss-safeguard-20b` are). Decide: run the pair on the worker (RAM budget) or amend ADR-011's backstop. **Resolved 2026-07-21 → ADR-011c:** backstop routed to `gpt-oss-safeguard-20b` on OpenRouter; Qwen3Guard-Gen stays on the worker. | Phase-2 moderation stack; probe 4's second classifier | Probe 4 runs one classifier while ADR-011 claims two; the gap is discovered during Phase 2 instead of now. | 🧑‍🏫 | ☑ |

---

## D. Do AFTER the Phase 0.5 probes run

| # | What to do | Waits on | Then it unblocks | Status |
|---|---|---|---|---|
| D1 | Take the first **effect-size estimate + inter-rater α** from Probe 1's rating dress-rehearsal. | Probe 1 (kill criterion) passing | **R2** — compute the required RQ5 reader N (probably the binding N of the study). | ☐ |
| D2 | If **Quill fails** but Pip passes: record it as the product's boundary — a *finding*, not a failure. Decide scope deliberately. | Probe 1 result | The Discussion/Limitations framing; possibly narrows scope. | ☐ |
| D3 | Read **Probe 2** (seed determinism). If either endpoint fails to reproduce, drop the reproducibility claim from Phase 0.5's method or change provider — don't keep the claim silently. | Probe 2 result | Phase 0.5 reproducibility wording (m1 cross-endpoint caveat). | ☐ |
| D4 | Run **Probe 4** (Filipino/Taglish moderation, both directions) before Phase 2 ships. | Phase 2 build | Child-safety gate; blocks classroom use if it misses. | ☐ |

---

## One-glance priority

1. **C1 (ethics) + A1–A2 (citations)** — start today; both are on the critical path and neither waits on anything.
2. **B1–B5** — one adviser meeting, before any data is collected.
3. **A4–A5 + Related Work** — before the first Word export.
4. **D1–D4** — as the probes complete.
