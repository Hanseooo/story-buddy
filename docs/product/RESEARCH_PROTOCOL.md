# StoryBuddy — Research Protocol

**Status:** living document · **Audience:** the research track (corpus, annotation, study, ethics)
**Companions:** PRD v2 (what the product is) · ADRs (why each decision) · ROADMAP (when)
**Research design:** quantitative-developmental. **SDLC:** Boehm's Spiral Model — risk-driven, stage-gated
phases (see ROADMAP's guiding principles and phase gates); full treatment in `docs/capstone/methodology.md`.

This document exists so that nobody on the research track has to read an ADR to run a rating session.
It consolidates what was previously smeared across PRD §10 and ADR-008. Where they disagree, **ADR-008
wins and this document is wrong** — file an issue.

Target output format is **IMRaD / IEEE**, so the framing below is written to drop into an Introduction
and a Methods section, not into a Philippine Chapter-1 template.

---

## 1. The problem, in one paragraph

A child writes a story. The teacher marks it. It goes in a folder. Nobody reads it. Prior work on writing
motivation is unusually consistent that an **authentic audience** and **actual publication** are among the
strongest levers on children's writing engagement — and illustrating and publishing forty stories is not
something a Grade 5–6 teacher can do. StoryBuddy collapses the cost of publishing an illustrated version
of a child's story from *impossible* to three minutes and a few pesos.

**But the artifact is only worth publishing if it actually *is* the child's story.** Generative models
drift: the hero is a boy on page one and a different boy on page four; the dog changes breed; the style
shifts. An inconsistent picture book does not transmit the child's story — it transmits noise.

The technical problem and the educational benefit are therefore **the same claim viewed from opposite ends.**
That is what makes this research rather than integration.

## 2. The five objectives

The manuscript states five objectives; this document exists to operationalize them, not to invent research
questions on top of them. **There is no RQ apparatus.** Do not write "RQ1".."RQ6" in this document or in
any rating instrument.

1. **Implement** an orchestrated AI pipeline as the core processing framework of StoryBuddy.
2. **Produce** digital picture books from child-written stories through the implemented pipeline.
3. **Determine the acceptability** of the generated digital picture books in terms of presentation quality
   and classroom suitability, through **expert validation** (§5).
4. **Evaluate the character-consistency classification performance** of the fine-tuned lightweight
   vision-language model against human-established reference labels using **precision, recall, and
   F1-score (F1 primary)** (§6).
5. **Evaluate the software quality** of StoryBuddy using applicable **ISO/IEC 25010** quality
   characteristics (§6).

Objectives 1–2 are engineering — the pipeline exists and produces books; they are the build, covered by
PRD §5 and the ADRs, not re-litigated here. **Objectives 3, 4, and 5 are the three evaluation legs**, and
everything past this point in this document is in service of one of them.

Objective 3's "story faithfulness" and "narrative coherence" criteria are where the drift risk above gets
judged; Objective 4 is where the mechanism that is supposed to catch it in-flight — the consistency
judge — gets measured against human labels in its own right, independent of the books it helped produce.

## 3. What we claim, and what we must not

**Claim:** that the generated outputs are rated acceptable by expert validators on the five criteria
(Objective 3); that the fine-tuned consistency judge classifies character consistency against human
reference labels with reportable precision, recall, and F1 (Objective 4); and that the software is rated
acceptable on ISO/IEC 25010 (Objective 5).

**On Objective 4, the comparison against the zero-shot base model and the existing prompted baseline is
optional and secondary.** The headline finding is the fine-tuned judge's absolute agreement with human
labels (F1 primary). If a base/prompted comparison is reported, it sits beside that finding — it is not
itself the finding, and it is not "forbidden" or "build-gate only." ADR-018's δ = 3 non-inferiority test is
a separate, **deployment** gate deciding whether the fine-tuned judge replaces the prompted incumbent in
the product; it is a build decision, not a reported research finding.

**Do not claim a causal "the pipeline helped" effect.** There is no control arm and no pipeline-ON-vs-OFF
ablation (dropped, ADR-008). The output-quality and classification results describe the single generated
arm and the trained judge, not a comparison against a naive baseline.

**Do not claim learning gains.** The corpus is 15 stories collected from Grade 5–6 learners (10 primary +
5 backup, §8) — no non-illustrated control group, no pre/post design, no longitudinal window. Prior
literature on authentic audience is the **warrant** for why fidelity and acceptability matter; it is **not
a finding of this study**. Overclaiming here is the single most likely way the defense goes badly.

**Do not claim privacy preservation.** The child's text transits a hosted inference provider. Only
on-device generation could claim otherwise, and that is Future Work (ADR-015).

**Do not claim watermark provenance.** SynthID-Image has no open equivalent; C2PA is Future Work (ADR-001).

**Do claim the equity angle.** An open-weight, self-hostable pipeline carries **no per-seat vendor cost** —
the difference between a tool a well-funded private school buys and one a provincial public school can run.
That is the SDG-4 hook, and it is a design property, not a hope.

---

## 4. The three evaluation legs, in one table

| Objective | Question | Method | Respondents |
|---|---|---|---|
| 3 — acceptability | Are the generated picture books acceptable for presentation quality and classroom use? | Written open-ended interview form (Tool B) + content analysis, five criteria (§5) | Expert validators: Dean/Professor of the Arts College, one Arts student/intern, one Education student/intern |
| 4 — judge classification | How well does the fine-tuned judge classify character consistency against human reference labels? | Precision / recall / F1 (F1 primary) on the character-disjoint held-out set; optional comparison vs zero-shot base + existing prompted baseline (§6) | None — model evaluated against researcher-established reference labels |
| 5 — software quality | Is StoryBuddy's software quality acceptable on ISO/IEC 25010? | 5-point Likert questionnaire (Tool C), five characteristics, weighted mean + SD (§6) | Designated software-quality evaluators (separate from the expert validators) |

**Objectives 1–2 sit outside this table, and are verified by Tool A.** They are the built artifact, not an
evaluation leg with respondents. The **Functional Verification Matrix** records system-generated pass/fail per
functional category as `Successful ÷ Total × 100`, over **fixture stories** — so it carries no ethics load and
is defensible in October ahead of the corpus. ⚠️ **A Pass means the stage executed and emitted valid output,
never that the judge approved it** — for scene generation a Pass includes a page the judge flagged and
best-of-fell-back on. Scoring Tool A by judge approval would make it a second judge-scored instrument and
break non-circularity (ADR-004). Spec: `docs/specs/functional-verification-matrix.md`.

**Instrument delivery.** Objective 4's labels are collected in the `(research)/annotate/` surface, with
`adjudicate/` for the third researcher; Objective 3's stimuli are served blinded (provenance stripped, order
shuffled per validator) from `(research)/books/`, though its **responses stay on paper** — the instrument is
open-ended prose, not a form. Objective 5's questionnaire is administered by form. Tool A is an offline
script. There is no researcher dashboard. See **ADR-026** and `docs/specs/annotation-surface.md`.

