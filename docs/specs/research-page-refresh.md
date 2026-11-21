# Spec index — research page refresh

**Status:** Ready (2026-11-21). O-01 (test seams) and O-02 (ADR-083) are resolved. What is left
(O-04, O-07, O-12, §7) affects single sentences only, and each has its placeholder text
defined, so building can start. Ready does not mean built or authorized.
**Decided in:** the `/han-grill` session of 2026-11-21 (rounds Q1–Q14), after five read-only audits.
**Delivery:** one PR (D-14).

## How to read this spec (agents start here)

This file holds the scope, the shared rules (`SH-`), decisions (`D-`), edge cases, open decisions
(`O-`) and a coverage index. Each detail file holds the user stories (`US-`) and acceptance criteria
(`AC-`) for one area. Read this file, then only the detail file for your story, then
`07-verification.md`. US-, SH-, D- and O- IDs are unique across all files; AC numbers are unique within a detail file and cited as `US-nn AC-nn`.

| File | Stories | Read when |
|---|---|---|
| [01-hub-and-navigation.md](research-page-refresh/01-hub-and-navigation.md) | US-01–US-03 | `/research` hub, header, previous/next, objectives page |
| [02-dataset.md](research-page-refresh/02-dataset.md) | US-04–US-09, US-27 | `/research/dataset` |
| [03-results-and-limitations.md](research-page-refresh/03-results-and-limitations.md) | US-10–US-14 | `/research/results`, `/research/limitations` |
| [04-chapter-pages.md](research-page-refresh/04-chapter-pages.md) | US-15–US-19, US-29 | the new pipeline, methodology, SDLC, instruments, architecture and ethics pages |
| [05-diagrams-and-exports.md](research-page-refresh/05-diagrams-and-exports.md) | US-20–US-23 | `docs/diagrams/`, PNG export, run-viewer graph |
| [06-source-docs.md](research-page-refresh/06-source-docs.md) | US-24–US-26, US-28 | repo docs the pages quote, docs hub, ADR-083 |
| [07-verification.md](research-page-refresh/07-verification.md) | — | test seams, checks, evidence required to call it done |
| [evidence/](research-page-refresh/evidence/) | — | the 2026-11-21 audit reports with file:line evidence. Reports cite IDs such as F4, B-2, P11, D8; detail files reference them as `evidence:<report>#<id>` |

The audit reports mention screenshots and a `paper.md` that lived in a temporary session folder and
may be gone. Re-create them with the procedure in `07-verification.md` if needed.

## 1. Purpose and scope

**Problem.** The public research pages are where groupmates (most without an ML background) are
meant to get the facts for the research paper ("StoryBuddy - UPDATED OCT", Google Doc, work in
progress). As of 2026-11-21 the pages are partly stale (the pipeline has 14 nodes, not 11), partly
wrong (a human/non-human table counts animals as human), hard to understand (what a "pair" is,
what "fewer false alarms" means), and they lack whole paper chapters (pipeline, architecture,
methodology, instruments, ethics, per-objective answers). Every diagram is out of date and none
can be downloaded as an image.

**Solution.** `/research` becomes a hub listing every research page in paper order. New static
chapter pages fill the paper's missing material. The dataset, results and limitations pages get
corrected and rewritten in plain words. Diagrams are updated or created and published as PNGs, and
the repo docs the pages quote are corrected first.

**Users.** Groupmates writing the paper (primary). The adviser and the panel reading the public
pages. The owner maintaining them. Agents implementing and re-verifying them.

**In scope.** `/research` and every page under `/research` except the run viewer's content;
`frontend/components/PipelineMap.tsx`; the run viewer's pipeline map
(`metrics/[jobId]/pipelineGraph.ts`); `docs/diagrams/`; the repo docs the pages quote; one new ADR.

