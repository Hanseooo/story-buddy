import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { TRADEOFF } from "../results/data";
import * as data from "./data";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
const read = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8");
const flat = (text: string) => text.replace(/\s+/g, " ");
const states = (text: string, sentence: string) => expect(flat(text).includes(sentence), sentence).toBe(true);

const goals = read(data.SOURCES.goals);
const objectivesSection = flat(goals.slice(goals.indexOf("## Objectives"), goals.indexOf("## 2. How StoryBuddy solves it"))).replace(/\*\*/g, "");

describe("objectives page data", () => {
  // AC-10: the wording is the manuscript's, pinned to research_direction_and_goals.md.
  it("words the five objectives as the goals doc does, in its order", () => {
    expect(data.OBJECTIVES.map((o) => o.n)).toEqual([1, 2, 3, 4, 5]);
    for (const o of data.OBJECTIVES) states(objectivesSection, `${o.n}. ${o.text}`);
    expect(objectivesSection.indexOf("1. Implement")).toBeLessThan(objectivesSection.indexOf("5. Evaluate the software quality"));
  });

  it("hand-checks the five wordings against the manuscript's verbs", () => {
    expect(data.OBJECTIVES.map((o) => o.text.split(" ")[0])).toEqual(["Implement", "Produce", "Determine", "Evaluate", "Evaluate"]);
  });

  // AC-11: every objective links to the chapter page that explains it, and its evidence points at tracked files.
  it("links evidence to tracked files and each objective to a research page", () => {
    for (const o of data.OBJECTIVES) {
      expect(o.explained.href, `${o.n}`).toMatch(/^\/research\/[a-z]+$/);
      for (const e of o.evidence) expect(existsSync(path.join(REPO_ROOT, e.path)), e.path).toBe(true);
    }
    expect(data.OBJECTIVES.map((o) => o.explained.href)).toEqual([
      "/research/pipeline",
      "/research/methodology",
      "/research/instruments",
      "/research/results",
      "/research/instruments",
    ]);
  });

  // AC-12, D-20.
  it("answers Objective 1 Achieved from the graph, the 42 books and the passing tests, with no Tool A", () => {
    const o = data.OBJECTIVES[0];
    expect(o.answer.lead).toBe("Achieved.");
    expect((read("backend/pipeline/graph.py").match(/\.add_node\(/g) ?? []).length).toBe(14);
    expect(o.answer.body.join(" ")).toContain("LangGraph graph of 14 nodes (11 in baseline mode)");
    states(read("docs/specs/research-page-refresh.md"), "the passing automated tests");
    states(read("docs/capstone/group-guide.md"), "The research corpus holds 42 generated books: 30 from synthetic stories and 12 from donated stories.");
    expect(o.evidence.map((e) => e.path)).toContain("backend/pipeline/graph.py");
    expect(JSON.stringify(data.OBJECTIVES)).not.toMatch(/Tool A/);
  });

  // AC-13: the corpus counts, and the three donated stories that did not finish, in the sourced wording.
  it("answers Objective 2 with 42 books, 30 synthetic and 12 donated, and the three that did not finish", () => {
    const o = data.OBJECTIVES[1];
    expect(o.answer.lead).toBe("42 digital picture books were produced through the pipeline: 30 from synthetic stories and 12 from donated stories.");
    const body = o.answer.body.join(" ");
    expect(body).toContain("Fifteen donated stories were collected and twelve were generated into books.");
    expect(body).toContain("did not finish (two invalid_terminal, one budget_stopped)");
    expect(body).not.toMatch(/backup stories/i);

    const methodology = read(data.SOURCES.methodology);
    states(methodology, "fifteen collected, of which twelve were generated into books and three were left out on purpose (two `invalid_terminal`, one `budget_stopped`;");
    states(methodology, "three stay quarantined on purpose, because 12 clear the held-out floor");
    states(read(data.SOURCES.changelog), "Corpus generated: 42 books (30 synthetic, 12 donated), about USD 30; three donated stories left out on purpose");
    const audit = flat(read(data.SOURCES.readiness));
    states(audit, "don-006 and don-015 (`invalid_terminal`), don-013 (`budget_stopped`)");
  });

  // AC-14, SH-07, D-10: nothing but the two words.
  it("shows Survey pending for Objectives 3 and 5 and nothing else", () => {
    for (const i of [2, 4]) {
      expect(data.OBJECTIVES[i].answer).toEqual({ lead: "Survey pending", body: [] });
      expect(data.OBJECTIVES[i].evidence).toEqual([]);
    }
  });

  // AC-15: the registered comparison, the verbatim tradeoff sentence and the partial note.
  it("answers Objective 4 with the F1 result, the tradeoff sentence verbatim and the partial note", () => {
    const o = data.OBJECTIVES[3];
    expect(o.answer.lead).toBe("The fine-tuned judge did not beat its untrained base on F1 (0.31 vs 0.47).");
    expect(o.answer.body).toContain(TRADEOFF);
    states(read(data.SOURCES.groupGuide), TRADEOFF);
    expect(TRADEOFF).toContain("(0.31 vs 0.47)");
    const partial = o.answer.body.find((s) => s.startsWith("The comparison is partial"));
    expect(partial).toBe(
      "The comparison is partial. The prompted Gemma baseline failed authentication, and paid evaluation stopped for budget. No claim-ladder or product-gate decision was made."
    );
    states(read(data.SOURCES.changelog), "The prompted Gemma baseline failed authentication, and paid evaluation stopped for budget.");
    states(read(data.SOURCES.changelog), "No claim-ladder or product-gate decision was made.");
  });
});
