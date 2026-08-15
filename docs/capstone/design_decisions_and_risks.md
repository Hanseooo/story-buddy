# StoryBuddy — Design Decisions & Open Risks

> **Working document — not authoritative, and deliberately so.** It records methodological weaknesses found
> under adversarial review, the options for each, a recommendation, and a **decision status**. Items marked
> `PENDING` are not yet reflected in the authoritative docs (`RESEARCH_PROTOCOL.md`, `ADRs.md`) and **must not
> be treated as decided** until an adviser signs off. Companion to `methodology.md` §9 (Threats to Validity):
> §9 lists threats *already mitigated by design*; this file lists decisions *still open*.

**Why this exists.** A proposal defense is where you *present* these, not hide them. "Here are our sharpest
vulnerabilities and the plan for each" beats a defense that pretends they don't exist. Nothing here must be
*solved* before the proposal defense; each has a target resolution window before the final defense.

**Numbering note (2026-07-25).** The manuscript is now authoritative and uses **Objective 1..5**, not
RQ1–RQ6 (ADR-008, revised 2026-07-25). Objective 3 = expert validation, Objective 4 = fine-tuned judge
classification (precision/recall/F1), Objective 5 = ISO/IEC 25010 software quality. Risks that existed only
because of the dropped RQ5 (naive-reader/reader-comprehension recall study), the Tier-1/Tier-2 respondent
tiers, or the Fun Toolkit have been retired below — those instruments no longer exist. Risks that survive the
pivot are reframed against the current Objectives.

---

## Summary

| # | Risk | Severity | Resolve by | Status |
|---|---|---|---|---|
| **R1** | Ablation is a 3-component *bundle* presented as a single-variable test | — | — | **MOOT (2026-07-20)** — the ablation itself is dropped (ADR-008). No arms exist to bundle. |
| **R2** | Corpus yield: 15 stories collected must clear a 10-story primary bar (+5 backup) that feeds both Objective 3 and Objective 4 | Medium | Before Ethics Stage-1 intake closes | **OPEN** — no promotion rule stated yet. |
| **R3** | Objective 4 (the fine-tuned judge) is load-bearing but the most timeline-fragile piece, several hops past the ethics gate | High | Ethics Stage 1 submission (now) | **OPEN** — Ethics Stage-1 submission is the pacing item; October is a fixture-pilot, full corpus lands after. |
| **R4** | Novelty/gap claim has a thin related-work moat; one sub-claim was falsifiable | Medium | Before final defense | Partially fixed |
| **R5** | Unverified arXiv citations + gap-claim overstatement in *frozen* docs | Medium | Before any Word export | Action list ready |
| **R6** | Presidio redacts *fictional* character names → breaks captions and narration | Medium | Before Phase-2 PII/moderation specs | **Owner-accepted (context-gated redaction, 2026-07-13)** |
| m1–m2 | Minor: seed cross-endpoint caveat (Phase-0.5) · annotator-agreement guide-revision risk for the judge's image-pair labels | Low | Before final defense | Noted |
| m3–m6 | Minor: judge test-set access policy · checkpoint-selection rule · DreamBench++ binarization (if the optional baseline comparison runs) · adult-participant ethics + withdrawal cutoff | Low | Pre-registration / Stage-1 submission | Drafted, need sign-off |

**Retired (pivot purge, 2026-07-25):** the pre-pivot R3 (RQ5 plot-vs-character co-primary choice), R7 (RQ5
caption contamination), and R9 (Tier-1/RQ5 rater-assignment matrix) are removed outright — the reader-
comprehension study they were about does not exist in the manuscript. m3 ("meant to tell" vs "wrote") is
retired with them; it was scored against the same dead instrument.

---

## R1 — The ablation bundles three components but is described as single-variable

**Status: MOOT (2026-07-20).** The pipeline-ON-vs-OFF ablation this entire risk is about is **dropped as the
study spine** (`docs/product/adr/ADR-008-evaluation-three-objective-evaluation-expert-validation.md`, revised 2026-07-25) — generated-output quality is now
evaluated directly on pipeline-ON books (Objective 3 expert panel + Objective 5 ISO/IEC 25010), not by
comparing arms. There is no OFF or REF-ONLY condition left to bundle or unbundle, and no third-arm decision
to make. Kept below for the historical record of what the panel asked and why the owner accepted a 3-arm
design at the time; nothing here should be acted on.

<details><summary>Original content (pre-pivot, 2026-07-13) — historical only</summary>

**Panel's question.** *"Your pipeline-ON = reference conditioning + judge + regeneration; pipeline-OFF =
none. You changed three things at once. How do you know the judge+regeneration loop — your actual research
contribution — did anything, and not the reference image alone (which any image-edit model does off the
shelf)? And OFF-as-nothing is a strawman that inflates your effect."*

