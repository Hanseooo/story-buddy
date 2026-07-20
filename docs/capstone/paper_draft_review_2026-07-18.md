# StoryBuddy — Capstone Paper Draft Review (2026-07-18)

> **Scope.** Reviews the pasted proposal draft text (Introduction: Background, Objectives, Significance,
> Scope and Delimitation; Methodology: Research Design through Ethical Consideration) against the project's
> own authoritative docs (`docs/product/RESEARCH_PROTOCOL.md`, `docs/capstone/methodology.md`,
> `docs/product/ADRs.md`, `docs/MASTER_SPEC.md`) and its live risk register
> (`design_decisions_and_risks.md`, `action_checklist.md`, `defense_prep.md`). Working document, same genre
> as `review_round2_2026-07-12.md` — nothing here is a directive, it's a findings list for a human to
> triage. Delete or fold into the checklist once acted on.
>
> **Headline finding.** The draft is not making things up — nearly every gap below is a known, already-
> tracked item in `design_decisions_and_risks.md` / `action_checklist.md` / `defense_prep.md`. What the draft
> actually has is a **propagation problem**: several fixes the project owner already accepted (3rd ablation
> arm, image-only RQ5 sessions, context-gated PII redaction, withdrawal data-lock clause) haven't been
> written into the authoritative docs yet, and the paper — quite reasonably — was drafted from those
> authoritative docs, so it inherited the pre-fix state. `defense_prep.md` §7 calls this out almost verbatim
> for the methodology; this review adds the ethics-side instances and two internal-consistency defects that
> are new (§1, §2 below).

---

## 1. Internal contradictions (the draft disagrees with itself)

### 1.1 Statistical test named twice, differently — HIGH
"Research Design" states: *"A Paired-Samples t-test will be applied to compare the mean scores of the
Pipeline ON versus Pipeline OFF conditions."* "Data Handling and Confidentiality" states: *"...the
Wilcoxon signed-rank test for paired experimental comparisons."*

**Canonical answer: Wilcoxon signed-rank is correct; the t-test line is stale.**
`methodology.md:460` (§7.1) fixes Wilcoxon signed-rank as primary (a cumulative-link mixed model as
secondary), specifically *because* the outcome is an ordinal 5-point Likert rating — a paired t-test's
normality assumption doesn't hold for ordinal data, and a mean of ordinal codes isn't cleanly
interpretable. `defense_prep.md` §5 has a fully rehearsed answer for "why Wilcoxon, not a t-test" ready to
go. **Fix: delete the "Paired-Samples t-test" sentence in Research Design and replace with Wilcoxon
signed-rank (+ the storybook-as-unit-of-analysis note), so the two sections agree.**

### 1.2 Two different 10-module pipeline lists — MEDIUM
"Research Design" lists 10 modules: (1) Input Moderation, (2) Story Analyzer, (3) Scene Segmentation,
(4) **Story Memory Manager**, (5) Character Bible, (6) **Style Bible Generator**, (7) Prompt Optimizer,
(8) Image Generation Engine, (9) **Quality Checker**, (10) **Slide Composer** — and later calls them
"Module 9 (Quality Checker)" / "Module 10 (Slide Composer)" in the same section.

"Phase 1 – Core Pipeline Development" (SDLC section) lists a *different* 10: Input Moderation, Story
Analyzer, Scene Segmentation, Character Bible Generator, Style Preset Selection, Prompt Optimizer, Image
Generator, **Consistency Judge**, **Targeted Regeneration**, and **Compose/Export**.

**Canonical answer, per `docs/MASTER_SPEC.md:88-121` and `docs/capstone/system_architecture.md:38-51`:**
the actual pipeline nodes are `input_gate → analyze → segment → char_bible → generate_scene →
consistency_check → regenerate → output moderation → compose → export`. Two things are structurally
settled and both lists in the draft get at least one of them wrong:
- **"Story Memory" is not a stage.** MASTER_SPEC §3 (line 125) calls it the cross-cutting Pydantic
  contract read/written by every node — it is not module #4 of anything. List 1 is wrong here.
- **"Style Bible Generator" is dead terminology.** `PRD_v2.md:58`: "Style Bible Generator removed as a
  module — style is a fixed constant... carried by the canonical character reference image" (ADR-007,
  ADR-022). Style presets are **config selected once**, not a node/generator. List 1 is wrong here; List
  2's "Style Preset Selection" is closer but still lists it as one of "ten pipeline stages" when it isn't
  a graph node either — that imprecision pre-exists in `system_architecture.md` itself, not invented by
  the paper.
- **"Quality Checker" / "Slide Composer" (List 1) are stale names** for what List 2 correctly calls
  "Consistency Judge" + "Targeted Regeneration" (two distinct nodes/ADRs — ADR-004 and ADR-010, not one
  module) and "Compose/Export" (two nodes).

