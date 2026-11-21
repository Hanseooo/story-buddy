import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { READING_ORDER, RESEARCH_PAGES, neighbours } from "./readingOrder";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const read = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8");
const APP_RESEARCH = path.resolve(__dirname, "../research");

const spec = read("docs/specs/research-page-refresh.md");

// Index 4.1: rows of | Group | Page | `route` | ... |, in the order the spec lists them.
const SPEC_ROWS = [...spec.matchAll(/^\| (Methodology|Results|Reference) \| ([^|]+?) \| `([^`]+)` \|/gm)].map((m) => ({
  group: m[1],
  title: m[2].replace(/ \(sign-in\)$/, ""),
  href: m[3],
}));

describe("research page list", () => {
  // SH-04 / US-01 AC-01, AC-02: one list, in the order of index 4.1.
  it("holds the pages of index section 4.1, in that order, with their groups", () => {
    expect(SPEC_ROWS).toHaveLength(11);
    expect(RESEARCH_PAGES.map(({ group, title, href }) => ({ group, title, href }))).toEqual(SPEC_ROWS);
  });

  it("has a page file for every route", () => {
    for (const { href } of RESEARCH_PAGES) {
      const dir = href.replace("/research/", "");
      const found = ["", "(reference)/"].some((prefix) => existsSync(path.join(APP_RESEARCH, prefix, dir, "page.tsx")));
      expect(found, href).toBe(true);
    }
  });

  it("puts Runs outside the reading order and keeps the other ten in it", () => {
    expect(READING_ORDER.map((p) => p.href)).toEqual(SPEC_ROWS.filter((r) => r.href !== "/research/metrics").map((r) => r.href));
    expect(READING_ORDER).toHaveLength(10);
  });

  // US-01 AC-03: every hub entry has one line and names the paper sections it feeds. Each name is in the audit's paper map.
  it("gives every entry one line and paper sections found in the audit's paper map", () => {
    const audit = (
      read("docs/specs/research-page-refresh/evidence/audit-3-docs-paper.md") +
      read("docs/specs/research-page-refresh/evidence/audit-1-dataset.md")
    ).toLowerCase();
    for (const page of RESEARCH_PAGES) {
      expect(page.line.length, page.href).toBeGreaterThan(10);
      for (const section of page.paper) expect(audit, `${page.href}: ${section}`).toContain(section.toLowerCase());
    }
  });
});

describe("neighbours", () => {
  it("gives the first page no Previous and the last page no Next", () => {
    expect(neighbours("/research/pipeline")).toEqual({ previous: null, next: READING_ORDER[1] });
    expect(neighbours("/research/docs")).toEqual({ previous: READING_ORDER[8], next: null });
  });

  it("names the neighbours of a middle page by the order, not by the alphabet", () => {
    const { previous, next } = neighbours("/research/dataset");
    expect(previous?.href).toBe("/research/methodology");
    expect(next?.href).toBe("/research/instruments");
    expect(neighbours("/research/objectives").next?.href).toBe("/research/results");
    expect(neighbours("/research/limitations").next?.href).toBe("/research/docs");
  });

  it("has no neighbours for the hub, Runs or a page outside the order", () => {
    for (const p of ["/research", "/research/metrics", "/research/metrics/abc", "/nowhere"]) {
      expect(neighbours(p), p).toEqual({ previous: null, next: null });
    }
  });
});