**Fixed so far.** The internal contradiction is corrected: `methodology.md` §1.4 and §6.5 no longer claim
"one variable differs" — they now state the ablation attributes an effect to the pipeline *as a whole*.

**Options.**
- **(a) Reword only** — claim causality for the *pipeline*, not "the loop." Cheapest. Leaves the strawman
  objection open.
- **(b) Add a third arm — RECOMMENDED** — `reference-only` (reference conditioning, **no** judge, **no**
  regeneration). Three arms: OFF (naive) · REF-ONLY · FULL. Now you can say the loop *specifically* earns its
  place, and REF-ONLY is the strong simple baseline a reviewer imagines. Cost: ~$10 on a ~$29 generation
  budget. The loop is the novel contribution — do not leave it unmeasured.

**Recommendation.** (b). **Decision status (superseded):** `OWNER-ACCEPTED (2026-07-13)` — three arms
(OFF · REF-ONLY · FULL). Note the cost that matters was not the ~$10 of generation but the **+50%
blind-rating workload** — this concern is now moot along with the arms themselves.

</details>

---

## R2 — Corpus yield: 15 collected must clear a 10-story primary bar

**Status: OPEN.** The manuscript targets **15 stories collected** from qualified Grade 5–6 learners at
Matina Aplaya Elementary School, split into a **10-story primary corpus + 5 backup**. Both evaluation legs
draw from the primary 10: Objective 3's expert validators read the books generated from them; Objective 4's
two researchers annotate character-image pairs generated from them for judge fine-tuning. There is no stated
sizing rule yet for what happens if fewer than 10 of the 15 collected stories survive moderation, consent
withdrawal, or usability screening (too short to segment, off-topic, PII that can't be safely handled) — the
5 backups exist for exactly this, but nobody has written down when a backup gets promoted, or what happens if
backups run out too.

**Recommendation.** State the promotion rule explicitly (e.g., first N usable stories in submission order)
before Ethics Stage 1 intake closes, and log exclusion reasons as they happen so a shortfall is diagnosable
rather than a late surprise.

**Decision status:** `OPEN` — no adviser decision needed, just document the rule.

---

## R3 — Objective 4 (the fine-tuned judge) is load-bearing but the most timeline-fragile piece

**Status: current.** The judge is fine-tuned (the one sanctioned LoRA, ADR-016→018) and is **Objective 4 in
its own right**: its binary character-consistency classification is scored against human-established
reference labels with **precision, recall, and F1 (F1 primary)** — this is a required evaluation leg, not a
descriptive-only aside. An **optional** secondary comparison (fine-tuned vs. zero-shot base model vs. the
existing prompted Consistency Judge baseline) on the same held-out pairs and human labels is permitted but
not required; the fine-tuned model's absolute agreement with human labels is what the objective actually
asks for.

Objective 4 sits four hops past the long pole: **Ethics Stage 1 → corpus → a Phase 1 run → image-pair
labelling → train.** With Ethics Stage 1 taking "months" and October being a technical (type-A) defense
(working system + pre-registered methodology + pilot results, not completed corpus-gated results — roadmap
§0.8), the full-corpus Objective 4 result is what's most likely to not finish if anything slips. The October
deliverable is a **pilot run on fixture stories**, explicitly labeled illustrative/demonstration; full-corpus
results land after October, behind Ethics Stage 1.

**Recommendation.**
1. **Submit Ethics Stage 1 now** — still the critical-path item nothing else compresses.
2. Rely on the October fixture-pilot / post-October full-corpus split (roadmap §0.8) — Objective 4 is a
   required evaluation leg, not an optional reach piece to drop if time runs short.

**Decision status:** `PARTIALLY RESOLVED` — the fixture-pilot/full-corpus split is made at the roadmap level
(§0.8); submitting Ethics Stage 1 is still an action to take immediately. Confirm the actual October defense
date against the Ethics Stage 1 timeline.

**Note — ADR-018's δ = 3 non-inferiority gate is a separate, deployment-only concern:** it decides whether
the fine-tuned judge replaces the prompted incumbent *in the product*, not what gets reported as a finding
for Objective 4.

---

## R4 — The novelty/gap claim had a falsifiable overstatement and a thin related-work moat

**What was wrong.** The claim *"no open image model has published identity-similarity benchmarks split by
human vs. non-human subject"* is **falsifiable** — DreamBench++ (which your own `judge-finetune.md` §5.1
already cites) reports concept-preservation scores by subject category on open-weight models. A domain reviewer
catches this from your own bibliography. Separately, the related work cited almost nothing from the crowded
2023–2025 character-consistency field (ConsiStory, StoryDiffusion, The Chosen One, TheaterGen).

