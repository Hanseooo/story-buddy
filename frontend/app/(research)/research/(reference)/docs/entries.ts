// The docs hub links here instead of rendering markdown (ADR-065 decision 2).
export const githubUrl = (repoPath: string) => `https://github.com/Hanseooo/story-buddy/blob/main/${repoPath}`;

export type DocEntry = {
  /** Repo-relative path. entries.test.ts fails when a listed file is renamed or deleted. */
  path: string;
  answers: string;
  /** ISO date of the file's last change. A literal, because git history is missing at build time;
   *  entries.test.ts fails when it is older than the file's last commit. */
  lastChanged: string;
  startHere?: true;
};
export type DocChapter = { id: string; title: string; blurb: string; entries: DocEntry[] };

const D = "docs/diagrams/drawio/";

// Grouped in paper order (audit-3 section 5b map).
export const DOC_CHAPTERS: DocChapter[] = [
  {
    id: "start",
    title: "Start here",
    blurb: "The study in plain words, and what changed since the plan was registered.",
    entries: [
      {
        path: "docs/capstone/group-guide.md",
        answers: "What is StoryBuddy, what did the study find, and what are its limits? Plain words, no code.",
        lastChanged: "2026-11-21",
        startHere: true,
      },
      {
        path: "docs/capstone/research-changelog.md",
        answers: "What changed since the plan was registered, and what must the paper say about it?",
        lastChanged: "2026-11-21",
      },
    ],
  },
  {
    id: "intro",
    title: "Chapter 1: Introduction",
    blurb: "Objectives, scope and what the study does not claim.",
    entries: [
      {
        path: "docs/capstone/research_direction_and_goals.md",
        answers: "What are the objectives, and what does the study not claim?",
        lastChanged: "2026-11-22",
      },
    ],
  },
  {
    id: "design",
    title: "Chapter 2: Methodology, design and ethics",
    blurb: "Research design, respondents, locale, consent and safety.",
    entries: [
      {
        path: "docs/capstone/methodology.md",
        answers: "How was the system built, and how is each objective evaluated?",
        lastChanged: "2026-11-22",
      },
      {
        path: "docs/capstone/sdlc-record.md",
        answers: "Which loop did each merged pull request belong to, and was each loop's gate met?",
        lastChanged: "2026-11-22",
      },
      {
        path: "docs/product/RESEARCH_PROTOCOL.md",
        answers: "What is the research protocol, and what is its current status?",
        lastChanged: "2026-11-22",
      },
      {
        path: "docs/product/PHASE_05_RESULTS.md",
        answers: "What did the Phase 0.5 gate find, for the Spiral loop table?",
        lastChanged: "2026-11-21",
      },
      {
        path: "docs/capstone/ethics_and_safety.md",
        answers: "Which ethics basis does the study rest on, and which safety features does the system have?",
        lastChanged: "2026-11-25",
      },
      {
        path: "docs/capstone/story_donation_consent_and_assent_draft.md",
        answers: "What do the story-donation consent and assent forms say? A draft, not yet administered.",
        lastChanged: "2026-08-24",
      },
      {
        path: "docs/capstone/design_decisions_and_risks.md",
        answers: "Which methodological weaknesses were found, and what is each one's decision status?",
        lastChanged: "2026-11-22",
      },
    ],
  },
  {
    id: "instruments",
    title: "Chapter 2: Methodology, evaluation instruments",
    blurb: "The expert questionnaire, the ISO/IEC 25010 questionnaire and the work behind them.",
    entries: [
      {
        path: "docs/capstone/research_instruments.md",
        answers: "How are the instruments written up for the manuscript?",
        lastChanged: "2026-11-21",
      },
      {
        path: "docs/capstone/expert-evaluation-questionnaire.md",
        answers: "Who are the expert evaluators, and what are the seven open-ended questions?",
        lastChanged: "2026-11-21",
      },
      {
        path: "docs/capstone/iso-25010-questionnaire.md",
        answers: "What are the 23 ISO/IEC 25010 items, and how are they scored?",
        lastChanged: "2026-11-21",
      },
      {
        path: "docs/capstone/evaluation_instruments_brief.md",
        answers: "What was decided about how StoryBuddy is evaluated, and why is it defensible?",
        lastChanged: "2026-11-21",
      },
      {
        path: "docs/specs/iso-25010-scope-freeze.md",
        answers: "Which ISO/IEC 25010 scope was frozen, and how was the work split?",
        lastChanged: "2026-11-21",
      },
      {
        path: "docs/capstone/iso_iec_25010_readiness_audit.md",
        answers: "How ready was the system for an ISO/IEC 25010 evaluation in August 2026?",
        lastChanged: "2026-11-21",
      },
      {
        path: "docs/specs/functional-verification-matrix.md",
        answers: "What did the per-stage functional check plan to cover? Dropped on 2026-11-21, kept as history.",
        lastChanged: "2026-11-21",
      },
    ],
  },
  {
    id: "dataset",
    title: "Chapter 2: Methodology, dataset, labelling and judge training",
    blurb: "What was fixed in advance, how pairs were labelled, and how the judge was trained.",
    entries: [
      {
        path: "docs/product/PREREGISTRATION_OBJ4.md",
        answers: "What was fixed before any result was seen: hypotheses, splits, metrics, and every dated amendment since.",
        lastChanged: "2026-10-02",
      },
      {
        path: "docs/specs/labelling-rulebook.md",
        answers: "How does a rater decide Same or Different for a pair of images?",
        lastChanged: "2026-09-14",
      },
      {
        path: "docs/capstone/adjudication-notes-2026-09.md",
        answers: "How were rater disagreements adjudicated, and what patterns did the owner note?",
        lastChanged: "2026-10-09",
      },
      {
        path: "docs/capstone/research_runbook.md",
        answers: "How were the judge's dataset, training and held-out evaluation run, and what were the numbers?",
        lastChanged: "2026-11-27",
      },
      {
        path: "docs/specs/judge-finetune.md",
        answers: "How is the judge's dataset made, how is a training run started, and how is it evaluated?",
        lastChanged: "2026-10-08",
      },
      {
        path: "docs/capstone/model_finetuning.md",
        answers: "Which models were considered for the judge, and how was the fine-tune planned?",
        lastChanged: "2026-10-11",
      },
      {
        path: "backend/finetune/train_qlora.yaml",
        answers: "Which settings was the judge trained with: epochs, learning rate, adapter size, checkpoints?",
        lastChanged: "2026-10-02",
      },
    ],
  },
  {
    id: "architecture",
    title: "Chapter 2: Methodology, system architecture, hardware and hosting",
    blurb: "How the system is built and where it runs.",
    entries: [
      {
        path: "docs/capstone/system_architecture.md",
        answers: "What are the system's components and pipeline stages, in both graph modes?",
        lastChanged: "2026-11-22",
      },
      {
        path: "docs/MASTER_SPEC.md",
        answers: "What is the master spec for the pipeline? Section 2 is the architecture.",
        lastChanged: "2026-11-22",
      },
      {
        path: "docs/TECH_STACK.md",
        answers: "Which tools, versions and hosting region does the system use?",
        lastChanged: "2026-11-22",
      },
      {
        path: "docs/capstone/hardware_and_hosting.md",
        answers: "Which hardware did development and training use, and where is the system hosted?",
        lastChanged: "2026-11-22",
      },
      {
        path: "docs/product/ADRs.md",
        answers: "Which architecture decisions were made, and which are still in force?",
        lastChanged: "2026-11-27",
      },
      {
        path: "docs/product/adr/ADR-083-research-pages-hub-chapter-routes-and-png-diagram-export.md",
        answers: "Why does the research site have a hub, chapter pages and PNG diagram export?",
        lastChanged: "2026-11-22",
      },
      {
        path: "docs/product/adr/ADR-084-the-study-corpus-is-english-only.md",
        answers: "Why is the study corpus English-only, and which stories were translated?",
        lastChanged: "2026-11-22",
      },
    ],
  },
  {
    id: "results",
    title: "Chapter 3: Results and discussion",
    blurb: "What was measured about the books and the model screens.",
    entries: [
      {
        path: "docs/capstone/pipeline-stage-audit-2026-10.md",
        answers: "For each defect in a finished book, which pipeline stage caused it?",
        lastChanged: "2026-10-12",
      },
      {
        path: "docs/capstone/model-probes-2026-10.md",
        answers:
          "What did the small October model screens find, did anything change, and which pipeline limits must the write-up state?",
        lastChanged: "2026-11-01",
      },
    ],
  },
  {
    id: "diagrams",
    title: "Appendices and figures: diagrams",
    blurb: "Drawn figures for the paper. The system diagrams are as built on 2026-11-21.",
    entries: [
      {
        path: `${D}langgraph_pipeline_after_2026-10.drawio.svg`,
        answers: "What does the pipeline look like as built on 2026-11-21, in both baseline and teacher-review modes?",
        lastChanged: "2026-11-21",
      },
      {
        path: `${D}langgraph_pipeline_before_2026-07.drawio.svg`,
        answers: "What did the pipeline look like in July 2026? Marked as the planned design, for comparison.",
        lastChanged: "2026-11-21",
      },
      {
        path: `${D}system_architecture.drawio.svg`,
        answers: "Which services and models make up the system, as built on 2026-11-21?",
        lastChanged: "2026-11-22",
      },
      {
        path: `${D}ipo_model.drawio.svg`,
        answers: "What goes in, what happens, and what comes out? The input-process-output figure.",
        lastChanged: "2026-11-21",
      },
      {
        path: `${D}dataset_build_and_annotation_flow.drawio.svg`,
        answers: "How was the image-pair dataset built and annotated?",
        lastChanged: "2026-11-21",
      },
      {
        path: `${D}student_journey.drawio.svg`,
        answers: "What does a student do, from signing in to reading the finished book?",
        lastChanged: "2026-11-21",
      },
      {
        path: `${D}teacher_journey.drawio.svg`,
        answers: "What does a teacher do, from setting up a classroom to approving a book?",
        lastChanged: "2026-11-21",
      },
    ],
  },
];
