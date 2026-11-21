# 04 — New chapter pages

Index: [../research-page-refresh.md](../research-page-refresh.md). All five pages depend on ADR-083
(D-19, written in US-26). Each is a static reference page: `page.tsx` + `data.ts` + `data.test.ts` under
`app/(research)/research/(reference)/<route>/`, using the existing reference layout and components
(`ScrollTable`, `Source`, `ImageCards`). Each quotes existing docs or code, and its test pins what it
quotes (SH-02).

## US-15 Conceptual framework and pipeline — `/research/pipeline`

As a groupmate writing the Conceptual Framework, I want the IPO model and the current pipeline
explained, so that I can fill Figures 1 and 2 and Appendices A and B.

Applies: SH-01, SH-02, SH-03, SH-06, SH-08

- **AC-01** The page shows the IPO figure (US-21) and the current LangGraph pipeline diagram
  (US-20), each per SH-06.
- **AC-02** It lists the 14 graph nodes with one plain line each, and says which run in which mode:
  - baseline mode, 11 nodes: the mode the study corpus was generated in
  - teacher-review mode, 14 nodes: the default since 2026-11-21

  The test compares the node list with `backend/pipeline/graph.py`.
- **AC-03** A table maps the paper's module names to graph nodes. It states that the paper's
  "prompt optimizer" is not a graph node (`evidence:audit-3-docs-paper.md#P9`). The caps are read
  from `config.py` per SH-08: up to 10 pages (minimum 3), 3 drawing attempts per page, 3 "try
  again" taps, and 500 words (300 when the corpus was made).
- **AC-04** The interactive `PipelineMap` moves here with AC-04 of US-01 fixed. Its node set matches
  AC-02. Per D-25, every node is visible on first render and in print. No node starts hidden waiting
  for a scroll.
- **AC-05** It says what happens when a check fails, per mode:
  - baseline: the job stops and no partial book is made
  - teacher-review: the job is held for the teacher (ADR-080)

  It also mentions the magic pencil and "other versions" at the reveal (ADR-082).

## US-16 Methodology at a glance — `/research/methodology`

As a groupmate, I want the research design, setting and corpus in one place, so that the
Methodology chapter matches the repo.

Applies: SH-02, SH-03

- **AC-06** It states the research design and the Spiral phases (source `methodology.md` §1,
  `PHASE_05_RESULTS.md`), with the Phase 0.5 gate result as recorded.
- **AC-07** Setting (D-04): the stories came from Vicente Hizon, Sr. Elementary School, collected
  through their teachers.
- **AC-08** Implementation site (D-16): both options are shown as undecided.
  - Option A: Vicente Hizon, Sr. ES, if the school admits researchers despite its PAASCU
    accreditation.
  - Option B: HCDC, with 40 School of Teacher Education (STE) students.
- **AC-09** Corpus counts, each with its source: 15 donated stories received, 12 generated, 30
  synthetic stories, 42 books.
- **AC-10** Respondents: expert validators per D-05, and ISO respondents per D-06.

## US-17 Evaluation instruments — `/research/instruments`

As a groupmate writing Evaluation of Instruments, I want both instruments described accurately, so
that the paper and the repo agree.

Applies: SH-02, SH-03

- **AC-11** Expert validation (Objective 3, D-05, D-21):
  - **Evaluators:** 2 BEEd professors and 1 Arts professor. Each signs an informed consent form
    first.
  - **Procedure:** each evaluator reviews the original child-written story and its generated book,
    and fills in one questionnaire per book with its Story ID.
  - **Questions:** 7 open-ended questions, answered in the evaluator's own words, with no rating
    and no yes/no. The page lists the seven question headings verbatim from the tracked copy
    (US-24 AC-10). Each heading has its guide prompt, which is guidance, not a separate question:
    1. How appropriate and meaningful is the generated picture book for its intended readers?
    2. How effectively does the written language communicate the story and engage its intended
       readers?
    3. How well are the characters and setting developed and represented throughout the picture
       book?
    4. How coherent and effective is the development of the plot from beginning to end?
    5. How effectively do the illustrations communicate and support the written narrative?
    6. How faithfully does the generated picture book represent the original child-written story?
    7. Considering the generated picture book as a whole, how effective is its overall presentation
       and reading experience, and what improvements would you recommend?
  - **Excluded:** the page shows no evaluator names and no researcher contact details.
