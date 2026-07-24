# StoryBuddy — Research Protocol

**Status:** living document · **Audience:** the research track (corpus, annotation, study, ethics)
**Companions:** PRD v2 (what the product is) · ADRs (why each decision) · ROADMAP (when)

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

## 2. The central question

> **Does an automated consistency-verification-and-correction loop produce picture books faithful enough
> that other readers recover the story the child meant to tell?**

- **RQ5** (naive-reader recall) is the **fidelity outcome** — does the generated book, on its own, transmit
  the child's characters and events to a reader who never saw the source text?
- **RQ3** (expert panel + ISO/IEC 25010) is **output quality** — are the generated books good?
- **RQ6** (judge agreement with human labels) is **descriptive instrument validity** — reported, not
  compared. Its fine-tuned-vs-baseline comparison was dropped as a research claim (ADR-008, revised
  2026-07-22).

RQ1 and RQ4 are supporting. **RQ2 (the pipeline ON-vs-OFF ablation) is dropped** — see ADR-008. **There is
no primary comparative study**: RQ5 + RQ3 answer Objective 3 (evaluate the generated outputs), ISO/IEC
25010 answers Objective 4 (software quality). This is **one study**, not six.

## 3. What we claim, and what we must not

**Claim:** that the generated outputs are rated acceptable by an expert panel (RQ3), that a naive reader can
recover the child's characters and events from the generated book alone (RQ5), and that the software is
rated acceptable on ISO/IEC 25010 (Objective 4). RQ6 is reported **descriptively** — the fine-tuned judge's
agreement with human labels on the character-disjoint held-out set.

**Do not claim the fine-tuned judge matches or beats a prompted 27B incumbent** (ADR-008, revised
2026-07-22). That comparison is dropped as a research claim; the paper reports agreement, not a contest.
ADR-018's δ = 3 non-inferiority test still runs — as a **deployment** gate deciding whether the fine-tuned
judge replaces the prompted incumbent in the product — but it is a build decision, not a reported finding.

**Do not claim a causal "the pipeline helped" effect.** The pipeline-ON-vs-OFF ablation (RQ2) is dropped
(ADR-008); there is no control arm, and the October type-A defense does not require one (roadmap §0.8). The
output-quality and fidelity results describe the single generated arm, not a comparison against a naive
baseline.

**Do not claim learning gains.** N ≈ 8–15 children, no non-illustrated control group, no pre/post design,
no longitudinal window. Prior literature on authentic audience is the **warrant** for why fidelity matters;
it is **not a finding of this study**. Overclaiming here is the single most likely way the defense goes badly.

**Do not claim privacy preservation.** The child's text transits OpenRouter to an upstream host. Only
on-device generation could claim otherwise, and that is Future Work (ADR-015).

**Do not claim watermark provenance.** SynthID-Image has no open equivalent; C2PA is Future Work (ADR-001).

**Do claim the equity angle.** An open-weight, self-hostable pipeline carries **no per-seat vendor cost** —
the difference between a tool a well-funded private school buys and one a provincial public school can run.
That is the SDG-4 hook, and it is a design property, not a hope.

---

## 4. Research questions

| RQ | Question | Tier | Instrument |
|---|---|---|---|
| RQ1 | How accurately does the system identify key scenes from child-written stories? | 1 | Story Completeness vs. annotated major plot points |
| RQ3 | How acceptable are the generated outputs (coherence, consistency, illustration quality, usability)? | 1 | Expert-panel feature-level ratings (Instrument A) for coherence/consistency/illustration quality; usability is measured separately via the ISO/IEC 25010 evaluator questionnaire (Instrument D, methodology §6.4), administered to IT practitioners and teachers — never by the expert panel |
| RQ4 | How gracefully does the system handle **under-length** stories without inventing content? | 1 | Scene-count floor behavior on short corpus items |
| RQ5 | Can a naive reader recover the author's characters and events from the generated book alone? | 1 (adults) | Single-arm naive-reader recall vs. RQ1's plot points; two raters, Cohen's κ |
| **RQ6** | How well does the fine-tuned open VLM judge agree with human labels on the character-disjoint held-out set — overall and on the **non-human** slice? | — | **Descriptive only** (ADR-008, revised 2026-07-22) — agreement (F1/κ) with human labels, character-clustered bootstrap CI, held-out set **read once**, IRR on the human labels reported. **No comparative claim** against the zero-shot base or prompted Gemma-27B. The δ = 3 non-inferiority test remains a **deployment** gate (ADR-018 amendment a, `docs/specs/judge-finetune.md` §7), not a reported finding |

