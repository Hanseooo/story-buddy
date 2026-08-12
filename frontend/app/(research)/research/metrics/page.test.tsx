import { expect, test } from "vitest";
import { computeAggregates, JobRow } from "@/utils/metrics";

test("aggregate math matches expected values", () => {
  const jobs: JobRow[] = [
    { id: "1", status: "complete", created_at: "2026-08-10", regen_count: 2, scenes_total: 5, scenes_passed: 4, usd_estimate: 0.25 },
    { id: "2", status: "complete", created_at: "2026-08-10", regen_count: 0, scenes_total: 5, scenes_passed: 5, usd_estimate: 0.125 },
  ];
  const stats = computeAggregates(jobs);
  expect(stats.totalRuns).toBe(2);
  expect(stats.complete).toBe(2);
  expect(stats.totalRegens).toBe(2);
  expect(stats.estCost).toBe(0.375);
  expect(stats.scenePassRate).toBe(9 / 10);
  expect(stats.jobPassRate).toBe(1);
});

test("handles jobs with NULL/missing cost columns safely", () => {
  const jobs: JobRow[] = [
    { id: "3", status: "failed", created_at: "2026-08-10", regen_count: null, scenes_total: null, scenes_passed: null, usd_estimate: null },
  ];
  const stats = computeAggregates(jobs);
  expect(stats.estCost).toBe(0);
  expect(stats.scenePassRate).toBe(0);
  expect(stats.jobPassRate).toBe(0);
});

// The bug this page shipped with: failed jobs never write scenes_total, so they fell out of
// BOTH sides of the scene fraction and the tile read 100% next to a column of failures.
test("jobPassRate counts failures that never recorded a scene", () => {
  const jobs: JobRow[] = [
    { id: "1", status: "complete", created_at: "2026-08-10", scenes_total: 4, scenes_passed: 4 },
    ...Array.from({ length: 7 }, (_, i) => ({
      id: `f${i}`,
      status: "failed",
      created_at: "2026-08-10",
    })),
  ];
  const stats = computeAggregates(jobs);
  expect(stats.scenePassRate).toBe(1);
  expect(stats.jobPassRate).toBe(1 / 8);
});

test("in-progress statuses are counted so the tiles sum to totalRuns", () => {
  const jobs: JobRow[] = [
    { id: "1", status: "complete", created_at: "2026-08-10" },
    { id: "2", status: "failed", created_at: "2026-08-10" },
    { id: "3", status: "awaiting_confirm", created_at: "2026-08-10" },
    { id: "4", status: "queued", created_at: "2026-08-10" },
    { id: "5", status: "running", created_at: "2026-08-10" },
  ];
  const stats = computeAggregates(jobs);
  expect(stats.inProgress).toBe(3);
  expect(stats.complete + stats.failed + stats.inProgress).toBe(stats.totalRuns);
  // Unconcluded runs must not drag the job pass rate down.
  expect(stats.jobPassRate).toBe(1 / 2);
});
