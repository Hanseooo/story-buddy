// "What the paper must say" (US-25 AC-05, AC-06). One row per audit-3 row P1-P24, plus C1.
// paper.test.ts pins every row to its source doc (SH-02): a `has` phrase must appear there, a
// `lacks` phrase must not. Where a repo doc was corrected, the row cites the decision (D-nn).

const CAPSTONE = "docs/capstone/";
const SPEC = "docs/specs/research-page-refresh.md";
const issue = (n: number) => `https://github.com/Hanseooo/story-buddy/issues/${n}`;

export type Pin = { file: string } & ({ has: string; lacks?: undefined } | { lacks: string; has?: undefined });
export type CorrectionStatus = "settled" | "repo-right" | "open";
export type Correction = {
  id: string;
  topic: string;
  /** What the paper says now, short. */
  paper: string;
  /** The settled value, the reason the repo is right, or what is still open. */
  value: string;
  status: CorrectionStatus;
  decision?: string;
  open?: { id: string; url: string };
  pins: Pin[];
};

export const PAPER_CORRECTIONS: Correction[] = [
  {
    id: "P1",
    topic: "Source school",
    paper: "Vicente Hizon, Sr. Elementary School",
    value:
      "Vicente Hizon, Sr. Elementary School is the source of the stories. The repo docs said Matina Aplaya and now agree. Which school hosts the implementation is open.",
    status: "open",
    decision: "D-04",
    open: { id: "O-07", url: issue(136) },
    pins: [
      { file: `${CAPSTONE}methodology.md`, has: "Vicente Hizon, Sr. Elementary School" },
      { file: SPEC, has: "Which implementation site is used." },
    ],
  },
  {
    id: "P2",
    topic: "Expert validators",
    paper: "2 BEEd teachers and 1 Arts expert, seven open-ended questions",
    value:
      "2 BEEd professors and 1 Arts professor, seven open-ended questions, no rating scale. How the seven answers are analysed is open.",
    status: "open",
    decision: "D-05",
    open: { id: "O-04", url: issue(135) },
    pins: [
      { file: `${CAPSTONE}expert-evaluation-questionnaire.md`, has: "2 Bachelor of Elementary Education (BEEd) professors and 1 Arts professor" },
      { file: `${CAPSTONE}expert-evaluation-questionnaire.md`, has: "seven open-ended questions and no rating scale" },
      { file: SPEC, has: "Content analysis or thematic analysis (to be decided)" },
    ],
  },
  {
    id: "P3",
    topic: "Likert scale",
    paper: "1 Strongly Disagree to 5 Strongly Agree",
    value:
      "5 = Strongly Agree, 1 = Strongly Disagree, so a higher mean is better. The paper is right and the repo docs now agree. The consent form's wording is open.",
    status: "open",
    decision: "D-06",
    open: { id: "O-12", url: issue(137) },
    pins: [
      { file: `${CAPSTONE}iso-25010-questionnaire.md`, has: "5 = Strongly Agree and 1 = Strongly Disagree" },
      { file: SPEC, has: "says \"25-item\" (the form has 23)" },
    ],
  },
  {
    id: "P4",
    topic: "ISO/IEC 25010 characteristics",
    paper: "6 characteristics",
    value:
      "23 items on 6 characteristics: Functional Suitability, Interaction Capability, Reliability, Performance Efficiency, Security, Compatibility. The paper is right.",
    status: "settled",
    decision: "D-06",
    pins: [{ file: `${CAPSTONE}iso-25010-questionnaire.md`, has: "23 Likert items on 6 characteristics" }],
  },
  {
    id: "P5",
    topic: "Respondents and statistics",
    paper: "At least 30 respondents, no CVI or reliability pilot",
    value:
      "At least 30 respondents in total from IT experts, IT students, teachers and education students. Descriptive statistics only, no CVI and no Cronbach's α pilot.",
    status: "settled",
    decision: "D-06",
    pins: [
      { file: `${CAPSTONE}iso-25010-questionnaire.md`, has: "At least 30 respondents in total" },
      { file: `${CAPSTONE}iso-25010-questionnaire.md`, has: "no Cronbach's α pilot" },
    ],
  },
  {
    id: "P6",
    topic: "Donated stories",
    paper: "15 collected, 13 met the requirements",
    value:
      "15 arrived and 12 were generated into books (the corpus is 30 synthetic plus 12 donated). Replace 13 with 12. The paper itself says 12 later. The repo is right.",
    status: "repo-right",
    pins: [
      { file: `${CAPSTONE}research-changelog.md`, has: "30 from synthetic stories and 12 from donated stories" },
      { file: `${CAPSTONE}methodology.md`, has: "twelve (12) were generated into books" },
    ],
  },
  {
    id: "C1",
    topic: "Why three donated stories are missing",
    paper: "Not stated",
    value:
      "Two stories ended invalid_terminal and one budget_stopped, so they did not finish. They were then left out on purpose, because 12 bundles already clear the held-out floor. Say both. The repo is right.",
    status: "repo-right",
    pins: [
      { file: "docs/specs/obj4-readiness-audit.md", has: "don-006 and don-015 (`invalid_terminal`), don-013 (`budget_stopped`)" },
      { file: "docs/specs/obj4-readiness-audit.md", has: "12 bundles clear it" },
      { file: `${CAPSTONE}research-changelog.md`, has: "three donated stories left out on purpose" },
    ],
  },
  {
    id: "P7",
    topic: "Who removed the names",
    paper: "Teachers removed the learners' names",
    value:
      "The repo plan has the researchers hand-redact the 15 stories, substituting identifiers. If teachers also removed names, say both.",
    status: "repo-right",
    pins: [{ file: "docs/specs/obj4-readiness-audit.md", has: "Hand-redact the 15 stories" }],
  },
  {
    id: "P8",
    topic: "Scenes per book",
    paper: "10 to 15 scenes",
    value: "3 to 10 scenes since ADR-037. The repo is right.",
    status: "repo-right",
    pins: [{ file: `${CAPSTONE}methodology.md`, has: "`MAX_SCENES = 10`" }],
  },
  {
    id: "P9",
    topic: "Module count",
    paper: "11-module pipeline",
    value:
      "Write \"ten logical modules\". The graph has 11 nodes in baseline mode and 14 in teacher-review mode. The repo is right.",
    status: "repo-right",
    pins: [
      { file: `${CAPSTONE}system_architecture.md`, has: "14 nodes instead of the baseline 11" },
      { file: `${CAPSTONE}methodology.md`, has: "ten logical modules" },
    ],
  },
  {
    id: "P10",
    topic: "Flagged content stops the book",
    paper: "Validation fails, so no partial book",
    value:
      "True for the study's 42 books (baseline mode). In teacher-review mode, on by default since 2026-11-21, a flag goes to a teacher hold instead.",
    status: "repo-right",
    pins: [{ file: `${CAPSTONE}system_architecture.md`, has: "Teacher-review mode (ADR-080, on by default since 2026-11-21" }],
  },
  {
    id: "P11",
    topic: "Learners as users",
    paper: "Learners are not the direct users",
    value:
      "Learners did not use the system during the study. The system supports teacher-issued student accounts.",
    status: "settled",
    decision: "D-08",
    pins: [
      {
        file: `${CAPSTONE}ethics_and_safety.md`,
        has: "learners did not use the system during the study. The system supports teacher-issued student accounts",
      },
    ],
  },
  {
    id: "P12",
    topic: "Hosting region",
    paper: "Northflank (North America)",
    value: "Northflank, North America region, free tier. The paper is right and TECH_STACK.md now agrees.",
    status: "settled",
    decision: "D-07",
    pins: [{ file: "docs/TECH_STACK.md", has: "North America region, free tier" }],
  },
  {
    id: "P13",
    topic: "Judge deployment",
    paper: "Fine-tuned judge under evaluation; serving GPU on Modal or RunPod",
    value:
      "The evaluation is finished and the fine-tuned judge is not deployed. The product judge stays prompted Gemma. The repo is right.",
    status: "repo-right",
    pins: [{ file: `${CAPSTONE}research-changelog.md`, has: "The product judge stays prompted Gemma" }],
  },
  {
    id: "P14",
    topic: "Objective 4 is partial",
    paper: "Results do not say the comparison is partial",
    value: "Say the Objective 4 result is partial: the prompted Gemma baseline failed and paid evaluation stopped for budget.",
    status: "repo-right",
    pins: [{ file: `${CAPSTONE}research-changelog.md`, has: "The Objective 4 result is partial." }],
  },
  {
    id: "P15",
    topic: "Annotation limits",
    paper: "Annotation procedure reads as clean",
    value: "State the label limitations listed in the changelog. The repo is right.",
    status: "repo-right",
    pins: [{ file: `${CAPSTONE}research-changelog.md`, has: "The labels have limitations of their own." }],
  },
  {
    id: "P16",
    topic: "Clothing and style criteria",
    paper: "Table lists clothing and style as identity checks",
    value: "A clothing or style change alone is Same. Say so beside the table. The repo is right.",
    status: "repo-right",
    pins: [{ file: "docs/specs/labelling-rulebook.md", has: "Clothing alone is Same" }],
  },
  {
    id: "P17",
    topic: "Inter-rater agreement",
    paper: "κ 0.634 and 89.7% only",
    value:
      "Also report κ 0.659 over all 795 pairs, and that the non-human slice (κ 0 at 96% agreement) is a prevalence artifact. The repo is right.",
    status: "repo-right",
    pins: [
      { file: `${CAPSTONE}research-changelog.md`, has: "all pairs 0.659" },
      { file: `${CAPSTONE}research-changelog.md`, has: "prevalence artifact" },
    ],
  },
  {
    id: "P18",
    topic: "McNemar test",
    paper: "p 0.0035 read as a significant difference in correctness",
    value:
      "Report p 0.0035 beside the counts: seed 1 was wrong on 40 pairs, the untuned model on 65. Do not cite it as evidence the fine-tuned judge is worse.",
    status: "repo-right",
    pins: [{ file: `${CAPSTONE}research-changelog.md`, has: "seed 1 was wrong on fewer pairs (40 against 65)" }],
  },
  {
    id: "P19",
    topic: "Story reconstruction tasks",
    paper: "Image-based story reconstruction tasks check understanding",
    value: "No such task or instrument exists. Remove the claim. The repo is right.",
    status: "repo-right",
    pins: [{ file: `${CAPSTONE}research_instruments.md`, lacks: "reconstruction" }],
  },
  {
    id: "P20",
    topic: "Word limit",
    paper: "500-word input limit",
    value:
      "True today (ADR-068). The frozen corpus was generated under the older 300-word ceiling and was not regenerated. Say both.",
    status: "repo-right",
    pins: [
      { file: "docs/product/ADRs.md", has: "Story input expands to 500 words" },
      { file: "docs/product/adr/ADR-068-story-input-expands-to-500-words-with-the-existing-page-and-image-ceilings.md", has: "300 words" },
    ],
  },
  {
    id: "P21",
    topic: "Ethics approval",
    paper: "Ethics subsections empty; institutional approval implied",
    value:
      "No ethics committee review was sought: the researchers did not interact with the children, and learners did not use the system during the study.",
    status: "settled",
    decision: "D-08",
    pins: [{ file: `${CAPSTONE}ethics_and_safety.md`, has: "No ethics committee review was sought" }],
  },
  {
    id: "P22",
    topic: "Privacy of donated stories",
    paper: "Privacy section empty",
    value:
      "Disclose that donated story IDs, plot summaries and character names stay in the public repository, on the teacher's agreement.",
    status: "settled",
    decision: "D-09",
    pins: [
      {
        file: `${CAPSTONE}ethics_and_safety.md`,
        has: "Donated story IDs, plot summaries and character names stay in the public repository",
      },
    ],
  },
  {
    id: "P23",
    topic: "Training GPU",
    paper: "NVIDIA RTX A6000, 48 GB VRAM",
    value: "Correct. The run record is git-ignored, so the figure now sits in hardware_and_hosting.md for citing.",
    status: "repo-right",
    pins: [{ file: `${CAPSTONE}hardware_and_hosting.md`, has: "NVIDIA RTX A6000, 49140 MiB (48 GB class)" }],
  },
  {
    id: "P24",
    topic: "Development hardware",
    paper: "i5 12th gen, 16 GB, RTX 3050 Ti 4 GB",
    value:
      "Print the RTX 3050 Ti with 4 GB VRAM, the only confirmed development hardware. The processor, memory and storage rows are July recommendations the owner has not confirmed.",
    status: "repo-right",
    pins: [
      {
        file: `${CAPSTONE}hardware_and_hosting.md`,
        has: "the only confirmed development hardware is the RTX 3050 Ti with 4 GB VRAM",
      },
    ],
  },
];

// research-changelog.md section 1, each point worded as in the changelog (the test checks).
export const CHANGELOG_POINTS = [
  "The fine-tuned judge is Qwen3.5-9B, not Qwen2.5-VL-7B.",
  "Labels came from two raters with owner adjudication.",
  "The Objective 4 result is partial.",
  "Fine-tuning ran; it did not improve the judge.",
  "Narration remains out of scope",
  "The corpus is 42 generated books:",
  "The page defects are limitations",
  "The labels have limitations of their own.",
  "The product did not change its models.",
];

export const PAPER_TYPOS = [
  { wrong: "Visibile", right: "Visible", where: "Annotation criteria, \"Text Visible\"" },
  { wrong: "Cohen's Cappa", right: "Cohen's Kappa", where: "Results tab" },
  {
    wrong: "considerable",
    right: "substantial",
    where: "Inter-annotator agreement: κ 0.634 is \"substantial\" (Landis and Koch)",
  },
  { wrong: "31%", right: "0.310", where: "Seed 1's F1 is 0.310, a score, not a percentage" },
];
