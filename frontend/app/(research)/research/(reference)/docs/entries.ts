// The docs hub links here instead of rendering markdown (ADR-065 decision 2).
export const githubUrl = (repoPath: string) => `https://github.com/Hanseooo/story-buddy/blob/main/${repoPath}`;

export type DocEntry = { file: string; answers: string; startHere?: true };
export type DocFolder = { path: string; holds: string; entries: DocEntry[] };

// entries.test.ts fails when a file listed here is renamed or deleted.
export const DOC_FOLDERS: DocFolder[] = [
  {
    path: "docs/capstone",
    holds: "The study in plain words, and its running record.",
    entries: [
      {
        file: "group-guide.md",
        answers: "What is StoryBuddy, what did the study find, and what are its limits? Plain words, no code.",
        startHere: true,
      },
      {
        file: "research-changelog.md",
        answers: "What changed since the plan was registered, and what must the paper say about it?",
      },
      {
        file: "research_direction_and_goals.md",
        answers: "What are the objectives, and what does the study not claim?",
      },
      {
        file: "methodology.md",
        answers: "How was the system built, and how is each objective evaluated?",
      },
      {
        file: "research_runbook.md",
        answers: "How were the judge's dataset, training and held-out evaluation run, and what were the numbers?",
      },
      {
        file: "pipeline-stage-audit-2026-10.md",
        answers: "For each defect in a finished book, which pipeline stage caused it?",
      },
      {
        file: "model-probes-2026-10.md",
        answers: "What did the small October model screens find, and did anything change?",
      },
    ],
  },
  {
    path: "docs/product",
    holds: "What was committed to in advance.",
    entries: [
      {
        file: "PREREGISTRATION_OBJ4.md",
        answers: "What was fixed before any result was seen: hypotheses, splits, metrics, and every dated amendment since.",
      },
      {
        file: "ADRs.md",
        answers: "Which architecture decisions were made, and which are still in force?",
      },
    ],
  },
  {
    path: "docs/specs",
    holds: "Rules the work follows.",
    entries: [
      {
        file: "labelling-rulebook.md",
        answers: "How does a rater decide Same or Different for a pair of images?",
      },
      {
        file: "judge-finetune.md",
        answers: "How is the judge's dataset made, how is a training run started, and how is it evaluated?",
      },
    ],
  },
  {
    path: "backend/finetune",
    holds: "The training code and its settings.",
    entries: [
      {
        file: "train_qlora.yaml",
        answers: "Which settings was the judge trained with: epochs, learning rate, adapter size, checkpoints?",
      },
    ],
  },
  {
    path: "docs/diagrams/drawio",
    holds: "The pipeline, drawn.",
    entries: [
      {
        file: "langgraph_pipeline_after_2026-10.drawio.svg",
        answers: "What does the pipeline look like as it runs today?",
      },
      {
        file: "langgraph_pipeline_before_2026-07.drawio.svg",
        answers: "What did the pipeline look like in July 2026, for comparison?",
      },
    ],
  },
];
