import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import * as data from "./data";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
const read = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8");

// The part of a document from one marker up to the next, so a value is looked for in its own section.
function between(text: string, start: string, end: string) {
  const from = text.indexOf(start);
  const to = text.indexOf(end, from + start.length);
  expect(from, start).toBeGreaterThan(-1);
  expect(to, end).toBeGreaterThan(from);
  return text.slice(from, to);
}
const rows = (section: string) => section.split(/\r?\n/).map((line) => line.trim());
const flat = (section: string) => section.replace(/\s+/g, " ");
// Fails with the missing sentence as its message, not with the whole document.
const states = (text: string, sentence: string) => expect(text.includes(sentence), sentence).toBe(true);

const runbook = read(data.SOURCES.runbook);
const exact = between(runbook, "#### Exact values of the partial comparison", "### Verification sources");
const sensitivity = between(runbook, "**Secondary sensitivity analysis**", "**Limitations.**");
const settings = between(runbook, "#### Registered training settings", "### Verification sources");

// The page's name for each judge, and the first cell of its row in the runbook's two tables.
const RUNBOOK_ROW: Record<string, [exact: string, sensitivity: string]> = {
  "Untrained Qwen3.5-9B": ["Untuned Qwen3.5-9B", "Untuned"],
  "Trained, seed 1 (picked in advance)": ["Seed 1 (preselected)", "Seed 1 (preselected)"],
  "Trained, seed 0": ["Seed 0", "Seed 0"],
  "Trained, seed 2": ["Seed 2", "Seed 2"],
};