**Scene coverage and under-length handling are described pipeline behaviours, not measured objectives.**
How completely the system's selected scenes cover a story's major plot points, and how gracefully the
system handles under-length stories without inventing content, are properties of Scene Segmentation
described in methodology (PRD §5.1, §8; ROADMAP Phase 1) — they carry no standalone instrument or
evaluation leg.

**Objective 3 is never scored using the judge.** The judge drives regeneration inside the pipeline; using
it as the outcome measure for the outputs it helped produce would be circular. Objective 3's acceptability
rating is the expert panel's; the judge's own accuracy is the separate Objective 4 question, measured on a
human-labeled, character-disjoint held-out set. This is the sharpest question a panel will ask — the answer
lives in ADR-004 and is repeated here so it is never improvised.

---

## 5. Objective 3 — Expert validation

- **Respondents.** Purposively selected expert validators from the Arts and Education colleges: the
  **Dean/Professor of the Arts College**, one **Arts student/intern**, and one **Education student/intern**.
  Arts-sector validators judge visual/artistic presentation; the Education-sector validator judges
  educational suitability.
- **Instrument.** A **written, open-ended interview form** (**Tool B**) — not a scored ordinal
  rubric.
- **Analysis.** **Content analysis.** Pre-set categories from the five criteria below; each written
  response is coded **positive feedback / negative feedback / suggestion for improvement** and tallied per
  criterion.
