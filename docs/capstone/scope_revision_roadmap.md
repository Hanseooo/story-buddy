# StoryBuddy — Scope-Revision Roadmap (Dec → Oct narrowing)

> **Working tracker — not manuscript.** Same genre as `action_checklist.md`: a scannable list of
> **sessions to run**, each scoped to a specific file set, each carrying only the context it needs.
> This exists because the Oct deadline forces a real pivot (see §0) and that pivot touches ~20 files
> across `docs/capstone/`, `docs/product/`, and `docs/specs/` — enough that doing it in one pass
> risks exactly the kind of drift `paper_draft_review_2026-07-18.md` already caught once (2-arm vs
> 3-arm stated in different sections of the same draft).
>
> **Delete this file once every session below is ☑** — fold any permanent decisions into
> `design_decisions_and_risks.md` / `ADRs.md` first. One home per artifact type (project rule).

**Legend — Status:** ☐ not started · ◐ in progress · ☑ done.

---

## 0. Resolved by the project owner (2026-07-20) — read this before every session

These are decided (items 1–5 on 2026-07-20; items 6–9 locked later the same day). No session below should re-litigate them; if a session finds a reason one
of these is wrong, stop and flag it back rather than working around it.

1. **RQ2 (pipeline ON-vs-OFF ablation) is dropped entirely.** It was the study's spine and is marked
   "Never cuttable" in `ROADMAP.md`'s de-scope ladder — that ladder is now wrong and gets corrected
   in Session 5.
