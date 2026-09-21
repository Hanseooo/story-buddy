export type ResearchPair = {
  id: string;
  canonical_signed_url: string;
  scene_signed_url: string;
};

export type TaxonomyState = {
  wrong_colour: boolean;
  wrong_species: boolean;
  wrong_body_feature: boolean;
  wrong_clothing: boolean;
  wrong_style: boolean;
  different_face: boolean;
  character_absent: boolean;
};

export const INITIAL_TAXONOMY: TaxonomyState = {
  wrong_colour: false,
  wrong_species: false,
  wrong_body_feature: false,
  wrong_clothing: false,
  wrong_style: false,
  different_face: false,
  character_absent: false,
};

// Wording follows docs/specs/labelling-rulebook.md Step 2 and Step 3. `description` is what counts,
// `doesNotCount` is what does not; edit the rulebook first, never only this text.
export const TAXONOMY_LABELS: Record<
  keyof TaxonomyState,
  { label: string; shortcut: string; doesNotCount: string; description: string }
> = {
  wrong_colour: {
    label: "Wrong Color",
    shortcut: "1",
    doesNotCount: "clothing colour (that is Wrong Clothing)",
    description: "Skin, fur, hair, eye or body colour differs from the reference",
  },
  wrong_species: {
    label: "Wrong Species",
    shortcut: "2",
    doesNotCount: "pose, angle",
    description: "Animal type or core silhouette differs",
  },
  wrong_body_feature: {
    label: "Wrong Body Feature",
    shortcut: "3",
    doesNotCount: "a part hidden by the pose",
    description: "Countable or structural parts differ: eyes, ears, tail, horns, wings, limbs",
  },
  wrong_clothing: {
    label: "Wrong Clothing/Accessories",
    shortcut: "4",
    doesNotCount: "a clothing change on its own, which is Same. Tick it only when another reason already makes the pair Different",
    description: "Clothing or accessories changed, added or missing",
  },
  wrong_style: {
    label: "Wrong Style",
    shortcut: "5",
    doesNotCount: "an art style change on its own, which is Same. Tick it only when another reason already makes the pair Different",
    description: "Art style, rendering or line work looks off",
  },
  different_face: {
    label: "Different Face",
    shortcut: "6",
    doesNotCount: "expression, mouth open, looking away",
    description: "Face shape, eye style, or facial markings belong to another individual",
  },
  character_absent: {
    label: "Character Absent",
    shortcut: "7",
    doesNotCount: "other characters on the page",
    description: "The reference character is not on the page",
  },
};
