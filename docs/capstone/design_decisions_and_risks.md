# StoryBuddy — Design Decisions & Open Risks

> **Working document — not authoritative, and deliberately so.** It records methodological weaknesses found
> under adversarial review, the options for each, a recommendation, and a **decision status**. Items marked
> `PENDING` are not yet reflected in the authoritative docs (`RESEARCH_PROTOCOL.md`, `ADRs.md`) and **must not
> be treated as decided** until an adviser signs off. Companion to `methodology.md` §9 (Threats to Validity):
> §9 lists threats *already mitigated by design*; this file lists decisions *still open*.

**Why this exists.** A proposal defense is where you *present* these, not hide them. "Here are our five
sharpest vulnerabilities and the plan for each" beats a defense that pretends they don't exist. Nothing here
must be *solved* before the proposal defense (~1–2 weeks out); each has a target resolution window before the
final defense (~4–5 months out).

---

## Summary

| # | Risk | Severity | Resolve by | Status |
|---|---|---|---|---|
| **R1** | Ablation is a 3-component *bundle* presented as a single-variable test | — | — | **MOOT (2026-07-20)** — the RQ2 ablation itself is dropped (ADR-008, roadmap §0.1). No arms exist to bundle. |
| **R2** | RQ5 (outcome of record) underpowered; no RQ5-specific power analysis | High | After Phase 0.5 (needs effect size) | **Reframed (2026-07-20)** — no more between-arm comparison; the open question is now the precision of a single-arm recall-rate estimate. Still blocked on Phase 0.5; (b)'s multi-book-per-reader recommendation still stands. |
| **R3** | RQ5 primary outcome (plot recall) may be blind to the fix (character identity) | High | Before pre-registration sign-off | **Resolved (2026-07-20)** — owner decision: plot recall stays primary, character recovery is secondary. RQ5 is a supporting measure (Objective 3), not the study's headline (RQ6), so the residual risk below is accepted rather than engineered around. `RESEARCH_PROTOCOL.md` §7, `ADR-008`, and `research_direction_and_goals.md` now state this explicitly. |
| **R4** | RQ6 (fine-tune) is load-bearing but 4 hops past a months-long ethics gate | High | Ethics Stage 1 submission (now) | **Reframed (2026-07-20)** — RQ6 is now the primary study and can no longer be de-scoped away (superseding this item's part 2). The timeline risk is instead handled by the October/type-A defense split: a pilot RQ6 run on fixtures ships in October, full corpus results follow after Stage 1 (roadmap §0.8). Part 1 (submit Ethics Stage 1 now) still stands. |
| **R5** | Novelty/gap claim has a thin related-work moat; one sub-claim was falsifiable | Medium | Before final defense | Partially fixed |
| **R6** | Unverified arXiv citations + gap-claim overstatement in *frozen* docs | Medium | Before any Word export | Action list ready |
| **R7** | RQ5's "naive reader" reads the story text via verbatim captions — the recall outcome is contaminated | High | Before pre-registration sign-off | **Owner-accepted (image-only sessions, 2026-07-13)** — still stands post-pivot; drafted into `RESEARCH_PROTOCOL.md` §7; pending adviser |
| **R8** | Presidio redacts *fictional* character names → breaks captions, narration, RQ5 scoring | Medium | Before Phase-2 PII/moderation specs | **Owner-accepted (context-gated redaction, 2026-07-13)** |
| **R9** | Rater-assignment matrix undesigned (IRR overlap × RQ5 naivety × fatigue caps jointly set the real N) | Medium | With R2, before pre-registration | Design task ready — now sized for a single condition (~50 books), not 2–3 arms |
| m1–m3 | Minor: seed cross-endpoint (**m1 now moot — ablation dropped**) · α-gate validity · "meant to tell" vs "wrote" | Low | Before final defense | Noted |
| m4–m7 | Minor: test-set access policy · checkpoint-selection rule · DreamBench++ binarization · adult-rater ethics + withdrawal cutoff | Low | Pre-registration / Stage-1 submission | **Drafted into docs 2026-07-13** — need sign-off |

---

## R1 — The ablation bundles three components but is described as single-variable

**Status: MOOT (2026-07-20).** The RQ2 pipeline-ON-vs-OFF ablation this entire risk is about is
**dropped as the study spine** (`ADRs.md` ADR-008, `scope_revision_roadmap.md` §0.1) — generated-output
quality is now evaluated directly on pipeline-ON books (expert panel + ISO/IEC 25010), not by comparing
arms. There is no OFF or REF-ONLY condition left to bundle or unbundle, and no third-arm decision to make.
Kept below for the historical record of what the panel asked and why the owner accepted a 3-arm design at
the time; nothing here should be acted on.

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

## R2 — RQ5, the outcome of record, is underpowered

**Status: reframed (2026-07-20).** RQ2's ablation is dropped, so RQ5 is no longer a between-arm comparison
(ADR-008) — there is no "~8–15 per arm" and no Mann–Whitney U against an OFF condition. The underlying
concern survives in a milder form: with N ≈ 15–30 readers and each reader currently reading **one** book,
the *precision* of the single-arm recall-rate estimate (not a between-group power calculation) is still set
by a small N spread thin across ~50 stories. Most stories are still read once or not at all.

**Panel's question (as originally posed, pre-pivot).** *"Each reader reads one book; N ≈ 15–30 total,
between-subjects → ~8–15 per arm across ~50 stories. Most stories are read once or not at all. A
Mann–Whitney U on ~10 vs ~10 with story as a random effect has almost no power. A null on your headline
outcome would be uninterpretable — underpowered-null looks identical to substrate-null."* The arm-comparison
framing no longer applies; the precision concern does.

**Root cause.** The only power statement (`methodology.md` §9, now updated to size the **Tier-1 rating**
load rather than the dropped RQ2's) still does **not** size the *RQ5 reader* load specifically, and RQ5
remains a single-datapoint-per-reader design.

**Options.**
- **(a)** Compute the required RQ5 reader N explicitly once Phase 0.5 yields an effect estimate, and state
  openly it is probably the binding N of the whole study.
- **(b) — RECOMMENDED, combine with (a)** Revise "one book per reader." *Within-reader, **different** stories*
  is clean: one reader reads several *different* books, never the same story twice. Each reader then
  contributes multiple datapoints and precision improves — with **no** contamination. This recommendation is
  unaffected by the ablation drop; it still tightens the single-arm recall-rate estimate.

**Recommendation.** (a)+(b). **Decision status:** `BLOCKED ON PHASE 0.5` for the number; the design change (b)
can be decided now. Needs adviser sign-off (changes pre-registration). Not yet adopted in `RESEARCH_PROTOCOL.md`
§7, which still describes "one book per reader" — flag to whoever next signs off the RQ5 instrument.

---

## R3 — RQ5's primary outcome may be insensitive to the exact thing the pipeline fixes

**Status: resolved (2026-07-20) — owner decision.** Plot-point recall stays RQ5's primary outcome;
character recovery is scored as a secondary/confirmatory outcome, not co-primary. Rationale: RQ5 sits
inside Objective 3 as a supporting fidelity measure — the study's headline is RQ6 (judge fine-tune) —
so the residual risk described below is accepted as a stated limitation rather than resolved by
re-weighting a secondary instrument. `RESEARCH_PROTOCOL.md` §7, `ADR-008`, and
`research_direction_and_goals.md` now all state plot-primary/character-secondary explicitly.

**Panel's question (original framing still explains why this matters).** *"Your intervention improves
character *identity consistency*. Your pre-registered *primary* outcome is *plot-point* recall. But a reader
recovers 'a boy found treasure' even if the boy looks different on every page — plot recall is robust to
character drift. You could get a null on your primary while your secondary (character recall) moves, and
pre-registration will have locked plot as primary."* This still applies to the single-arm RQ5: the pipeline's
actual mechanism is character identity, not plot transmission, so plot recall alone would still be an
insensitive primary outcome.

**Original recommendation (2026-07-13, superseded below).** Make **character recovery co-primary** (or
primary) — it is the causally-proximal outcome of a character-consistency intervention. Keep plot-point
recall as the "does it still hold the narrative" secondary.

**Decision status:** `RESOLVED (2026-07-20)` — owner decided against the original recommendation: plot
recall remains primary, character recovery secondary. Pre-register **both**, with this rationale (and
the panel's objection above) stated openly as a limitation, so it doesn't look like post-hoc selection.
Still worth a one-line mention to the adviser for the record, but not blocking.

---

## R4 — RQ6 (the fine-tune) is load-bearing but the most timeline-fragile piece

**Status: reframed (2026-07-20).** RQ6 is now the study's **primary comparative study** (ADR-008,
roadmap §0.2) — the old part-2 recommendation, "build a de-scope position where RQ2+RQ5 stand alone and RQ6
is the droppable reach piece," is now backwards: RQ2 is gone, so RQ6 *is* the spine, not a reach contribution
to retreat from. The timeline risk this item worried about is real and still open, but it's now handled by a
scope split rather than a de-scope option:

- **October is a technical (type-A) defense**, requiring a working system + pre-registered methodology +
  **pilot results**, not completed corpus-gated results (roadmap §0.8). The October deliverable is a **pilot
  RQ6 run on fixture stories**, explicitly labeled illustrative/demonstration, never presented as findings.
  Full corpus RQ6 results land after October, behind Ethics Stage 1.
- This is what makes RQ6-primary survivable despite being the most timeline-fragile piece: the piece that's
  load-bearing for October is fixture-gated, not corpus-gated.

**Original problem (still accurate).** RQ6 sits four hops past the long pole: *Ethics Stage 1 → corpus → a
Phase 1 run → image-pair labelling → train.* With the final defense ~4–5 months out (now dated: October 2026)
and Ethics Stage 1 taking "months," the full-corpus RQ6 result is what's most likely to not finish if anything
slips — the fixture pilot is the insurance.

**Recommendation.**
1. **Submit Ethics Stage 1 now** — unchanged, still the critical-path item nothing else compresses.
2. ~~Build the de-scope position that RQ2+RQ5 stand alone~~ — **superseded.** There is no RQ2 to stand
   alongside, and RQ6 cannot be dropped. Rely on the October fixture-pilot / post-October full-corpus split
   (§0.8) instead of a droppability argument.

**Decision status:** `PARTIALLY RESOLVED` — the framing decision (2) is made at the roadmap level (§0.8);
(1) is still an action to take immediately. Confirm the actual October defense date against the Ethics
Stage 1 timeline, same as before.

---

## R5 — The novelty/gap claim had a falsifiable overstatement and a thin related-work moat

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
pairwise + open-weight). Draft input exists from the literature sweep; **verify every citation first** (R6).

**Decision status:** `PARTIALLY FIXED` — manuscript reworded; Related Work paragraph and authoritative-doc
alignment outstanding.

---

## R6 — Citation integrity + the same overstatement lives in *frozen* docs

**Two coupled problems, both blocking a Word/IEEE export.**

1. **Unverified citations.** The literature sweep could not confirm several 2025–2026 arXiv IDs, and your own
   docs already contain one with the same suspicious pattern: `ADRs.md` (ADR-004 reasoning) cites
   **`NearID (arXiv:2604.01973)`** and attributes a **79.6% human-agreement ceiling to DreamBench++**. A
   `2604.xxxxx` ID means April 2026; it cannot be confirmed here and may be a hallucinated citation baked in
   earlier. **A fabricated citation in an IEEE paper is far more damaging than a slightly overstated gap.**
2. **The overstatement in authoritative docs.** The falsifiable gap claim (R5) also lives in **frozen**
   files — `ADRs.md` (ADR-001 line ~21, and lines ~564–565), `RESEARCH_PROTOCOL.md` (§2, §246),
   `ROADMAP.md` (line ~36). These were **not** edited, per the project's frozen-ADR rule.

**Action list (needs your go-ahead — none done yet).**
- [ ] Resolve **every** arXiv ID currently in the docs against the real arXiv. Treat anything dated ≥ 2025 as
      unverified until checked. Flagged specifically: `arXiv:2604.01973` (NearID), the `79.6%` DreamBench++
      figure, and any CHARIS / StyleID / ID-Sim IDs before they are cited.
- [ ] Once verified/corrected, apply the R5 conjunction wording to `ADRs.md`, `RESEARCH_PROTOCOL.md`,
      `ROADMAP.md` so the authoritative docs match the manuscript. Per the frozen-ADR rule, ADR-001's
      literature note is corrected as a **factual accuracy fix** (the *decision* is unchanged), with a one-line
      changelog entry — confirm this is how you want it recorded.

**Decision status:** `PENDING` — do this before any capstone doc becomes a Word document.

---

## R7 — RQ5's naive reader reads the story text: captions contaminate the recall outcome

**Status: survives the pivot unchanged (2026-07-20).** RQ5 is now single-arm, but the caption-contamination
problem isn't about arms — it's about whether the recall instrument measures the visual pipeline or reading
comprehension, which applies just as much to a single generated book as it did to a pair. Still owner-accepted
and still pending adviser sign-off.

**Panel's question (as originally posed).** *"Your 'naive reader who has never seen the story text' is
handed a book whose captions ARE the story text, verbatim (ADR-013). Character names and plot events are
recoverable from the captions alone. What exactly does your outcome of record measure — the visual pipeline,
or reading comprehension?"*

This is the structural version of R3: not "the primary outcome might miss the effect" but "the recall
outcome measures a channel the pipeline never touches." Likely empirical signature: high recall regardless
of image quality, an uninterpretable result on the study's dependent variable of record.

**Options considered:** (a) image-only comprehension sessions (captions stripped); (b) keep
captions, switch primary to visually-grounded items (appearance recovery vs. the Character Bible,
page-pair identity); (c) two-pass hybrid.

**Decision status:** `OWNER-ACCEPTED (2026-07-13)` — **(a) image-only primary**: RQ5 sessions
present images and page order only; the claim becomes *"the visual narrative alone transmits the
story."* The shipped artifact keeps captions; Methods states the deviation (the shipped book is
strictly easier). Draft merged into `RESEARCH_PROTOCOL.md` §7. **Pending adviser sign-off — decide
together with R2 (power) and R3 (co-primary choice, which now applies within the image-only
instrument) in one meeting, before the pre-registration is timestamped.**

