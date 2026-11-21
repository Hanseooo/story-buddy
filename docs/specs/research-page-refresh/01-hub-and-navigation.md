# 01 — Hub, navigation and objectives

Index: [../research-page-refresh.md](../research-page-refresh.md). The shared rules (SH-) and
decisions (D-) referenced here are defined there.

Current code: `frontend/app/(research)/research/page.tsx` (async, reads session and profile, own
nav, hero "View Live Metrics"), `frontend/components/PipelineMap.tsx`,
`_shared/components/ResearchHeader.tsx`, `_shared/constants.ts:80-97` (`RESEARCH_TABS`),
`(reference)/layout.tsx` ("Back to Methodology").

## US-01 Hub

As a groupmate writing the paper, I want `/research` to list every research page in paper order,
so that I can find the page for the paper section I am writing.

Applies: SH-01, SH-03, SH-04, SH-07, SH-10

- **AC-01** Opening `/research` shows three groups, Methodology, Results and Reference, holding the
  pages of the index §4.1 in that order.
- **AC-02** The Previous/Next reading order is index §4.1 from Conceptual framework and pipeline
  through Docs. Runs is outside the reading order: it needs sign-in.
- **AC-03** Each hub entry shows the page title, one line on what it covers, and the paper
  section(s) it feeds. Example: "Dataset — what a pair is, labels, splits · Paper: Methodology →
  Dataset, Annotation, Dataset Division".
- **AC-04** `/research` no longer contains: the "11 deterministic nodes" claim, the self-hosting
  claim (`page.tsx:181,184`), or the marketing headlines (`page.tsx:70,149,152,194,197`). The
  pipeline map moves to the pipeline page (US-15). Wherever `PipelineMap` renders, the console has
  no error. The retry loop is drawn without `calc()` in an SVG `d` attribute (`PipelineMap.tsx:115`).
- **AC-05** (D-26) The hub reads no session and no profile. It renders identically logged in and
  logged out, and the header's `showAccount` is off, as on the reference pages.

## US-02 Header and page-to-page navigation

As a groupmate on a phone, I want a short header and Previous/Next links, so that I can move
through the pages without hunting through tabs.

Applies: SH-04, SH-10

- **AC-06** On every research page the header shows Research home, Docs and Runs, plus the
  role-gated Annotate and Adjudicate for researchers (D-24). The tabs Dataset, Results and
  Limitations leave the header.
- **AC-07** Each page in the reading order starts with "Back to research home" (replacing "Back to
  Landing" and "Back to Methodology"). It ends with Previous and Next links whose text names the
  target page.
- **AC-08** Pressing Tab from page load reaches the skip and header links, then the back link, the
  content and Previous/Next, in that order. Each shows the `FOCUS` outline.
- **AC-09** At 390px the header fits on at most two lines (the existing wrap behaviour) and no page
  scrolls sideways.

## US-03 Objectives and answers

As a groupmate writing the Results chapter, I want each objective with its current answer and
evidence, so that I can write each results subsection from one place.

Applies: SH-01, SH-02, SH-03, SH-07

- **AC-10** `/research/objectives` lists the five objectives in the manuscript's order, worded as in
  `docs/capstone/research_direction_and_goals.md` §Objectives (lines 75–83). The data test pins the
  wording to that file.
- **AC-11** Each objective shows **Answer**, **Evidence** (links to tracked files) and **Explained
  on** (a link to the chapter page).
- **AC-12 (Objective 1, D-20)** Answer: "Achieved." The orchestrated pipeline is implemented as a
  LangGraph graph of 14 nodes (11 in baseline mode). It produced the 42 study books end to end, and
  its automated tests pass. Evidence links: `backend/pipeline/graph.py`, the pipeline page, and the
  Objective 2 figures. The page does not mention Tool A, which was dropped (D-28).
- **AC-13 (Objective 2)** Answer: 42 digital picture books were produced through the pipeline, 30
  from synthetic stories and 12 from donated stories. Three donated stories did not finish and were
  replaced by backup stories of the same style. Each figure cites its runbook or changelog source.
- **AC-14 (Objectives 3 and 5)** Answer: "Survey pending". Nothing else (D-10).
- **AC-15 (Objective 4)** Answer: the fine-tuned judge did not beat its untrained base on F1 (0.31
  vs 0.47), plus the false-alarm tradeoff sentence from US-10 AC-02. It says the comparison is
  partial (US-10 AC-05) and links to `/research/results`.
