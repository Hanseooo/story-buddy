import { describe, expect, it } from "vitest";
import { canOpenRun, hideTitles, type ResearchViewer } from "./viewer";

const annotator: ResearchViewer = {
  id: "r-1", role: "researcher", isAdjudicator: false, displayName: null,
};
const adjudicator = { ...annotator, isAdjudicator: true };
const teacher = { ...adjudicator, role: "teacher" };

describe("canOpenRun", () => {
  it.each([
    ["signed out", null, false],
    ["annotator", annotator, true],
    ["adjudicator", adjudicator, true],
    ["teacher even with adjudicator flag", teacher, false],
    ["student", { ...annotator, role: "student" }, false],
  ] as const)("%s: can open %s", (_, viewer, allowed) => {
    expect(canOpenRun(viewer)).toBe(allowed);
  });
});

describe("hideTitles", () => {
  it("keeps a title only where the viewer can open the run, without mutating rows", () => {
    const rows = [
      { id: "a", title: "Approved Kite", approved_at: "2026-10-01" },
      { id: "b", title: "Unapproved Kite", approved_at: null },
    ];
    expect(hideTitles(annotator, rows).map((row) => row.title)).toEqual(["Approved Kite", "Unapproved Kite"]);
    expect(hideTitles(teacher, rows).map((row) => row.title)).toEqual([null, null]);
    expect(hideTitles(null, rows).map((row) => row.title)).toEqual([null, null]);
    expect(rows[1].title).toBe("Unapproved Kite");
  });
});
