// ADR-066: every number below is copied from one of these tracked files, as the string the file
// prints, and the held-out test set appears only as whole-slice counts. data.test.ts checks both.
export const SOURCES = {
  runbook: "docs/capstone/research_runbook.md",
  groupGuide: "docs/capstone/group-guide.md",
  preregistration: "docs/product/PREREGISTRATION_OBJ4.md",
  changelog: "docs/capstone/research-changelog.md",
  finetuneSpec: "docs/specs/judge-finetune.md",
  trainConfig: "backend/finetune/train_qlora.yaml",
} as const;

export type SourceKey = keyof typeof SOURCES;

// Runbook, "Partial untuned versus fine-tuned comparison (2026-10-08)".
export const RESULT_DATE = "2026-10-08";

// Runbook, "Exact values of the partial comparison (copied 2026-10-11)".
export const TEST = { pairs: 329, different: 47, same: 282 } as const;

export type Judge = {
  name: string;
  f1: string;
  f1Interval: string;
  precision: string;
  recall: string;
  caught: number;
  missed: number;
  falseAlarms: number;
  correctSame: number;
  unreadable: number;
  // The selected checkpoint and its F1 on the validation split. The untrained model has neither.
  checkpoint?: number;
  validationF1?: string;
  // Runbook, "Secondary sensitivity analysis": the same judge with the ambiguous reference dropped.
  sensitivity: { f1: string; precision: string; recall: string };
};

// Names follow group-guide.md §5.2. The runbook calls them Untuned, Seed 1 (preselected), Seed 0 and Seed 2.
const UNTRAINED: Judge = {
  name: "Untrained Qwen3.5-9B",
  f1: "0.472",
  f1Interval: "0.236 to 0.629",
  precision: "0.382",
  recall: "0.617",
  caught: 29,
  missed: 18,
  falseAlarms: 47,
  correctSame: 235,
  unreadable: 3,
  sensitivity: { f1: "0.476", precision: "0.391", recall: "0.610" },
};

const SEED_1: Judge = {
  name: "Trained, seed 1 (picked in advance)",
  f1: "0.310",
  f1Interval: "0.000 to 0.491",
  precision: "0.818",
  recall: "0.191",
  caught: 9,
  missed: 38,
  falseAlarms: 2,
  correctSame: 280,
  unreadable: 40,
  checkpoint: 40,
  validationF1: "0.444",
  sensitivity: { f1: "0.346", precision: "0.818", recall: "0.220" },
};

const SEED_0: Judge = {
  name: "Trained, seed 0",
  f1: "0.361",
  f1Interval: "0.000 to 0.586",
  precision: "0.786",
  recall: "0.234",
  caught: 11,
  missed: 36,
  falseAlarms: 3,
  correctSame: 279,
  unreadable: 44,
  checkpoint: 40,
  validationF1: "0.333",
  sensitivity: { f1: "0.400", precision: "0.786", recall: "0.268" },
};

const SEED_2: Judge = {
  name: "Trained, seed 2",
  f1: "0.417",
  f1Interval: "0.214 to 0.566",
  precision: "0.353",
  recall: "0.511",
  caught: 24,
  missed: 23,
  falseAlarms: 44,
  correctSame: 238,
  unreadable: 8,
  checkpoint: 140,
  validationF1: "0.364",
  sensitivity: { f1: "0.438", precision: "0.382", recall: "0.512" },
};

// The runbook's row order: the untrained model, then the seed picked in advance, then the other two.
export const JUDGES = [UNTRAINED, SEED_1, SEED_0, SEED_2] as const;

// Arithmetic on a judge's row. The runbook's "Derived from the table" paragraph states the results.
export const calledDifferent = (judge: Judge) => judge.caught + judge.falseAlarms;
export const wrong = (judge: Judge) => judge.falseAlarms + judge.missed;

// Same section: seed 1 minus the untrained model, with the runbook's own minus sign.
export const COMPARISON = { deltaF1: "−0.161", interval: "−0.358 to +0.003", mcnemarP: "0.0035" } as const;
export const RESAMPLES = "10,000";
export const SEEDS = { meanF1: "0.363", sampleSd: "0.054" } as const;
export const VALIDATION = { pairs: 86, different: 4 } as const;

// Runbook, "Registered agreement and sensitivity analyses (2026-10-09)". The dropped character is
// named there. It is a donated one, so its id stays out of this file (ADR-066 decision 9).
export const SENSITIVITY = {
  droppedPairs: 20,
  pairs: 309,
  different: 41,
  deltaF1: "−0.130",
  interval: "−0.333 to +0.053",
  mcnemarP: "0.0075",
} as const;

// Same section: the two raters on the test slice.
export const AGREEMENT = { kappa: "0.634", agreement: "89.7%" } as const;

// Runbook, "What the registered freeze contains": the train split, and the constructed pairs in it
// that contradict a rated pair.
export const TRAIN = { records: 484, different: 157, constructed: 104 } as const;
export const CONTRADICTION = { pairs: 2, records: 4 } as const;

// Runbook, "Registered training settings (copied 2026-10-11)". `key` is the setting's name in
// train_qlora.yaml, and `value` is the string both files print (ADR-066 amendment (a)).
export const TRAINING_SETTINGS = [
  { key: "model_name_or_path", value: "Qwen/Qwen3.5-9B", means: "The model that is trained. The untrained judge is this same model." },
  { key: "finetuning_type", value: "lora", means: "The model's own weights stay frozen. A small add-on, the adapter, is trained." },
  { key: "quantization_bit", value: "4", means: "The frozen model is loaded in a compressed 4-bit form. This is the Q in QLoRA." },
  { key: "lora_rank", value: "16", means: "The size of the adapter." },
  { key: "lora_alpha", value: "32", means: "How strongly the adapter's output is scaled." },
  { key: "image_max_pixels", value: "262144", means: "Each picture is shrunk to at most 512 × 512 pixels." },
  { key: "num_train_epochs", value: "3.0", means: "The model sees every training pair three times." },
  { key: "per_device_train_batch_size", value: "1", means: "One pair is read at a time." },
  { key: "gradient_accumulation_steps", value: "8", means: "The adapter is updated once for every 8 pairs." },
  { key: "learning_rate", value: "1.0e-4", means: "The largest size of one update." },
  { key: "lr_scheduler_type", value: "cosine", means: "The update size falls smoothly toward zero by the end." },
  { key: "warmup_ratio", value: "0.1", means: "The update size rises from zero over the first tenth of training." },
  { key: "save_steps", value: "10", means: "A checkpoint, a saved copy of the adapter, is kept every 10 updates." },
] as const;

// Same section, and group-guide.md §5.3 for the share of synthetic stories about non-human characters.
export const TRAINING = { updatesPerEpoch: 61, updatesPerSeed: 183, generationCap: 256, syntheticNonHuman: "83%" } as const;

// group-guide.md §5.2, on seeds 0 and 1.
export const UNREADABLE_SHARE = "about one pair in eight";
