import { describe, expect, it } from "vitest";
import { canOpenRun, hideTitles, type ResearchViewer } from "./viewer";

const annotator: ResearchViewer = {
  id: "r-1", role: "researcher", isAdjudicator: false, displayName: null,
};
const adjudicator = { ...annotator, isAdjudicator: true };
const teacher = { ...adjudicator, role: "teacher" };
const approved = { approved_at: "2026-10-01" };
const unapproved = { approved_at: null };

describe("canOpenRun", () => {
  it.each([
    ["signed out", null, false, false],
    ["annotator", annotator, true, false],
    ["adjudicator", adjudicator, true, true],
    ["teacher even with adjudicator flag", teacher, false, false],
    ["student", { ...annotator, role: "student" }, false, false],
  ] as const)("%s: approved %s, unapproved %s", (_, viewer, onApproved, onUnapproved) => {
    expect(canOpenRun(viewer, approved)).toBe(onApproved);
    expect(canOpenRun(viewer, unapproved)).toBe(onUnapproved);
  });
});

describe("hideTitles", () => {
  it("keeps a title only where the viewer can open the run, without mutating rows", () => {
    const rows = [
      { id: "a", title: "Approved Kite", ...approved },
      { id: "b", title: "Unapproved Kite", ...unapproved },
    ];
    expect(hideTitles(annotator, rows).map((row) => row.title)).toEqual(["Approved Kite", null]);
    expect(hideTitles(null, rows).map((row) => row.title)).toEqual([null, null]);
    expect(rows[1].title).toBe("Unapproved Kite");
  });
});
