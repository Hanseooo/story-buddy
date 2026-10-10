import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import * as data from "./data";

const FRONTEND = path.resolve(__dirname, "../../../../..");
const REPO_ROOT = path.resolve(FRONTEND, "..");
const IMAGE_DIR = path.join(FRONTEND, "public/research/dataset");
const FREEZE = path.join(REPO_ROOT, "data/judge/freezes/obj4-v1");

describe("dataset page data", () => {
  // ADR-065 decision 5: donated material appears only as whole-split counts.
  it("names no donated story, in the data or in an image filename", () => {
    expect(JSON.stringify(data)).not.toMatch(/don-/i);
    expect(readdirSync(IMAGE_DIR).join("\n")).not.toMatch(/don-/i);
  });

  it("matches the totals in the runbook's freeze table", () => {
    const sum = (key: "pairs" | "same" | "different" | "constructed") =>
      data.SPLITS.reduce((total, split) => total + split[key], 0);

    expect(data.SPLITS.map((split) => split.pairs)).toEqual([484, 86, 329]);
    expect([sum("pairs"), sum("same"), sum("different"), sum("constructed")]).toEqual([899, 691, 208, 104]);
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
});