**Out of scope.**
- `/`, the app's home page. It stays as it is (D-11).
- The run viewer, `/annotate` and `/adjudicate`, apart from the pipeline map in US-23.
- Editing the paper. Groupmates do that from the pages.
- Any new measurement, any read of the held-out test set, and running the scoring scripts.
- Survey results for Objectives 3 and 5. They are shown as "Survey pending" (D-10).
- Flagged for later: `/research/metrics` without a trailing slash returns 200 when logged out
  (`frontend/middleware.ts:33,85`); the `private_assets` bucket has no migration
  (`backend/finetune/materialize_pairs.py:28`); ADR-010 and ADR-026 are still marked Accepted
  although later ADRs replaced them.

**Existing behaviour that constrains the change (verified).**
- The reference pages are public, static server components that show synthetic material only
  (ADR-065 decisions 1 and 5, ADR-066, ADR-067, ADR-070). `frontend/middleware.ts` guards only
  `/research/metrics/`.
- Page data modules are pinned to their source docs. Each `data.test.ts` reads the source doc and
  fails when a page value is not in it (ADR-066 decision 6; e.g. `results/data.test.ts`).
- The header is `_shared/components/ResearchHeader.tsx` and renders `RESEARCH_TABS` from
  `_shared/constants.ts:80-97` (Runs, Dataset, Results, Limitations, Docs, and the role-gated
  Annotate and Adjudicate).
- `/research/page.tsx` is async (it reads the session and the profile) and has no `loading.tsx`.
- ADRs are frozen (AGENTS.md Hard Rules). A new public route needs a new ADR plus its row in
  `docs/product/ADRs.md`, accepted before building.
- The frontend has no E2E runner. `pnpm test` runs vitest. Real-browser checks use `playwright-cli`.

**Acceptance journeys.**
- **J1 — writing the paper's Dataset section.** A groupmate opens `/research`, picks Dataset under
  Methodology, reads what a pair is, one real record and why the splits are as they are, downloads
  the dataset-flow PNG, and follows Next to Evaluation instruments.
- **J2 — writing Results 3.3.** A groupmate opens Objectives and answers and reads Objective 4's
  answer. They follow the link to Results, read the definitions box and the false-alarm tradeoff
  sentence, and download the confusion-matrix PNG.
- **J3 — on a phone.** At 390px the header shows three items. A wide table shows that it scrolls
  sideways, and the page itself never scrolls sideways. Previous and Next work.
- **J4 — checking a paper fact.** A groupmate opens Docs and reads the "What the paper must say"
  panel, which lists each settled paper/repo correction.
- **J5 — after a code change.** A developer adds a pipeline node or edits a diagram without
  re-exporting it. A test goes red and names what to update.

## 2. Shared rules

**SH-01 Static and synthetic only.**
- The reference and chapter pages read no session and run no live query.
- They show no donated-story image and no held-out test image. Donated material appears only as
  whole-split counts (ADR-065 decisions 1 and 5).

**SH-02 Source first.**
- Every number and factual sentence on a page lives in a tracked source file that the page names.
  The page's data module has a test that fails when the value or sentence is not in that source
  (the ADR-066 decision 6 pattern).
- A fact not yet in a tracked doc gets a runbook entry and a `research-changelog.md` row before a
  page cites it.
- Page copy changes and their source-doc changes land in the same commit.

**SH-03 Plain language.**
- Each term in SH-09 is defined on first use on each page that uses it: inline, or in that page's
  definitions box.
- Judge comparisons never say "more careful", "more reliable", "less reliable" or "more accurate"
  without naming the measure.
- No marketing copy: the tone of "the science behind the magic" or "eliminating generative identity
  drift". Remaining jargon from `evidence:audit-5-render.md` ("Undefined jargon") is defined or cut.

**SH-04 Navigation.**
- The header shows three items for every viewer: Research home (`/research`), Docs, and Runs. The
  role-gated Annotate and Adjudicate stay for researchers (D-24).
- Every page except the hub starts with a "Back to research home" link to `/research`.
- Every page in the reading order (US-01 AC-02) ends with Previous and Next links naming the
  target page. The first page has no Previous and the last has no Next.