- **Five criteria:** narrative coherence, story faithfulness, visual presentation, visual style
  consistency, suitability for classroom use.

This replaces the earlier feature-level scored rubric (1–5 ordinal ratings, CVI, Krippendorff's α), which
is dropped. There is no reader-recall or comprehension instrument riding alongside it — Objective 3's
"story faithfulness" and "narrative coherence" criteria are where fidelity is judged, by the expert
validators, not by a naive-reader recall session.

---

## 6. Objective 4 — Judge classification, and Objective 5 — ISO/IEC 25010

### Objective 4 — judge classification

- **Model.** **Qwen2.5-VL-7B-Instruct**, fine-tuned with **QLoRA**, binary character-consistency
  classification.
- **Labels.** `1 = Different Character`, `0 = Same Character` (the `different_character` class is the
  positive class; the schema field `same_character: bool` encodes the same distinction — one int, one
  bool, same fact, stated once so it never needs re-deriving).
- **Annotation.** Two researchers annotate independently; disagreements resolved via the established
  criteria procedure (`docs/specs/judge-finetune.md`).
- **Split.** **Character-identity level** (train / validation / held-out test) — the same identity never
  appears in two subsets (leakage control).
- **Metrics.** **Precision, recall, F1 — F1 is the primary summary metric.**
- **Optional, secondary comparison.** Fine-tuned vs **zero-shot base model** vs the **existing prompted
  Consistency Judge baseline**, on the same held-out pairs and human labels. This sits beside the
  fine-tuned model's absolute agreement with human labels — it is not itself the headline finding, but it
  is permitted, not forbidden. (The prompted baseline is unnamed in the manuscript; these docs may keep
  the concrete `gemma-3-27b-it` name internally.)
- Structured output includes the classification plus a failure-reason taxonomy (`judge-finetune.md` §4).

ADR-018's δ = 3 non-inferiority test still runs — as a **deployment** gate deciding whether the fine-tuned
judge replaces the prompted incumbent in the product — but that is a build decision, not a reported
finding of Objective 4.

### Objective 5 — ISO/IEC 25010 software quality

- **Five applicable characteristics:** Functional Suitability, Performance Efficiency, Usability,
  Reliability, Security.
- **Instrument (D):** **5-point Likert (1 = Poor … 5 = Excellent).**
- **Analysis:** descriptive statistics — **weighted mean + standard deviation** per characteristic,
  interpreted against the manuscript's Table 4 bands: **4.20–5.00 Excellent · 3.40–4.19 Very Good ·
  2.60–3.39 Good · 1.80–2.59 Fair · 1.00–1.79 Poor.**
- **Respondents:** **designated software-quality evaluators** (IT practitioners and teachers), separate
  from the Objective 3 expert validators.

---

## 7. Respondents, roles, and corpus role

Three respondent groups, three roles — none of them overlap:

| Group | Role | Contributes to |
|---|---|---|
| Grade 5–6 learners | Write **original stories only** — no validation/evaluation role | Corpus (§8) |
| Expert validators (Dean/Professor of Arts College, Arts student, Education student) | Written open-ended interview + content analysis | Objective 3 |
| Designated software-quality evaluators (IT practitioners, teachers) | ISO/IEC 25010 questionnaire (Tool C) | Objective 5 |

Learners are anonymized and assigned unique IDs at intake (§9); they never see, rate, or comment on any
generated book, their own or anyone else's — the classroom gallery is display-only (ADR-021) and carries
no research instrument. Objective 4 has no human respondent group of its own — it evaluates the trained
model against researcher-established reference labels (two researchers annotate independently per §6).

---

## 8. Corpus

Test stories must be **real or realistic child writing**, not builder-authored clean prose (which measures
best-case only). Grade 5–6, English with Taglish code-switching tolerated.

**Target: 15 stories collected, split into 10 primary corpus + 5 backup.** Collected from qualified
**Grade 5 & 6 learners** at **Matina Aplaya Elementary School**. Learners submit **original stories only**
— no validation/evaluation role; anonymized and assigned unique IDs at intake. **Do not use the old
"~50 (60–70) donated stories" numbers anywhere** — that target belonged to the dropped comparative judge
study design and no longer applies.

**Locale.** Stories are collected at **Matina Aplaya Elementary School**; system development and
evaluation take place at **Holy Cross of Davao College (HCDC)**, Davao City, Philippines.

**This is a recruitment decision and it is unfixable later.** By Phase 2.5 the corpus is closed. Ask for
the extra stories at Stage 1.

**One corpus, two uses:** the primary corpus (10 stories) is the evaluation stimuli behind Objective 3 (the
expert panel judges the books produced from it), and — once the pipeline has drawn it and researchers have
labelled the drawings — the corpus (primary + backup, and the characters in them) is also the source of the
judge's Objective 4 training and evaluation data. Corpus = **donated child writing + researcher labels**
(ADR-008); researcher-written stories appear only as judge-training-split augmentation, never as evaluation
stimuli. The split itself is **character-disjoint** (train / validation / held-out test); exact split
counts are a planning target owned by `docs/specs/judge-finetune.md`, not restated here. This is why §9's
consent clause is not optional.

**Primary source: Stage-1 story donation (§9).** Document provenance — reviewers will ask.

**PII redaction at intake (added 2026-07-13).** Donated stories are redacted **manually on
receipt** — one researcher redacts real names, addresses, school names, and contact details before
the story is stored; a second researcher spot-checks. This step is independent of the product's
automated Presidio stack, which is a Phase-2 deliverable and does not exist when the corpus starts
arriving. Fictional character names are kept (they are the story); names co-occurring with
real-world anchors (addresses, phone numbers, "ako si… taga…" framings) are treated as real.

**Insurance, if Stage 1 slips:** researchers writing deliberately as ten-year-olds (including messy and
non-linear ones), or a public children's-writing dataset. **Survey what actually exists before assuming one
does** — one researcher, one day. Many candidates turn out to be L2-learner essays or published books rather
than child writing.

---

## 9. Ethics — two stages, and why

The original single submission contained a hidden dependency: the corpus is real child writing, and the
Grade 5–6 learners who write it are the only respondent group requiring guardian consent. Separating their
low-risk story-donation role from any evaluation role keeps the corpus — and everything downstream of it —
from stalling on a heavier review it doesn't need.

**Stage 1 — story donation.** Children write stories. They never touch the system, never see each other's
work, never validate or rate any output. We collect anonymized text and nothing about the child. Narrow,
low-risk, comparatively fast. **Unblocks:** corpus → Objective 3's evaluation stimuli → the judge's
training labels (Objective 4).

> **The Stage-1 consent form must state that donated stories may be used to build and evaluate an AI model.**
> Training on participant data without that clause is a violation, not a technicality. It costs one sentence,
> and there is no retroactive fix. (ADR-018, `docs/specs/judge-finetune.md` §12.)

**Why the clause is required, in one sentence:** the donated story is turned into illustrations, those
illustrations are labelled by researchers, and those labels become weights in a model we ship — so the
child's creative content flows into the model, and anonymising the child's *name* does not change that.

Draft language, to be adapted to the ethics board's template:

> *Guardian consent.* Your child's story may be used to generate pictures. Researchers will look at those
> pictures and mark whether the characters were drawn correctly. Those markings may be used to build,
> train, and evaluate a computer program (an artificial-intelligence model) that checks whether pictures
> match a story. The program may be used in future research and in the StoryBuddy application. Your child's
> name and any personal details will be removed before this happens and will never appear in the program,
> in any picture, or in any publication.

> *Child assent (age-appropriate).* We will use a computer to draw pictures for your story. Some grown-ups
> will look at the pictures and say if they look right. That helps us teach the computer to draw better. We
> will not use your name. You can say no, and you can stop any time.

**If stories are collected before this clause is in the signed form, the only lawful options are to
re-consent every child or to delete the data.** Do not plan around a fix that does not exist.

**Withdrawal cutoff (added 2026-07-13 — required, because a trained model cannot be untrained).**
The consent form states a **data-lock date** — the start of image-pair labelling (Phase 2.5).
Withdrawal before that date removes the story entirely. Withdrawal after it deletes the story and
every label derived from it from all datasets and excludes them from any future training, but
models already trained are retained — machine unlearning cannot be promised, and promising it
anyway is a violation waiting for a DPA reviewer to find. Draft additions:

> *Guardian consent (append):* You may withdraw your child's story at any time. If you withdraw
> before **[data-lock date]**, the story is removed completely. After that date, the story and all
> markings made from it will be deleted from our records and never used again, but a computer
> program that has already been trained cannot have the training removed.

> *Child assent (replace the last sentence):* You can say no, and you can stop any time. If you
> change your mind before **[date]**, we will take your story out.

**Adult participants need a protocol too (added 2026-07-13).** The **expert validators** (Objective 3, §5)
and the **designated software-quality evaluators** (Objective 5, §6) are human-subjects data collection;
most boards require review or a formal exemption even at minimal risk. **Bundle the adult-respondent
protocol (recruitment, consent, session structure, instruments) into the Stage-1 submission** or file it
in the same envelope — otherwise these evaluation legs still have an unfiled dependency.

**Stage 2 — system use.** Children use StoryBuddy and read classmates' books in the display-only gallery.
Interactive, peer-visible, child-authored content (their own storybook). A materially heavier review.
**Gates:** in-classroom system use only — it gates no evaluation leg (Objectives 3–5 run on the expert
validators and the software-quality evaluators, not on the learners).

**Both stages require guardian informed consent *and* age-appropriate child assent** (**Data Privacy Act of
2012, Republic Act No. 10173** + the university ethics board). Removing parental controls from the
*product* (ADR-017) did not remove parental consent from the *research*; adding peer sharing made Stage 2
heavier, not lighter.

**File Stage 1 immediately.** It is the long pole.

---

## 10. Recruitment

**Learners (corpus, §8).** Stories are collected at **Matina Aplaya Elementary School**, from qualified
Grade 5–6 learners. Their only role is writing their own story — no validation or evaluation role in
Objectives 3–5.

**Expert validators (Objective 3, §5).** Purposively selected: the Dean/Professor of the Arts College, one
Arts student/intern, one Education student/intern — recruited through **Holy Cross of Davao College
(HCDC)**, Davao City, where system development and evaluation take place.

**Software-quality evaluators (Objective 5, §6).** Designated separately from the expert validators, drawn
from IT practitioners and teachers.

A classroom-level intervention study, or recruitment beyond the named institutions, would need a broader
ethics footprint. That is a bigger thesis than this one.

---

## 11. Scope and delimitation

**Grade 5–6 (ages 10–12), Philippines, English with Taglish tolerated.** This is derived from the
objectives, not chosen for convenience, and each boundary is load-bearing:

- They **write independently** → the story is unambiguously the child's. Scaffold a Grade 2 student and
  Objective 3's story-faithfulness criterion is meaningless: whose story did we illustrate?
- They **read fluently** → they can author at length, and the books produced from their stories are
  substantive enough for expert validators to judge coherence and faithfulness against.
  *(This boundary originally rested on in-app peer comprehension, which is cut — §7, ADR-021. It survives
  on authoring fluency, not on the cut instrument.)*
- **English is the medium of instruction** from Grade 4 (DepEd) → one language, one moderation regime, one
  TTS voice.
- They are **pre-adolescent** → age-appropriate content and interaction design throughout.

At a 15-story corpus the study cannot stratify by age, and age is one of the largest sources of variance in
children's writing. Broadening the band would add variance, not generality. **A tight population is a
delimitation, not an apology** — and "anyone can use it" was never true anyway: word cap, reading level,
moderation thresholds, failure copy, and narration voice are all calibrated to a band.

---

## 12. Metrics

| Metric | What it measures | Source |
|---|---|---|
| Expert validation (Objective 3) | Positive / negative / suggestion tallies per criterion (narrative coherence, story faithfulness, visual presentation, visual style consistency, classroom suitability) | Content analysis of Tool B responses |
| Judge classification (Objective 4) | Precision, recall, F1 (F1 primary) vs human reference labels, character-identity-level split | Held-out test set; optional comparison vs zero-shot base + prompted baseline |
| Software quality (Objective 5) | Weighted mean + SD per ISO/IEC 25010 characteristic (Functional Suitability, Performance Efficiency, Usability, Reliability, Security), interpreted against Table 4 bands | Tool C, designated software-quality evaluators |
| Generation Time | Submission → completed storybook | Instrumentation (Langfuse) |
| AI Resource Usage | Avg generation time, image count, regen count | Instrumentation (Langfuse; `Cost.image_count` / `Cost.regen_count`) |
| AI Resource Usage — cost | API cost/story | ⚠️ **not instrumented** (see below) |

> ⚠️ **One row requires instrumentation that does not exist yet (2026-07-22).** Do not report it until it
> does; if it never lands, drop it from Methods rather than estimating.
> - **API cost/story.** `Cost.usd_estimate` is declared in `docs/specs/story-memory-contract.md`, but
>   `backend/providers.py` does **no** token or cost accounting and no spec owns populating the field.
>   Needs a per-call token/price capture at the provider boundary before this metric is producible.
>
> Generation time, image count and regen count **are** covered: Langfuse tracing is wired and
> `Cost.image_count` / `Cost.regen_count` are in the Story Memory contract.

---

## 13. Pre-registration

**Write the analysis plan — hypotheses, baselines, metrics, and success criteria — before running anything.**

For Objective 4, pre-registration is what makes the reported F1 trustworthy: the human labels carry
reported inter-rater reliability, and the held-out set is **read once**, against an analysis plan fixed in
advance — so the reported precision/recall/F1 figures are the ones committed to, whatever they turn out to
be. The optional base/prompted comparison, if reported, follows the same discipline. The same rigor governs
Objective 3: the five criteria and the content-analysis coding scheme are fixed before data collection, so
a weak result is a finding, not a fudge.

Almost no capstone does this. It is the cheapest defensive move available.

---

## 14. Anticipated defense questions

| Question | Where the answer lives |
|---|---|
| "Isn't this just an API wrapper?" | Objective 3's expert validation (§5) rates the outputs the architecture actually produces, not a bare API call. |
| "Isn't the fine-tuned judge circular?" | ADR-004 non-circularity note. **Objective 3's expert validation is never scored using the judge.** |
| "Does it improve children's writing?" | We do not claim that (§3). Prior work is the warrant; acceptability is the finding. |
| "Only fifteen stories?" | §8 — the corpus size is a recruitment reality, not a design choice; Objective 3's expert panel needs only the 10-story primary corpus, and Objective 4's character-disjoint split is the more demanding downstream consumer. |
| "Is a LoRA on ~1,000 examples meaningful?" | Character-disjoint splits, multiple baselines, CIs, a pre-registered plan (§13). |
| "Why not train on an existing dataset?" | None exists for this task. Surveyed and rejected with reasons: `judge-finetune.md` §5.1. |
| "Isn't your training data just the model's own output?" | Positives are **human-confirmed**, never auto-labelled. That is the shortcut, and we name it. |
| "So is your fine-tuned judge better than the prompted 27B?" | Objective 4's headline finding is the fine-tuned judge's **absolute agreement with human labels** (F1 primary). A base/prompted comparison is optional and secondary, not the finding. Whether it replaces the prompted incumbent *in the product* is a deployment gate (ADR-018's δ = 3), not a finding of this study. |
| "**DINOv2 beat your judge on F1.**" | Then it is a finding about metrics, not a product decision. DINOv2 emits a scalar; ADR-010's regeneration controller needs `failure_reasons` to correct a prompt. A cosine cannot say "restate the scarf." Pre-declared: `judge-finetune.md` §7.3. |
| "Did you pick the test set after seeing results?" | The split, the stratification, and the primary endpoint were timestamped before the first label was collected. The held-out set was read once. |
| "Why not just use GPT/Gemini?" | Open-weight mandate (ADR-015) — and the equity claim it enables (§3). |
| "Why only Grade 5–6?" | §11. Each boundary is derived from the objectives. |
| "What if the image model can't hold non-human characters?" | Phase 0.5 kill criterion. We looked, cheaply, before building. |
