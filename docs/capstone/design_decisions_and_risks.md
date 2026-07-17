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
| **R1** | Ablation is a 3-component *bundle* presented as a single-variable test | High | Before generation run (Phase 3) | **Owner-accepted (3 arms, 2026-07-13)** — pending adviser |
| **R2** | RQ5 (outcome of record) underpowered; no RQ5-specific power analysis | High | After Phase 0.5 (needs effect size) | Blocked on Phase 0.5 |
| **R3** | RQ5 primary outcome (plot recall) may be blind to the fix (character identity) | High | Before pre-registration sign-off | Recommendation ready (now applies *within* R7's image-only instrument) |
| **R4** | RQ6 (fine-tune) is load-bearing but 4 hops past a months-long ethics gate | High | Ethics Stage 1 submission (now) | Recommendation ready |
| **R5** | Novelty/gap claim has a thin related-work moat; one sub-claim was falsifiable | Medium | Before final defense | Partially fixed |
| **R6** | Unverified arXiv citations + gap-claim overstatement in *frozen* docs | Medium | Before any Word export | Action list ready |
| **R7** | RQ5's "naive reader" reads the story text via verbatim captions — both recall outcomes contaminated | High | Before pre-registration sign-off | **Owner-accepted (image-only sessions, 2026-07-13)** — pending adviser |
| **R8** | Presidio redacts *fictional* character names → breaks captions, narration, RQ5 scoring | Medium | Before Phase-2 PII/moderation specs | **Owner-accepted (context-gated redaction, 2026-07-13)** |
| **R9** | Rater-assignment matrix undesigned (IRR overlap × RQ5 naivety × fatigue caps jointly set the real N) | Medium | With R2, before pre-registration | Design task ready |
| m1–m3 | Minor: seed cross-endpoint · α-gate validity · "meant to tell" vs "wrote" | Low | Before final defense | Noted |
| m4–m7 | Minor: test-set access policy · checkpoint-selection rule · DreamBench++ binarization · adult-rater ethics + withdrawal cutoff | Low | Pre-registration / Stage-1 submission | **Drafted into docs 2026-07-13** — need sign-off |

---

## R1 — The ablation bundles three components but is described as single-variable

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

**Recommendation.** (b). **Decision status:** `OWNER-ACCEPTED (2026-07-13)` — three arms
(OFF · REF-ONLY · FULL). Pending adviser sign-off before the Phase 3 generation run. Note the cost
that matters is not the ~$10 of generation but the **+50% blind-rating workload** — factor it into
R2/R9's rater budget. Side benefit: REF-ONLY vs FULL is a within-model comparison
(`qwen-image-edit` in both), which contains the model-identity confound in m1 (OFF runs
`fal-ai/qwen-image`, a sibling checkpoint, not the same weights with conditioning removed — state
this in Methods).

---

## R2 — RQ5, the outcome of record, is underpowered

**Panel's question.** *"Each reader reads one book; N ≈ 15–30 total, between-subjects → ~8–15 per arm across
~50 stories. Most stories are read once or not at all. A Mann–Whitney U on ~10 vs ~10 with story as a random
effect has almost no power. A null on your headline outcome would be uninterpretable — underpowered-null looks
identical to substrate-null."*

**Root cause.** The only power statement (`methodology.md` §9) sizes the *RQ2 rating* load from the Phase 0.5
effect estimate — it does **not** size the *RQ5 reader* load, which is far larger because RQ5 is
between-subjects and each reader is a single datapoint.

**Options.**
- **(a)** Compute the required RQ5 reader N explicitly once Phase 0.5 yields an effect estimate, and state
  openly it is probably the binding N of the whole study.
- **(b) — RECOMMENDED, combine with (a)** Revise "one book per reader." You correctly rejected *within-reader,
  same story* (a reader who saw ON already knows the plot). But *within-reader, **different** stories* is
  clean: one reader reads several *different* books, never the same story twice, conditions counterbalanced.
  Each reader then contributes multiple datapoints and power multiplies — with **no** contamination. The
  §6.3 rule appears to have conflated these two cases.

**Recommendation.** (a)+(b). **Decision status:** `BLOCKED ON PHASE 0.5` for the number; the design change (b)
can be decided now. Needs adviser sign-off (changes pre-registration).

---

## R3 — RQ5's primary outcome may be insensitive to the exact thing the pipeline fixes

**Panel's question.** *"Your intervention improves character *identity consistency*. Your pre-registered
*primary* outcome is *plot-point* recall. But a reader recovers 'a boy found treasure' even if the boy looks
different on every page — plot recall is robust to character drift. You could get a null on your primary while
your secondary (character recall) moves, and pre-registration will have locked plot as primary."*

Not addressed anywhere in the current docs. This is a self-inflicted risk and it is **free to fix now**,
because the pre-registration is not yet signed.

**Recommendation.** Make **character recovery co-primary** (or primary) — it is the causally-proximal outcome
of a character-consistency intervention. Keep plot-point recall as the "does it still hold the narrative"
secondary. Pre-register **both**, with this rationale stated, so neither looks like post-hoc selection.

**Decision status:** `PENDING` — adviser sign-off before pre-registration is timestamped.

---

## R4 — RQ6 (the fine-tune) is load-bearing but the most timeline-fragile piece

**The problem.** RQ6 sits four hops past the long pole: *Ethics Stage 1 → corpus → a Phase 1 run → image-pair
labelling → train.* The docs frame RQ6 as integral ("instrument validity… one study, not six") and, unlike
Tier-2 children, do **not** mark the *research question* droppable. With the final defense ~4–5 months out and
Ethics Stage 1 taking "months," RQ6 is what fails to finish if anything slips. No document reconciles the
calendar.

**Recommendation — two parts.**
1. **Submit Ethics Stage 1 now.** It is the only thing on the critical path that cannot be compressed by
   working faster. Everything after `images` is a weekend; everything before it is months.
2. **Build the explicit de-scope position that RQ2 + RQ5 are a complete, defendable study on their own**, with
   RQ6 as the *reach* contribution. Rung C ("fine-tune loses to prompted Gemma, keep prompting") is honest and
   publishable for a *paper*, but a *capstone must be done by a date* — you need a story that survives RQ6 not
   finishing. The current framing forbids that retreat; loosen it.

**Decision status:** `PENDING` — (1) is an action to take immediately; (2) needs a framing decision with your
adviser. Confirm your actual defense date against the ethics timeline.

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

## R7 — RQ5's naive reader reads the story text: captions contaminate both recall outcomes

**Panel's question.** *"Your 'naive reader who has never seen the story text' is handed a book whose
captions ARE the story text, verbatim (ADR-013), identical in both arms. Character names and plot
events are recoverable from the captions alone. What exactly does your outcome of record measure —
the visual pipeline, or reading comprehension?"*

This is the structural version of R3: not "the primary outcome might miss the effect" but "*both*
recall outcomes measure a channel the ablation never touches." Likely empirical signature: high
recall in both arms, an uninterpretable null on the study's dependent variable of record.

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

~50 stories × 3 arms (R1) ≈ 150 books; blind ratings on 5 dimensions plus RQ5 comprehension, from
a pool of 15–30 adults, under interacting constraints: IRR needs overlap (α is uncomputable on
disjoint assignments); RQ5 readers must be naive to the story (a rater who rated any arm of story X
is burned for story X); R2(b)'s multi-book readers must never see the same story twice,
counterbalanced; methodology §5.2's fatigue caps bound books-per-rater. These jointly determine the
required N — and the *structure* is independent of effect size, so it can be designed now rather
than after Phase 0.5.

**Recommendation.** A one-page assignment design (raters × stories × arms; overlap fraction for α;
RQ5-naivety bookkeeping) inside the `tier1-rating-harness` spec, before pre-registration. R2's
power answer is meaningless without it.

**Decision status:** `DESIGN TASK` — no adviser decision needed, just the page.

---

## Minor items (m1–m3)

- **m1 — Seed comparability across endpoints.** Probe 2 verifies each endpoint (`edit_image`, `text_to_image`)
  reproduces *on itself*. It does **not** establish that a matched seed means the same starting state *across*
  a text-to-image vs an image-edit endpoint — the fairness assumption RQ2 leans on. If REF-ONLY is added (R1),
  ON and REF-ONLY share the edit endpoint, which strengthens the within-edit comparison. State the
  cross-endpoint seed caveat as a limitation rather than an equivalence claim.
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
   R2** (size the RQ5 reader N) and validates the R1 rating instrument.
   - *If Probe 1 fails / Quill fails:* that is a **reportable finding**, not a catastrophe (see
     `PHASE_05_RESULTS.md` branches). The product's scope narrows and the paper gains its most interesting
     sentence. R2/R3 then apply to whatever regime survives.
2. **Probe 2 (seed determinism).** Confirms each endpoint reproduces. Necessary but **not sufficient** for R1's
   cross-arm fairness — see m1. If either endpoint fails, drop the reproducibility claim from RQ2's method or
   change provider (do not silently keep the claim). Decide R1's arm structure with the Probe 2 result in hand,
   since a 3-arm design shares the edit endpoint for two of the three arms.
3. **In parallel, independent of the probes:** submit **Ethics Stage 1** (R4) and run the **citation
   verification** (R6). Neither needs the probes and both are on the critical path to the final defense.

**Bottom line for the proposal defense:** present R1–R6 from this document as *known, planned* risks. Solve
none of them yet. The plan is the deliverable.