**The output evaluation is never scored using the judge.** The judge drives regeneration inside the
pipeline; using it as an outcome measure would be circular. The output-quality outcomes are the expert
panel + ISO/IEC 25010 ratings (RQ3) and RQ5's naive-reader recall — neither of which the judge optimizes.
This is the sharpest question a panel will ask — the answer lives in ADR-004 and is repeated here so it is
never improvised.

---

## 5. Design: the two evaluation legs

Output quality is evaluated **directly on the generated books**, not by an ON-vs-OFF ablation (dropped —
ADR-008):

- **Expert panel (RQ3).** 1 professor + 1 education student + 1 art student rate the storybooks,
  illustrations, and story consistency with feature-level rubrics (Instrument A). This is the
  panel-requested "evaluate the generated outputs" leg — outputs, not internal pipeline components.
  RQ3's usability dimension is measured separately, by the ISO/IEC 25010 software-quality questionnaire
  (Instrument D) administered to IT practitioners and teachers — never by this panel.
- **Software quality (Objective 4).** The ISO/IEC 25010 questionnaire (Instrument D), administered to IT
  practitioners and teachers. This is Objective 4's whole content (ADR-008, revised 2026-07-22).

**RQ6 is no longer a leg** (ADR-008, revised 2026-07-22). The fine-tuned Qwen2.5-VL-7B judge is still
trained and its **agreement with human labels on the character-disjoint held-out set is reported
descriptively**; the comparison against its zero-shot base and prompted Gemma-27B is not a research claim.
Full treatment in ADR-018 and `docs/specs/judge-finetune.md`.

RQ5 (§7) adds the reader-side fidelity measure: a naive reader is given the generated book alone and asked
to recall its characters and events, scored against the same human-annotated plot points RQ1 requires.

---

## 6. Tiers

### Tier 1 — adults (N ≈ 15–30). **Carries RQ1, RQ3, RQ4, RQ5, RQ6. Designed to stand alone.**
Expert-panel and blind scored ratings of narrative coherence, visual consistency, illustration quality,
story completeness, plus the RQ5 comprehension instrument. **Inter-rater reliability defined up front** for
"major plot points" (Cohen's / Krippendorff's).

### Tier 2 — children (N ≈ 8–15). **Enrichment. May slip without sinking the capstone.**
- **Validated instruments:** Fun Toolkit (Read & MacFarlane) — Smileyometer (liking) + Again-Again (engagement proxy). Cite in Methods.
- **Story fidelity item** (author-only): "Did the book tell the story you wanted to tell?"
- ~~**Peer comprehension**, in-app: the same RQ5 instrument, answered by classmates.~~ **Cut as an RQ5
  instrument (ADR-008/ADR-021, 2026-07-20).** RQ5 is now a single-arm naive-reader recall measure scored on
  Tier-1 adult readers (§7, ADR-008), so the in-app peer-comprehension instrument isn't needed. The gallery
  is display-only (ADR-021, revised 2026-07-21) — there is no in-product reflection surface at all.
- **Behavioral logging** (more reliable than child self-report): completion rate, time-on-task, spontaneous
  second-story starts, "try again" frequency. Watch the novelty confound — repeat use *within* a session
  matters more than first-reaction delight. The child operates the app directly (ADR-017, reversed
  2026-07-20), so this data is collectable — but it stays **Tier-2 enrichment gated on Ethics Stage 2**,
  tied to no research question, and post-October.

---

## 7. The RQ5 comprehension instrument

A reader who has **never seen the story text** is given the book alone, then asked:

