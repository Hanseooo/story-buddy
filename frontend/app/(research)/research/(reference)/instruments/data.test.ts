import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import * as data from "./data";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
const raw = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8");
// Wrapped lines joined. Bold marks stay, so a heading is pinned as a heading.
const flat = (text: string) => text.replace(/\s+/g, " ");
// Fails with the missing sentence as its message, not with the whole document.
const states = (text: string, sentence: string) => expect(text.includes(sentence), sentence).toBe(true);

const expertRaw = raw(data.SOURCES.expert);
const isoRaw = raw(data.SOURCES.iso);
const expert = flat(expertRaw);
const iso = flat(isoRaw);
const spec = flat(raw(data.SOURCES.spec));

describe("instruments page data: expert questionnaire", () => {
  it("lists the seven question headings and their prompts word for word", () => {
    expect(data.QUESTIONS).toHaveLength(7);
    expect(data.QUESTIONS[0].heading).toBe("How appropriate and meaningful is the generated picture book for its intended readers?");
    for (const q of data.QUESTIONS) states(expert, `${q.n}. **${q.heading}** ${q.prompt}`);
  });

  it("has no more and no fewer questions than the tracked form", () => {
    const section = expertRaw.slice(expertRaw.indexOf("**III. Questions.**"), expertRaw.indexOf("**Additional comments:**"));
    expect(section.match(/^\d+\. \*\*/gm)).toHaveLength(7);
  });

  it("takes who, how and the answer style from the tracked form", () => {
    for (const s of [data.EXPERT.evaluators, data.EXPERT.procedure, data.EXPERT.format, data.EXPERT.answerStyle]) states(expert, s);
  });

  it("leaves the analysis method undecided, as the spec words it", () => {
    expect(data.ANALYSIS_TBD).toBe("Content analysis or thematic analysis (to be decided)");
    states(spec, `"${data.ANALYSIS_TBD}"`);
  });
});

describe("instruments page data: ISO/IEC 25010 questionnaire", () => {
  it("lists 23 items under six headings, each word for word and in order", () => {
    expect(data.ISO_GROUPS.map((g) => g.items.length)).toEqual([5, 4, 5, 3, 4, 2]);
    expect(data.ISO_GROUPS.flatMap((g) => g.items).map((i) => i.n)).toEqual(Array.from({ length: 23 }, (_, i) => i + 1));
    for (const g of data.ISO_GROUPS) {
      states(iso, `**${g.letter}. ${g.name}** — ${g.description} ${g.items[0].n}. `);
      for (const i of g.items) states(iso, `${i.n}. ${i.text}`);
    }
  });

  it("has no more and no fewer items than the tracked form", () => {
    const section = isoRaw.slice(isoRaw.indexOf("**A. Functional Suitability**"));
    expect(section.match(/^\d+\. /gm)).toHaveLength(23);
  });

  it("takes scale, respondents and statistics from the tracked form", () => {
    for (const s of [data.ISO.scale, data.ISO.rating, data.ISO.respondents, data.ISO.statistics, data.ISO.consent]) states(iso, s);
  });
});

describe("both instruments", () => {
  it("are pending until a survey is run", () => {
    expect(data.PENDING).toBe("Survey pending");
    for (const doc of [expert, iso]) states(doc, `No survey has been run yet (D-10, "${data.PENDING}").`);
  });
});
