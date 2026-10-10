import type { TaxonomyState } from "../../../_shared/constants";

// ADR-065: every number below is stated in one of these tracked files, and donated material
// appears only as whole-split counts. data.test.ts checks both.
export const SOURCES = {
  runbook: "docs/capstone/research_runbook.md",
  preregistration: "docs/product/PREREGISTRATION_OBJ4.md",
  rulebook: "docs/specs/labelling-rulebook.md",
  groupGuide: "docs/capstone/group-guide.md",
  manifest: "backend/finetune/manifest.py",
  buildDataset: "backend/finetune/build_dataset.py",
} as const;

export type SourceKey = keyof typeof SOURCES;

// Runbook, "What the registered freeze contains".
export const SPLITS = [
  { name: "Train", storiesFrom: "Synthetic", stories: 24, characters: 44, pairs: 484, same: 327, different: 157, constructed: 104 },
  { name: "Validation", storiesFrom: "Synthetic", stories: 6, characters: 11, pairs: 86, same: 82, different: 4, constructed: 0 },
  { name: "Held-out test", storiesFrom: "Donated", stories: 12, characters: 24, pairs: 329, same: 282, different: 47, constructed: 0 },
] as const;

export type SplitName = (typeof SPLITS)[number]["name"];

// Same table. A pair can carry several reasons, so these sum to 236 over 208 Different pairs.
export const REASON_PAIRS: Record<keyof TaxonomyState, number> = {
  different_face: 141,
  wrong_body_feature: 50,
  character_absent: 18,
  wrong_clothing: 12,
  wrong_colour: 9,
  wrong_style: 4,
  wrong_species: 2,
};

// Runbook, "Registered agreement and sensitivity analyses (2026-10-09)".
export const AGREEMENT = [
  { slice: "Held-out test (the registered number)", pairs: 329, kappa: "0.634", agreement: "89.7%" },
  { slice: "Held-out test, non-human characters", pairs: 25, kappa: "0.000", agreement: "96.0%" },
  { slice: "Every labelled pair", pairs: 795, kappa: "0.659", agreement: "89.3%" },
] as const;

// One row of the freeze's manifest, as stored, without `images` (two local file paths). ADR-066.
export type FrozenRecord = {
  pair_id: string;
  char_id: string;
  split: "train" | "val";
  provenance: "synthetic";
  pair_type: "pipeline" | "constructed";
  differences_observed: string;
  same_character: boolean;
  label: boolean;
  anatomy_intact: boolean;
  text_free: boolean;
  failure_reasons: (keyof TaxonomyState)[];
  ref_verdict_status: "passed" | "failed" | "unverified";
};

type ExampleImage = { src: string; alt: string };

export type Example = {
  record: FrozenRecord;
  // Each rater's first Same-or-Different answer; null for a constructed pair, which no rater saw.
  raterAnswers: [boolean, boolean] | null;
  reference: ExampleImage;
  page: ExampleImage;
  note: string;
};

const image = (pairId: string, role: "reference" | "page", alt: string): ExampleImage => ({
  src: `/research/dataset/${pairId}-${role}.webp`,
  alt,
});

