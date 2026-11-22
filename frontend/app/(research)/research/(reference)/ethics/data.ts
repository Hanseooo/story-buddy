// SH-02: each fact is a page sentence plus a quote that its named source prints. data.test.ts fails when a
// quote is gone, so a changed source doc stops the page until the page is updated too.
export const SOURCES = {
  ethics: "docs/capstone/ethics_and_safety.md",
  spec: "docs/specs/research-page-refresh.md",
  chapterSpec: "docs/specs/research-page-refresh/04-chapter-pages.md",
  hardware: "docs/capstone/hardware_and_hosting.md",
  adr080: "docs/product/adr/ADR-080-teacher-held-moderation-and-exact-content-clearance.md",
  adr081: "docs/product/adr/ADR-081-teacher-notes-the-child-can-read.md",
  adr082: "docs/product/adr/ADR-082-magic-pencil-child-edits-and-other-versions.md",
  adr083: "docs/product/adr/ADR-083-research-pages-hub-chapter-routes-and-png-diagram-export.md",
  mainPy: "backend/app/main.py",
  config: "backend/app/config.py",
} as const;

export type Fact = { text: string; source: keyof typeof SOURCES; quote: string };

// D-08
export const BASIS: Fact[] = [
  {
    text: "No ethics committee review was sought.",
    source: "ethics",
    quote: "No ethics committee review was sought: the researchers did not interact with the children, and learners did not use the system during the study.",
  },
  {
    text: "The researchers did not interact with the children.",
    source: "ethics",
    quote: "the researchers did not interact with the children",
  },
  {
    text: "Learners did not use the system during the study.",
    source: "ethics",
    quote: "learners did not use the system during the study",
  },
  {
    text: "The system supports teacher-issued student accounts.",
    source: "ethics",
    quote: "The system supports teacher-issued student accounts.",
  },
];

// D-22: the teacher's agreement is a consent form, and the page claims nothing more about its scope.
export const CONSENT: Fact[] = [
  {
    text: "The stories were used with the teacher's signed hard-copy consent.",
    source: "chapterSpec",
    quote: "the stories were used with the teacher's signed hard-copy consent",
  },
  {
    text: "This page says nothing more about what that consent covers.",
    source: "ethics",
    quote: "nothing is claimed about its wider scope",
  },
  {
    text: "No separate parental consent was collected.",
    source: "ethics",
    quote: "no separate parental consent was collected",
  },
  {
    text: "Expert evaluators sign their own informed consent form.",
    source: "spec",
    quote: "Evaluators sign an informed consent form",
  },
];

// D-07, D-09
export const PRIVACY: Fact[] = [
  {
    text: "Donated story IDs, plot summaries and character names are kept in the public repository.",
    source: "ethics",
    quote: "Donated story IDs, plot summaries and character names stay in the public repository.",
  },
  {
    text: "The owner chose this over unlinking them from the public site. The teacher's agreement is the recorded basis.",
    source: "ethics",
    quote: "the teacher's agreement is the recorded basis",
  },
  {
    text: "The research pages show no donated images.",
    source: "adr083",
    quote: "no donated image and no held-out test image",
  },
  {
    text: "Presidio finds personal information in the story text and redacts it before the text is stored or captioned.",
    source: "ethics",
    quote: "to detect and redact PII from the input text before any storage or captioning occurs",
  },
  {
    text: "Phone numbers, addresses and ID numbers are always redacted. Person names are not replaced by default (ADR-045), so a first name a child writes can reach the model providers and the stored captions.",
    source: "ethics",
    quote: "A first name a child writes — including their own — now reaches the analyzer, the image providers, and the stored captions.",
  },
  {
    text: "Donated stories were redacted by hand when they arrived. Presidio did not run on them.",
    source: "ethics",
    quote: "Donated stories collected for the study are **redacted manually on receipt**",
  },
  {
    text: "The backend is hosted on Northflank in the North America region, on the free tier.",
    source: "hardware",
    quote: "Northflank, North America region, free tier",
  },
  {
    text: "The database region is not recorded in any tracked doc.",
    source: "hardware",
    quote: "The Supabase project region is not recorded in any tracked doc.",
  },
  {
    text: "The project does not claim a privacy guarantee. A child's text passes through the model hosts OpenRouter and fal.ai.",
    source: "hardware",
    quote: "StoryBuddy does not claim a privacy guarantee",
  },
];

export const PENCIL = { chars: 200, pagePencils: 5 } as const;

