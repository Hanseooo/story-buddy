import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { CHANGELOG_POINTS, PAPER_CORRECTIONS, PAPER_TYPOS } from "./paper";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
const squash = (text: string) => text.replace(/\s+/g, " ");
const read = (file: string) => squash(readFileSync(path.join(REPO_ROOT, file), "utf8"));
const CHANGELOG = "docs/capstone/research-changelog.md";

const pinCases = PAPER_CORRECTIONS.flatMap((c) =>
  c.pins.map((pin) => ({ name: `${c.id} ${pin.has !== undefined ? "has" : "lacks"} "${pin.has ?? pin.lacks}" in ${pin.file}`, pin }))
);

describe("what the paper must say: source pins (SH-02)", () => {
  it("covers every audit row P1 to P24 once, plus the second source conflict C1", () => {
    const ids = PAPER_CORRECTIONS.map((c) => c.id);
    const expected = [...Array.from({ length: 24 }, (_, i) => `P${i + 1}`), "C1"];
    expect([...ids].sort()).toEqual([...expected].sort());
  });

  it.each(pinCases.map((c) => [c.name, c.pin] as const))("%s", (_name, pin) => {
    const source = read(pin.file);
    if (pin.has !== undefined) expect(source).toContain(squash(pin.has));
    else expect(source.toLowerCase()).not.toContain(pin.lacks!.toLowerCase());
  });

  it("gives every correction a settled value, 'repo is right', or an open flag, with a source", () => {
    for (const c of PAPER_CORRECTIONS) {
      expect(["settled", "repo-right", "open", "unconfirmed"]).toContain(c.status);
      expect(c.pins.length).toBeGreaterThan(0);
    }
  });

  it("settles the donated-story conflicts for the repo, with the 12 and the reason the three were left out", () => {
    const donated = PAPER_CORRECTIONS.find((c) => c.id === "P6")!;
    expect(donated.status).toBe("repo-right");
    expect(donated.value).toMatch(/13/);
    expect(donated.value).toMatch(/12/);
    const threeLeftOut = PAPER_CORRECTIONS.find((c) => c.id === "C1")!;
    expect(threeLeftOut.status).toBe("repo-right");
    expect(threeLeftOut.value).toMatch(/invalid_terminal/);
    expect(threeLeftOut.value).toMatch(/budget_stopped/);
  });

  it("leaves only O-04, O-07 and O-12 open", () => {
    expect(PAPER_CORRECTIONS.filter((c) => c.status === "open").map((c) => c.open?.id).sort()).toEqual([
      "O-04",
      "O-07",
      "O-12",
    ]);
  });

  it("shows P7 and P24 as unconfirmed, with no issue link", () => {
    const unconfirmed = PAPER_CORRECTIONS.filter((c) => c.status === "unconfirmed");
    expect(unconfirmed.map((c) => c.id).sort()).toEqual(["P24", "P7"]);
    for (const c of unconfirmed) expect(c.open).toBeUndefined();
    expect(PAPER_CORRECTIONS.find((c) => c.id === "P24")!.pins.map((p) => p.file)).toContain(
      "docs/capstone/research_runbook.md"
    );
  });

  it("links the open owner decisions to their GitHub issues", () => {
    const issues = Object.fromEntries(PAPER_CORRECTIONS.flatMap((c) => (c.open ? [[c.open.id, c.open.url]] : [])));
    expect(issues).toEqual({
      "O-04": "https://github.com/Hanseooo/story-buddy/issues/135",
      "O-07": "https://github.com/Hanseooo/story-buddy/issues/136",
      "O-12": "https://github.com/Hanseooo/story-buddy/issues/137",
    });
  });
});

describe("research-changelog.md section 1", () => {
  it("lists all nine points, each worded as in the changelog", () => {
    expect(CHANGELOG_POINTS).toHaveLength(9);
    const changelog = read(CHANGELOG);
    for (const point of CHANGELOG_POINTS) expect(changelog).toContain(squash(point));
  });
});

describe("paper typos", () => {
  it("lists the four typos with the corrected form", () => {
    expect(PAPER_TYPOS.map((t) => t.wrong)).toEqual(["Visibile", "Cohen's Cappa", "considerable", "31%"]);
    expect(PAPER_TYPOS.map((t) => t.right)).toEqual(["Visible", "Cohen's Kappa", "substantial", "0.310"]);
  });

  it("pins the corrected numbers to the runbook", () => {
    const runbook = read("docs/capstone/research_runbook.md");
    expect(runbook).toContain("0.634");
    expect(runbook).toContain("0.310");
  });
});