// Hand-picked by the owner from a local contact sheet (ADR-065 decision 6). The records are copied
// from the obj4-v1 manifest (ADR-066); data.test.ts compares them with the freeze where it is on disk.
// The notes apply the rulebook's wording.
export const EXAMPLES: Example[] = [
  {
    record: {
      pair_id: "033b8372e89e4c06",
      char_id: "syn-025:c0",
      split: "val",
      provenance: "synthetic",
      pair_type: "pipeline",
      differences_observed: "Present on the page: human, brown hair, tan skin, human body with arms and legs, human face with eyes, nose, and mouth, human body, blue shirt, pants.",
      same_character: true,
      label: false,
      anatomy_intact: true,
      text_free: true,
      failure_reasons: [],
      ref_verdict_status: "passed",
    },
    raterAnswers: [true, true],
    reference: image("033b8372e89e4c06", "reference", "A man with brown hair in a blue polo shirt and dark blue trousers."),
    page: image("033b8372e89e4c06", "page", "The same man, smiling, fixing an egg-shaped robot on a kitchen table."),
    note: "The pose, the expression and the setting changed. The face, hair and build did not.",
  },
  {
    record: {
      pair_id: "14126f2a535e8682",
      char_id: "syn-020:c0",
      split: "train",
      provenance: "synthetic",
      pair_type: "pipeline",
      differences_observed: "Present on the page: tortoise, white, blue, tortoise with a teacup shell, tortoise face, chipped teacup shell with a handle, back legs sticking out.",
      same_character: true,
      label: false,
      anatomy_intact: true,
      text_free: true,
      failure_reasons: [],
      ref_verdict_status: "passed",
    },
    raterAnswers: [true, true],
    reference: image("14126f2a535e8682", "reference", "A white tortoise with a blue shell and a cracked teacup on its back."),
    page: image("14126f2a535e8682", "page", "The same tortoise, looking sad, beside a dried-up pond."),
    note: "A sad face is an expression, which does not count. Species, body colours and the teacup all match. The last card checks this same page against another tortoise's reference.",
  },
  {
    record: {
      pair_id: "4198b9cd8341bd3f",
      char_id: "syn-022:c0",
      split: "train",
      provenance: "synthetic",
      pair_type: "pipeline",
      differences_observed: "Present on the page: dog, brown and white fur, one blue eye, one brown eye, four-legged canine, dog face with one blue eye and one brown eye, bent tail, none.",
      same_character: true,
      label: false,
      anatomy_intact: true,
      text_free: true,
      failure_reasons: [],
      ref_verdict_status: "passed",
    },
    raterAnswers: [true, true],
    reference: image("4198b9cd8341bd3f", "reference", "A brown and white dog with long brown ears and blue eyes."),
    page: image("4198b9cd8341bd3f", "page", "The same dog, small in the frame, barking at a man who is mopping outside a row of storage units."),
    note: "Only the character in the reference is compared. The man on the page does not count, and an open mouth is an expression.",
  },
  {
    record: {
      pair_id: "1843d7d4835a8397",
      char_id: "syn-016:c0",
      split: "train",
      provenance: "synthetic",
      pair_type: "pipeline",
      differences_observed: "The face is that of a different individual. Expected: dust bunny, grey, round ball, smooth surface with button eye, ball-shaped, one lost button eye, none.",
      same_character: false,
      label: true,
      anatomy_intact: true,
      text_free: true,
      failure_reasons: ["different_face"],
      ref_verdict_status: "failed",
    },
    raterAnswers: [false, false],
    reference: image("1843d7d4835a8397", "reference", "A round grey creature with two small bumps on top, one ringed eye and a round snout patch."),
    page: image("1843d7d4835a8397", "page", "A round grey creature with two large eyes and a small open mouth, in front of crouching soldiers and a robot."),
    note: "The body is the same shape and colour, but the face is another individual's: two large eyes where the reference has one ringed eye and a snout patch.",
  },
  {
    record: {
      pair_id: "b865a5466cccc89f",
      char_id: "syn-009:c0",
      split: "train",
      provenance: "synthetic",
      pair_type: "pipeline",
      differences_observed: "The character is not the species the reference shows. The face is that of a different individual. Expected: bird, brown, orange, small round bird body with long beak, bird face with large eyes and curved beak, round body, long curved beak, none.",
      same_character: false,
      label: true,
      anatomy_intact: true,
      text_free: true,
      failure_reasons: ["wrong_species", "different_face"],
      ref_verdict_status: "failed",
    },
    raterAnswers: [false, false],
    reference: image("b865a5466cccc89f", "reference", "A brown and orange bird with a long curved orange beak."),
    page: image("b865a5466cccc89f", "page", "An orange creature with a cat's ears, whiskers and face and a long beak, standing by burrows in a field."),
    note: "The colours and the beak carried over, but the page drew a cat's head on the body. That is another animal and another face.",
  },
  {
    record: {
      pair_id: "848c636f47f8e342",
      char_id: "syn-020:c1",
      split: "train",
      provenance: "synthetic",
      pair_type: "constructed",
      differences_observed: "The face and build are those of a different individual; this is not the reference character.",
      same_character: false,
      label: true,
      anatomy_intact: true,
      text_free: true,
      failure_reasons: ["different_face"],
      ref_verdict_status: "failed",
    },
    raterAnswers: null,
    reference: image("848c636f47f8e342", "reference", "A green tortoise with a brown shell, smiling."),
    page: image("848c636f47f8e342", "page", "A white tortoise with a blue shell and a cracked teacup on its back, looking sad, beside a dried-up pond."),
    note: "A constructed pair: a script set this tortoise's reference against the page of the other tortoise in the same story. The species matches and the individual does not. Every constructed pair carries this one reason and this one sentence, written by the script and not by a rater.",
  },
];

// ADR-066 decision 2. Meanings follow the comments on `ManifestRecord` in backend/finetune/manifest.py.
export const RECORD_FIELDS: { field: keyof FrozenRecord; meaning: string }[] = [
  { field: "pair_id", meaning: "The pair's id, made by the build script. It carries no meaning." },
  { field: "char_id", meaning: "The story and the character the reference belongs to. Splits are made on it. It never reaches the training text." },
  { field: "split", meaning: "train, val or test. Bookkeeping, not training text." },
  { field: "provenance", meaning: "synthetic for a story the researchers wrote, donated for a child's story." },
  { field: "pair_type", meaning: "pipeline for a page the pipeline drew for this character, which the two raters labelled. constructed for a pair a script made from two characters." },
  { field: "differences_observed", meaning: "A sentence a script builds from the ticked reasons and the character's stored attributes. No rater wrote it." },
  { field: "same_character", meaning: "The final answer. true means Same." },
  { field: "label", meaning: "The opposite of same_character. true means Different, the class the judge is scored on." },
  { field: "anatomy_intact", meaning: "false when a rater ticked Broken Anatomy. A constructed pair takes the default, true." },
  { field: "text_free", meaning: "false when a rater ticked Text Visible. A constructed pair takes the default, true." },
  { field: "failure_reasons", meaning: "The reasons ticked, from the fixed list of seven above." },
  { field: "ref_verdict_status", meaning: "Whether the automatic check of the reference picture passed when the book was made. Bookkeeping, not training text." },
];

// ADR-066 decision 3: the train.json entry for the constructed example, without `images`.
// `target` is the stored string; the page pretty-prints it.
export const TRAINING_RECORD = {
  pairId: "848c636f47f8e342",
  prompt: "<image><image>The FIRST image is a canonical character reference. The SECOND image is one page of a picture book in which that character should appear drawn to match the reference.\n\nFirst describe every difference you observe between the character on the page and the reference. Then say whether it is the same character; list which of the reference's attributes are actually present on the page; whether the page is drawn in the same art style as the reference; whether the character's anatomy is intact; whether the character is drawn exactly once; and whether the picture is free of any text. Finally list the failure reasons that apply, choosing only from the fixed set.",
  target: "{\"differences_observed\": \"The face and build are those of a different individual; this is not the reference character.\", \"same_character\": false, \"attributes_present\": [], \"style_match\": false, \"anatomy_intact\": true, \"subjects_unique\": true, \"text_free\": true, \"failure_reasons\": [\"different_face\"]}",
};