// Where each moderation layer runs. `modelSettings` are keys of MODELS in ../architecture/data, which reads config.py.
export const MODERATION_LAYERS = [
  {
    layer: "Title",
    runsIn: "Web service, before the job row is written",
    file: "backend/app/main.py",
    mentions: "check_text",
    modelSettings: ["moderation_primary_model", "moderation_backstop_model"],
    text: "Checked by the two text classifiers. In teacher review mode it is redacted with Presidio first.",
    source: "mainPy",
    quote: "title_safe, title_categories, checked_title = check_text(title, evidence=title_evidence)",
  },
  {
    layer: "Story text",
    runsIn: "Worker, first step of the pipeline",
    file: "backend/pipeline/input_gate.py",
    mentions: "classify_text_primary",
    modelSettings: ["moderation_primary_model", "moderation_backstop_model"],
    text: "Two classifiers from different vendors. A flag from either one stops the text. In teacher review mode it holds the job for the teacher instead.",
    source: "ethics",
    quote: "If either signal flags the content, it fails.",
  },
  {
    layer: "Pictures",
    runsIn: "Worker, for every reference and page picture",
    file: "backend/pipeline/output_mod.py",
    mentions: "_check_image",
    modelSettings: ["moderation_primary_image_model", "moderation_backstop_image_model"],
    text: "Each picture is checked before the child sees it. The character references are checked too.",
    source: "ethics",
    quote: "Generated images are moderated **before** the child ever sees them.",
  },
  {
    layer: "Magic pencil text",
    runsIn: "Web service, when the child sends the change",
    file: "backend/app/moderation_hold.py",
    mentions: "def checked_pencil_text",
    modelSettings: ["moderation_primary_model", "moderation_backstop_model"],
    text: "Redacted with Presidio first, then checked by the two text classifiers.",
    source: "ethics",
    quote: "Pencil text is moderated after PII redaction.",
  },
] as const satisfies readonly (Fact & { layer: string; runsIn: string; file: string; mentions: string; modelSettings: readonly string[] })[];

export const SAFETY_FEATURES: (Fact & { name: string })[] = [
  {
    name: "Teacher approval",
    text: "Every generated book passes teacher review before it enters the classroom gallery.",
    source: "ethics",
    quote: "every generated book passes teacher review before it enters the classroom gallery (ADR-017)",
  },
  {
    name: "Teacher hold (ADR-080)",
    text: "In teacher review mode, a first moderation flag holds the job for the teacher. The teacher can allow exact content under a written policy, ask for one picture replacement, or stop the job.",
    source: "ethics",
    quote: "a first moderation flag holds the job for the teacher, who can allow exact content under a written policy, request one picture replacement, or stop",
  },
  {
    name: "Teacher hold default",
    text: "Teacher review mode has been on by default since 2026-11-21.",
    source: "ethics",
    quote: "On by default since 2026-11-21 (`backend/app/config.py:90`)",
  },
  {
    name: "Teacher notes (ADR-081)",
    text: "The child can read their own teacher note.",
    source: "ethics",
    quote: "The child can read their own teacher note.",
  },
  {
    name: "Teacher notes, who else",
    text: "No classmate, researcher or export can reach a note.",
    source: "adr081",
    quote: "No classmate, gallery, researcher or export read path exists.",
  },
  {
    name: "Magic pencil length (ADR-082)",
    text: `The child writes a short change of about ${PENCIL.chars} characters.`,
    source: "ethics",
    quote: "write a short change (about 200 characters)",
  },
  {
    name: "Magic pencil allowance",
    text: `A book gets at most ${PENCIL.pagePencils} page pencils.`,
    source: "adr082",
    quote: "5 page pencils per book inside `IMAGE_BUDGET`",
  },
  {
    name: "Magic pencil scope",
    text: "The pencil works only on jobs submitted in teacher review mode.",
    source: "adr082",
    quote: "Only on jobs submitted in `teacher_review_v1` with the new setting on",
  },
  {
    name: "Accounts",
    text: "A teacher issues each student a nickname account. There is no email and no self-sign-up.",
    source: "ethics",
    quote: "no email on the account and no self-serve signup",
  },
  {
    name: "Gallery",
    text: "The classroom gallery shows approved books only. It has no comments or scores.",
    source: "ethics",
    quote: "There is no reflection, comment, or scoring surface of any kind (ADR-021)",
  },
  {
    name: "Pictures stored privately",
    text: "Pictures sit in a private bucket and are reached through short-lived signed links.",
    source: "ethics",
    quote: "There are no public buckets",
  },
];

export const LIMITS: Fact[] = [
  {
    text: "None of the later features above is cleared for real children yet.",
    source: "ethics",
    quote: "none is cleared for real children yet",
  },
  {
    text: "The ethics re-review and the moderation audit still apply before any real-child use.",
    source: "ethics",
    quote: "the ethics re-review and the moderation-audit gate before real-child use still apply",
  },
  {
    text: "Open image models such as Qwen-Image-Edit ship without safety filters, so the picture check is not optional.",
    source: "ethics",
    quote: "open image models (like Qwen-Image-Edit) do not ship with built-in safety filters",
  },
  {
    text: "Taglish and Filipino text is a known risk for the text checks.",
    source: "ethics",
    quote: "The Taglish and Filipino performance of open text gates is treated as a critical child-safety vulnerability.",
  },
];