- All of these are real links, reachable by Tab in reading order, with the existing `FOCUS` outline.
  The current header item has `aria-current="page"`.
- The label is "Runs" everywhere. "View Live Metrics" is gone.

**SH-05 Wide tables.**
- Tables use the existing `ScrollTable`.
- When a table is wider than the viewport, a visible cue says it scrolls sideways, and the key
  column (the row name) is first.
- The scroll region can be focused and scrolled by keyboard, and has an accessible name.

**SH-06 Figures.** Every diagram and chart shows:
- the image inline, with alt text that states what it shows
- a caption "As of YYYY-MM-DD"
- a download link to its PNG whose text names the file; browsers that ignore `download` open the
  PNG instead
- a link to the editable source on GitHub

A missing PNG fails a test. It never shows as a broken image.

**SH-07 States.**
- Chapter pages are static and need no loading state. They keep the segment's existing `error.tsx`.
- A pending objective shows the literal text "Survey pending" with no other placeholder text.

**SH-08 Pipeline facts come from code.** These page values are tested against the code text:
- the node count and node names (`backend/pipeline/graph.py`)
- pages per book, attempts per page and "try again" taps (`backend/app/config.py`)
- the word limit (ADR-068)

**SH-09 One vocabulary.** natural pair · constructed pair · reference · page drawing · Same /
Different · study owner · freeze (registered) · train / validation / held-out test set · seed ·
checkpoint · catch · miss · false alarm · unreadable answer · precision · recall · F1.

**SH-10 Phone width.**
- At 390px no page scrolls sideways.
- Tap targets keep the existing `min-h-11`.
- Long Previous/Next titles wrap.

## 3. Decisions and rationale

