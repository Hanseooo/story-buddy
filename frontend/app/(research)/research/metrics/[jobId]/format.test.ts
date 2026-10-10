import { describe, expect, it } from "vitest";
import { formatDuration, totalDurationMs } from "./format";

describe("durations", () => {
  it("sums known durations and skips the failing step's null", () => {
    expect(
      totalDurationMs([
        { node: "a", started_at: "", duration_ms: 1500 },
        { node: "b", started_at: "", duration_ms: 2500 },
        { node: "c", started_at: "", duration_ms: null },
      ])
    ).toBe(4000);
    expect(totalDurationMs([{ node: "a", started_at: "", duration_ms: null }])).toBeNull();
  });

  it("reads as seconds, minutes, or hours", () => {
    expect(formatDuration(1500)).toBe("1.5 s");
    expect(formatDuration(125_000)).toBe("2 min 5 s");
    expect(formatDuration(7_380_000)).toBe("2 h 3 min");
    expect(formatDuration(null)).toBe("—");
  });
});
