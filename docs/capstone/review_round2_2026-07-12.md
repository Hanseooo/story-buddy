# StoryBuddy — Adversarial Review, Round 2 (2026-07-12)

> **MERGED 2026-07-13 — this file is now an archive; the live homes are listed below.**
>
> | Item | Disposition |
> |---|---|
> | N1 (RQ5 captions) | → **R7** in `design_decisions_and_risks.md`; owner-accepted (image-only); draft in `RESEARCH_PROTOCOL.md` §7; checklist B6 |
> | N2 (PII fiction names) | → **R8**; owner-accepted (context-gated); probe-4 cases added; corpus-intake rule in `RESEARCH_PROTOCOL.md` §8 |
> | N3 (rung D / read-once) | → m4; access policy + malformed-output rule drafted in `judge-finetune.md` §7.5/§7.1; checklist B7 |
> | N4 (field order) | → **fixed in code**: order guard in `providers._chat` + 2 tests; probe-3 pass condition updated |
> | N5, N6 (adult ethics, withdrawal) | → m7; drafts in `RESEARCH_PROTOCOL.md` §9; folded into checklist C1 |
> | N7 (probe 1 scale/ties/model confound) | → probe scaled to 10 scenes ×2 chars (owner-accepted); tie rule + optimism note in `PHASE_05_RESULTS.md`; model confound recorded under R1 |
> | N8 (probe 4) | → union-of-two-classifiers logic + ~26-case set in `phase_05.py`; **routing finding: neither Qwen3Guard nor Granite Guardian is on OpenRouter (verified 2026-07-13)** → checklist C5, MASTER_SPEC §8 |
> | N9, N10, N11 | → m5/m6 + template spec, drafted into `judge-finetune.md` §6.4, §5.2, §7.4 |
> | N12 (rater matrix) | → **R9**; design task for the `tier1-rating-harness` spec |
> | N13 (major characters) | → draft definition in `RESEARCH_PROTOCOL.md` §7; checklist B7 |
> | N14 (corpus intake redaction) | → `RESEARCH_PROTOCOL.md` §8 |
> | D1–D6 | → fixed in place (protocol split numbers, PRD §8/§9/§15, MASTER_SPEC §4/§6/§8, ROADMAP counts, RQ3 instrument note) |
> | R1 third arm | → owner-accepted (3 arms) 2026-07-13; pending adviser (B1 ◐) |
> | §6 CI gap | → checklist C4 |



> **Working document — same genre and rules as `design_decisions_and_risks.md`.** Nothing here is
> decided. Items a human accepts should migrate into that file's R-series (or the action checklist)
> and this file should then be deleted — one home per artifact type.
>
> **Scope of this pass:** all of `docs/product/`, `docs/capstone/`, `docs/specs/judge-finetune.md`,
> `docs/MASTER_SPEC.md`, plus the actual code (`backend/spikes/phase_05.py`, `backend/providers.py`,
> `backend/app/config.py`). Round 1 (R1–R6, m1–m3) is **not repeated** — everything below is new.

---

## 0. Verdict on feasibility

**The project is feasible, conditionally.** The build is comfortably feasible: the walking skeleton
is real (FastAPI + RQ + LangGraph + Supabase wired end-to-end, probes written), phase estimates
(≈10–13 weeks of build) are realistic for the scope, and total model spend is trivial (~$100).
The research is feasible **only if** three conditions hold:

1. **Ethics Stage 1 is filed immediately** (already known — R4/C1). At a 4–5-month defense horizon,
   every week of delay converts directly into RQ6 risk and eventually RQ1/RQ4/RQ5 risk.
2. **RQ6 is explicitly framed as the reach contribution** with RQ2+RQ5 as the complete core study
   (already known — R4.2). The docs still occasionally frame RQ6 as integral ("one study, not six");
   that framing forbids the retreat you will most likely need.
3. **The RQ5 instrument survives finding N1 below.** As currently designed, RQ5 — the outcome of
   record — has a structural validity hole that Round 1 came close to (R3) but did not reach.

The documentation quality is exceptional — genuinely stronger than most published capstones. The
findings below are the residue after an already-hostile prior review, which is why several of them
live in the seams *between* documents, or between the documents and the code.