**Fixed so far (manuscript docs only).** `research_direction_and_goals.md` §1.2, §7, and §9 now state the
**defensible conjunction**: existing benchmarks are photographic or method-preference studies, and *none
provides human **pairwise** identity judgments over stylized, invented, non-human characters.* This holds
regardless of DreamBench++'s exact methodology.

**Still to do.** Write a Related Work paragraph that *acknowledges* the crowded field, names the 3–4 most
relevant *verified* works, and explains why each misses your corner (stylized + invented + non-human + human
pairwise + open-weight). Draft input exists from the literature sweep; **verify every citation first** (R5).

**Decision status:** `PARTIALLY FIXED` — manuscript reworded; Related Work paragraph and authoritative-doc
alignment outstanding.

---

## R5 — Citation integrity + the same overstatement lives in *frozen* docs

**Two coupled problems, both blocking a Word/IEEE export.**

1. **Unverified citations.** The literature sweep could not confirm several 2025–2026 arXiv IDs, and your own
   docs already contain one with the same suspicious pattern: `docs/product/adr/ADR-004-consistency-via-vlm-as-judge-control-loop-human-ratings.md` (its reasoning) cites
   **`NearID (arXiv:2604.01973)`** and attributes a **79.6% human-agreement ceiling to DreamBench++**. A
   `2604.xxxxx` ID means April 2026; it cannot be confirmed here and may be a hallucinated citation baked in
   earlier. **A fabricated citation in an IEEE paper is far more damaging than a slightly overstated gap.**
2. **The overstatement in authoritative docs.** The falsifiable gap claim (R4) also lives in **frozen**
   files — `docs/product/adr/ADR-001-image-generation-model-qwen-image-edit-open-weight.md` (**Consequences**,
   the ⚠️ non-human identity bullet) and `docs/product/adr/ADR-018-fine-tune-the-consistency-judge-qwen2-5-vl-7b-qlora.md`
   (**Context**, the "ADR-001 records that no published benchmark splits…" sentence), `RESEARCH_PROTOCOL.md` (§2, §246),
   `ROADMAP.md` (line ~36). These were **not** edited, per the project's frozen-ADR rule.

**Action list (needs your go-ahead — none done yet).**
- [ ] Resolve **every** arXiv ID currently in the docs against the real arXiv. Treat anything dated ≥ 2025 as
      unverified until checked. Flagged specifically: `arXiv:2604.01973` (NearID), the `79.6%` DreamBench++
      figure, and any CHARIS / StyleID / ID-Sim IDs before they are cited.
- [ ] Once verified/corrected, apply the R4 conjunction wording to `ADRs.md`, `RESEARCH_PROTOCOL.md`,
      `ROADMAP.md` so the authoritative docs match the manuscript. Per the frozen-ADR rule, ADR-001's
      literature note is corrected as a **factual accuracy fix** (the *decision* is unchanged), with a one-line
      changelog entry — confirm this is how you want it recorded.

**Decision status:** `PENDING` — do this before any capstone doc becomes a Word document.

---

## R6 — PII redaction will redact fictional character names, breaking captions and narration