describe("results page data", () => {
  // ADR-066 decision 6: a value on the page that is not in the runbook fails here.
  it("gives each judge the row the runbook's table of exact values has", () => {
    expect(data.JUDGES.map((judge) => judge.name)).toEqual(Object.keys(RUNBOOK_ROW));
    for (const j of data.JUDGES) {
      expect(rows(exact), j.name).toContain(
        `| ${RUNBOOK_ROW[j.name][0]} | ${j.f1} | ${j.f1Interval} | ${j.precision} | ${j.recall} | ${j.caught} | ${j.missed} | ${j.falseAlarms} | ${j.correctSame} | ${j.unreadable} |`
      );
    }
  });

  it("gives each judge the row the runbook's sensitivity table has", () => {
    for (const { name, sensitivity: s } of data.JUDGES) {
      expect(rows(sensitivity), name).toContain(`| ${RUNBOOK_ROW[name][1]} | ${s.f1} | ${s.precision} | ${s.recall} |`);
    }
  });

  it("takes the comparison, the seed summary and the validation figures from the runbook", () => {
    const { TEST, COMPARISON: c, SEEDS, VALIDATION: v, SENSITIVITY: s } = data;
    const [, seed1, seed0, seed2] = data.JUDGES;
    const table = flat(exact);

    states(runbook, `### Partial untuned versus fine-tuned comparison (${data.RESULT_DATE})`);
    states(table, `Test slice: ${TEST.pairs} pairs, ${TEST.different} Different and ${TEST.same} Same.`);
    states(
      table,
      `Seed 1 minus untuned: ΔF1 ${c.deltaF1}, 95% character-clustered interval ${c.interval}, exact McNemar p = ${c.mcnemarP}. Intervals use ${data.RESAMPLES} resamples clustered by character.`
    );
    states(table, `The three seeds: mean F1 ${SEEDS.meanF1}, sample SD ${SEEDS.sampleSd}.`);
    states(
      table,
      `seed 0 \`checkpoint-${seed0.checkpoint}\` ${seed0.validationF1}, seed 1 \`checkpoint-${seed1.checkpoint}\` ${seed1.validationF1}, seed 2 \`checkpoint-${seed2.checkpoint}\` ${seed2.validationF1}. The validation split has ${v.different} Different pairs out of ${v.pairs}`
    );
    states(flat(sensitivity), `so ${s.droppedPairs} pairs were dropped: n = ${s.pairs}, ${s.different} Different`);
    states(
      flat(sensitivity),
      `Seed 1 minus untuned: ΔF1 ${s.deltaF1}, 95% character-clustered CI ${s.interval}, exact McNemar p = ${s.mcnemarP}.`
    );
  });

  // ADR-066 decision 8: the reading of McNemar's p is arithmetic on the table, and the runbook states it.
  it("derives the error counts the runbook derives", () => {
    const [untrained, seed1] = data.JUDGES;
    const table = flat(exact);
    const said = (j: data.Judge) => `called ${data.calledDifferent(j)} pairs Different and was wrong on ${data.wrong(j)}`;
    const errors = (j: data.Judge) => `(${j.falseAlarms} false alarms, ${j.missed} misses)`;

    states(table, `the untuned model ${said(untrained)} pairs ${errors(untrained)}`);
    states(table, `Seed 1 ${said(seed1)} ${errors(seed1)}`);
    states(table, `seed 1 being wrong on ${data.wrong(untrained) - data.wrong(seed1)} fewer pairs`);
  });

  // ADR-066 amendment (a): a setting on the page is in the runbook's table and in the config itself.
  it("takes each training setting from the runbook and from the config", () => {
    const config = rows(read(data.SOURCES.trainConfig));

    for (const { key, value } of data.TRAINING_SETTINGS) {
      expect(rows(settings), key).toContain(`| \`${key}\` | ${value} |`);
      expect(config.some((line) => line === `${key}: ${value}` || line.startsWith(`${key}: ${value} `)), key).toBe(true);
    }
    // Typed by hand from train_qlora.yaml.
    expect(data.TRAINING_SETTINGS.map(({ key, value }) => `${key}=${value}`)).toEqual(
      expect.arrayContaining(["num_train_epochs=3.0", "learning_rate=1.0e-4", "lora_rank=16", "save_steps=10"])
    );
  });

  it("takes the training length, the cap and the story mix from the files it cites", () => {
    const { TRAIN, TRAINING: t } = data;

    states(
      flat(settings),
      `Training length: ${t.updatesPerEpoch} updates per epoch, ${t.updatesPerSeed} per seed, on the ${TRAIN.records} training records.`
    );
    states(flat(settings), `capped at ${t.generationCap} tokens`);
    states(flat(runbook), `All ${TRAIN.constructed} constructed pairs carry the one reason`);
    states(flat(read(data.SOURCES.groupGuide)), `The synthetic stories are ${t.syntheticNonHuman} non-human`);
    expect(t).toMatchObject({ updatesPerEpoch: 61, updatesPerSeed: 183, generationCap: 256 });
  });

  it("takes the rest from the files it cites", () => {
    const { AGREEMENT: a, CONTRADICTION: c, TEST, TRAIN } = data;

    expect(rows(runbook)).toContain(`| Test slice (registered number) | ${TEST.pairs} | ${a.kappa} | ${a.agreement} |`);
    expect(rows(runbook).some((row) => row.startsWith("| Train (synthetic) |") && row.endsWith(`| ${TRAIN.records} | 327 | ${TRAIN.different} | ${TRAIN.constructed} |`))).toBe(true);
    states(
      flat(runbook),
      `${c.pairs} of the ${TRAIN.constructed} constructed pairs, ${c.records} of the ${TRAIN.records} training records`
    );
    states(flat(read(data.SOURCES.groupGuide)), `Seeds 0 and 1 gave unreadable answers on ${data.UNREADABLE_SHARE}`);
  });

  // Typed by hand from the runbook's table, not computed.
  it("holds the values of the untrained model and of seed 1", () => {
    const [untrained, seed1] = data.JUDGES;

    expect(untrained).toMatchObject({ name: "Untrained Qwen3.5-9B", f1: "0.472", caught: 29, falseAlarms: 47, unreadable: 3 });
    expect(seed1).toMatchObject({
      name: "Trained, seed 1 (picked in advance)",
      f1: "0.310",
      caught: 9,
      missed: 38,
      falseAlarms: 2,
      unreadable: 40,
    });
    for (const judge of data.JUDGES) {
      expect(judge.caught + judge.missed, judge.name).toBe(47);
      expect(judge.falseAlarms + judge.correctSame, judge.name).toBe(282);
    }
  });

  // ADR-066 decision 9: test material stays aggregate.
  it("names no donated story", () => {
    expect(JSON.stringify(data)).not.toMatch(/don-/i);
  });

  it("cites only files that are in the repository", () => {
    for (const file of Object.values(data.SOURCES)) {
      expect(existsSync(path.join(REPO_ROOT, file)), file).toBe(true);
    }
  });
});
