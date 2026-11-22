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

// Ticket 08: the November state, with every count pinned to the file that holds it (SH-02).
const probes = flat(read(data.SOURCES.probes));
const adr056 = flat(read(data.SOURCES.adr056));
const adr082 = flat(read(data.SOURCES.adr082));
const referenceJudge = flat(read(data.SOURCES.referenceJudge));
const readiness = flat(read(data.SOURCES.readiness));
const changelog = flat(read(data.SOURCES.changelog));
const stageAudit = flat(read(data.SOURCES.stageAudit));
const adr068 = flat(read(data.SOURCES.adr068));

describe("limitations page November data", () => {
  it("adds up the page-check totals: 77 + 71 + 2 = 150", () => {
    const a = data.AUDIT;

    expect([a.defective, a.acceptable, a.uncertain]).toEqual([77, 71, 2]);
    expect(77 + 71 + 2).toBe(a.pages);
    states(stageAudit, `${a.defective} of ${a.pages} have at least one major defect, ${a.acceptable} are acceptable, ${a.uncertain} uncertain.`);
    expect(data.CHECK_SENTENCES.totals).toBe("77 of 150 have a major defect, 71 are acceptable and 2 are uncertain.");
  });

  it("states the reference check as the stage audit and ADR-082 do", () => {
    states(adr082, "The reference checker wrongly fails about 4 in 10 clean references.");
    states(stageAudit, "`char_bible` ships the best failing draw, so every detected defect still reached the pages.");
    expect(data.CHECK_SENTENCES.reference).toBe(
      "The check fails most bad references (15 of 17), but it also fails about 4 in 10 good ones (15 of 38). The pipeline then ships the best of the failing draws, so every defect it found still reached the pages."
    );
  });

  it("states the page check with its wasted redraws", () => {
    states(stageAudit, "23 of the 71 rejected first draws were acceptable");
    expect(data.CHECKS.page.rejectedFirstDrafts).toEqual({ whole: 71, acceptable: 23 });
    expect(data.CHECK_SENTENCES.page).toContain("29 of the 77 defective pages through");
    expect(data.CHECK_SENTENCES.page).toContain("28 of the 71 acceptable ones");
    expect(data.CHECK_SENTENCES.page).toContain("23 of the 71 redrawn first drafts were already acceptable");
  });

  it("counts duplicates on redrawn drafts and on finished pages", () => {
    states(probes, "| Duplicate character | 28 of 221 (13%);");
    states(stageAudit, "`duplicate_character` 15");
    expect(data.LIMITATIONS[0].body).toContain("About 13% of page images, counting redrawn drafts (28 of 221), show a character twice. On finished pages it is 15 of 150.");
  });

  it("adds the klein action count and names the one rater", () => {
    states(probes, "| Action | 2 | 8 |");
    expect(data.KLEIN.action).toEqual({ qwen: 2, klein: 8 });
    states(probes, "one rater (the assistant, looking at each image)");
    expect(data.KLEIN_NOTES.rater).toBe("Scored by one rater, the AI assistant, with the editor's name hidden.");
  });

  it("records the November probe that failed, and the magic pencil as shipped and on by default", () => {
    states(probes, "an edit with only the chip's wording fixed 2 of 9 count misses, against 5 of 9 with hand-written change instructions");
    states(probes, "failed the 6-of-9 rule");
    states(changelog, "are now on by default");
    states(changelog, "Every use is logged with redacted text only");
    const chip = data.TRIED.find((t) => t.tried.startsWith("Editing the reference with only the tapped chip"))!;
    expect(chip).toMatchObject({ outcome: "Rejected" });
    expect(chip.result).toContain("2 of 9 fixed, against 5 of 9 with hand-written instructions");
    const counts = data.LIMITATIONS.find((l) => l.title === "Stated body counts")!;
    expect(counts.body).toContain("only 2 of 9 with the chip's own words");
    expect(counts.body).toContain("on by default since 2026-11-21");
    expect(counts.body).toContain("unmeasured");
  });

  it("says generation versions 6 and 7 and 500-word stories are unmeasured", () => {
    states(changelog, "generation version 6");
    states(changelog, "Generation version 7");
    states(changelog, "Quality at the larger input ceiling is unmeasured");
    states(adr068, "500 words");
    expect(data.AUDIT_NOTE).toContain("generation versions 6 and 7");
    expect(data.AUDIT_NOTE).toContain("500-word");
    expect(data.AUDIT_NOTE).toContain("magic pencil");
  });

  it("adds the reference check's blind spot as two new limitations, with its measured cause", () => {
    const l = data.LIMITATIONS.find((x) => x.title === "The reference check cannot verify stated details")!;
    expect(data.LIMITATIONS).toHaveLength(11);
    expect(l.body).toContain("metal comb");
    states(referenceJudge, "demands *metal beak and comb*");
    states(referenceJudge, "bright yellow beak");
    states(adr056, "it listed `\"six legs\"` in `attributes_present`");
    states(adr056, "The gap is what the task compares.");
  });

  it("states the backstop's measured stop count and nothing about human review (D-23)", () => {
    const l = data.LIMITATIONS.find((x) => x.title === "Safety checks sometimes refuse harmless stories")!;
    expect(l.body).toContain("4 of 30 synthetic stories");
    states(readiness, "All four `output_moderation_failed` quarantines carry the same shape: `backstop (primary said safe) after retry`.");
    states(readiness, "The primary classifier cleared every one of them.");
    states(readiness, "On the fourth round s0 passed moderation unaided");
    expect(JSON.stringify(data)).not.toMatch(/human review|reviewed the stored images|operator/i);
  });

  it("gives the groups-with-no-reference limit its measured rate", () => {
    states(probes, "17 of 150 scenes direct them; those scenes ship a duplicate or extra on 24% of pages, against 10% elsewhere");
    states(probes, "dust-bunny soldiers came out as human boys");
    const l = data.LIMITATIONS.find((x) => x.title === "Characters with no reference")!;
    expect(l.body).toContain("24% of pages, against 10% elsewhere");
  });

  it("names a stable id and a PNG for each outcome chart", () => {
    expect(data.CHARTS.map((c) => c.id)).toEqual(["reference-check-outcomes", "page-check-outcomes"]);
    for (const c of data.CHARTS) expect(c.png).toBe(`/research/diagrams/${c.id}.png`);
    expect(data.CHARTS_AS_OF).toBe(data.AUDIT.date);
  });
});
