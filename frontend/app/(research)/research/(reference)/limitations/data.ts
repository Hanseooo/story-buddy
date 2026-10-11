// ADR-067: every number below is copied from one of these tracked files, and TRIED and LIMITATIONS
// are the group guide's own rows and items, word for word. data.test.ts checks both.
export const SOURCES = {
  groupGuide: "docs/capstone/group-guide.md",
  stageAudit: "docs/capstone/pipeline-stage-audit-2026-10.md",
  probes: "docs/capstone/model-probes-2026-10.md",
  phase05: "docs/product/PHASE_05_RESULTS.md",
} as const;

// Group guide §5.3. The date is the stage audit's "Provisional results" heading.
export const AUDIT = {
  date: "2026-10-08",
  books: 30,
  pages: 150,
  references: 55,
  defective: 77,
} as const;

export type Share = { part: number; whole: number };

// Group guide §5.3: the same count, for human characters and for non-human ones.
export const BY_KIND: { title: string; human: Share; nonHuman: Share }[] = [
  { title: "Pages with a major defect", human: { part: 11, whole: 33 }, nonHuman: { part: 66, whole: 117 } },
  { title: "Reference pictures with a major defect", human: { part: 2, whole: 21 }, nonHuman: { part: 15, whole: 34 } },
  { title: "Pages with a duplicate or extra character", human: { part: 1, whole: 33 }, nonHuman: { part: 16, whole: 117 } },
];

// Counts: stage audit, "Where the 77 come from". Names and descriptions: group guide §5.3.
export const DEFECTS = [
  {
    code: "reference_inherited",
    name: "Reference inherited",
    pages: 34,
    looksLike: "A mistake in the reference picture (for example six legs drawn as four) repeats on every page",
  },
  { code: "duplicate_character", name: "Duplicate character", pages: 15, looksLike: "The same character appears twice on one page" },
  {
    code: "action_mismatch",
    name: "Missing or wrong action",
    pages: 9,
    looksLike: "The character stands there instead of doing what the text says",
  },
  {
    code: "identity_drift",
    name: "Identity drift",
    pages: 8,
    looksLike: "The character's colours, hair or shape change between pages",
  },
  { code: "extra_character", name: "Extra character", pages: 5, looksLike: "Someone who is not in the story appears" },
] as const;

// Stage audit, "References" and "Page gate": what the pipeline's own two checks said about the reviewed images.
export const CHECKS = {
  reference: { defective: 17, defectiveFailed: 15, acceptable: 38, acceptableFailed: 15 },
  page: { defective: 77, defectivePassed: 29, acceptable: 71, acceptableFailed: 28 },
} as const;

// Group guide §5.4, first row: the blinded screen of 2026-10-08.
export const KLEIN = {
  pages: 30,
  duplicates: { qwen: 4, klein: 4 },
  identityLost: { qwen: 3, klein: 10 },
} as const;

// Group guide §5.1: one invented character, with its reference picture and without it.
export const PHASE_05 = {
  qwen: { withReference: "70%", without: "40%" },
  omnigen: { withReference: "80%", without: "30%" },
} as const;

export type Outcome = "Rejected" | "Not adopted" | "No change" | "Merged" | "Stated limitation" | "A lead, not adopted";

// Group guide §5.4, every row. `outcome` is this page's one-word reading of `result`.
export const TRIED: { tried: string; result: string; outcome: Outcome }[] = [
  {
    tried: "A different scene editor (FLUX.2 klein)",
    result:
      "On 30 random pages it drew as many duplicates as Qwen (4 each) and lost character identity more often (10 against 3). Rejected (ADR-063).",
    outcome: "Rejected",
  },
  {
    tried: 'A prompt line asking for "one moment"',
    result: "1 of 10 draws free of duplicates. Not adopted.",
    outcome: "Not adopted",
  },
  {
    tried: "Rewriting the direction as one frozen instant",
    result:
      "3 of 10 free of duplicates. Not adopted. It did fix both pages where the text described something absent or pretend.",
    outcome: "Not adopted",
  },
  {
    tried: "Shipping whichever attempt the judge did not flag for duplicates",
    result: "Helped one scene and hurt another. Not adopted.",
    outcome: "Not adopted",
  },
  { tried: "A different text model", result: "No open-weight model beat Mistral.", outcome: "No change" },
  {
    tried: 'Adding a character the direction names by species ("the moth")',
    result: "Fixed the one story it targets. Merged on 2026-10-09 (PR #101).",
    outcome: "Merged",
  },
  {
    tried: "Other reference-picture models for stated body counts",
    result: 'None drew counts like "six legs" correctly. Already a stated limitation (ADR-056).',
    outcome: "Stated limitation",
  },
  {
    tried: "Editing the finished reference to fix the count (October 11)",
    result:
      "5 of 9 fixed with the character unchanged, 1 borderline, 3 missed. Pages redrawn from the fixed references then showed the right count on 5 of 6 (1 borderline). One try each, with instructions written by hand. Not adopted yet: it needs a test with automatic instructions and an ADR.",
    outcome: "A lead, not adopted",
  },
];

export type Area = "The pictures" | "How it was scored" | "The judge" | "Scope";

// Group guide §6, every item in its order. `area` is this page's grouping.
export const LIMITATIONS: { title: string; body: string; area: Area }[] = [
  {
    title: "Duplicate characters",
    body: "About 13% of page images show a character twice. Two different scene editors do this at the same rate, and four fixes failed. It is a limitation of this kind of edit model, measured on two of them, and it remains open.",
    area: "The pictures",
  },
  {
    title: "Stated body counts",
    body: '"Six legs" or "seven stripes" usually come out wrong. No tested model draws them from text (ADR-056). Editing the finished reference fixed 5 of 9 in one small test, and pages redrawn from those references kept the fix. It is a lead and not yet a fix: one try each, with instructions written by hand.',
    area: "The pictures",
  },
  {
    title: "Characters with no reference",
    body: 'Background groups like "his six dust-bunny soldiers" have no reference picture. The model guesses what they look like, and once drew them as human boys.',
    area: "The pictures",
  },
  {
    title: "Actions",
    body: "Some pages miss the action, or give it to the wrong character. Describing only what is visible helped where the text mentioned something absent or pretend. That kind is about 3 pages in 150, too few to measure a fix before the defense.",
    area: "The pictures",
  },
  {
    title: "How the image findings were sampled",
    body: "Most October probes used pages chosen because they had failed, with one or two draws each. Only the klein screen was blinded and used random pages.",
    area: "How it was scored",
  },
  {
    title: "The judge result",
    body: "Objective 4's result is partial, and the trained judge scored lower F1 than the untrained one.",
    area: "The judge",
  },
  {
    title: "The labels",
    body: 'Two groupmates labelled every pair and the owner settled disagreements. Pairs both raters got wrong were never re-checked, apart from ten audited ones. Hair length is not a rule, so raters could split on it. Object characters (such as a tin can) lean toward "different" because their pages add arms and legs their references never had.',
    area: "The judge",
  },
  {
    title: "Scope",
    body: "One grade band, one school, one country. The base model changed after registration, and AI assistance in labelling is disclosed. Both are reported as limitations.",
    area: "Scope",
  },
  {
    title: "Where the defect rate comes from",
    body: 'The "about half the pages" figure is from invented stories, with 117 of 150 pages tagged as containing non-human characters, including mixed casts. Human-only pages did better (11 of 33 against 66 of 117), but 33 pages is too few to call a rate, and no donated story was reviewed.',
    area: "How it was scored",
  },
];
