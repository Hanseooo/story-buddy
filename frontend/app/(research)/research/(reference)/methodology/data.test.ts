import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import * as data from "./data";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
// One line of text: wrapped lines joined, and the bold and italic marks of the source dropped.
const read = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8").replace(/\*+/g, "").replace(/\s+/g, " ");
// Fails with the missing sentence as its message, not with the whole document.
const states = (text: string, sentence: string) => expect(text.includes(sentence), sentence).toBe(true);

const methodology = read(data.SOURCES.methodology);
const ethics = read(data.SOURCES.ethics);
const guide = read(data.SOURCES.groupGuide);
const expert = read(data.SOURCES.expert);
const iso = read(data.SOURCES.iso);

describe("methodology page data", () => {
  it("takes the research design from methodology.md", () => {
    for (const part of data.DESIGN.parts) states(methodology, part);
    for (const procedure of data.DESIGN.procedures) states(methodology, procedure);
    states(methodology, data.SPIRAL.definition);
  });

  it("names the source school and the teacher's consent form", () => {
    states(methodology, data.SETTING.school);
    states(methodology, data.SETTING.development);
    states(ethics, data.SETTING.agreement);
    expect(data.SETTING.school).toBe("Stories are collected at Vicente Hizon, Sr. Elementary School");
  });

  it("shows both implementation sites as undecided", () => {
    states(methodology, "Implementation site (undecided; D-16, O-07).");
    states(methodology, data.SITES.a);
    states(methodology, data.SITES.b);
    expect(data.SITES.b).toBe("Option B: HCDC, with 40 School of Teacher Education (STE) students.");
  });

  it("states each corpus count where its source does", () => {
    expect(data.CORPUS.map((c) => c.count)).toEqual([15, 12, 30, 42]);
    for (const c of data.CORPUS) states(c.source === "groupGuide" ? guide : methodology, c.sentence);
  });

  it("takes the respondent groups from the two questionnaire docs", () => {
    states(expert, data.RESPONDENTS.expert);
    states(iso, data.RESPONDENTS.iso);
  });
});