---

## R8 — PII redaction will redact fictional character names, breaking captions, narration, and RQ5 scoring

**The problem.** Every PII discussion treats the risk as under-redaction; the inverse error is
unexamined. A PERSON recognizer cannot distinguish the hero "Juan" from a real Juan — and the
mandated Filipino-name recognizers will fire on fictional Filipino names *more*. Redaction runs
before storage/captioning/export (CC-2), so a false positive cascades: placeholder tokens in the
verbatim captions (violating ADR-012/013's fidelity argument), spoken aloud by Kokoro, characters
unnameable by RQ5 readers, and a protagonist that may not survive entity extraction.

**Decision status:** `OWNER-ACCEPTED (2026-07-13)` — **context-gated redaction**: redact PERSON
entities only when they co-occur with real-world anchors (address structures, phone patterns,
"my name is / ako si" framings); fictional names in narrative stay. Benign-fiction cases are now in
the probe-4 test set and must be in the Phase-2 PII test set. Escalation path if the leak rate
demands it: add a teacher-confirmation queue for ambiguous names. Lands in the
`filipino-pii-recognizers` and `moderation-stack` specs (Phase 2); the corpus-intake manual
redaction protocol (`RESEARCH_PROTOCOL.md` §8) applies the same fiction-vs-real rule by hand.

---

## R9 — Nobody has designed the rater-assignment matrix, and it silently sets the study's real N

**Reworked (2026-07-20) — no longer sized for arms.** With R1 moot, there's one pipeline-ON condition, not
2–3 arms: **~50 stories ≈ 50 books**, not 100–150. The rest of the constraint set is unaffected by the
ablation drop: blind ratings on the expert-panel/Tier-1 dimensions plus RQ5 comprehension, from a pool of
15–30 adults, under interacting constraints — IRR needs overlap (α is uncomputable on disjoint assignments);
RQ5 readers must be naive to the story (a rater who rated story X is burned for story X); R2(b)'s multi-book
readers must never see the same story twice; methodology §5.2's fatigue caps bound books-per-rater. These
jointly determine the required N — and the *structure* is independent of effect size, so it can be designed
now rather than after Phase 0.5.

**Recommendation.** A one-page assignment design (raters × stories; overlap fraction for α;
RQ5-naivety bookkeeping) inside the `tier1-rating-harness` spec, before pre-registration. R2's
precision answer is meaningless without it.

**Decision status:** `DESIGN TASK` — no adviser decision needed, just the page.

---

## Minor items (m1–m3)

- **m1 — Seed comparability across endpoints (partially moot 2026-07-20).** The RQ2 fairness assumption this
  originally described is dropped along with the ablation. The underlying probe concern still stands, though,
  for **Phase 0.5's own kill-criterion probe**, which still pipeline-ON/OFF-compares `edit_image` vs.
  `text_to_image` internally (a technical substrate check, not the dropped research arm — `methodology.md`
  §3.4). Probe 2 verifies each endpoint reproduces *on itself*; it does **not** establish that a matched seed
  means the same starting state *across* the two endpoints. State the cross-endpoint seed caveat as a
  limitation of the Phase 0.5 result rather than an equivalence claim.
- **m2 — α-gate validity.** "Revise the guide and recalibrate until α ≥ 0.67" (methodology §5.2) can inflate
  *reliability* at the cost of *validity* if raters converge on an easy-to-agree-but-invalid rubric. Cap the
  number of guide revisions, and report how many occurred.
- **m3 — "meant to tell" vs "wrote".** The central RQ says the reader recovers *"the story the child **meant**
  to tell,"* but the instrument scores against annotations of the **text the child wrote**. Meant ≠ wrote.
  Either soften to "wrote" or be ready to defend text-as-best-available-proxy-for-intent. (Left unchanged; it
  spans authoritative docs — decide alongside R6.)

**m4–m7 — drafted into the docs 2026-07-13 (round 2); each needs adviser sign-off with the
pre-registration, none needs further design work:**

- **m4 — Test-set access policy + malformed-output rule.** "Held-out read once" and "rung D →
  debug" were jointly contradictory; the pre-declared resolution (debug on train/val only; one
  permitted second read, reported as a deviation) and the unparseable-verdict scoring rule are now
  in `judge-finetune.md` §7.5 / §7.1.
