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

export const TAXONOMY_LABELS: Record<
  keyof TaxonomyState,
  { label: string; shortcut: string; example: string; description: string }
> = {
  wrong_colour: {
    label: "Wrong Color",
    shortcut: "1",
    example: "Cream chest patch is rendered brown; fur hue shifted",
    description: "Fur, hair, skin, or dominant color differs from reference",
  },
  wrong_species: {
    label: "Wrong Species",
    shortcut: "2",
    example: "Fox cub rendered as a dog; animal silhouette altered",
    description: "Species, animal type, or defining core silhouette is altered",
  },
  wrong_body_feature: {
    label: "Wrong Body Feature",
    shortcut: "3",
    example: "Two eyes instead of three; tail or wings missing/added",
    description: "Countable or structural body parts (ears, tail, horns, snout, wings, limbs)",
  },
  wrong_clothing: {
    label: "Wrong Clothing/Accessories",
    shortcut: "4",
    example: "Striped scarf absent, recolored, or hat missing",
    description: "Attire, hat, collar, glasses, or signature accessories missing or altered",
  },
  wrong_style: {
    label: "Wrong Style",
    shortcut: "5",
    example: "Photorealistic rendering rather than flat storybook gouache",
    description: "Art style, rendering medium, line weight, or texture differs from reference",
  },
  different_face: {
    label: "Different Face",
    shortcut: "6",
    example: "Same species, but facial expression identity or eyes belong to an unrelated individual",
    description: "Facial structure, muzzle shape, eye style, or facial markings mismatch",
  },
  character_absent: {
    label: "Character Absent",
    shortcut: "7",
    example: "Main character does not appear in the scene at all",
    description: "Main character is completely absent from the composition",
  },
};
