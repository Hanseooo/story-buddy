import { describe, expect, it } from "vitest";
import { computeAggregates, failedSplit, filterJobs, JobRow, parseRunFilter, styleBreakdown } from "@/utils/metrics";

const run = (over: Partial<JobRow>): JobRow => ({ id: "x", status: "complete", created_at: "2026-10-01", ...over });

describe("new aggregates", () => {
  it("splits failures by reason, counting a missing reason", () => {
    const jobs = [
      run({ status: "failed", failure_reason: "machine" }),
      run({ status: "failed", failure_reason: "machine" }),
      run({ status: "failed", failure_reason: "machine" }),
      run({ status: "failed", failure_reason: "machine" }),
      run({ status: "failed", failure_reason: "child_text" }),
      run({ status: "failed", failure_reason: null }),
    ];
    const stats = computeAggregates(jobs);

    expect(stats.failedByReason).toEqual({ machine: 4, child_text: 1, unrecorded: 1 });
    expect(failedSplit(stats.failedByReason)).toBe("4 pipeline error · 1 content blocked · 1 no reason recorded");
  });

  it("sums unchecked pages and divides images by pages where both are set", () => {
    const stats = computeAggregates([
      run({ scenes_unchecked: 2, image_count: 9, scenes_total: 6 }),
      run({ scenes_unchecked: 1, image_count: 4, scenes_total: 4 }),
      run({ scenes_unchecked: null, image_count: 5, scenes_total: null }),
    ]);

    expect(stats.uncheckedPages).toBe(3);
    expect(stats.imagesPerPage).toBe(1.3);
    expect(stats.pagesTotal).toBe(10);
  });

  it("has no images-per-page figure before any page is drawn", () => {
    const stats = computeAggregates([run({ status: "failed", failure_reason: "machine" })]);

    expect(stats.imagesPerPage).toBeNull();
    expect(stats.uncheckedPages).toBe(0);
  });
});

describe("styleBreakdown", () => {
  it("groups by style with No style last", () => {
    const rows = styleBreakdown([
      run({ style_preset_id: "cel", status: "complete", scenes_total: 5, scenes_passed: 5, usd_estimate: 0.25 }),
      run({ style_preset_id: "cel", status: "failed", usd_estimate: 0.125 }),
      run({ style_preset_id: null, status: "complete", scenes_total: 2, scenes_passed: 2 }),
      run({ style_preset_id: "gouache", status: "complete", scenes_total: 4, scenes_passed: 3, usd_estimate: 0.5 }),
      run({ style_preset_id: "gouache", status: "running" }),
    ]);

    expect(rows).toEqual([
      { style: "cel", runs: 2, jobPassRate: 0.5, pagePassRate: 1, avgCost: 0.1875 },
      { style: "gouache", runs: 2, jobPassRate: 1, pagePassRate: 0.75, avgCost: 0.5 },
      { style: null, runs: 1, jobPassRate: 1, pagePassRate: 1, avgCost: null },
    ]);
  });
});

describe("run filters", () => {
  const jobs = [
    run({ id: "a", status: "complete", style_preset_id: "cel" }),
    run({ id: "b", status: "failed", style_preset_id: "cel" }),
    run({ id: "c", status: "awaiting_confirm", style_preset_id: null }),
    run({ id: "d", status: "failed", style_preset_id: null }),
  ];
  const ids = (rows: JobRow[]) => rows.map((row) => row.id);

  it("reads the URL, treating an unknown status as all", () => {
    expect(parseRunFilter({ status: "failed", style: "cel" })).toEqual({ status: "failed", style: "cel" });
    expect(parseRunFilter({ status: "bogus" })).toEqual({ status: "all", style: "all" });
    expect(parseRunFilter({ status: ["failed", "complete"] })).toEqual({ status: "failed", style: "all" });
  });

  it("filters by status, by missing style, and by both", () => {
    expect(ids(filterJobs(jobs, { status: "in_progress", style: "all" }))).toEqual(["c"]);
    expect(ids(filterJobs(jobs, { status: "all", style: "none" }))).toEqual(["c", "d"]);
    expect(ids(filterJobs(jobs, { status: "failed", style: "cel" }))).toEqual(["b"]);
    expect(ids(filterJobs(jobs, { status: "all", style: "pixel" }))).toEqual([]);
  });
});