| ID | Decision | Reason |
|---|---|---|
| D-01 | One new static page per paper chapter: pipeline, methodology, instruments, architecture and specs, ethics (Q1 B). | Maps one to one onto the paper. The owner chose it over a longer `/research`. |
| D-02 | `/research/objectives` is its own page (Q7 B). `/research` becomes the hub. | Owner: keep all research navigation on the research hub, and keep UX simple. |
| D-03 | The header has three items, the hub is a table of contents in paper order, and pages have Previous/Next (Q13 A). | The simplest option that works at 390px with no new control. A flat header would hide most of about 11 tabs off-screen on phones. |
| D-04 | Source school: Vicente Hizon, Sr. Elementary School. Matina Aplaya is wrong everywhere (Q2.1). | Owner. |
| D-05 | Expert validation: 2 BEEd professors and 1 Arts professor. A 7-question, qualitative written interview with no rating scale (Q9, final answer). | Owner. |
| D-06 | ISO/IEC 25010 questionnaire: 23 Likert items on 6 characteristics (functional suitability, interaction capability, reliability, security, compatibility, performance efficiency). At least 30 respondents in total from IT experts, IT students, teachers and education students, not split equally. Scale 1–5, where 5 = Strongly Agree and 1 = Strongly Disagree. Descriptive statistics only, no CVI and no Cronbach's α pilot (Q2.3–2.5, Q9, Q12). | Owner. Higher mean = better, which the pages must say. |
| D-07 | Hosting: Northflank, North America region, because of the free tier (Q2.6). | Owner. Also disclosed in the privacy material. |
| D-08 | No ethics committee review: researchers did not interact with the children, and learners did not use the system during the study. Story use rests on a hard-copy agreement from the teacher. The paper's line "learners are not direct users" is reconciled as "learners did not use the system during the study; the system supports teacher-issued student accounts" (Q10). | Owner. Residual risk recorded: no separate parental consent, and donated details stay public (D-09). |
| D-09 | Donated story IDs, plot summaries and character names stay in the public repo and are disclosed in the paper's privacy section (Q3 A). | Owner. The assistant recommended unlinking them from the public site. The owner declined; the teacher's agreement is the recorded basis. |
| D-10 | Objectives 3 and 5 show "Survey pending" with no method text (Q8, Q12). | Owner: the surveys have not been run yet. |
| D-11 | `/` (the app's home page) is unchanged (Q11). | Owner. |
| D-12 | The 9 clothing/style-only Different labels are disclosed as known errors, and the freeze is unchanged. The human/non-human table is recounted by species (Q4 B). | The table is page reporting, not registered data, so correcting it changes nothing registered. The preregistered freeze must not change. |
| D-13 | Diagrams: update the pipeline (both modes) and the run-viewer map; redraw the system architecture as `.drawio.svg`; mark the July diagram as the planned design; create the IPO model, the dataset build and annotation flow, and the student and teacher journeys. Export PNGs with Playwright (Q5 B). | Fills the paper's empty figure slots plus the dataset confusion and the shipped November features. Playwright is already installed, and draw.io desktop is not. |
| D-14 | One PR (Q14 B). | Owner. Commits inside the PR follow §4.2's order so each one can be reviewed and reverted on its own. |
| D-15 | `docs/capstone/hardware_and_hosting.md` is restored from `2cb6d2f^` and then updated (Q6). | The 2026-07-28 cut left the 4-byte text `proc` while the same commit deleted other files cleanly. Inferred accidental. Four docs still cite its sections. |
| D-16 | Implementation site has two options. Option A: Vicente Hizon, Sr. ES, if the school admits researchers despite its PAASCU accreditation. Option B: HCDC, with 40 School of Teacher Education (STE) students. The methodology page shows both until one is chosen (Q10). | Owner. |
| D-17 | The spec uses progressive disclosure, not `docs/specs/TEMPLATE.md` (owner, final round). | `TEMPLATE.md` is for one pipeline node. This spec spans pages, docs and diagrams. |
| D-18 | Test seams S-1 to S-4 are approved. S-5, the manual real-browser check, is dropped, and no E2E runner is added (O-01, owner: "no need for e"). | Owner. Known cost: console errors and phone-width layout faults are found only by eye. The owner's global rule asks for real-browser evidence, and this explicit choice overrides it for this change. |
| D-19 | ADR-083 is accepted by the owner (O-02, 2026-11-21). It is written with status Accepted as part of US-26. | Owner. |
| D-20 | Objective 1 is **Achieved**. Evidence: the implemented graph (`backend/pipeline/graph.py`), the passing automated tests, and the 42 books produced end to end (O-03). | Owner: "we already tested and used it and it works." Tool A, the per-stage success-rate script in `docs/specs/functional-verification-matrix.md`, is a draft and was never written. It is dropped (D-28). |
| D-21 | Expert evaluation is the 7-question open-ended questionnaire supplied by the owner on 2026-11-21. Each expert reviews the original story and its generated book, and fills in one questionnaire per book with a Story ID. Evaluators sign an informed consent form (O-05). | Owner. The researcher's name and email on the form are not copied into any page or doc. |
| D-22 | The teacher's hard-copy agreement is a consent form. The pages say exactly that and claim nothing more about its scope (O-06). | Owner: "only the consent." |
| D-23 | The backstop limitation states only the measured stop count (4 of 30). The unverified human-review sentence is dropped (O-08). | The owner was unsure it was needed. The sources disagree (2 vs 4), so the sentence is cut rather than guessed. |
| D-24 | The Annotate and Adjudicate tabs stay in the header for researchers (O-09). The dataset page explains why the team built its own labelling tool (US-27). | Owner. |
| D-25 | The pipeline map shows every node with no scroll-triggered reveal. Any animation starts from a visible state, so print and full-page capture show all nodes (O-10). | Delegated to the assistant. Simpler, works for print, and avoids hidden content for reduced-motion users. |
| D-27 | The ISO/IEC 25010 questionnaire is the owner's 23-item form supplied on 2026-11-21. Items 1–5 are Functional Suitability, 6–9 Interaction Capability, 10–14 Reliability, 15–17 Performance Efficiency, 18–21 Security and 22–23 Compatibility. Each is rated 5 = Strongly Agree down to 1 = Strongly Disagree. Respondents sign a consent form first (O-05b). | Owner. The researcher's contact details are not copied. |
| D-28 | The Tool A, Tool B and Tool C labels are retired. Tool A, the per-stage success-rate script, is dropped and not built. Tool B becomes "the expert questionnaire" and Tool C becomes "the ISO/IEC 25010 questionnaire" in every live doc. Frozen ADRs are not edited (US-28; resolves O-03b). | Owner: "stale … remove it now." |
| D-26 | `/research` reads no session and is static like the reference pages, so no `loading.tsx` is needed (O-11). | Owner accepted the recommendation. Matches ADR-065. |

## 4. Structure

### 4.1 Pages

Reading order. The hub groups pages, and Previous/Next follow this order:

| Group | Page | Route | Status | Detail |
|---|---|---|---|---|
| Methodology | Conceptual framework and pipeline | `/research/pipeline` | new | US-15 |
| Methodology | Methodology at a glance | `/research/methodology` | new | US-16 |
| Methodology | Development loops (SDLC) | `/research/sdlc` | new | US-29 |
| Methodology | Dataset | `/research/dataset` | exists | US-04–US-09 |
| Methodology | Evaluation instruments | `/research/instruments` | new | US-17 |
| Methodology | System architecture and specifications | `/research/architecture` | new | US-18 |
| Methodology | Ethics and safety | `/research/ethics` | new | US-19 |
| Results | Objectives and answers | `/research/objectives` | new | US-03 |
| Results | Character-consistency results (Objective 4) | `/research/results` | exists | US-10–US-13 |
| Results | Limitations | `/research/limitations` | exists | US-14 |
| Reference | Docs | `/research/docs` | exists | US-25 |
| Reference | Runs (sign-in) | `/research/metrics` | exists, unchanged | — |

The order follows the paper's table of contents (Conceptual Framework → Methodology → Results).
Training and validation is in the paper's Methodology but stays on the results page, where its
numbers already are (inferred; not discussed).

### 4.2 Commit order inside the one PR

1. Source docs and ADR-083 (US-24, US-26).
2. Fixes to wrong facts on the existing pages (US-01 AC-04, US-09, US-14).
3. Clarity copy (US-04–US-08, US-10–US-12).
4. Diagrams and the export script (US-20–US-23).
5. New pages, the hub and navigation (US-01–US-03, US-15–US-19, US-25).

New pages follow the existing reference-page pattern: `page.tsx` plus `data.ts` plus
`data.test.ts` under `app/(research)/research/(reference)/<route>/`, inside that segment's layout.

## 5. Edge cases

| Case | Expected behaviour | Home |
|---|---|---|
| A diagram's PNG is missing | A test fails and names the PNG. The page never shows a broken image. | SH-06, US-22 AC-09 |
| A diagram source is edited but not re-exported | A test fails: the source hash differs from the export manifest. | US-22 AC-08 |
| A node is added to `graph.py` | A test fails on the pipeline page and on the run-viewer map. | SH-08, US-15 AC-02, US-23 AC-12 |
| A source-doc sentence changes but the page copy doesn't | The page data test fails (existing pattern). | SH-02 |
| A table is wider than the viewport | Scroll cue, key column first, page width unchanged. | SH-05, SH-10 |
| Someone opens a chapter page directly from a paper link | It renders logged out, and the back link goes to the hub. | SH-01, SH-04 |
| First and last pages in the reading order | No Previous on the first, no Next on the last. | SH-04 |
| A browser ignores the `download` attribute | The link opens the PNG. | SH-06 |
| Survey results arrive later | Out of scope. "Survey pending" stays until a later change. | D-10 |
| Objective 1 while Tool A was never built | Shown as Achieved with its evidence. Tool A is dropped. | D-20, D-28 |
| The scope of the teacher's hard-copy agreement | Stated only as a signed consent. | D-22, US-19 AC-20 |
| The analysis method is not yet chosen | Shows "to be decided". | O-04, US-17 AC-12 |
| The implementation site is not yet chosen | Both options are shown. | D-16, US-16 AC-08 |
| Donated details exist in the repo | Pages still show none (SH-01). The ethics page discloses the repo decision. | D-09, US-19 AC-21 |
| The pipeline map is printed or captured full-page | All nodes visible. Today 3 of 11 are hidden by the scroll animation (`evidence:audit-5-render.md#F2`). | D-25, US-15 AC-04 |
| A logged-out visitor uses the hub's Runs link | Existing sign-in redirect for `/research/metrics/`. The no-slash gap is out of scope. | §1 out of scope |

## 6. Verification

Seams, checks and the evidence required are in
[07-verification.md](research-page-refresh/07-verification.md). The seams S-1 to S-4 are
**confirmed** (D-18). Nothing in this spec has been run. It establishes no passing behaviour.

## 7. Open decisions

Resolved on 2026-11-21: O-01 → D-18, O-02 → D-19, O-03 → D-20, O-05 (expert form) → D-21,
O-06 → D-22, O-08 → D-23, O-03b → D-28, O-05b → D-27, O-09 → D-24, O-10 → D-25, O-11 → D-26.

| ID | Decision or evidence needed | Blocks | Who |
|---|---|---|---|
| O-04 ([issue](https://github.com/Hanseooo/story-buddy/issues/135)) | Content analysis or thematic analysis for the 7 open-ended answers. Until then the page shows "Content analysis or thematic analysis (to be decided)". D-06's "descriptive statistics only" applies to the ISO form only. | US-17 AC-12 wording | owner |
| O-07 ([issue](https://github.com/Hanseooo/story-buddy/issues/136)) | Which implementation site is used. | Nothing now. A later page update. | owner, later |
| O-12 ([issue](https://github.com/Hanseooo/story-buddy/issues/137)) | The ISO consent form disagrees with the questionnaire: it says "25-item" (the form has 23), "five" characteristics (it lists six), and "Usability" (section B is Interaction Capability). Its role boxes (Teacher, IT Professional, IT Student (Graduating), Other) do not list education students, one of the four respondent groups in D-06. The owner fixes the paper form. The pages use the questionnaire's own values. | Nothing in the pages. The form groupmates hand out. | owner |

## 8. Coverage index

Each source item and where its requirement lives.

| Source | Home |
|---|---|
| Audit F1 (SVG `calc()` console error) | US-01 AC-04 |
| Audit R1 (11 vs 14 nodes), R3 (self-host), F8 (marketing), R4 | US-01 AC-04, US-15 AC-02, AC-05 |
| Audit R6 (`loading.tsx`) | D-26, US-01 AC-05 |
| Audit R8 / F10 (nav names) | SH-04, US-02 |
| Dataset B1–B8, F1–F5 | US-04–US-09 |
| Render F3 (phone tables), jargon list | SH-05, SH-03 |
| Render F4–F7 | US-09 AC-22, AC-23, US-05 AC-06, US-14 AC-16 |
| Results B-1–B-7, P14 | US-10–US-12 |
| Results B-8–B-10, L2–L4 | US-14 |
| Results B-11 charts | US-13, US-22 |
| Docs D2–D13 | US-24, US-25 |
| Diagrams (a)–(d) | US-20–US-23 |
| Paper conflicts P1–P24 | US-24 AC-01 (repo side), US-25 AC-05 (panel); owner-only rows → D-04–D-08, D-16 |
| Q1–Q14 and the final answer | D-01–D-17 |
| New objectives section | US-03 |
| Spec format request | D-17, this index |
| Answers to the open decisions, 2026-11-21 | D-18–D-26 |
| Why the team built its own labelling tool | US-27 |
| Expert questionnaire (owner-supplied) | D-21, US-17 AC-11, US-24 AC-10 |
| ISO questionnaire (owner-supplied) | D-27, US-17 AC-13, US-24 AC-13, O-12 |
| Retire Tool A/B/C | D-28, US-28 |
