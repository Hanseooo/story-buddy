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

const guide = read(data.SOURCES.groupGuide);
const phase05 = flat(between(guide, "### 5.1 ", "### 5.2 "));
const pages = flat(between(guide, "### 5.3 ", "### 5.4 "));
const tried = between(guide, "### 5.4 ", "## 6. ");
const limitations = flat(between(guide, "## 6. ", "## 7. "));
const audit = flat(between(read(data.SOURCES.stageAudit), `## Provisional results — ${data.AUDIT.date}`, "## Deviation"));

describe("limitations page data", () => {
  // ADR-067 decision 3: a number on the page that its source does not print fails here.
  it("takes the audit's totals and its split by character kind from the group guide", () => {
    const { AUDIT: a, BY_KIND } = data;
    const [page, reference, duplicate] = BY_KIND;

    states(pages, `Every shipped page of the ${a.books} synthetic books was reviewed: ${a.pages} pages and ${a.references} references.`);
    states(pages, `About half the pages (${a.defective} of ${a.pages}) have at least one major defect.`);
    states(
      pages,
      `${page.nonHuman.part} of ${page.nonHuman.whole}, against ${page.human.part} of ${page.human.whole} for human characters.`
    );
    states(
      pages,
      `(${reference.human.part} of ${reference.human.whole} human references have a major defect, against ${reference.nonHuman.part} of ${reference.nonHuman.whole} non-human)`
    );
    states(
      pages,
      `duplicates (${duplicate.human.part} of ${duplicate.human.whole} human pages, against ${duplicate.nonHuman.part} of ${duplicate.nonHuman.whole})`
    );
    states(pages, `The audit tags ${page.nonHuman.whole} of ${a.pages} shipped pages as containing non-human characters, including mixed human and non-human casts; the other ${page.human.whole} pages are human-only.`);
  });

  it("gives each defect the count the stage audit prints and the description the guide gives", () => {
    states(audit, `Most common majors: ${data.DEFECTS.map((d) => `\`${d.code}\` ${d.pages}`).join(", ")}.`);
    for (const d of data.DEFECTS) expect(rows(between(guide, "### 5.3 ", "### 5.4 ")), d.name).toContain(`| ${d.name} | ${d.looksLike} |`);
  });

  it("takes what the two automatic checks did from the stage audit", () => {
    const { reference: r, page: p } = data.CHECKS;

    states(audit, `**References.** ${r.defective} of ${data.AUDIT.references} defective`);
    states(
      audit,
      `The stored reference gate failed ${r.defectiveFailed} of those ${r.defective} and also ${r.acceptableFailed} of the ${r.acceptable} acceptable references.`
    );
    states(
      audit,
      `Of the ${p.defective} defective shipped pages, ${p.defectivePassed} passed the stored gate; of the ${p.acceptable} acceptable, ${p.acceptableFailed} failed it.`
    );
  });

  it("takes both scene-editor comparisons from the group guide", () => {
    const { KLEIN: k, PHASE_05: p } = data;

    states(
      flat(tried),
      `On ${k.pages} random pages it drew as many duplicates as Qwen (${k.duplicates.klein} each) and lost character identity more often (${k.identityLost.klein} against ${k.identityLost.qwen}).`
    );
    expect(k.duplicates.qwen).toBe(k.duplicates.klein);
    states(phase05, `recognisable on ${p.qwen.withReference} of pages with its reference picture, and on ${p.qwen.without} without it.`);
    states(phase05, `(OmniGen2, Run 3) reached ${p.omnigen.withReference} against ${p.omnigen.without}.`);
  });

  // The guide restates these. The files that measured them have to print the same numbers.
  it("finds both scene-editor comparisons in the files that measured them", () => {
    const { KLEIN: k, PHASE_05: p } = data;
    const results = read(data.SOURCES.phase05);

    states(
      flat(read(data.SOURCES.probes)),
      `on ${k.pages} random scenes, klein drew as many duplicates as Qwen (${k.duplicates.klein} each) and lost identity on ${k.identityLost.klein} pages to Qwen's ${k.identityLost.qwen}`
    );
    states(between(results, "### Result — Run 2", "### Result — Run 3"), `| Quill | ${p.qwen.withReference} | ${p.qwen.without} |`);
    states(between(results, "### Result — Run 3", "### Secondary arm"), `| Quill | ${p.omnigen.withReference} | ${p.omnigen.without} |`);
  });

  // ADR-067 decision 4: the two lists are the guide's own rows and items, word for word.
  it("copies every row of the guide's table of what was tried", () => {
    const table = rows(tried).filter((row) => row.startsWith("| ") && !row.startsWith("| Tried") && !row.startsWith("|---"));

    expect(data.TRIED.map((t) => `| ${t.tried} | ${t.result} |`)).toEqual(table);
  });

  it("copies every limitation the guide lists, in order", () => {
    data.LIMITATIONS.forEach((l, index) => states(limitations, `${index + 1}. **${l.title}.** ${l.body}`));
    expect(limitations).not.toContain(`${data.LIMITATIONS.length + 1}. **`);
  });

  it("names sources that exist in the repository", () => {
    for (const file of Object.values(data.SOURCES)) expect(existsSync(path.join(REPO_ROOT, file)), file).toBe(true);
  });

  // ADR-065 decision 5: nothing here may name a donated story.
  it("names no donated story", () => {
    expect(JSON.stringify(data)).not.toMatch(/don-/i);
  });

  it("ships only local synthetic examples with tracked provenance", () => {
    expect(data.EXAMPLES.map((example) => example.storyId)).toEqual(["syn-021", "syn-002", "syn-019", "syn-016"]);
    const provenance = read(data.SOURCES.examples);
    for (const example of data.EXAMPLES) {
      expect(example.split).toBe("train");
      expect(provenance).toContain(example.storyId);
      expect(provenance).toContain(example.requirement);
      for (const image of example.images) {
        expect(image.src).toMatch(/^\/research\/(limitations|dataset)\/[^/]+\.webp$/);
        expect(image.alt.length).toBeGreaterThan(0);
        expect(existsSync(path.join(REPO_ROOT, "frontend/public", image.src)), image.src).toBe(true);
      }
    }
  });
});
