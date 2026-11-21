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

// Same section; non-human counts come from the runbook's generated-character/pair mix table.
export const TRAINING = { updatesPerEpoch: 61, updatesPerSeed: 183, generationCap: 256, nonHumanPairs: 264 } as const;

// group-guide.md §5.2, on seeds 0 and 1.
export const UNREADABLE_SHARE = "about one pair in eight";

// ---- Plain-words copy, accuracy, the checkpoint tie, recommendations and charts (research page refresh) ----

// group-guide.md §5.2, "In plain words". The page and the guide print this sentence word for word.
export const TRADEOFF =
  "The fine-tuned judge raises far fewer false alarms (2 vs 47) because it rarely says 'different' at all. As a result it misses most real character changes (38 of 47 vs 18 of 47), and 12% of its answers could not be read. On the main score, F1, it is worse (0.31 vs 0.47).";

// group-guide.md §5.2, under its table. Nobody counted how many unreadable answers fell on Different pairs.
export const UNREADABLE_NOTE = `Seeds 0 and 1 gave unreadable answers on ${UNREADABLE_SHARE}. An unreadable answer on a Different pair counts as a miss, so this may lower their recall. How many of them fell on Different pairs was not counted.`;

// research-changelog.md §1 item 3: why the comparison is partial.
export const PARTIAL_SENTENCES = [
  "The prompted Gemma baseline failed authentication, and paid evaluation stopped for budget.",
  "No claim-ladder or product-gate decision was made.",
] as const;

// Runbook, "Results figures recounted for the research page refresh (2026-11-21)".
export const CHARTS_AS_OF = "2026-11-21";

export type AccuracyRow = { name: string; accuracy: string; correctSame: string; falseAlarmRate: string; missRate: string };
export const ACCURACY: AccuracyRow[] = [
  { name: "Always answering Same", accuracy: "282 / 329 = 85.7%", correctSame: "282 / 282 = 100%", falseAlarmRate: "0%", missRate: "100%" },
  { name: "Untuned Qwen3.5-9B", accuracy: "264 / 329 = 80.2%", correctSame: "235 / 282 = 83.3%", falseAlarmRate: "16.7%", missRate: "38.3%" },
  { name: "Seed 1", accuracy: "289 / 329 = 87.8%", correctSame: "280 / 282 = 99.3%", falseAlarmRate: "0.7%", missRate: "80.9%" },
  { name: "Seed 0", accuracy: "290 / 329 = 88.1%", correctSame: "279 / 282 = 98.9%", falseAlarmRate: "1.1%", missRate: "76.6%" },
  { name: "Seed 2", accuracy: "262 / 329 = 79.6%", correctSame: "238 / 282 = 84.4%", falseAlarmRate: "15.6%", missRate: "48.9%" },
];
export const ACCURACY_NOTE =
  "Seed 1's accuracy is 2.1 points above always answering Same, and it gets there by answering Same more often, not by finding more Different pairs.";

// Runbook, "Checkpoint tie". Each cell is the string the runbook's table prints.
export const CHECKPOINT_TIE = [
  { seed: "0", f1: "0.333", selected: "checkpoint 40 (1 caught, 1 false alarm, 3 missed)", alternative: "checkpoint 80 (2, 6, 2)", unreadable: "13, 0" },
  { seed: "1", f1: "0.444", selected: "checkpoint 40 (2, 3, 2)", alternative: "checkpoint 110 (2, 3, 2)", unreadable: "8, 0" },
  { seed: "2", f1: "0.364", selected: "checkpoint 140 (2, 5, 2), no tie", alternative: "none", unreadable: "2" },
] as const;
export const TIE_SENTENCES = [
  "The rule fixed in advance picks the checkpoint with the best validation Different-class F1 and, on a tie, the earlier step.",
  "Seeds 0 and 1 had a tie, and the earlier step won both times",
  "The unreadable counts follow on the test set: seeds 1 and 0 (checkpoint 40) gave 40 and 44 unreadable answers of 329, seed 2 gave 8.",
  "seed 0 from checkpoint 120 and seed 1 from checkpoint 130 caught none of the 4 validation Different pairs",
] as const;