1. **Who was the story about?** (free recall of characters)
2. **What happened?** (free recall of events)
3. *What did you learn / what can you say about the story?* — reflective, not scored; retained as a
   qualitative source.

Scoring: recalled characters and events are matched against the **human-annotated major plot points** —
**the same annotation RQ1 already requires.** One annotation, two uses. **Plot-point recall is the
primary outcome; character recovery is secondary/confirmatory** (owner decision, `design_decisions_and_risks.md`
R3, 2026-07-20) — RQ5 is one of Objective 3's two output measures, alongside the expert panel (ADR-008,
revised 2026-07-22: with RQ6 demoted there is no headline comparative study for RQ5 to sit behind).

> ⚠️ **Owner-accepted change pending adviser sign-off (2026-07-13 — `design_decisions_and_risks.md` R7):**
> comprehension sessions present the book **with captions stripped** (images and page order only).
> The captions are the child's verbatim text (ADR-013); a captioned book lets the reader recover
> characters and plot from the text channel alone, which would inflate recall regardless of the
> illustrations' fidelity. Image-only sessions isolate the visual channel — the one this study's
> consistency claims are actually about. The shipped artifact keeps captions; Methods states the
> deviation. Do not timestamp the pre-registration before this is signed off.

**Character-recovery scoring (draft for the annotation guide — ⚠️ confirm with adviser):** scored
over **major characters** — named characters participating in ≥ 2 annotated major plot points —
which aligns the denominator with what the ≤ 2-canonical-reference Character Bible can actually
act on. Recovery over *all* annotated characters is reported descriptively. Minor characters are
un-conditioned by the Character Bible, so including them dilutes rather than biases the measure.

Two properties worth stating in Methods. First, **the reader need not be a child**, which is why RQ5 runs on
Tier-1 adults and survives an ethics delay. Second, **asking the author "did it match your intent?" is a
weaker instrument** — authors know what they meant and will read it into any illustration. A naive reader cannot.

**The sharing feature and this measure are independent.** RQ5 needs a reader, a book, and a questionnaire —
that is the Tier-1 harness. If in-app sharing slips, the research does not.

> **Open alternative to "one book per reader" (not decided here).** `design_decisions_and_risks.md`
> **R2(b)** recommends *within-reader, different stories* — one reader reads several different books, never
> the same story twice — to tighten the single-arm recall-rate estimate without contamination. It is
> **not yet adopted**; this section still specifies one book per reader. Needs adviser sign-off (it changes
> the pre-registration) and interacts with R9's rater-assignment matrix.

---

## 8. Corpus

Test stories must be **real or realistic child writing**, not builder-authored clean prose (which measures
best-case only). Grade 5–6, English with Taglish code-switching tolerated.

**Target: 50 stories, and take 60–70 if recruitment allows.** That number is set by the fine-tune, not the
output evaluation — stories yield characters, and characters are the unit of the fine-tune's disjoint
33 / 5 / 12 split (`docs/specs/judge-finetune.md` §5.5). RQ6 no longer makes a superiority claim (ADR-008,
revised 2026-07-22), but its held-out test set must still be large enough for the reported agreement figure
to have a usable confidence interval — and ADR-018's δ = 3 deployment gate resolves a few points of F1
either way; **more characters is the cheapest statistical power the project has.** The expert-panel and RQ5 output evaluation would need fewer.

**This is a recruitment decision and it is unfixable later.** By Phase 2.5 the corpus is closed. Ask for the
extra stories at Stage 1.

**One corpus, two uses:** the evaluation stimuli (RQ1, RQ3, RQ5 — Tier-1 rating material and naive-reader
recall), and — once the pipeline has drawn it and researchers have labelled the drawings — the judge's
training and evaluation data (RQ6). Corpus = **donated child writing + researcher labels** (ADR-008);
researcher-written stories appear only as judge-training-split augmentation, never as evaluation stimuli.
This is why §9's consent clause is not optional.

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

