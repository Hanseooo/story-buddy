import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import * as data from "./data";

const FRONTEND = path.resolve(__dirname, "../../../../..");
const REPO_ROOT = path.resolve(FRONTEND, "..");
const IMAGE_DIR = path.join(FRONTEND, "public/research/dataset");
// The freeze is git-ignored. A worktree has no copy, so fall back to the main checkout three levels up.
const FREEZE =
  [REPO_ROOT, path.resolve(REPO_ROOT, "../../..")]
    .map((root) => path.join(root, "data/judge/freezes/obj4-v1"))
    .find((dir) => existsSync(dir)) ?? path.join(REPO_ROOT, "data/judge/freezes/obj4-v1");

const read = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8");
// Source docs wrap lines, so compare with every run of whitespace as one space.
const flat = (file: string) => read(file).replace(/\s+/g, " ");

describe("dataset page data", () => {
  // ADR-065 decision 5: donated material appears only as whole-split counts.
  it("names no donated story, in the data or in an image filename", () => {
    expect(JSON.stringify(data)).not.toMatch(/don-/i);
    expect(readdirSync(IMAGE_DIR).join("\n")).not.toMatch(/don-/i);
  });

  it("matches the runbook's freeze table row by row", () => {
    const runbook = read(data.SOURCES.runbook);
    for (const split of data.SPLITS) {
      const row = `| ${split.name} (${split.storiesFrom.toLowerCase()}) | ${split.stories} | ${split.characters} | ${split.pairs} | ${split.same} | ${split.different} | ${split.constructed} |`;
      expect(runbook, split.name).toContain(row);
    }
    // Hand-worked from the runbook's "All" row.
    expect(runbook).toContain("| All | 42 | 79 | 899 | 691 | 208 | 104 |");
    expect(data.SPLITS.map((split) => split.pairs)).toEqual([484, 86, 329]);
    expect(data.EXPLORATORY).toEqual({ excluded: 16, trainPairs: 468 });
  });

  it("counts characters by species, as the runbook's recount says", () => {
    const runbook = flat(data.SOURCES.runbook);
    const [train, validation] = data.CHARACTER_KINDS;
    expect(runbook).toContain(
      `gives train ${train.humanCharacters} human and ${train.nonHumanCharacters} non-human characters, ${train.humanPairs} human and ${train.nonHumanPairs} non-human pairs`
    );
    expect(runbook).toContain(
      `Validation is the same either way: ${validation.humanCharacters} human and ${validation.nonHumanCharacters} non-human characters, ${validation.humanPairs} and ${validation.nonHumanPairs} pairs`
    );
    expect(data.CHARACTER_KINDS).toEqual([
      { split: "Train", humanCharacters: 12, nonHumanCharacters: 32, humanPairs: 178, nonHumanPairs: 306 },
      { split: "Validation", humanCharacters: 9, nonHumanCharacters: 2, humanPairs: 75, nonHumanPairs: 11 },
    ]);
    expect(runbook).toContain("Seven training characters the roster called human are not human");
    expect(data.ROSTER_MISSES).toBe(7);
  });

  it("matches the runbook's reason counts and agreement table", () => {
    const runbook = read(data.SOURCES.runbook);
    const names: Record<string, string> = {
      different_face: "Different Face",
      wrong_body_feature: "Wrong Body Feature",
      character_absent: "Character Absent",
      wrong_clothing: "Wrong Clothing/Accessories",
      wrong_colour: "Wrong Color",
      wrong_style: "Wrong Style",
      wrong_species: "Wrong Species",
    };
    for (const [key, count] of Object.entries(data.REASON_PAIRS)) {
      expect(runbook, key).toContain(`| ${names[key]} | ${count} |`);
    }
    for (const row of data.AGREEMENT) {
      expect(runbook, row.slice).toContain(`| ${row.pairs} | ${row.kappa} | ${row.agreement} |`);
    }
  });

  it("states each pair and label fact as the runbook's recount does", () => {
    const runbook = flat(data.SOURCES.runbook);
    const { pairs, natural, constructed, laterAttempt } = data.PAIR_FACTS;
    expect(runbook).toContain(`${pairs} pairs: train 484, validation 86, test 329. ${natural} natural pairs`);
    expect(runbook).toContain(`${laterAttempt} of the ${natural} natural pairs use a second or later drawing attempt`);
    expect(runbook).toContain(`and ${constructed} constructed pairs`);
    expect(runbook).toContain("a page with two characters makes two pairs");
    expect(data.PAIR_FACTS).toEqual({ pairs: 899, books: 42, natural: 795, constructed: 104, laterAttempt: 422 });

    const f = data.LABEL_FACTS;
    expect(runbook).toContain(`${f.conflicted} pairs were conflicted, meaning the raters differed on any field`);
    expect(runbook).toContain(`${f.differedOnSameDifferent} of the ${f.conflicted} differed on Same/Different`);
    expect(runbook).toContain(`${f.aiAssisted} pairs (9 train, 1 validation) were relabelled by the owner after an AI-assisted`);
    expect(runbook).toContain(`${f.changed} final labels are Same although both raters first answered Different`);
    expect(runbook).toContain(`The other ${f.changedByAdjudication} (train 10, validation 2, test 1) went through ordinary adjudication`);
    expect(runbook).toContain(
      `${f.kept.total} final labels are Different with only \`wrong_clothing\` (6) or \`wrong_style\` (3) ticked: train ${f.kept.train}, validation ${f.kept.validation}, test ${f.kept.test}`
    );
    expect(runbook).toContain("The owner could see which rater gave which label");
    expect(runbook).toContain("Train 157 of 484 (104 constructed, 53 natural of 380 natural)");
    expect(f).toEqual({
      conflicted: 172,
      differedOnSameDifferent: 85,
      aiAssisted: 10,
      changed: 23,
      changedByAdjudication: 13,
      kept: { total: 9, train: 6, validation: 1, test: 2 },
    });
    expect(data.TRAIN_DIFFERENT).toEqual({ total: 157, constructed: 104, natural: 53 });
    expect(runbook).toContain("Broken Anatomy on 32, Text Visible on 3");
    expect(data.RECORD_FIELDS.map((r) => r.meaning).join(" ")).toContain("(32 of 899 pairs)");
    expect(data.RECORD_FIELDS.map((r) => r.meaning).join(" ")).toContain("(3 of 899 pairs)");
  });

  it("pins the process steps' dates and model to the runbook", () => {
    const runbook = flat(data.SOURCES.runbook);
    expect(runbook).toContain("Dataset handoff (2026-09-30)");
    expect(runbook).toContain("| `model_name_or_path` | Qwen/Qwen3.5-9B |");
    expect(runbook).toContain("each final trainer state records step 183 and epoch 3.0");
    expect(flat(data.SOURCES.preregistration)).toContain("the 30 synthetic stories");
    expect(data.PROCESS_STEPS[7].text).toContain("Qwen3.5-9B");
    expect(data.PROCESS_STEPS[5].text).toContain("2026-09-30");
    expect(data.DEFINITIONS.find((d) => d.term.startsWith("Freeze"))?.meaning).toContain("2026-09-30");
  });

  it("states the split decisions as the preregistration and runbook do", () => {
    const prereg = flat(data.SOURCES.preregistration);
    expect(prereg).toContain("the 30 synthetic stories are 24 train and 6 validation, allocated as 8 train and 2 validation stories per preset");
    expect(prereg).toContain("**Held-out test** | **Donated stories only**");
    expect(prereg).toContain("test keeps external validity");
    expect(prereg).toContain("Spending donated characters on the training split");
    expect(prereg).toContain("the 15 donated candidates");
    const runbook = flat(data.SOURCES.runbook);
    expect(runbook).toContain("Three donated candidate stories never entered the registered freeze because their pipelines failed");
    expect(runbook).toContain(`holds ${data.CONSTRUCTED.matches} frozen matches`);
    expect(runbook).toContain(`${data.CONSTRUCTED.humanMatches} of the ${data.CONSTRUCTED.matches} are human with human`);
    expect(data.CONSTRUCTED).toEqual({ matches: 14, humanMatches: 12 });
    expect(data.DONATED_CANDIDATES).toBe(15);
  });

  it("gives the labelling-tool reasons in the tracked doc", () => {
    const raw = read("docs/specs/annotation-surface.md");
    expect(data.OWNER_TOOL_REASONS).toEqual([
      "It saves time.",
      "Both raters can label in parallel.",
      "Every label saves to the cloud as it is made.",
      "It is easy for teammates to use.",
    ]);
    for (const reason of data.OWNER_TOOL_REASONS) expect(raw, reason).toContain(reason);
    const doc = flat("docs/specs/annotation-surface.md");
    expect(doc).toContain("images stay in a private bucket and open only through short-lived signed links");
    expect(doc).toContain("no training data sits on a shared lab PC");
    expect(doc).toContain("a rater cannot see the other rater's labels");
    expect(data.DOCUMENTED_TOOL_REASONS).toHaveLength(3);
    expect(existsSync(path.join(REPO_ROOT, data.SOURCES.labellingDemo))).toBe(true);
  });

  it("lists the ten steps in the order the spec gives", () => {
    expect(data.PROCESS_STEPS.map((step) => step.name)).toEqual([
      "Stories",
      "Generated books",
      "Pairs",
      "Two raters",
      "Adjudication",
      "Freeze",
      "Splits",
      "Training",
      "Checkpoint choice",
      "One held-out test read",
    ]);
  });

  it("serves the dataset-flow diagram byte for byte from the docs source", () => {
    const source = path.join(REPO_ROOT, data.FLOW_DIAGRAM.source);
    expect(data.FLOW_DIAGRAM.source).toBe("docs/diagrams/drawio/dataset_build_and_annotation_flow.drawio.svg");
    expect(readFileSync(path.join(FRONTEND, "public", data.FLOW_DIAGRAM.svg)).equals(readFileSync(source))).toBe(true);
    expect(data.FLOW_DIAGRAM.png).toBe("/research/diagrams/dataset_build_and_annotation_flow.png");
  });

  it("cites only files that are in the repository", () => {
    for (const file of Object.values(data.SOURCES)) {
      expect(existsSync(path.join(REPO_ROOT, file)), file).toBe(true);
    }
  });

  it("shows six train or validation examples whose images are committed", () => {
    expect(data.EXAMPLES).toHaveLength(6);
    for (const example of data.EXAMPLES) {
      expect(["train", "val"]).toContain(example.record.split);
      expect(existsSync(path.join(FRONTEND, "public", example.reference.src)), example.reference.src).toBe(true);
      expect(existsSync(path.join(FRONTEND, "public", example.page.src)), example.page.src).toBe(true);
    }
  });

  // Rulebook: Different needs a reason you can name, and Same carries none.
  it("gives every Different example a reason and no Same example one", () => {
    for (const { record } of data.EXAMPLES) {
      expect(record.failure_reasons.length > 0, record.pair_id).toBe(!record.same_character);
      expect(record.label, record.pair_id).toBe(!record.same_character);
    }
  });

  // ADR-066 decisions 1 and 4.
  it("shows the tortoise pair as the constructed example, with no file paths in any record", () => {
    expect(data.EXAMPLES.map((example) => example.record.pair_id)).toEqual([
      "033b8372e89e4c06",
      "14126f2a535e8682",
      "4198b9cd8341bd3f",
      "1843d7d4835a8397",
      "b865a5466cccc89f",
      "848c636f47f8e342",
    ]);
    const constructed = data.EXAMPLES[5];
    expect(constructed.record.pair_type).toBe("constructed");
    expect(constructed.record.char_id).toBe("syn-020:c1");
    expect(constructed.raterAnswers).toBeNull();
    for (const example of data.EXAMPLES) expect(Object.keys(example.record)).not.toContain("images");
    expect(data.TRAINING_RECORD.pairId).toBe("848c636f47f8e342");
  });

  it("shows the one verbatim record in the stored field order, shortened with an ellipsis only", () => {
    expect(data.VERBATIM_RECORD.pair_id).toBe("033b8372e89e4c06");
    expect(Object.keys(data.VERBATIM_RECORD)).toEqual([
      "pair_id", "char_id", "split", "provenance", "pair_type", "images", "differences_observed",
      "same_character", "label", "anatomy_intact", "text_free", "failure_reasons", "ref_verdict_status",
    ]);
    expect(data.VERBATIM_RECORD.split).toBe("val");
    expect(data.VERBATIM_RECORD.images).toHaveLength(2);
    expect(JSON.stringify(data.VERBATIM_RECORD)).not.toMatch(/don-/i);
  });

  // The freeze is git-ignored, so this runs on a machine that has it and is skipped in CI (ADR-066).
  it.skipIf(!existsSync(FREEZE))("copies each record, rater answer and the training record from the freeze", () => {
    const lines = (file: string) =>
      readFileSync(path.join(FREEZE, file), "utf8").split("\n").filter(Boolean).map((line) => JSON.parse(line));
    const rows = [...lines("manifest.train.jsonl"), ...lines("manifest.val.jsonl")];
    const answers = lines("annotation_agreement.jsonl");

    for (const example of data.EXAMPLES) {
      const { images, ...stored } = rows.find((row) => row.pair_id === example.record.pair_id);
      expect(images).toHaveLength(2);
      expect(example.record).toEqual(stored);
      expect(example.raterAnswers).toEqual(answers.find((row) => row.pair_id === example.record.pair_id)?.labels ?? null);
    }

    const shown = rows.find((row) => row.pair_id === data.TRAINING_RECORD.pairId);
    const train = JSON.parse(readFileSync(path.join(FREEZE, "train.json"), "utf8"));
    const stored = train.filter((entry: { images: string[] }) => entry.images.join() === shown.images.join());
    expect(stored).toHaveLength(1);
    expect(data.TRAINING_RECORD.prompt).toBe(stored[0].conversations[0].value);
    expect(data.TRAINING_RECORD.target).toBe(stored[0].conversations[1].value);
  });

  it.skipIf(!existsSync(FREEZE))("shows the verbatim record exactly as manifest.val.jsonl stores it", () => {
    const stored = readFileSync(path.join(FREEZE, "manifest.val.jsonl"), "utf8")
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line))
      .find((row) => row.pair_id === "033b8372e89e4c06");
    const shown = data.VERBATIM_RECORD as unknown as Record<string, unknown>;
    expect(Object.keys(shown)).toEqual(Object.keys(stored));
    // "…" stands for cut text: the head and the tail of the shown value must be the stored value's.
    const matches = (a: unknown, b: unknown): boolean => {
      if (typeof a === "string" && typeof b === "string") {
        if (!a.includes("…")) return a === b;
        const [head, tail] = a.split("…");
        return b.startsWith(head) && b.endsWith(tail) && b.length >= head.length + tail.length;
      }
      if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v, i) => matches(v, b[i]));
      return a === b;
    };
    for (const key of Object.keys(stored)) expect(matches(shown[key], stored[key]), key).toBe(true);
  });
});