**The problem.** Every PII discussion treats the risk as under-redaction; the inverse error is
unexamined. A PERSON recognizer cannot distinguish the hero "Juan" from a real Juan — and the
mandated Filipino-name recognizers will fire on fictional Filipino names *more*. Redaction runs
before storage/captioning/export (CC-2), so a false positive cascades: placeholder tokens in the
verbatim captions (violating ADR-012/013's fidelity argument), spoken aloud by Kokoro, and a
protagonist that may not survive entity extraction.

**Decision status:** `OWNER-ACCEPTED (2026-07-13)` — **context-gated redaction**: redact PERSON
entities only when they co-occur with real-world anchors (address structures, phone patterns,
"my name is / ako si" framings); fictional names in narrative stay. Benign-fiction cases are now in
the probe-4 test set and must be in the Phase-2 PII test set. Escalation path if the leak rate
demands it: add a teacher-confirmation queue for ambiguous names. Lands in the
`filipino-pii-recognizers` and `moderation-stack` specs (Phase 2); the corpus-intake manual
redaction protocol (`RESEARCH_PROTOCOL.md` §8) applies the same fiction-vs-real rule by hand.

---

## Minor items (m1–m2)

- **m1 — Seed comparability across endpoints (partially moot 2026-07-20).** The RQ2-era fairness assumption
  this originally described is dropped along with the ablation. The underlying probe concern still stands,
  though, for **Phase 0.5's own kill-criterion probe**, which still pipeline-ON/OFF-compares `edit_image` vs.
  `text_to_image` internally (a technical substrate check, not a research arm — `methodology.md` §3.4).
  Probe 2 verifies each endpoint reproduces *on itself*; it does **not** establish that a matched seed means
  the same starting state *across* the two endpoints. State the cross-endpoint seed caveat as a limitation of
  the Phase 0.5 result rather than an equivalence claim.
- **m2 — Annotator-agreement guide-revision risk (reframed 2026-07-25).** Objective 4's two researchers
  annotate character-image pairs independently and resolve disagreements via an established criteria
  procedure (`judge-finetune.md`). Revising that criteria guide and recalibrating until agreement is
  "acceptable" can inflate *reliability* at the cost of *validity* if the annotators converge on an
  easy-to-agree-but-invalid rule. Cap the number of guide revisions, and report how many occurred. (This item
  previously described the now-retired Tier-1 rating rubric α-gate; the underlying methodological risk —
  reliability bought at the cost of validity — carries over to the judge's image-pair labels.)

**m3–m6 — drafted into the docs 2026-07-13 (round 2); each needs adviser sign-off with the
pre-registration, none needs further design work:**

- **m3 — Test-set access policy + malformed-output rule.** "Held-out read once" and "rung D →
  debug" were jointly contradictory; the pre-declared resolution (debug on train/val only; one
  permitted second read, reported as a deviation) and the unparseable-verdict scoring rule are now
  in `judge-finetune.md` §7.5 / §7.1.
- **m4 — Checkpoint-selection rule.** Reported checkpoint per seed selected by minority-class F1 on
  validation, not by eval loss (`judge-finetune.md` §6.4).
- **m5 — DreamBench++ binarization.** Relevant only if Objective 4's optional baseline comparison uses it;
  the graded-ratings→binary mapping is fixed in advance, verified against the actual scale during A2
  (`judge-finetune.md` §7.4).
- **m6 — Adult-participant ethics + withdrawal cutoff.** The protocol covering adult participants (Objective
  4's two annotators, Objective 3's expert validators, Objective 5's software-quality evaluators) is bundled
  into Stage 1; consent gains a data-lock/withdrawal-cutoff clause because a trained LoRA cannot be untrained
  (`RESEARCH_PROTOCOL.md` §9). The child assent's "you can stop any time" was quietly promising the
  impossible.

---

## Sequencing — what happens after the Phase 0.5 probes

Phase 0.5 is a build gate for pipeline substrate validity. Order of operations:

1. **Probe 1 (kill criterion) passes** → substrate holds identity → Phase 1 opens.
   - *If Probe 1 fails / Quill fails:* that is a **reportable finding**, not a catastrophe (see
     `PHASE_05_RESULTS.md` branches). The product's scope narrows and the paper gains its most interesting
     sentence.
   - **What actually happened (2026-07-29) — a case this ordering did not enumerate.** Quill *passed*
     and the pooled **separation** gate failed, on the primary model and again one rung down. Neither
     branch above fits: the substrate holds identity, so there is nothing to narrow, but a
     pre-committed gate is red, so "passes → opens" overstates it. Resolution: Phase 1 opens under the
     ADR-001 amendment with the missed gate carried as an explicit limitation. The lesson for the
     remaining probes is that a two-criteria gate has **four** outcomes and this list wrote down two.
2. **Probe 2 (seed determinism).** Confirms each endpoint reproduces on itself — see m1. If either endpoint
   fails, drop the reproducibility claim from the affected method or change provider (do not silently keep
   the claim).
3. **In parallel, independent of the probes:** submit **Ethics Stage 1** (R3) and run the **citation
   verification** (R5). Neither needs the probes and both are on the critical path to the October defense.

**Bottom line for the proposal defense:** present R2–R6 from this document as *known, planned* risks (R1 is
moot post-pivot). Solve none of them yet. The plan is the deliverable.

> **Phase 2 update (2026-08-04):** Phase 0.5 closed per `PHASE_05_RESULTS.md`. **Phase 1 is complete
> (2026-08-02)** — all ten specs built, from the `StoryMemory` contract through `compose`. **Phase 2 is in
> progress:** the moderation stack (input text → char-ref → output image, ADR-011 ordering enforced in
> `graph.py`), input-gate hardening (ADR-012 length clamp + Filipino PII recognizers), and the kid-facing
> flow (`jobs.pages` persistence, the ADR-029 reveal + `POST /jobs/{id}/confirm`, failure semantics, and
> the reader/wait-state surfaces) are built. Open: `auth-and-classroom` (the classroom RLS gap),
> `teacher-dashboard`, `narration`, `export-pdf`, `rate-limiting`, `data-deletion`. Probe 4
> (Filipino/Taglish moderation) is still un-run and remains a Phase-2 *release* gate.