The original single submission contained a hidden dependency: the corpus is real child writing, the children
who write it are the Tier-2 participants, therefore **Tier 1 was silently blocked on Tier-2 clearance** — the
exact thing Tier-1 self-sufficiency exists to prevent. Splitting the submission is the fix.

**Stage 1 — story donation.** Children write stories. They never touch the system, never see each other's
work. We collect anonymized text and nothing about the child. Narrow, low-risk, comparatively fast.
**Unblocks:** corpus → Tier 1 → the output evaluation → the judge's training labels.

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

**Adult participants need a protocol too (added 2026-07-13).** Tier-1 raters and readers, and the
ISO/IEC 25010 evaluators, are human-subjects data collection; most boards require review or a
formal exemption even at minimal risk. **Bundle the adult-rater protocol (recruitment, consent,
session structure, instruments) into the Stage-1 submission** or file it in the same envelope —
otherwise "Tier 1 stands alone" still has an unfiled dependency, which is the same deadlock the
two-stage split exists to prevent.

**Stage 2 — system use.** Children use StoryBuddy and read classmates' books in the display-only gallery.
Interactive, peer-visible, child-authored content (their own storybook). A materially heavier review.
**Gates:** Tier 2 only.

**Both stages require guardian informed consent *and* age-appropriate child assent** (PH Data Privacy Act
2012 + the university ethics board). Removing parental controls from the *product* (ADR-017) did not remove
parental consent from the *research*; adding peer sharing made Stage 2 heavier, not lighter.

**File Stage 1 immediately.** It is the long pole.

---

## 10. Recruitment

The researcher occupies the teacher/owner role during the study (ADR-017), so **no school partnership is
required** to reach N ≈ 8–15. In order of speed:

1. **Private school** — principal's discretion. Weeks.
2. **Tutoring / learning centre** — lowest barrier, still Grade 5–6.
3. **Parent-recruited convenience sample** at one venue.
4. **Public school** — requires a Schools Division Office permit. The slowest door available.

A classroom-level intervention study would need a school. That is a bigger thesis than this one.

---

## 11. Scope and delimitation

**Grade 5–6 (ages 10–12), Philippines, English with Taglish tolerated.** This is derived from the research
questions, not chosen for convenience, and each boundary is load-bearing:

- They **write independently** → the story is unambiguously the child's. Scaffold a Grade 2 student and
  RQ5 is meaningless: whose story did we illustrate?
- They **read fluently** → they can author at length, and the books they produce are readable stimuli.
  *(This boundary originally rested on in-app peer comprehension, which is cut — §6, ADR-021. It survives
  on authoring fluency, not on the cut instrument.)*
- **English is the medium of instruction** from Grade 4 (DepEd) → one language, one moderation regime, one
  TTS voice.
- They are **pre-adolescent** → peer feedback is unlikely to be cruel.

At N ≈ 8–15 the study cannot stratify by age, and age is one of the largest sources of variance in
children's writing. Broadening the band would add variance, not generality. **A tight population is a
delimitation, not an apology** — and "anyone can use it" was never true anyway: word cap, reading level,
moderation thresholds, failure copy, and narration voice are all calibrated to a band.

---

## 12. Metrics

| Metric | What it measures | Source |
|---|---|---|
| Story Completeness | Major plot points represented in selected scenes | Human annotation + IRR |
| Character Consistency | Same character recognizable across scenes | **Human (headline)** + VLM-judge (control signal only) |
| Style Consistency | Fixed style maintained across scenes | Human + VLM-judge |
| **Reader Comprehension (RQ5)** | Does the book transmit the story? | Naive-reader free recall vs. annotated plot points |
| Story Fidelity | Book matches child's intent | Child (Tier 2) |
| Engagement | Repeat-use / liking | Fun Toolkit + ⚠️ behavioral logs — **not instrumented** (see below) |
| Generation Time | Submission → completed storybook | Instrumentation (LangSmith) |
| AI Resource Usage | Avg generation time, image count, regen count | Instrumentation (LangSmith; `Cost.image_count` / `Cost.regen_count`) |
| AI Resource Usage — cost | API cost/story | ⚠️ **not instrumented** (see below) |
| **VLM–Human agreement (RQ6)** | How well does the fine-tuned judge agree with human labels? | Held-out agreement (F1/κ), split by human/non-human character — **descriptive**, no comparison (ADR-008, revised 2026-07-22) |