2. **RQ6 (fine-tuned Qwen2.5-VL-7B judge vs. its own zero-shot baseline) becomes the primary
   comparative study** — the "AI performance evaluation" leg the panel asked for. It was previously
   the most cuttable, reach piece (de-scope rung 4).
   **Framing (locked):** present RQ6 as the panel-requested *AI-performance evaluation leg*, **not** as
   "benchmarking an internal component" (that invites Arvin's note-8 objection). Lead the claim with
   **fine-tuned 7B matches/beats prompted Gemma-3-27B** — self-hostable, zero marginal cost; the
   beat-your-own-zero-shot-base number is the necessary sanity check and is **never presented alone**
   (`judge-finetune.md` §7.1).
3. **Target-user reframing adopted:** teacher / BEED student = the actual system operator (inputs
   the child's story, reviews/generates the storybook). Grade 5–6 learner = story-source and
   beneficiary, not an account holder or evaluator.
   > **⚠️ Partially reversed — see item 10 (2026-07-20, later same day).** The child is now a
   > teacher-issued *account holder* who operates the app directly; the teacher narrows to account
   > issuer + reviewer. The "not an account holder" clause above no longer holds, and "teacher/BEED as
   > operator" is now "teacher/BEED **and** child both operate." Item 10 is authoritative; read it before
   > acting on the scope warning below.
   **Scope warning found during self-review:** this is a bigger change than "update a user-role
   line." `ADR-017` ("teacher-owned classroom, **student authors**") and `ADR-021` (peer reflection,
   child sees their own Story Map, child-authored input through `input_gate`) currently build the
   **entire interaction model** around the child directly operating the app. Reframing to
   "child never touches the tool" means Session 4 must decide what happens to: who submits peer
   reflections (teacher relays them? feature dropped?), whether the Story Map / formative-feedback
   loop (ADR-021's whole reason for existing) survives at all, and how RQ5's "student authors" wording
   in `ADR-008`/`ADR-021` gets restated. Don't treat this as a one-line edit.
4. **Evaluator panel:** 1 professor + 1 education student + 1 art student *become* the expert
   evaluator panel — folded into/replacing Instrument D (ISO/IEC 25010 panel) — the "evaluate
   generated outputs" leg (storybook / illustrations / story consistency, not internal pipeline
   components, per panel note 8).
5. **ADRs get rewritten in place, not superseded.** Owner's call: it's early enough that
   `ADR-008` (and `ADR-017` if it needs the BEED-student addition) get their decision text edited
   directly. This is a deliberate deviation from the ADR-016→ADR-018 supersession pattern already
   in this repo — don't "fix" it back to a new-ADR pattern in a later session.
6. **RQ5 is kept, reframed single-arm.** The old pipeline-ON-vs-OFF comparison dies with the ablation.
   RQ5 becomes a single-arm output-fidelity measure — *can a naive reader recover the child's characters
   and events from the generated book?* — scored by a **validated recall protocol** against RQ1's
   human-annotated plot points (one annotation, two uses), two independent raters, Cohen's κ reported.
   The *method* is locked; the exact **named** instrument (story-grammar / narrative-recall scoring, fit
   to Grade 5–6 English + Taglish) is an adviser-confirm. RQ5 folds into the Objective-3 output-evaluation
   track. **This resolves Session 2's flagged "RQ5's fate" and removes it from §3.**
7. **Dataset rule (locked).** Corpus = **donated child writing**; researchers put **labels** on the
   pipeline-generated image pairs. Researcher-written stories are permitted **only in the judge-training
   split** (augmentation, like the constructed negatives in `judge-finetune.md` §5.4) — **never** in the
   evaluation corpus (RQ1/RQ3/RQ5 stimuli) and **never** in the judge val / held-out-test splits, which
   must keep the real deployment distribution. The manuscript must **not** state "researchers created the
   stories" (Hans's panel simplification) — that phrasing voids RQ5 and the authentic-audience motivation.
   State it as: **donated child writing + researcher labels**, with fixture/researcher stories for dev and
   training-augmentation only.
8. **October = technical defense, type (A) scope.** The October defense requires a **working system + the
   pre-registered methodology + pilot/partial results**, **not** completed corpus-gated results. This is
   the governing scope criterion for every session: the load-bearing deliverables are ethics-independent
   (working pipeline on fixture stories, the `methodology.md` §7 pre-registration, a pilot RQ6 run). Full
   corpus results (real RQ6 / RQ5 / expert-eval on donated writing) land after October behind Ethics
   Stage-1. **This is what makes RQ6-primary safe despite it being the most timeline-fragile piece.**
   Bright line: pilot numbers generated from fixture stories are *demonstration, not evidence* — label
   them illustrative, never as findings.
9. **Objectives — canonical home + locked draft.** They currently live only in the manuscript, which the
   docs cannot verify against. Canonical home = a new `## Objectives` section in
   `research_direction_and_goals.md`, added during Session 2. Locked draft — one verb each, no compound:
     1. **Develop** the StoryBuddy pipeline (child story → consistent illustrated storybook).
     2. **Implement** the pipeline as a deployable, teacher-operated system.
     3. **Evaluate** the generated outputs — storybook, illustrations, story consistency — via expert
        panel and ISO/IEC 25010.
     4. **Assess** the AI performance of the consistency judge (fine-tuned 7B vs. the 27B baseline) — RQ6.

Net effect on the objective structure: adopt the panel's suggested flow verbatim — **Develop the
pipeline → Implement it → Evaluate the generated outputs (expert panel + ISO-25010) → Assess AI
performance (RQ6 judge fine-tune)** — one verb, one objective, no compound objectives.

10. **Child-interaction model reversed (2026-07-20, later same day) — supersedes item 3's "child never
    touches the tool."** After items 1–9 were locked, the owner reversed the teacher-only-operator model:
    the child now holds a **teacher-issued, classroom-scoped account** (nickname + teacher-set password,
    no email, no self-serve signup, teacher-initiated reset only), **logs in and inputs their own story
    directly**, and the classroom gallery may show **short reflection answers the child types about their
    own book** in response to teacher-toggled fixed questions. The teacher narrows from sole operator to
    **account issuer + reviewer**. Recorded in `ADRs.md` by editing **ADR-017 and ADR-021 in place** (per
    item 5's edit-in-place convention) plus a light touch to **ADR-011** (child-entered story + reflection
    answers as moderated text surfaces) — **no new ADR**; the reversal fits inside the ADRs it reverses.
    - **Auto-approve is deferred to Future Work**, not built. The teacher approves every book manually; an
      auto-approve toggle would remove the human backstop and **cannot ship without an ethics re-review**.
      Owner decision, 2026-07-20.
    - **Behavioral logging** (RESEARCH_PROTOCOL Tier 2) is *collectable* again but stays enrichment, tied
      to no RQ, Stage-2-gated — not "reinstated" as load-bearing.
    - **Consent/assent weight rises:** a child-held account + peer-visible typed content is Stage-2 scope
      requiring guardian consent **and** child assent. `ethics_and_safety.md` updated to match. **October
      scope is unaffected** — fixtures, no real child accounts (item 8 holds).
    - **Propagation status:** roadmap §0 (this item), `RESEARCH_PROTOCOL.md`, and `ethics_and_safety.md`
      done in this pass. Still stale and owned by later sessions: `PRD_v2.md`, `ROADMAP.md`, `ROUTE_MAP.md`,
      `USER_FLOW.md`, `research_instruments.md` — several of these also carry *pre-pivot* staleness
      independent of this reversal. Session 4 should propagate the **reversed** ADR-017/021 as ground
      truth, not "child never touches the tool."

---

## 1. Session plan

Each row = one Opus session. Read **only**: this file's row + `ADRs.md` (post-Session-1 state) +
root `CLAUDE.md`. Don't load the whole `docs/` tree per project rule ("lean context = better output").

| # | Session | Files in scope | What changes | Must resolve | Depends on | Status |
|---|---|---|---|---|---|---|
| 1 | Anchor ADRs | `docs/product/ADRs.md` (ADR-008, ADR-017, ADR-021), root `CLAUDE.md` (line 25–26 stale ADR-016 note) | Rewrite ADR-008's decision text: drop the ablation, record RQ6 as primary + the two-leg evaluation split. Rewrite ADR-017's interaction model (see §0.3 scope warning — this is substantive, not a one-liner) so the teacher/BEED student is the operator. Decide ADR-021's fate (peer-reflection/Story-Map feature depended on the child directly using the app). Fix the stale "No fine-tuning (ADR-016)" note in `CLAUDE.md` to mention ADR-018's judge exception (pre-existing, unrelated drift, cheap to fix while in the file). | Whether ADR-021 (peer reflection) survives in any form, or is cut — flag to owner if unclear. | — | ☑ |
| 2 | Research core | `research_direction_and_goals.md`, `methodology.md`, `RESEARCH_PROTOCOL.md` | Remove the ablation/RQ2 section and all 2-arm/3-arm language; restate RQ table around RQ6-primary + output-quality evaluation; rewrite objectives per §0's Develop→Implement→Evaluate→Assess flow, one verb each. | **Resolved — see §0.6.** RQ5 is kept single-arm, folded into the Objective-3 output-evaluation track, scored by validated recall protocol vs RQ1's plot points. Also add the canonical `## Objectives` section here (§0.9 draft). | 1 | ☑ |
| 3 | Evaluation/instruments | `research_instruments.md`, `docs/specs/judge-finetune.md`, `model_finetuning.md` | Update Instrument D to the 3 named evaluators; tighten every rubric to feature-level indicators (per panel's character-consistency example: appearance/clothing/hairstyle/face/color/missing-elements — not a bare "consistent/inconsistent"). Keep RQ6's claim-ladder and stats machinery (McNemar's, bootstrap CI) — that part isn't in question. | **Which metrics tool(s)** — keep the two evaluations as **separate instruments** (Owen note 11 listed them separately): ISO-25010 questionnaire for the *software* leg (operator-facing), a feature-level artifact rubric for the *output* leg. Reuse `judge-finetune.md` §4's closed taxonomy as the consistency rubric's indicators. RQ5's recall-instrument *method* is locked (§0.6); the exact **named** tools remain adviser-confirm — name them, don't leave "a tool for valid metrics" unspecified. | 1 | ☑ |
| 4 | Target users & product | `docs/product/PRD_v2.md`, `docs/specs/ROUTE_MAP.md`, `docs/specs/USER_FLOW.md`, `ethics_and_safety.md` (consent language) | Apply teacher/BEED-student-as-operator reframing throughout, using Session 1's rewritten ADR-017/ADR-021 as ground truth (don't re-decide the interaction model here, just propagate it); fix the stale "Parent account" references already flagged in `review_round2` (D-item) since this touches the same user-role model anyway; drop "Style/Character Consistency" emphasis from the title per panel note 13. | Confirm parent/guardian stays consent-only (not an operator role) — should already be true, verify it didn't drift. | 1 | ☑ |
| 5 | Risk/tracking cleanup | `design_decisions_and_risks.md`, `action_checklist.md`, `ROADMAP.md`; **deleted** `review_round2_2026-07-12.md` (self-marked, fully migrated, confirmed) | Retired R1 (3rd ablation arm — moot, no arms left) and m1 (partially — the RQ2-fairness half is moot, the Phase-0.5-probe half survives). Reframed R2 (power → single-arm precision), R3 (co-primary — found already adopted in `RESEARCH_PROTOCOL.md` §7, flagged as a doc-consistency gap vs. ADR-008/`research_direction_and_goals.md`, not fixed here — out of row scope), R4 (RQ6 can no longer be de-scoped away; timeline risk now handled by the October fixture-pilot / post-October corpus split, roadmap §0.8), and R9 (rater matrix sized for ~50 books, not 2–3 arms × 50). R7 and R8 survive unchanged — neither was ablation-dependent. Mirrored the same retirements into `action_checklist.md` B1/B2/B3/B5/C3/D3. Fixed `ROADMAP.md`'s de-scope ladder ("Never" row: replaced "the ablation" with "RQ6's judge evaluation" since RQ6, not the ablation, is now the never-cuttable piece), Phase 3 (dropped the dead `condition`-flag ablation-switch bullet, added the expert-panel+ISO-25010 harness), and the dependency map (`RQ1,2,3,5,6` → `RQ1,3,5,6`). | Depends on Session 2's RQ5 call. | 2 | ☑ |
| 6 | Value proposition & framing | `value_proposition.md`, AI-Powered vs. AI-Assisted language pass across `research_direction_and_goals.md` Introduction (panel note 4) | Rewrote `value_proposition.md`'s Layer-3 "measured finding" (§2 table + chain paragraph) and Trap B to drop the pipeline-ON/OFF ablation framing — RQ5 is single-arm now, no OFF condition exists in the study at all, not just no text-only arm. The "machinery works" claim now rests on **RQ6** (the automated judge matches/beats its prompted baseline) + **RQ3** (independent expert-panel ratings), with **RQ5** kept as the transmission-fidelity leg (reader recovers the child's story from the book alone). Mirrored the same trio into §5's Discussion-mapping bullet. Added an explicit "the pipeline is fully automated; human judgment enters only at teacher-gated review and at evaluation (RQ3/RQ5)" statement to `research_direction_and_goals.md` §1.3, right after the central RQ — the Introduction had no *AI-Assisted*-reading language to begin with, so this was an addition (a missing explicit claim), not a correction. | — | 2, 3 | ☑ |
| 7 | Paper reconciliation (deferred) | `paper_draft_review_2026-07-18.md` | This reviewed an old draft against old protocol; once the manuscript itself is rewritten to match Sessions 1–6, re-run the adversarial pass (or delete and redo) rather than patching it now. **Do not start this until the manuscript is actually updated.** | — | 1–6 | ☐ |
| 8 | Drift sweep (final gate) | whole `docs/` tree + root `CLAUDE.md` | See §2 below. | — | 1–6 | ☐ |

---

## 2. Drift sweep (Session 8) — grep list

Run these (case-insensitive) across `docs/` and root `CLAUDE.md` after Sessions 1–6 land. Every hit
must be either an intentional historical reference (e.g., inside a dated review doc explaining what
used to be true) or a bug to fix — nothing in between.

- `pipeline.{0,10}(on|off)`, `ablation`, `2-arm`, `3-arm`, `REF-ONLY`, `reference-only arm`
- `ADR-016` (should only appear alongside a note that ADR-018 supersedes it for the judge)
- `Grade 5.{0,15}(primary|account holder|user)` (should no longer claim Grade 5–6 as the operator)
- `BEED` (should now appear in PRD/user-flow docs; zero hits currently — confirm it's been added)
- `Parent account`
- Any leftover title text emphasizing "Style Consistency" / "Character Consistency"

Also run `git diff --stat` against the pre-revision commit to sanity-check that only the files listed
in §1's rows actually changed — an edit landing in a file no session claimed is itself a drift signal.

---

## 3. Explicitly deferred — not to be silently decided by any session

These came up during scoping but are owner/adviser/panel calls, not something an agent session
should resolve on its own:

- The exact **named** output-quality / recall instruments (RQ5's *method* is locked in §0.6; the
  ISO-25010-vs-artifact-rubric split is recommended in the Session 3 row) — still adviser-confirm
- Evaluator-panel size beyond the 3 named people, and CVI/alpha thresholds (`action_checklist.md`
  B8/B9 — unresolved before this pivot too, still open)
- The two possibly-fabricated citations, `action_checklist.md` A1/A2 (arXiv:2604.01973 "NearID" and
  the DreamBench++ 79.6% figure) — unrelated to this pivot, still unresolved, don't let this roadmap
  make it look resolved
- Whether the three-illustration-style limit (panel note 13) is already reflected in
  `hardware_and_hosting.md` — verify, don't assume

> The **dataset rule is now decided** (§0.7) — no longer deferred. What remains is *propagation*
> (state "donated child writing + researcher labels" wherever datasets are described, and scrub any
> "researchers created the stories" phrasing) — that's session work, not an owner-call.

## 4. Pre-existing, unrelated drift (noticed, not part of this pivot)

- Stale "Llama Guard 4" default in `PRD_v2.md` §15 and `backend/app/config.py` after the
  Qwen3Guard/Granite-Guardian swap (ADR-011b) — already flagged in `review_round2` D-item, still
  unfixed. Fix opportunistically if a session is already touching that file; don't scope-creep a
  session into it otherwise. **Checked during Session 4: no longer present in `PRD_v2.md`'s text as of
  2026-07-20; `backend/app/config.py` unchecked (out of docs scope).**
- **Found during Session 4, fixed in a follow-up pass (2026-07-20):** `PRD_v2.md` §10 (Research Questions &
  Evaluation Plan), §19's `eval.condition: "pipeline_on|pipeline_off"` sketch field, and §20's
  reproducibility note carried the **full pre-pivot RQ2 ablation spine** — same content Session 2
  removed from `research_direction_and_goals.md`/`methodology.md`/`RESEARCH_PROTOCOL.md`, but Session 2's
  row never listed `PRD_v2.md`, so it was missed there. Resolved by hand-propagating ADR-008's two-leg
  design (expert panel + ISO-25010 for RQ3/RQ5, RQ6 as the primary comparative study) into §10's RQ list,
  evaluation-design section, metrics table, and corpus paragraph; dropped the dead `condition` field from
  §19's sketch; reworded §20's reproducibility note to drop the ablation framing. §0 line 61's changelog
  entry ("Evaluation redesigned around a comparative ablation") is left as-is — it's a dated historical
  record of the v1→v2 change, not live content.
- **Found and resolved via owner call during Session 4:** `ADRs.md` ADR-017's decision text (as written by
  Session 1) says the teacher "may toggle auto-approve," but roadmap item 10 — recorded the same day —
  says auto-approve is "deferred to Future Work, not built." Owner resolved this 2026-07-20: **roadmap
  item 10 wins** — product docs (Session 4's files) describe manual-only review, no auto-approve toggle.
  `ADR-017`'s auto-approve clause itself is still stale text and was **not** edited (ADRs.md is outside
  Session 4's file scope) — a follow-up should tighten ADR-017 to match item 10 explicitly.