- **m5 — Checkpoint-selection rule.** Reported checkpoint per seed selected by minority-class F1 on
  validation, not by eval loss (`judge-finetune.md` §6.4).
- **m6 — DreamBench++ binarization.** The graded-ratings→binary mapping is fixed in advance,
  verified against the actual scale during A2 (`judge-finetune.md` §7.4).
- **m7 — Adult-rater ethics + withdrawal cutoff.** Adult-participant protocol bundled into Stage 1;
  consent gains a data-lock/withdrawal-cutoff clause because a trained LoRA cannot be untrained
  (`RESEARCH_PROTOCOL.md` §9). The child assent's "you can stop any time" was quietly promising
  the impossible.

---

## Sequencing — what happens after the Phase 0.5 probes

Phase 0.5 is not just a build gate; it feeds three of these decisions. Order of operations:

1. **Probe 1 (kill criterion) passes** → substrate holds identity → Phase 1 opens **and** you get the *first
   effect-size estimate + first inter-rater α* from the rating-instrument dress rehearsal. → **This unblocks
   R2** (size the RQ5 reader N) and validates the rating instrument.
   - *If Probe 1 fails / Quill fails:* that is a **reportable finding**, not a catastrophe (see
     `PHASE_05_RESULTS.md` branches). The product's scope narrows and the paper gains its most interesting
     sentence. R2/R3 then apply to whatever regime survives.
2. **Probe 2 (seed determinism).** Confirms each endpoint reproduces — see m1. If either endpoint fails, drop
   the reproducibility claim from the affected method or change provider (do not silently keep the claim).
3. **In parallel, independent of the probes:** submit **Ethics Stage 1** (R4) and run the **citation
   verification** (R6). Neither needs the probes and both are on the critical path to the October defense.

**Bottom line for the proposal defense:** present R2–R9 (R1 is moot post-pivot) from this document as *known,
planned* risks. Solve none of them yet. The plan is the deliverable.
