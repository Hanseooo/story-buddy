# StoryBuddy — SDLC record

**As of:** PR #134, merged 2026-11-21. Written 2026-11-22 (issue #138).

This file is the evidence behind `methodology.md` §1 and the `/research/sdlc` page. It lists the
development loops as they ran and every merged pull request, each with the merge commit anyone can
check with `git show <hash>`. Where `methodology.md` §1 and this file disagree, this file is checked
against git and wins.

## 1. How to check it

- **What git records.** For each PR row, the merge commit's subject is `Merge pull request #N from …`,
  its body's first line is the PR title, and the date is the merge commit's date as git records it
  (`git log -1 --format=%cs <hash>`, Philippine time, +0800). GitHub shows merge times in UTC, so a
  PR merged after 16:00 UTC shows the day before on GitHub. Three merge commits (#79, #128, #129)
  have no body, so their titles are copied from GitHub and git cannot check them.
- **What we decided.** The Loop column is a classification, not a fact from git. A PR belongs to
  the loop whose risk it addresses, read from its title and body. Dates do not decide it, which is
  why loops overlap in time.
- **The test.** `frontend/app/(research)/research/(reference)/sdlc/data.test.ts` checks every row
  against git, checks that every PR merge up to #134 is listed, and checks the loop table's counts
  and dates against the rows.
- **Not listed.** PR numbers missing from the table (for example #23–#29) are GitHub issues, which
  share the numbering, or the one PR closed without merging. Phase 0 and Phase 0.5 were committed
  straight to `main` before PR #1, so loop 1 has no PRs.

## 2. Loops

| Loop | Phase | Risk it addressed | Merged PRs | First merge | Last merge | Gate | Gate result |
|---|---|---|---|---|---|---|---|
| 1 | 0 & 0.5 | Can an open image model hold a stylized, invented, non-human character across scenes? | 0 | — | — | Reference conditioning retains identity on ≥ 80% of items and exceeds unconditioned by ≥ 30 points. | Split. Run 3 passed absolute (80%), failed separation (+25 vs ≥30); the failed gate is carried as a stated limitation. |
| 2 | 1 | Does the consistency loop work on clean stories? | 21 | 2026-07-29 | 2026-10-13 | A clean multi-scene, multi-character story produces a coherent, character-consistent storybook, and you can point to a case where the VLM-judge caught an off-model image and the targeted retry fixed it. | Partial. The loop runs end to end, but the judge's accuracy fell short: in the October audit it passed 29 of 77 defective pages, and in no audited redraw did it catch an off-model character and accept the fix. That weakness became loop 4's risk. |
| 3 | 2 | Is it safe for a real child in a real classroom, and does it survive messy input? | 20 | 2026-08-02 | 2026-10-23 | Entry: probe 4 (Filipino/Taglish moderation), no MISS in either direction. | Not run. Phase 2 was built without its entry gate, for lack of time. No child has used the system, so the risk it guards has not arisen; it stays a gate before children use it. |
| 4 | 2.5 | Does fine-tuning make the Consistency Judge better? | 17 | 2026-08-22 | 2026-10-09 | The results table exists and is honest, and the held-out set was read exactly once. | Partial. Paid evaluation stopped on 2026-10-07; on the held-out set the untuned model scored higher F1 than every fine-tuned seed. |
| 5 | After the technical defense | Do the panel's suggestions work without weakening child safety? | 5 | 2026-10-26 | 2026-11-21 | Items that touch ADR-011, ADR-017, ADR-029 or the teacher-review spec ship behind an off-by-default setting pending an ethics re-review. | Shipped off by default, then turned on by default on 2026-11-21 so they can be tested. The real-child gates (ethics re-review, moderation audit 01) still apply. |
| 6 | 3 | Does the system hold up under the study's three evaluations? | 5 | 2026-08-10 | 2026-10-11 | One full expert-validation session (Objective 3) and one full ISO/IEC 25010 session (Objective 5) end-to-end, and a clean metrics table. | Open. The repository records no completed session yet, and the functional verification matrix was dropped (D-28). |

Sources, by loop:

1. `docs/product/PHASE_05_RESULTS.md` status line (2026-07-29). The walking skeleton's slideshow is
   commit `1e33a27` (2026-07-08); the probes and gates were pre-declared in commit `b5c57ac`
   (2026-07-10).
2. `docs/product/ROADMAP.md` Phase 1 exit criteria; `methodology.md` §1.3 as it stood before
   2026-11-22 ("Complete (2026-08-02) — all ten Phase-1 specs built"). The result is from
   `docs/capstone/pipeline-stage-audit-2026-10.md` (Page gate: 29 of 77 defective pages passed) and
   `docs/specs/research-page-refresh/evidence/loop2_redraws.py`, which reads the audit's local data: of
   71 redrawn scenes, 9 had a bad first draw and a good shipped page, and the judge passed the shipped
   page in 1, whose defect was an action, not an off-model character. The audit's reviews are AI-only
   and the owner did not confirm them, so these counts are provisional.
3. `docs/product/ROADMAP.md` Phase 1 "Gate → Phase 2" and Phase 2 "Entry"; `PHASE_05_RESULTS.md`
   status line ("⬜ Probes 2 and 4 not run"); `docs/capstone/action_checklist.md` D4 (unchecked). The
   reason, lack of time, is the owner's (2026-11-22); that no child uses the system is `methodology.md`
   §3.2 (Stage 1, story donation).
4. `docs/product/ROADMAP.md` Phase 2.5 exit criteria; `docs/capstone/group-guide.md` §4,
   Objective 4; `docs/capstone/research-changelog.md` §1, point 4.
5. `docs/capstone/research-changelog.md` rows 2026-10-25 and 2026-11-21; the "Default changed"
   notes in ADR-080 and ADR-082. The defended version is the tag `technical-defense-2026-10`.
6. `docs/product/ROADMAP.md` Phase 3 exit criteria; `docs/capstone/group-guide.md` §4,
   Objectives 3 and 5; `docs/capstone/evaluation_instruments_brief.md` (D-28, 2026-11-21).

## 3. Where the work left the plan

1. **Loop 1's separation gate was missed.** It was reported as a miss and carried as a limitation,
   not as a pass. The escalation was declined (ADR-001).
2. **Loop 3 started without its entry gate.** Probe 4 has not run. The moderation stack shipped in
   PR #12 on 2026-08-02 without it. It was skipped for time (owner, 2026-11-22), and children only donate
   stories in the study (ethics Stage 1, `methodology.md` §3.2), so no child has met the unchecked filter.
3. **Loop 2 kept going after its gate.** 10 consistency PRs merged after Phase 1 was recorded
   complete, the last on 2026-10-13. The pipeline's output is not deterministic, so running it on more
   stories kept turning up edge cases, each fixed in its own PR.
4. **Loop 4's exit criterion is not met.** The held-out result is partial: paid evaluation stopped
   for budget and the Gemma baseline failed authentication (group-guide.md §4).
5. **Scope changed inside loop 3.** Narration and PDF export were cut (ADR-058, PR #79); PDF
   download was restored on 2026-10-21 (ADR-071, PR #128).
6. **A planned instrument was dropped.** The functional verification matrix for Objectives 1–2 was
   never built (D-28).
7. **Loop 5's off-by-default rule was relaxed for testing.** The features are on by default since
   PR #134; the release gate for real children did not change.

## 4. Assignments that needed a judgment

- **#19** (research metrics dashboard) is loop 6: the dashboard is Phase 3's metrics work, although
  it merged during loop 3.
- **#30, #35, #38, #40, #41, #43** are loop 2: each changes how pages and characters stay consistent,
  the risk loop 2 owns. #34, #36 and #42 are loop 3: they fix production failures or an unsafe image.
- **#79** (ISO/IEC 25010 scope freeze) is loop 6: it fixes the system the ISO questionnaire rates.
- **#82–#91** are loop 4: each fixes a stop in the Objective 4 corpus campaign (B5, B6).
- **#122, #123** are loop 3 (the child's cast screen); **#124–#127** are loop 2 (scene retries and
  the judge's feedback).

## 5. Merged pull requests

| PR | Merge commit | Merged | Title | Loop |
|---|---|---|---|---|
| #1 | `ae683a8` | 2026-07-29 | feat(contracts): implement StoryMemory schema & port graph to partial-return | 2 |
| #2 | `54b4f91` | 2026-07-29 | feat(pipeline): implement story-analyzer node and roster extraction | 2 |
| #3 | `1443f66` | 2026-07-30 | feat(pipeline): implement scene-segmentation node and spec | 2 |
| #4 | `8f4a220` | 2026-07-31 | feat(pipeline): implement character-bible node (Phase 1) | 2 |
| #5 | `af7dea8` | 2026-07-31 | feat(pipeline): implement style presets (ADR-022) & resolve D-I (ADR-029) | 2 |
| #6 | `a0689b1` | 2026-07-31 | refactor(backend): module-level STYLE_PRESETS and style preset improvements | 2 |
| #7 | `05bd923` | 2026-07-31 | feat(pipeline): implement prompt-optimizer per spec (build_prompt and correct_prompt) | 2 |
| #8 | `8f40341` | 2026-07-31 | feat(pipeline): implement reference-conditioned image-generator node | 2 |
| #9 | `81a73f9` | 2026-08-01 | feat(pipeline): implement consistency-checker VLM judge node and close per-scene loop | 2 |
| #10 | `c746955` | 2026-08-02 | feat(pipeline): implement regeneration-controller node & ADR-010 retry loop | 2 |
| #11 | `b7d0059` | 2026-08-02 | feat(pipeline): implement compose node terminal gate | 2 |
| #12 | `a58b4e5` | 2026-08-02 | feat(moderation): implement complete moderation stack (input_gate, char_ref_mod, output_mod) | 3 |
| #13 | `ce38a3a` | 2026-08-02 | feat: input gate hardening (length guard + Filipino PII) | 3 |
| #14 | `86aaf3d` | 2026-08-04 | feat(ui): implement kid-flow-ui (S1-S4) | 3 |
| #15 | `47d8d7b` | 2026-08-07 | feat: auth and classroom implementation | 3 |
| #16 | `b458223` | 2026-08-09 | feat: Implement Teacher Dashboard | 3 |
| #17 | `06ad9d4` | 2026-08-09 | feat: classroom sharing and student customization | 3 |
| #18 | `1199e01` | 2026-08-10 | feat: UI and UX improvements | 3 |
| #19 | `fe350b7` | 2026-08-10 | feat: implement research metrics dashboard and frontend updates | 6 |
| #20 | `f4dff8e` | 2026-08-11 | fix: pipeline hardening round 2 | 3 |
| #21 | `dd71a99` | 2026-08-11 | fix(backend): restore SDK retries on every OpenRouter client | 3 |
| #22 | `abef420` | 2026-08-11 | fix(backend): align output_mod's classifier-error posture and pin vision providers | 3 |
| #30 | `d4cc323` | 2026-08-12 | fix: deduplicate ref_paths, filter notes all-or-nothing, fix missing-set spec | 2 |
| #34 | `d0ea931` | 2026-08-12 | fix: unstick the prod job — report killed horses, bound LLM calls, ban lettering, floor the segmenter | 3 |
| #35 | `62a1b6f` | 2026-08-13 | feat: implement scene setting and subject binding pipeline updates | 2 |
| #36 | `1926842` | 2026-08-13 | fix(output_mod): screen each scene as it is drawn, and say which classifier flagged | 3 |
| #37 | `6fdf043` | 2026-08-13 | PII pseudonymization, retry fix, and reader UX | 3 |
| #38 | `a269787` | 2026-08-13 | feat: implement lettering suppression detection channel and style preset updates | 2 |
| #39 | `673a045` | 2026-08-13 | feat: implement reference moderation retry loop (spec reference-moderation-retry) | 3 |
| #40 | `c88e785` | 2026-08-15 | feat: complete implementation of failure diagnostics and continuity fixes | 2 |
| #41 | `dbde5d6` | 2026-08-16 | fix(pipeline): harden reference pipeline & adopt ADR-039 for narrative-free character identity | 2 |
| #42 | `af69e71` | 2026-08-16 | fix(pipeline): sanitize placeholder character prompts | 3 |
| #43 | `9279541` | 2026-08-16 | feat(pipeline): implement visual-prompt reliability and adopt ADR-040 | 2 |
| #66 | `012d118` | 2026-08-22 | feat: implement research annotation surface and dataset infrastructure | 4 |
| #67 | `9794c06` | 2026-08-24 | feat(research): implement research corpus operations, queue materialization, and dataset freeze | 4 |
| #69 | `133bbad` | 2026-09-01 | Log out from empty research queues; Objective-4 readiness docs | 4 |
| #70 | `5dafe70` | 2026-09-04 | Judge correctness, object duplication, and the campaign-fatal Phase C blocker (ADR-045 … ADR-057) | 4 |
| #79 | `ac55472` | 2026-09-05 | ISO/IEC 25010 scope freeze: cut narration and PDF export, fix the five real defects | 6 |
| #80 | `77a46fe` | 2026-09-12 | feat: implement story recovery, titles, and character review UX | 3 |
| #81 | `ad9fb0a` | 2026-09-15 | Objective 4 campaign readiness: fal retry and attempt harvest | 4 |
| #82 | `059c416` | 2026-09-16 | fix(segment): drop object names outside the roster instead of raising | 4 |
| #83 | `d6d1a98` | 2026-09-16 | fix(input_gate): raise on backstop error so a resume re-runs the check | 4 |
| #84 | `1ddf1ce` | 2026-09-16 | fix(build_corpus): quarantine a moderation verdict and continue the campaign | 4 |
| #85 | `c1f0557` | 2026-09-16 | fix(segment): drop a character name outside the roster instead of raising | 4 |
| #86 | `ce7f8d5` | 2026-09-16 | fix(providers): retry an upstream error that OpenRouter sends as HTTP 200 | 4 |
| #87 | `f2048a4` | 2026-09-16 | fix(corpus): quarantine a fal content-checker 422 instead of stopping the campaign | 4 |
| #88 | `7576eee` | 2026-09-17 | fix(providers): ask again when fal's content checker rejects a draw | 4 |
| #89 | `4dd55e7` | 2026-09-17 | feat(corpus): allow a second readmission when the first is acknowledged | 4 |
| #90 | `56d7f4c` | 2026-09-17 | docs(obj4): log what Phase B6 actually did, decided and cost | 4 |
| #91 | `aff5516` | 2026-09-17 | chore(corpus): raise the hard spend ceiling to USD 30.50 | 4 |
| #93 | `757a406` | 2026-09-21 | fix(annotate): guide states the rulebook; round 2 reshuffles and stays shut for two raters | 4 |
| #101 | `6cc22ae` | 2026-10-09 | Segment species fix, Obj 4 resume, October probes and group guide | 4 |
| #113 | `0cd08cd` | 2026-10-10 | Add research run browser with pipeline graph | 6 |
| #115 | `ab95b31` | 2026-10-11 | Add research docs hub, dataset and results pages | 6 |
| #116 | `ed65d41` | 2026-10-11 | feat(research): limitations page and labelling demos (ADR-067, #111) | 6 |
| #122 | `dee3304` | 2026-10-12 | Show full character pictures when confirming the cast | 3 |
| #123 | `ce94812` | 2026-10-12 | Make character redraw suggestions distinct and explain replacement | 3 |
| #124 | `fbef571` | 2026-10-13 | fix: scope scene retry corrections to visible cast | 2 |
| #125 | `6f34c8f` | 2026-10-13 | Target scene retry identity corrections to the evaluated character | 2 |
| #126 | `c0390be` | 2026-10-13 | fix: distinguish named cast from requested background groups | 2 |
| #127 | `06cf920` | 2026-10-13 | docs: investigate scene-judge feedback and document its limits | 2 |
| #128 | `7a7b357` | 2026-10-21 | Improve StoryBuddy reader UX and add PDF downloads | 3 |
| #129 | `3049323` | 2026-10-23 | Fix student class-code login and improve book progress headers | 3 |
| #130 | `865b6e8` | 2026-10-26 | feat: require students to replace teacher-issued passwords | 5 |
| #131 | `1466981` | 2026-10-29 | feat: teacher-held moderation calibration (ADR-080) | 5 |
| #132 | `5197353` | 2026-11-01 | feat: teacher notes the child can read (ADR-081) | 5 |
| #133 | `8bf8d8a` | 2026-11-05 | feat: magic pencil (ADR-082, tickets 04-11 + review fixes) | 5 |
| #134 | `47ed5f7` | 2026-11-21 | feat: teacher review, magic pencil and student notes on by default | 5 |