---

## 1. New high-severity findings

### N1 — RQ5's "naive reader" reads the story text: captions contaminate both recall outcomes

**The problem.** RQ5's instrument gives a reader "who has never seen the story text" the book alone
(methodology §6.3). But **the book contains the story text.** ADR-013: captions are the child's
*verbatim text excerpts*; the slide composer renders image + caption on every page; segmentation
selects excerpts precisely to cover the plot. A "naive" reader therefore reads a lightly-abridged
version of the story itself. Free recall of characters (names appear in captions) and plot points
(events appear in captions) can be satisfied **from the text channel alone, identically in both
arms** — the captions are the same in ON and OFF by construction.

**Why this is worse than R3.** R3 said plot recall may be insensitive to character drift. N1 says
*both* recall outcomes (plot **and** the proposed co-primary, character recovery) are largely
insensitive to *everything the pipeline does*, because the transmission channel they measure is the
one channel the ablation never touches. The likely empirical signature: high recall in both arms,
a null on RQ5, and the null is uninterpretable — exactly the outcome R2 warned about, but caused by
the instrument rather than by power.

**Options.**
- **(a) Image-only comprehension condition — RECOMMENDED.** For RQ5 sessions, present the book with
  captions stripped (images + page order only). The claim becomes *"the visual narrative alone
  transmits the story"* — clean, causally aligned with the intervention, and the strongest possible
  version of the fidelity claim. Cost: the rated artifact deviates from the shipped artifact; say so
  in Methods (the shipped artifact is strictly easier).
- **(b) Keep captions; change the primary outcome to visually-grounded items.** E.g., recovery of
  character *appearance* (scored against Character Bible attributes, which never appear in caption
  text), and/or a page-pair identity item ("do these two pages show the same character?"). Cost:
  overlaps with RQ2's rating instrument; the "reader recovers the story" framing weakens.
- **(c) Both:** captions stripped for recall, then shown for a second, exploratory pass.

**Decision status: `PENDING` — must be resolved in the same adviser meeting as R2/R3, before the
pre-registration is timestamped.** All three RQ5 risks (R2 power, R3 outcome choice, N1 channel)
reshape the same instrument; decide them together, once.

### N2 — PII redaction will redact *fictional character names*, breaking captions, narration, and RQ5 scoring