**Fix: standardize on List 2's naming (it's the one that's a near-verbatim match to
`system_architecture.md`), delete List 1 entirely or rewrite it to match, and stop calling anything
"Module 9 (Quality Checker)" / "Module 10 (Slide Composer)" in the Research Design narrative.**

### 1.3 Two vs. three experimental arms, asserted in the same paper — HIGH
Every section of the draft except one describes a **two-condition** study: Objectives ("full pipeline...
against a naive baseline"), Research Design ("Pipeline ON" / "Pipeline OFF"), Data Collection Phase 1
("two experimental conditions"), the entire Evaluation of Instruments section (Instrument A's dimensions
are scored per book, ON vs. OFF, nothing else). Then "Data Set" §2 (D-Align) introduces a **third arm**:
Arm A (OFF), **Arm B (REF-ONLY, "baseline")**, Arm C (FULL) — 600 scenes, 3×50×4.

**This is not the paper being wrong so much as the paper being ahead of the authoritative docs on a change
that hasn't been ratified.** `design_decisions_and_risks.md` R1 records the 3-arm design as
**owner-accepted 2026-07-13, pending adviser sign-off**, and both `RESEARCH_PROTOCOL.md` §5 and
`methodology.md` §7.1 **still describe two arms** — `action_checklist.md` B1 and `defense_prep.md` §2 both
list this as an open reconciliation item ("until that propagates, the 'the loop is the contribution' claim
rests on an unmeasured component"). So: the Data Set section is describing the *target* design the team
already wants; everywhere else in the same draft describes the *current, authoritative* design. Both can't
appear as fact in one document.

**Separate factual error inside the same Arm B description, independent of the above:** the draft says Arm
B (REF-ONLY) is generated "via IP-Adapter or InstantID, operating in a single-pass execution framework."
`design_decisions_and_risks.md` R1 specifies REF-ONLY must run on the **same `qwen-image-edit` endpoint**
as the FULL arm, specifically so the ablation stays within-model (REF-ONLY vs. FULL isolates the judge/
regen loop; only OFF vs. REF-ONLY carries a model swap). IP-Adapter/InstantID is a categorically different
conditioning mechanism and would undermine the exact reason R1 exists. **This should be corrected
regardless of whether the 3-arm design is adopted.**

**Fix: this needs one adviser decision (already flagged B1), then one consistent arm-count used
everywhere in the paper. If 3 arms are adopted, Arm B's mechanism description must be corrected to
"same edit model/endpoint as Arm C, reference-conditioned in a single pass, no judge/regeneration" — not
IP-Adapter/InstantID.**

---

## 2. Methodology gaps (paper is consistent with itself, but incomplete vs. the canonical design)

### 2.1 D-Fine split: paper describes 2-way, canonical design is 3-way and character-disjoint — HIGH
The draft's "Data Set" §3 and "Training and Validation" both describe an 80%/20% train/validation split.
The canonical split, per `docs/specs/judge-finetune.md:247-252` (§5.5) and `RESEARCH_PROTOCOL.md:149`
(restated in `methodology.md:274-278`), is a **character-disjoint three-way split**: Train = 33 characters
(~945 pairs), Validation = 5 characters (~75 pairs, where all iteration happens), **held-out Test = 12
characters (~240+ pairs, stratified human/non-human, read exactly once)**. There's also a fourth,
never-trained-on transfer check (DreamBench++).

This matters beyond terminology: the entire RQ6 claim ladder (rungs A–D, McNemar's test, the 95% CI on
ΔF1) is built on a test partition that is distinct from validation and read *once*. A reader of the paper
as currently drafted would reasonably conclude there's no such partition — validation *is* the final
evaluation set. **Fix: describe all three partitions (train/validation/held-out test) with character-
disjoint splitting, and add the single-read-test-set rule.**

### 2.2 Corpus size states a hard N=50; canonical framing is "50 floor, 60–70 if recruitment allows" — LOW
`research_direction_and_goals.md:142`, `RESEARCH_PROTOCOL.md:148`, `methodology.md:231-232` all frame 50
as a floor gated on character yield, with an explicit note that the corpus **closes once labelling begins
and cannot be grown afterward**. The draft's "N = 50" (Data Set §1, Respondents) is consistent with the
floor but omits the recruitment-gated upside and the closure rule. Not a contradiction, just incomplete —
worth a sentence if the final corpus size is still open when this is submitted.

### 2.3 RQ5 / Instrument B: the "naive reader" reads the story's own text via captions — CRITICAL, unresolved everywhere
The draft's Instrument B says a reader recovers the story "after reading a book alone, with no access to
the original text." But per ADR-013, page captions **are** the child's verbatim text excerpts, identical
in both ON and OFF arms by construction. A reader can satisfy both free-recall items (characters, events)
from the caption text alone, regardless of whether the illustrations are consistent — meaning, as
currently designed, **RQ5 (the study's outcome of record) may not measure anything the consistency
pipeline does.**

This is not a documentation-lag issue like the others above — **the fix itself is still unresolved
everywhere**, not just in the paper:
- `design_decisions_and_risks.md` R7: owner-accepted (image-only sessions, captions stripped) but
  "pending adviser sign-off."
- `RESEARCH_PROTOCOL.md` §7: carries the same fix in a blockquote flagged "owner-accepted change pending
  adviser sign-off" — drafted, not merged as settled text.
- `methodology.md` §6.3 and `research_instruments.md` (Instrument B) — **both still say "book alone" with
  no caption-stripping** — the two docs the paper's own instrument section was drafted from.
- `defense_prep.md` §2 independently flags this as one of the most exposed flanks a panel can find.

**Fix: this needs an actual adviser decision (already queued, `action_checklist.md` B6), not a paper
edit — the paper is accurately reflecting an instrument that, as designed today, has a validity hole.
Decide alongside B2 (character-recovery co-primary) and B3 (multi-book RQ5 design) since all three reshape
the same instrument, per `action_checklist.md`.**

### 2.4 "Major character" is undefined; rater-assignment matrix doesn't exist yet — LOW, flag not fix
Story completeness (Instrument A) and story recovery (Instrument B) both score against "major plot points
and characters," but "major character" has only a draft, unconfirmed definition
(`RESEARCH_PROTOCOL.md:128-132`: "≥2 annotated major plot points," marked "confirm with adviser"). Neither
`methodology.md` nor `research_instruments.md` nor the paper defines it. Separately, no
`tier1-rating-harness` spec or rater-assignment design exists anywhere (`design_decisions_and_risks.md` R9
is still an open "design task," not a decision). Both are appropriately silent in a *proposal*-stage paper
— just flagging so they don't get lost before pre-registration, per `action_checklist.md` B7/B9's own
framing.

---

## 3. Ethics / privacy gaps — paper reflects the *pre-fix* state on three separate points

All three of the items below have an accepted design fix on record, but the fix hasn't propagated into
`docs/capstone/ethics_and_safety.md` either — so, same pattern as §2.3, the paper is consistent with the
current (stale) ethics doc, not with the decision the team already made.

### 3.1 Withdrawal promise doesn't acknowledge trained-model retention — HIGH, ethics-board-facing
The draft's "Voluntary Participation and Right to Withdraw" makes an unqualified promise: *"the
researchers will remove the participant's identifiable research data and exclude it from the final
analysis."* Once a child's story has been used as a judge fine-tuning label, this can't be fully honored —
an adapter cannot have one training example "unlearned." `RESEARCH_PROTOCOL.md:211-224` already drafts the
fix: a stated **data-lock date** (start of Phase 2.5 labelling) — full withdrawal before that date, and
after it, the story/labels are deleted from all datasets and excluded from future training, but the
already-trained model is retained, stated explicitly to the participant. This is marked `m7`, "needs
adviser sign-off," in `design_decisions_and_risks.md` — not yet closed, and not yet in
`ethics_and_safety.md` either. **Fix: add the data-lock clause to both the consent-form draft and this
section before any Word export — `action_checklist.md` C1 already bundles this with the Ethics Stage 1
submission, so it's on the critical path regardless of the paper.**

### 3.2 PII redaction described as blanket; accepted fix is context-gated — MEDIUM
The draft's Scope/Delimitation, Ethical Consideration, and Data Set (§1, C-Story) sections all describe
Presidio stripping "local names... before the text reaches any storage system." A PERSON-entity recognizer
cannot distinguish the fictional hero "Juan" from a real Juan — and the mandated Filipino-name recognizers
will fire on fictional Filipino names *more*, not less, once added. `design_decisions_and_risks.md` R8:
owner-accepted (2026-07-13) fix is **context-gated redaction** — only redact names co-occurring with
real-world anchors (address structures, phone patterns, "my name is / ako si" framings). `ethics_and_safety.md`
§1 itself still says redaction "applies uniformly," so the paper is consistent with that doc — both need
the same update. Left as-is, the blanket description risks: placeholder-redacted captions (breaking
ADR-012's "illustrate the child's actual words" guarantee), narration reading the placeholder aloud, and
RQ5 readers being unable to name characters in *either* arm.

### 3.3 Consent language doesn't cover "train" — MEDIUM, no retroactive fix
The draft's Informed Consent section says stories "may be used to develop and evaluate the AI-powered
StoryBuddy system." `RESEARCH_PROTOCOL.md:187-189` (citing ADR-018) specifies the required clause must say
donated stories may be used to **"build, train, and evaluate"** a model — because judge fine-tuning is a
training use, not just development/evaluation, and per the same doc "there is no retroactive fix" once
consent is collected without it. **Fix: this is a one-sentence, pre-submission change — but it must happen
before Ethics Stage 1 is filed (`action_checklist.md` C1), not after.**

### 3.4 Corpus intake redaction: automated stack described as already operative — LOW
The draft's C-Story description presents the Qwen3Guard-Gen + Granite Guardian + Presidio stack as the
mechanism anonymizing stories on intake. That automated Filipino-recognizer stack is a **Phase 2
deliverable**; the corpus (and two human annotators reading raw stories) may arrive before Phase 2 is
built. `RESEARCH_PROTOCOL.md:163-168` already adds an interim **manual redaction-at-intake** step
(researcher redacts on receipt, second researcher spot-checks) precisely to cover this gap — not reflected
in the paper's corpus description.

---

## 4. Technical / hardware table — mostly accurate, two loose ends

- **Moderation and TTS model names in the tech table are correct and current** (Qwen3Guard-Gen + Granite
  Guardian; Chatterbox primary / Kokoro-82M fallback) — this table is actually **ahead of** some other
  project docs (`PRD_v2.md` §15 and `backend/app/config.py` still reference the retired Llama Guard 4, per
  `review_round2_2026-07-12.md` D2). No action needed here beyond what's already tracked in C5.
- **Hardware table lists "CyberLab PC: NVIDIA RTX 4060" flatly**, with no VRAM figure or caveat.
  `hardware_and_hosting.md:74,78-82` calls this spec "tentative, to be confirmed" and warns the RTX 4060's
  8GB will "likely run out of memory" for the QLoRA judge fine-tune (which needs ~16–20GB); the dev laptop's
  RTX 3050 is stated outright as unable to train it (`hardware_and_hosting.md:198`). The Training and
  Validation *prose* correctly hedges ("contingent on VRAM threshold... or a rented GPU"), but the *table*
  doesn't carry the same caveat — a reader skimming only the table would assume the local hardware suffices.
  **Fix: add a VRAM figure + "tentative/likely insufficient, rented GPU is the expected path" note to the
  table**, matching the prose.
- `model_finetuning.md` has more precise figures than the paper adopts (1–2 hrs, 24GB GPU, ~1,200 training
  examples) — not a contradiction, just an opportunity to tighten the paper's vaguer "tens of dollars... a
  few hours" language if those numbers are stable enough to commit to print.

---

## 5. Not checked here (outside the pasted text) — flag before submission anyway

- **Citation integrity** — `action_checklist.md` A1/A2 flag the NearID citation (`arXiv:2604.01973`) and
  the DreamBench++ "79.6% human agreement" figure as **possibly fabricated/unverified**, and A4 flags three
  more Related-Work IDs unverified. None of these appear in the pasted Introduction/Methodology text, but
  they underpin ADR-004/ADR-018's rationale and will very likely appear in this paper's Related Work or
  Discussion. **Verify or delete every one before any Word export — this is rated the single most damaging
  possible integrity failure at defense** (`action_checklist.md` A1, `defense_prep.md` §2).
- CLAUDE.md (this repo's project instructions) still states "No fine-tuning (ADR-016)" as a flat rule with
  no mention that ADR-018 supersedes it for the judge specifically. Not a paper defect, but worth a note to
  self so a future session doesn't flag the judge fine-tune as an ADR violation — ADR-016 itself says it's
  "retained, not deleted" and superseded in the opposite direction by ADR-018.

---

## 6. Priority order

1. **Before anything else, independent of the paper:** Ethics Stage 1 submission (`action_checklist.md`
   C1) — bundling the data-lock clause (§3.1), the "build, train, and evaluate" consent language (§3.3),
   and the adult-rater protocol. Every week of delay is RQ6/RQ1/RQ4/RQ5 risk.
2. **One adviser meeting, before pre-registration is timestamped:** 3-arm decision (§1.3/B1), image-only
   RQ5 sessions (§2.3/B6), character-recovery co-primary (B2), multi-book RQ5 design (B3) — decide as one
   package, then propagate into `RESEARCH_PROTOCOL.md`/`methodology.md`, then into this paper.
3. **Cheap, mechanical, do anytime before the next draft pass:** fix the t-test/Wilcoxon contradiction
   (§1.1), unify the two pipeline module lists on List 2's naming (§1.2), correct Arm B's generation
   mechanism (§1.3), describe the 3-way D-Fine split (§2.1), add the hardware-table VRAM caveat (§4).
4. **Before any Word export:** citation verification (§5) — this one is non-negotiable regardless of
   everything else on this list.