// Runbook, "Validation scores by checkpoint": all 57 rows. F1 is on the 4 Different validation pairs.
export type CheckpointPoint = { step: number; f1: string; unreadable: number };
export const CHECKPOINTS: Record<0 | 1 | 2, CheckpointPoint[]> = {
  0: [{ step: 10, f1: "0.250", unreadable: 1 }, { step: 20, f1: "0.121", unreadable: 29 }, { step: 30, f1: "0.000", unreadable: 28 }, { step: 40, f1: "0.333", unreadable: 13 }, { step: 50, f1: "0.000", unreadable: 1 }, { step: 60, f1: "0.000", unreadable: 2 }, { step: 70, f1: "0.111", unreadable: 0 }, { step: 80, f1: "0.333", unreadable: 0 }, { step: 90, f1: "0.000", unreadable: 0 }, { step: 100, f1: "0.286", unreadable: 0 }, { step: 110, f1: "0.174", unreadable: 0 }, { step: 120, f1: "0.000", unreadable: 1 }, { step: 130, f1: "0.000", unreadable: 4 }, { step: 140, f1: "0.000", unreadable: 1 }, { step: 150, f1: "0.000", unreadable: 0 }, { step: 160, f1: "0.000", unreadable: 0 }, { step: 170, f1: "0.000", unreadable: 0 }, { step: 180, f1: "0.000", unreadable: 0 }, { step: 183, f1: "0.000", unreadable: 0 }],
  1: [{ step: 10, f1: "0.273", unreadable: 2 }, { step: 20, f1: "0.000", unreadable: 38 }, { step: 30, f1: "0.000", unreadable: 35 }, { step: 40, f1: "0.444", unreadable: 8 }, { step: 50, f1: "0.200", unreadable: 0 }, { step: 60, f1: "0.182", unreadable: 2 }, { step: 70, f1: "0.000", unreadable: 3 }, { step: 80, f1: "0.000", unreadable: 11 }, { step: 90, f1: "0.000", unreadable: 8 }, { step: 100, f1: "0.261", unreadable: 0 }, { step: 110, f1: "0.444", unreadable: 0 }, { step: 120, f1: "0.125", unreadable: 0 }, { step: 130, f1: "0.000", unreadable: 1 }, { step: 140, f1: "0.000", unreadable: 1 }, { step: 150, f1: "0.000", unreadable: 2 }, { step: 160, f1: "0.000", unreadable: 2 }, { step: 170, f1: "0.000", unreadable: 2 }, { step: 180, f1: "0.000", unreadable: 1 }, { step: 183, f1: "0.000", unreadable: 1 }],
  2: [{ step: 10, f1: "0.261", unreadable: 2 }, { step: 20, f1: "0.214", unreadable: 34 }, { step: 30, f1: "0.121", unreadable: 7 }, { step: 40, f1: "0.095", unreadable: 2 }, { step: 50, f1: "0.000", unreadable: 19 }, { step: 60, f1: "0.095", unreadable: 5 }, { step: 70, f1: "0.000", unreadable: 10 }, { step: 80, f1: "0.143", unreadable: 13 }, { step: 90, f1: "0.108", unreadable: 1 }, { step: 100, f1: "0.000", unreadable: 0 }, { step: 110, f1: "0.267", unreadable: 0 }, { step: 120, f1: "0.167", unreadable: 0 }, { step: 130, f1: "0.250", unreadable: 2 }, { step: 140, f1: "0.364", unreadable: 2 }, { step: 150, f1: "0.235", unreadable: 0 }, { step: 160, f1: "0.154", unreadable: 0 }, { step: 170, f1: "0.125", unreadable: 1 }, { step: 180, f1: "0.133", unreadable: 0 }, { step: 183, f1: "0.129", unreadable: 0 }],
};
// The selected checkpoints are on JUDGES. The tied later checkpoints are in the runbook's tie table.
export const TIED_STEP = { 0: 80, 1: 110 } as const;

// Runbook, "No score to sweep".
export const NO_CURVE_SOURCE =
  "Each judge answers with a verdict and no score, so no ROC, precision-recall or threshold curve can be drawn for them.";

// group-guide.md §5.2, "What we recommend". The guide prints `guide`. The page prints `lead` then `body`.
const rec = (lead: string, body: string, untested: boolean) => ({ lead, body, untested, guide: body ? `${lead} ${body}` : lead });
export const RECOMMENDATIONS = [
  rec("Keep prompted Gemma, a no-change decision.", "Gemma was not scored on this test set.", false),
  rec("Reject checkpoints with many unreadable answers, and enlarge validation's Different class.", "", true),
  rec("Record the judge's full answer text.", "", true),
  rec("Fix the constructed-pair sentence shared by 104 training pairs.", "", true),
  rec("Report the result in the bounded wording of research-changelog.md section 1 item 4.", "", false),
] as const;
// research-changelog.md §1 item 4.
export const BOUNDED_WORDING =
  "Under the evaluated dataset, training settings and inference constraints, fine-tuning did not demonstrate a reliable improvement over the untuned baseline.";

// Each chart has a stable id. Ticket 11 screenshots `[data-chart-id]` into the PNG named here.
const chart = (id: string, title: string, alt: string) => ({ id, title, alt, png: `/research/diagrams/${id}.png` });
export const CHARTS = [
  chart(
    "judge-confusion-matrices",
    "What the untrained model and seed 1 did on the test pairs",
    `Two tables of counts on the ${TEST.pairs} test pairs. The untrained model: ${UNTRAINED.caught} caught, ${UNTRAINED.missed} missed, ${UNTRAINED.falseAlarms} false alarms, ${UNTRAINED.correctSame} correct Same. Seed 1: ${SEED_1.caught} caught, ${SEED_1.missed} missed, ${SEED_1.falseAlarms} false alarms, ${SEED_1.correctSame} correct Same.`
  ),
  chart(
    "judge-f1-precision-recall",
    "F1, precision and recall of the four judges",
    `Bars of F1, precision and recall for four judges, with the F1 interval. F1 is ${UNTRAINED.f1} for the untrained model, ${SEED_1.f1} for seed 1, ${SEED_0.f1} for seed 0 and ${SEED_2.f1} for seed 2.`
  ),
  chart(
    "judge-catches-false-alarms",
    "Pairs each judge called Different: catches and false alarms",
    `For each judge, the pairs it called Different, split into catches and false alarms. Untrained ${calledDifferent(UNTRAINED)} (${UNTRAINED.caught} catches, ${UNTRAINED.falseAlarms} false alarms), seed 1 ${calledDifferent(SEED_1)} (${SEED_1.caught}, ${SEED_1.falseAlarms}), seed 0 ${calledDifferent(SEED_0)} (${SEED_0.caught}, ${SEED_0.falseAlarms}), seed 2 ${calledDifferent(SEED_2)} (${SEED_2.caught}, ${SEED_2.falseAlarms}).`
  ),
  chart(
    "judge-validation-checkpoints",
    "Validation F1 and unreadable answers by checkpoint",
    "Two line charts of the 86 validation pairs, one line per seed, by training checkpoint. One shows F1 on the Different class, the other the unreadable answers. The selected checkpoints and the ties are marked. Seeds 0 and 1 were tied at checkpoint 40 with a later checkpoint that had no unreadable answers."
  ),
] as const;