**The problem.** Every PII discussion in the docs treats the risk as *under*-redaction ("Presidio
leaks Filipino PII"). The inverse error is unexamined and it collides with three load-bearing
features. A child writes *"Si Juan ang matapang na kaharian ng dragon"* — Juan is the **hero**, not
the child. A PERSON-entity recognizer cannot distinguish a fictional first name from a real one;
after the mandated Filipino-name recognizers are added, it will fire on fictional Filipino names
*more* often. Since redaction runs before storage, captioning, and export (CC-2), the consequences
cascade:

- **Captions** are the child's verbatim words — now with the hero's name replaced by a placeholder.
  ADR-012's whole argument ("illustrate the child's story, not a summary") is violated by the
  safety stack itself.
- **Narration** (Kokoro reads redacted text) speaks the placeholder aloud.
- **RQ5 character recall** is scored against annotated characters; if character names are redacted
  from the artifact, readers *cannot* name them, in either arm, and the co-primary proposed in R3
  is damaged at the source.
- **The Story Analyzer** extracts characters from redacted text — a redacted protagonist may not
  even survive entity extraction.

**Options.**
- **(a) Context-gated redaction — RECOMMENDED as the design direction.** Redact PERSON entities only
  when they co-occur with real-world anchors (address structures, phone patterns, "my name is / ako
  si" framings, school names); leave bare names inside narrative text alone. Presidio supports
  custom recognizer logic and allow-lists.
- **(b) Consistent pseudonymization** (Presidio anonymizer with a stable name→name mapping) instead
  of placeholder tokens — preserves narrative readability but silently rewrites the child's story
  (fidelity cost; ADR-013's spirit).
- **(c) Teacher-in-the-loop review of redactions** before generation — a human resolves ambiguity;
  fits the existing teacher-gate posture, adds friction to the write flow.

Whatever is chosen: **add benign-fiction cases to the Phase 2 PII test set** (a story whose hero is
"Juan dela Cruz" with no real-world anchors) exactly as probe 4 already does for moderation — the
false-positive direction is the one that dead-ends a child's story.

**Decision status: `PENDING` — design decision needed before the `filipino-pii-recognizers` and
`moderation-stack` specs are written (Phase 2), and worth a line in the ethics submission.**

### N3 — The claim ladder's rung D contradicts "the held-out set is read exactly once"

**The problem.** The evaluation protocol is: all iteration on validation; the held-out test set is
read **once**; rung D ("does not beat base") = "a bug — debug, do not report." But rung D is only
*discoverable by reading the held-out set*. The moment it fires, the prescribed response — debug,
retrain, re-evaluate — requires a **second read of a set that must be read once**. The two rules
are individually correct and jointly contradictory, and the docs never resolve the collision. A
defense panel that notices asks: *"so if the held-out result was bad, you'd have re-run until it
wasn't?"* — which is the moved-goalpost accusation the whole ladder exists to prevent.

Also unpre-registered in the same area: **what counts as a scoreable answer from the zero-shot
baseline.** A zero-shot 7B may emit malformed JSON on some items. Is an unparseable verdict scored
as `same_character` (miss), excluded (shrinks N and flatters the baseline), or retried? Any of
these is defensible; deciding *after* seeing results is not.

**Fix (cheap, before pre-registration):** pre-declare a **test-set access policy** — e.g., "rung D
triggers a debugging investigation conducted exclusively on train/validation; one (1) second
held-out evaluation is permitted after the defect is identified; the deviation and both readings
are reported." And pre-declare the malformed-output rule for every baseline (recommended: force
schema via constrained decoding where the serving stack supports it; count residual failures as
incorrect-on-the-minority-class, i.e. against the judge).

**Decision status: `PENDING` — one paragraph added to the §7.5 pre-registration text.**

### N4 — Probe 3 cannot detect the failure it exists to catch: field order is never asserted *(code-verified)*

**The problem.** ADR-004 makes reason-then-score field order load-bearing. Probe 3's pass condition
is "strict `json_schema` → Pydantic round-trip succeeds" (`PHASE_05_RESULTS.md` probe 3;
`spikes/phase_05.py::structured`). But **Pydantic validation is order-insensitive**: a provider that
emits `{"same_character": ..., "differences_observed": ...}` — score first, rationale second, i.e.
the exact rationalization failure ADR-004 mitigates — **passes the probe**. `providers._chat()` uses
`completions.parse()`, which never exposes key order either. Structured-output implementations do
not uniformly honor schema property order, and OpenRouter routes across heterogeneous providers, so
this is a real, silent failure mode — the same *class* of bug as the text-only-judge probe already
recorded in `tasks/lessons.md`.

**Fix (small):** in probe 3, also fetch the raw completion text and assert
`raw.index('"differences_observed"') < raw.index('"same_character"')`. Consider the same assertion
as a lightweight runtime check (or at least a traced warning) in `providers.judge()`, since a
provider reroute after Phase 0.5 could regress it invisibly.

### N5 — Adult raters are covered by *neither* ethics stage: "Tier 1 stands alone" still has an unfiled dependency

**The problem.** The two-stage split fixed the child-side deadlock, but Tier 1 itself — 15–30 adult
raters and readers, plus the ISO/IEC 25010 evaluators — is human-subjects data collection, and most
university ethics boards require review or a formal exemption for *any* human participation,
adults included. The docs say Tier 1 "needs no special clearance typically" (PRD §10), which is
about risk level, not about whether a protocol must be filed. If the adult-rater protocol is not
part of a submission, the study's self-sufficient tier is itself blocked at rating time — a smaller
version of the exact deadlock ADR-008 amendment (a) was written to kill.

**Fix:** bundle the adult-rater/reader protocol (recruitment, consent, session structure,
instruments) into the Stage 1 submission or file it as a third, minimal-risk application in the
same envelope. It is boilerplate now and a blocker in month four. Confirm the board's exemption
rules for adult minimal-risk studies with your adviser this week.

**Decision status: `PENDING` — one addition to C1 before it is submitted.**

### N6 — "You can stop any time" vs. a model already trained on the child's data: consent needs a withdrawal-cutoff clause

**The problem.** The draft child assent says *"You can say no, and you can stop any time."* The
donated story's labels become LoRA weights. After training, withdrawal can remove a child's story
from the corpus and its pairs from the dataset — but not from an adapter already trained (machine
unlearning is not a thing you can promise). The current consent language promises a right the
project cannot honor after step 7 of `judge-finetune.md` §0, and a careful ethics board (or DPA
reviewer — the right to erasure is statutory) will ask exactly this.

**Fix:** standard practice, one sentence in the guardian consent: withdrawal is honored fully up to
a stated data-lock date (label collection / training start); after that date, already-trained
models are retained but the child's story and labels are deleted from all datasets and excluded
from any future training. Mirror it age-appropriately in the assent ("if you change your mind
before ___, we take your story out"). Pair it with a **corpus data-lock date** in the protocol —
which you need anyway, since "the corpus is closed after Phase 2.5" is currently a research rule
with no participant-facing statement.

**Decision status: `PENDING` — edit the §9 draft language before submission. No retroactive fix,
same as the AI-use clause.**

---

## 2. Medium-severity findings

### N7 — Probe 1 decides the project on 10 items per condition, scored by non-naive raters, with ON and OFF on *different model weights*

Three separate weaknesses in the kill criterion's own measurement, none fatal, all cheap to fix:

1. **Statistical resolution.** The gate is 2 characters × 5 scenes = **10 items per condition**
   (majority-vote per item). "≥ 80%" means 8/10 — the 95% binomial interval on 8/10 spans roughly
   0.49–0.94. The separation gate (≥ 30 points) on 10 paired items is similarly coarse; one
   flipped item moves a rate by 10 points. For the single most consequential decision in the
   project, this is thin. At ~$0.04/image, doubling to 10 scenes per character costs ≈ $1.60 and
   roughly halves the interval. **Recommend: 10 scenes/character before running, since the probe
   is not yet run and the scene list is the only change.**
2. **Rater independence.** The blind scorers are the team — people who designed the mechanism, know
   what reference-conditioned outputs tend to look like (pose anchoring, composition echo), and
   have a stake in PASS. Blind-to-label is not blind-to-tell. Fine for a probe; but the dress-
   rehearsal κ and effect size from Probe 1 feed R2's power analysis — treat them as optimistic
   bounds, and say so when sizing the Tier-1 load. (Also: `_majority` scores a 2–2 tie as
   *not-identity*; with four raters ties are likely on exactly the ambiguous items. Fine, but
   record the tie rule in `PHASE_05_RESULTS.md` before scoring, since it is part of the instrument.)
3. **The OFF arm is a different model, not just a different endpoint.** `config.py`: ON =
   `fal-ai/qwen-image-edit-2511`, OFF = `fal-ai/qwen-image` — sibling checkpoints, not the same
   weights with conditioning removed. m1 flagged seed comparability across endpoints; the sharper
   statement is that **the OFF-vs-ON contrast confounds mechanism with model identity**. R1's
   REF-ONLY arm largely rescues this (REF-ONLY vs FULL is within-model and isolates the loop;
   OFF vs REF-ONLY carries the model swap), which is one more argument for adopting R1(b). State
   the confound in Methods either way.

### N8 — Probe 4 tests one classifier with a generic prompt; ADR-011's actual design is two guard models with native formats *(code-verified)*

`config.py` still defaults `moderation_model` to `meta-llama/llama-guard-4-12b` — the model ADR-011
revision (b) **demoted**. The probe calls it through `structured_text()` with a hand-written
"you are a child-safety classifier" prompt and a forced JSON schema. Three gaps:

1. **It probes neither Qwen3Guard-Gen nor Granite Guardian**, the two models the shipped gate
   actually uses. (The config comment acknowledges the Qwen3Guard id is unverified — resolving that
   id is a prerequisite for the probe meaning anything.)
2. **Guard models have native prompt/output formats** (fixed safety taxonomies, `safe/unsafe S1…`
   outputs). Forcing arbitrary JSON through a generic instruction measures a different regime than
   production will use — a PASS here doesn't validate the real gate, and a FAIL may be an artifact
   of the calling convention rather than the model's Filipino coverage.
3. **n = 7 cases** for a probe whose pass condition is "no MISS in either direction" and whose
   role is *release gate for a child-safety system*. The probe's own output says "extend the set
   before trusting it" — do that before running it, not after: ~30–50 cases spanning harmful
   (violence, self-harm, sexual, bullying) × benign-peril × benign, in Filipino, Taglish, and
   English, is an afternoon of work and makes the gate decision meaningful. Add N2's
   benign-fiction PII cases while you're there.

Fix before running Phase 0.5 — the probe file is the only thing that changes.

### N9 — Checkpoint selection on validation *loss* can silently pick a checkpoint that is bad at the one class that matters

Methodology §5.1 / `train_qlora.yaml`: `load_best_model_at_end` on eval loss, with validation =
~75 pairs at natural distribution (≈ 15 minority-class items). Token-level loss over a 80/20-skewed
set is dominated by the majority class and by rationale tokens; the checkpoint that minimizes it is
not necessarily the one with the best `different_character` F1 — the metric of record. With 15
minority items, val-F1 is noisy too, but it is at least the right quantity. **Recommend:** keep
loss-based early stopping, but select the *reported* checkpoint per seed by minority-class F1 on
validation (a tiny eval script over ~75 pairs), and pre-register that rule.

### N10 — The training target `differences_observed` has no defined source for its prose

The spec is internally split: §3.4 says annotators pick **checkboxes** (8 s/pair, no prose), but
§5.2's example targets contain free prose ("Two eyes rather than three; the scarf is unstriped."),
and positives require confirmation prose ("Three eyes, striped scarf… all present"). Who writes
those sentences? If annotators do, the 8-second estimate and the two-hour weekend die. If they are
generated from checkboxes, the generator is unspecified — and if a *model* writes them, §3.4's
distillation argument comes back through the side door.

**Fix:** a deterministic **template** per taxonomy entry, keyed on the Character Bible's attribute
list (e.g., `wrong_body_feature` + bible attribute "three amber eyes" → "The character does not
show the expected three amber eyes."), concatenated for multi-reason items; positives render the
bible's attribute checklist as an "all present" sentence. Human-supervised (the checkbox is the
supervision), zero prose labour, and — bonus — byte-stable, which §6.1's "training target must
round-trip through the production schema" already needs. Specify it in `judge-finetune.md` §5.2
before annotation-guide writing starts.

### N11 — The DreamBench++ transfer evaluation has no defined mapping between their graded ratings and your binary verdict

DreamBench++'s human scores are graded concept-preservation ratings, not binary same/different
pairwise verdicts. To report "κ vs. human on DreamBench++," a binarization threshold (or an ordinal
correlation choice) must be picked — and if it is picked after seeing results, the one transfer
number in the paper is post-hoc. One sentence in the pre-registration fixes it (e.g., "DreamBench++
concept-preservation ratings are binarized at ≥ x per the benchmark's own 'preserved' convention;
agreement reported as κ and AUROC"). Verify the actual scale while doing A2 — the same PDF answers
both.

### N12 — Nobody has designed the rater-assignment matrix, and it is the study's real logistics problem

~50 stories × 2 arms (3 with R1's third arm) = 100–150 books. Blind rating on 5 dimensions plus
RQ5 comprehension, from a shared pool of 15–30 adults, under constraints that interact:

- IRR needs **overlap** (multiple raters per book) — α is uncomputable on disjoint assignments.
- RQ5 needs readers **naive to the story** — a rater who rated story X's ON book is burned for
  story X entirely (any arm).
- R2(b)'s multi-book readers must never see the same story twice, counterbalanced across arms.
- Session caps (methodology §5.2's fatigue/drift rules) bound books-per-rater.

These jointly determine the real required N, and they are not designed anywhere — methodology §9
defers "sizing the rating load" to Phase 0.5's effect estimate, but the *assignment structure* is
independent of effect size and can be designed now. Recommend: a one-page assignment design
(Latin-square-ish: raters × stories × arms, overlap fraction for α, RQ5 naivety bookkeeping) as
part of the `tier1-rating-harness` spec, before pre-registration — R2's power answer is
meaningless without it.

### N13 — "Characters recovered" needs a denominator the pipeline can actually act on

The Character Bible caps at **≤ 2 canonical references**; stories will regularly contain 3+
named characters. Annotators mark "characters" from text; RQ5 scores recovery against that
annotation. Minor characters are un-conditioned in *both* arms, so this doesn't bias the
comparison — but it dilutes it: the outcome averages over characters the intervention cannot touch.
Define **"major character"** in the annotation guide (e.g., "appears in ≥ k plot points"), align it
with what the Character Bible will canonicalize, and pre-register character-recovery as scored
over major characters (all-characters as descriptive secondary). Free now; a hole in the analysis
if discovered after annotation.

### N14 — The corpus needs PII redaction at intake, but the Filipino recognizers are scheduled for Phase 2

Stage 1 collects "anonymized text" — but the anonymization *mechanism* for narrative-embedded PII
("ako si Juan, taga Purok 3…") is the Presidio + Filipino-recognizer stack, which is a **Phase 2
deliverable**, while the corpus should start arriving as soon as Stage 1 clears — potentially
before Phase 2. Two researchers will also read every story during annotation (§6.1), before any
pipeline runs. **Fix:** the research protocol needs a manual redaction step at corpus intake
(researcher redacts on receipt, before storage; second researcher spot-checks), independent of the
product's automated stack. Feasible at 50–70 stories; just currently unwritten. It also feeds N2:
the manual pass will produce the first real data on the fiction-vs-real-name ambiguity.

---

## 3. Documentation consistency defects (fix before any Word export)

| # | Where | Defect |
|---|---|---|
| D1 | `RESEARCH_PROTOCOL.md` §8 | Says the fine-tune split is **"30/5/15"**; `judge-finetune.md` §5.5 and `methodology.md` §4.3 say **33/5/12**. A pre-registration with two different split declarations in circulation is a defense liability. Fix the protocol. |
| D2 | `PRD_v2.md` §15 cost table | "Text moderation (Llama Guard 4)" — stale; ADR-011(b) replaced it with Qwen3Guard + Granite Guardian. Same stale default in `backend/app/config.py` (see N8). |
| D3 | `PRD_v2.md` §8 MVP list | "Parent account + kid profile" and "Parent library/dashboard" — superseded by ADR-017 (teacher/classroom). §9 "Parent flow" and MASTER_SPEC §4's "shadcn/ui (parent)" / "parent dashboard" likewise. One terminology sweep. |
| D4 | `MASTER_SPEC.md` §8 | Open item still says DreamBench++ image licensing must be "confirm[ed] with the authors **before training on them**" — the decision is now *never train, evaluate only* (`judge-finetune.md` §12, resolved). Move it to Resolved. |
| D5 | RQ3 wording | RQ3 includes "usability," but the blind rating instrument (§6.2) has no usability item — usability lives in the ISO/IEC 25010 questionnaire. Either drop the word from RQ3 or note the split, so RQ3's instrument list is honest. |
| D6 | `ROADMAP.md` / `PHASE_05_RESULTS.md` vs code | Probe 1 counts drifted: docs say "~22 images, ~$0.80" (+20 secondary); `phase_05.py` says ~34 images, ~$1.20 total. Trivial; align the docs with the code before filling in results. |

(D-items are factual-accuracy fixes of the R6 kind: correct them with the same one-line-changelog
discipline already agreed for frozen docs.)

---

## 4. Knowledge gaps worth closing (short explainers)

- **Why probe 3 passes even when field order is wrong (N4):** Pydantic parses JSON into a dict
  first; JSON object key order is preserved in Python but ignored by validation. Round-trip success
  therefore proves schema *conformance*, not emission *order*. Only inspecting the raw completion
  string proves order. Same reason the CI test in `judge-finetune.md` §10 ("a test asserts field
  order") must assert on the *schema/serialized output*, not on a validated model instance.
- **Krippendorff's α under class skew:** with ~80/20 pass/fail, chance agreement is high, so α
  penalizes disagreements harshly — hitting 0.67 on the image-pair task will be harder than the raw
  agreement percentage suggests. Expect this; it is not a broken guide. The Probe-1 dress rehearsal
  gives you the first read. (m2's cap on guide revisions still applies.)
- **Blind-to-label ≠ blind-to-condition:** reference-conditioned edits often echo the reference's
  pose/composition; experienced raters can classify ON vs OFF above chance without being told.
  This is inherent to all image-ablation studies and is not fixable — but it belongs in Threats to
  Validity (§9) as *rater condition inference*, and it is another reason Tier-1 raters must be
  outsiders, not the team.
- **Right to erasure vs. trained weights (N6):** the PH DPA gives data subjects erasure rights;
  the accepted research practice is a consent-stated data-lock date, because removing a
  contribution from trained weights is not technically feasible. This is standard, defensible, and
  only a problem if the consent form promises otherwise — which the current draft does.
- **Guard models vs. chat models (N8):** Llama Guard / Qwen3Guard are classifiers fine-tuned to a
  fixed taxonomy and output grammar. Calling them like a chat model with a custom rubric discards
  their calibration. The production gate should use each model's native convention; the probe
  should exercise exactly what production will run.

---

## 5. What to do, in order (merges into `action_checklist.md`)

1. **This week, independent of everything:** C1 (Ethics Stage 1) **+ N5** (adult-rater protocol in
   the same envelope) **+ N6** (withdrawal-cutoff sentence in both consent drafts) — one submission,
   three fixes. A1–A2 citation checks unchanged.
2. **Before running Phase 0.5** (all changes are to `phase_05.py`/config only, cheap):
   N7.1 (10 scenes/character), N7.2 (record the tie rule), N4 (raw field-order assert),
   N8 (resolve Qwen3Guard id; probe both real classifiers in native format; grow to ~30–50 cases,
   including benign-fiction names).
3. **One adviser meeting, before the pre-registration is timestamped:** B1–B5 from the existing
   checklist **+ N1** (RQ5 channel — decide with R2/R3 as one package), **N3** (test-set access
   policy + malformed-output rule), **N9** (checkpoint-selection rule), **N11** (DreamBench++
   binarization), **N13** (major-character definition).
4. **Before the relevant spec is written:** N2 (PII false-positive design → `filipino-pii-
   recognizers` spec), N10 (checkbox→prose template → `judge-finetune.md` §5.2), N12
   (rater-assignment matrix → `tier1-rating-harness` spec), N14 (manual corpus-intake redaction →
   `RESEARCH_PROTOCOL.md`).
5. **Before any Word export:** D1–D6 sweep (fold into the existing A5 pass).

---

## 6. What was checked and found sound (so you don't re-audit it)

- The non-circularity architecture (RQ2 never judged by the judge) is airtight and consistently
  stated everywhere it matters.
- The two-gate RQ6 design (research vs. product comparator) genuinely de-risks the external
  fine-tuning requirement; the claim ladder is defensible given N3's paragraph is added.
- Character-disjoint splits, human-confirmed positives, constructed-negatives-in-train-only, and
  the character-clustered bootstrap are all correct and correctly reasoned — these are the places
  fine-tune capstones usually die, and they are pre-empted.
- The ethics two-stage split, the consent AI-use clause, and the Tier-1/Tier-2 separation are
  structurally right (N5/N6 are additions, not corrections).
- Cost, GPU, and serving arithmetic all check out (QLoRA on a 7B VLM in 24 GB, ~$5–15/run,
  vLLM LoRA serving, rollback-by-env-var).
- The walking skeleton exists as documented: real queue/worker/checkpoint/Realtime path, real
  probe suite, deterministic tests mocking `providers.py`, 4 pipeline nodes correctly stubbed for
  Phase 1. Code matches MASTER_SPEC's map. (One gap: **no CI workflow exists** — `.github/` is
  absent, so "CI must stay green" and the split-disjointness guard "tested in CI" are currently
  aspirations. Stand up the pytest+vitest workflow before Phase 1, or the bright line has no fence.)
