import { expect, test } from "vitest";
import { computeAggregates, JobRow } from "@/utils/metrics";

test("aggregate math matches expected values", () => {
  const jobs: JobRow[] = [
    { id: "1", status: "complete", created_at: "2026-08-10", image_count: 10, regen_count: 2, scenes_total: 5, scenes_passed: 4, usd_estimate: 0.25 },
    { id: "2", status: "complete", created_at: "2026-08-10", image_count: 5, regen_count: 0, scenes_total: 5, scenes_passed: 5, usd_estimate: 0.125 },
  ];
  const stats = computeAggregates(jobs);
  expect(stats.totalRuns).toBe(2);
  expect(stats.complete).toBe(2);
  expect(stats.totalImages).toBe(15);
  expect(stats.totalRegens).toBe(2);
  expect(stats.estCost).toBe(0.375);
  expect(stats.passRate).toBe(9 / 10);
});

test("handles jobs with NULL/missing cost columns safely", () => {
  const jobs: JobRow[] = [
    { id: "3", status: "failed", created_at: "2026-08-10", image_count: null, regen_count: null, scenes_total: null, scenes_passed: null, usd_estimate: null },
  ];
  const stats = computeAggregates(jobs);
  expect(stats.totalImages).toBe(0);
  expect(stats.passRate).toBe(0);
});

test("totalImages sums image_count only over complete jobs", () => {
  const jobs: JobRow[] = [
    { id: "1", status: "complete", created_at: "2026-08-10", image_count: 10 },
    { id: "2", status: "failed", created_at: "2026-08-10", image_count: 7 },
  ];
  const stats = computeAggregates(jobs);
  expect(stats.totalImages).toBe(10);
});
