// SH-02: every sentence below is copied from one of these tracked files, with the source's bold marks
// dropped. data.test.ts checks each one.
export const SOURCES = {
  methodology: "docs/capstone/methodology.md",
  groupGuide: "docs/capstone/group-guide.md",
  ethics: "docs/capstone/ethics_and_safety.md",
  expert: "docs/capstone/expert-evaluation-questionnaire.md",
  iso: "docs/capstone/iso-25010-questionnaire.md",
} as const;

export const DESIGN = {
  parts: [
    "a developmental component that builds and iteratively refines the ten-module pipeline",
    "an evaluation component that measures the system and its outputs through three procedures",
  ],
  procedures: [
    "expert validation of the generated picture books (Objective 3)",
    "the Consistency Judge's classification performance against human labels (Objective 4)",
    "ISO/IEC 25010 software quality (Objective 5)",
  ],
} as const;

export const SPIRAL = {
  definition: "Boehm's Spiral Model — a risk-driven, iterative SDLC with stage-gated phases.",
} as const;

export const SETTING = {
  school: "Stories are collected at Vicente Hizon, Sr. Elementary School",
  development: "system development is at Holy Cross of Davao College (HCDC), Davao City",
  agreement: "The stories were used under a hard-copy agreement from the teacher, which is a consent form",
} as const;

// D-16, O-07: both options stay until the owner chooses.
export const SITES = {
  a: "Option A: Vicente Hizon, Sr. Elementary School, if the school admits researchers despite its PAASCU accreditation.",
  b: "Option B: HCDC, with 40 School of Teacher Education (STE) students.",
} as const;

export const CORPUS = [
  { count: 15, label: "donated stories received", source: "methodology", sentence: "fifteen (15) original stories collected" },
  { count: 12, label: "generated into books", source: "methodology", sentence: "twelve (12) were generated into books" },
  {
    count: 30,
    label: "synthetic stories",
    source: "groupGuide",
    sentence: "The research corpus holds 42 generated books: 30 from synthetic stories and 12 from donated stories.",
  },
  {
    count: 42,
    label: "books",
    source: "groupGuide",
    sentence: "The research corpus holds 42 generated books: 30 from synthetic stories and 12 from donated stories.",
  },
] as const;

export const RESPONDENTS = {
  expert: "Three evaluators: 2 Bachelor of Elementary Education (BEEd) professors and 1 Arts professor.",
  iso: "At least 30 respondents in total, from IT experts, IT students, teachers and education students, not split equally.",
} as const;