- **AC-12** Analysis: "Content analysis or thematic analysis (to be decided)" until O-04 is
  settled. The page never calls the expert results descriptive statistics.
- **AC-13** ISO/IEC 25010 questionnaire (Objective 5):
  - 23 Likert items on the 6 characteristics, listed verbatim from the tracked copy (US-24 AC-13)
    and grouped as in D-27
  - scale 1–5, where 5 = Strongly Agree, so a higher mean is better
  - at least 30 respondents in total from IT experts, IT students, teachers and education
    students, not split equally
  - descriptive statistics only, with no CVI and no Cronbach's α pilot
  - respondents sign a consent form first; the page shows no researcher contact details
- **AC-14** Both instruments show the status "Survey pending" until results exist (D-10).

## US-18 System architecture and specifications — `/research/architecture`

As a groupmate writing System Architecture and Hardware and Software Specifications, I want every
component and spec with its source, so that Tables 5–8 and the components table are correct.

Applies: SH-02, SH-06, SH-08

- **AC-15** It shows the redrawn system-architecture diagram (US-20) per SH-06.
- **AC-16** A components table lists each component with its role and source file. It includes the
  ones the old diagram missed:
  - Supabase Auth
  - the FastAPI → Redis enqueue
  - OpenRouter and fal.ai
  - moderation and Presidio in the web tier (`backend/app/main.py:171-200`)
  - Langfuse (Sentry was listed here until its removal on 2026-11-22)
  - the research endpoint
  - teacher review, notes, magic pencil and PDF export
- **AC-17** Specification tables (paper Tables 5–8), each value citing its source:
  - model IDs from `config.py`
  - library versions from `pyproject.toml` and `package.json`
  - training hardware from the training run's record (RTX A6000 48 GB, CUDA 12.8, LLaMA-Factory
    v0.9.5), copied into the restored `hardware_and_hosting.md` (US-24) because the run record is
    git-ignored
  - hosting: Northflank, North America, free tier (D-07)
- **AC-18** Development hardware lists only what is confirmed: the RTX 3050 Ti 4 GB
  (`research_runbook.md:549`). Other rows are left for the owner to supply in
  `hardware_and_hosting.md`.

## US-19 Ethics and safety — `/research/ethics`

As a groupmate writing Ethical Considerations, I want the study's ethics basis and the system's
safety measures stated plainly, so that the paper's empty ethics sections can be filled honestly.

Applies: SH-01, SH-02, SH-03

- **AC-19** Basis (D-08): no ethics committee review, because researchers did not interact with the
  children and learners did not use the system during the study. The system supports
  teacher-issued student accounts.
- **AC-20** Consent (D-22): the stories were used with the teacher's signed hard-copy consent. The
  page claims nothing further about its scope, and says no separate parental consent was collected.
  Expert evaluators sign their own informed consent form (D-21).
- **AC-21** Privacy (D-07, D-09): it discloses all of the following:
  - Donated story IDs, plot summaries and character names are kept in the public repository.
  - The pages show no donated images.
  - Personal information is redacted before storage (Presidio).
  - Hosting is in North America.
- **AC-22** Safety measures as configured: the moderation layers and where each runs, teacher
  approval, the teacher hold (ADR-080), teacher notes (ADR-081) and the magic pencil limits
  (ADR-082). Sources: `ethics_and_safety.md` after its update (US-24), and `config.py`.
