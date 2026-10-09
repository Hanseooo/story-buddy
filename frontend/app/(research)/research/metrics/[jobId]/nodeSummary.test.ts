import { describe, expect, it } from "vitest";
import fixture from "./__fixtures__/run.json";
import { summarizeNodes } from "./nodeSummary";
import type { RunDetail } from "./types";

const RUN = fixture as unknown as RunDetail;

describe("summarizeNodes", () => {
  it("says what the input gate decided, or that nothing was recorded", () => {
    expect(summarizeNodes(RUN).input_gate.lines).toEqual(["Story passed the safety check.", "7 words after redaction."]);

    const blocked = summarizeNodes({ ...RUN, moderation: { input: null } });
    expect(blocked.input_gate.lines[0]).toBe("Input safety result not recorded.");
    expect(blocked.input_gate.section).toEqual({ id: "safety", label: "Safety checks" });
  });

  it("describes each page's attempts for the drawing nodes", () => {
    const summary = summarizeNodes(RUN).consistency_check;
    expect(summary.lines).toEqual(["Page 1: 2 attempts, shipped attempt 2.", "Page 2: 1 attempt, shipped attempt 1."]);
    expect(summary.section.id).toBe("pages");
  });
});