> ⚠️ **Two rows require instrumentation that does not exist yet (2026-07-22).** Do not report them until
> it does; if it never lands, drop them from Methods rather than estimating.
> - **API cost/story.** `Cost.usd_estimate` is declared in `docs/specs/story-memory-contract.md`, but
>   `backend/providers.py` does **no** token or cost accounting and no spec owns populating the field.
>   Needs a per-call token/price capture at the provider boundary before this metric is producible.
> - **Behavioral logs** (completion rate, time-on-task, spontaneous second-story starts, "try again"
>   frequency). These fields appear in no schema, no spec, and no backlog row. Engagement currently rests
>   on the Fun Toolkit self-report alone. (Already Tier-2, Ethics-Stage-2-gated and post-October — §6.)
>
> Generation time, image count and regen count **are** covered: LangSmith tracing is wired and
> `Cost.image_count` / `Cost.regen_count` are in the Story Memory contract.

---

## 13. Pre-registration

**Write the analysis plan — hypotheses, baselines, metrics, and success criteria — before running anything.**

For RQ6 the discipline is what makes a *descriptive* number trustworthy: the human labels carry reported
inter-rater reliability, and the held-out set is **read once**, against an analysis plan fixed in advance —
so the reported agreement figure is the one we committed to, whatever it turns out to be. (ADR-008, revised
2026-07-22: no superiority test is pre-registered, because no comparative claim is made.) The same
discipline governs the output evaluation and RQ5: the success criteria and the recall protocol are fixed
before data, so a weak result is a finding, not a fudge.

Almost no capstone does this. It is the cheapest defensive move available.

---

## 14. Anticipated defense questions

| Question | Where the answer lives |
|---|---|
| "Isn't this just an API wrapper?" | The expert panel + ISO/IEC 25010 (§5, RQ3) rate the outputs the architecture actually produces, not a bare API call. |
| "Isn't the fine-tuned judge circular?" | ADR-004 non-circularity note. **The output evaluation is never evaluated using the judge.** |
| "Does it improve children's writing?" | We do not claim that (§3). Prior work is the warrant; fidelity is the finding. |
| "Only twelve children?" | Tier 1 (15–30 adults) carries every core RQ. Tier 2 enriches (§6). |
| "Is a LoRA on ~1,000 examples meaningful?" | Character-disjoint splits, four baselines, CIs, ≥3 seeds, pre-registered plan (§13). |
| "Why not train on an existing dataset?" | None exists for this task. Surveyed and rejected with reasons: `judge-finetune.md` §5.1. |
| "Isn't your training data just the model's own output?" | Positives are **human-confirmed**, never auto-labelled. That is the §3.1 shortcut, and we name it. |
| "So is your fine-tuned judge better than the prompted 27B?" | **We do not claim either way** (ADR-008, revised 2026-07-22). The paper reports the fine-tuned judge's *agreement with human labels* on a character-disjoint held-out set, read once. Whether it replaces the prompted incumbent *in the product* is a deployment gate (ADR-018's δ = 3), not a finding of this study. |
| "**DINOv2 beat your judge on F1.**" | Then it is a finding about metrics, not a product decision. DINOv2 emits a scalar; ADR-010's regeneration controller needs `failure_reasons` to correct a prompt. A cosine cannot say "restate the scarf." Pre-declared: `judge-finetune.md` §7.3. |
| "Did you pick the test set after seeing results?" | The split, the stratification, the primary endpoint, and δ were timestamped before the first label was collected. The held-out set was read once. |
| "Why not just use GPT/Gemini?" | Open-weight mandate (ADR-015) — and the equity claim it enables (§3). |
| "Why only Grade 5–6?" | §11. Each boundary is derived from an RQ. |
| "What if the image model can't hold non-human characters?" | Phase 0.5 kill criterion. We looked, cheaply, before building. |
