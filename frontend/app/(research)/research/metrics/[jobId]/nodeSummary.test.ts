import { describe, expect, it } from "vitest";
import fixture from "./__fixtures__/run.json";
import passedWithWarnings from "./__fixtures__/passed-with-warnings.json";
import { summarizeNodes } from "./nodeSummary";
import type { RunDetail } from "./types";

const RUN = fixture as unknown as RunDetail;

describe("summarizeNodes", () => {
  it("says what the input gate decided, or that nothing was recorded", () => {
    expect(summarizeNodes(RUN).input_gate.result).toBe("Story passed the safety check.");
    expect(summarizeNodes(RUN).input_gate.lines).toEqual(["7 words after redaction."]);

    const blocked = summarizeNodes({ ...RUN, moderation: { input: null } });
    expect(blocked.input_gate.result).toBe("Input safety result not recorded.");
    expect(blocked.input_gate.section).toEqual({ id: "safety", label: "Safety checks" });
  });

  it("describes each page's attempts for the drawing nodes", () => {
    const summary = summarizeNodes(RUN).consistency_check;
    expect(summary.purpose).toBe("Compares each drawing with the character references and the page's requirements.");
    expect(summary.result).toBe("2 drawings passed required checks; 1 failed; 0 have no complete check result.");
    expect(summarizeNodes({ ...RUN, steps: [...RUN.steps, { ...RUN.steps[0], node: "generate_scene" }] }).generate_scene.result).toBe("Recorded initial drawings for 2 pages.");
    expect(summarizeNodes(RUN).regenerate.result).toBe("Recorded 1 extra drawing across 1 page.");
    expect(summarizeNodes(RUN).regenerate.lines).toEqual([
      "Page 1: 1 redraw recorded. Attempt 2 was selected for the book.",
    ]);
    expect(summary.pageResults).toEqual([
      { page: 1, drawings: 2, selectedAttempt: 2, attempts: [
        { number: 1, outcome: "Failed required checks", required: ["Character colour differs from the reference"], warnings: [] },
        { number: 2, outcome: "Passed required checks", required: [], warnings: [] },
      ] },
      { page: 2, drawings: 1, selectedAttempt: 1, attempts: [
        { number: 1, outcome: "Passed required checks", required: [], warnings: [] },
      ] },
    ]);
    expect(summary.lines).toEqual([]);
    expect(summary.section.id).toBe("pages");
    const unchecked = {
      ...RUN,
      scenes: [{ ...RUN.scenes[0], shipped_attempt: null, attempts: [{ ...RUN.scenes[0].attempts[0], failure_reasons: [] }] }],
    };
    expect(summarizeNodes(unchecked).consistency_check.pageResults).toEqual([
      { page: 1, drawings: 1, selectedAttempt: null, attempts: [
        { number: 1, outcome: "Not checked", required: [], warnings: [] },
      ] },
    ]);
    const compositionFailure = {
      ...unchecked,
      scenes: [{
        ...unchecked.scenes[0],
        attempts: [{
          ...unchecked.scenes[0].attempts[0],
          scene_contradictions: RUN.scenes[0].attempts[0].failure_reasons,
        }],
      }],
    };
    expect(summarizeNodes(compositionFailure).consistency_check.pageResults?.[0].attempts[0]).toEqual(
      { number: 1, outcome: "Failed required checks", required: ["wrong_colour"], warnings: [] }
    );
  });

  it("distinguishes unvisited steps, waiting and missing results", () => {
    const summaries = summarizeNodes(RUN);
    expect(summaries.reveal.result).toBe("This step did not run.");
    expect(summaries.reveal.lines).toEqual([]);
    const waiting = summarizeNodes({ ...RUN, ended_on: { node: "reveal", kind: "waiting" }, cost: null });
    expect(waiting.reveal.result).toBe("Waiting for the child to confirm the character references.");
    expect(waiting.reveal.lines).toEqual(["Requests to redraw the references: not recorded."]);
    const blocked = summarizeNodes({ ...RUN, ended_on: { node: "input_gate", kind: "failed" }, moderation: null });
    expect(blocked.input_gate.result).toBe("The run stopped at this step. Its result may be incomplete.");
    expect(blocked.input_gate.lines[0]).toBe("Input safety result not recorded.");
    const incomplete = summarizeNodes({
      ...RUN,
      scenes: [{ ...RUN.scenes[1], attempts: [{ ...RUN.scenes[1].attempts[0], ...passedWithWarnings, passed: false, scene_contradictions: null }] }],
    });
    expect(incomplete.consistency_check.result).toBe("0 drawings passed required checks; 0 failed; 1 has no complete check result.");
    expect(incomplete.consistency_check.pageResults?.[0].attempts[0]).toEqual({
      number: 1, outcome: "Not checked", required: [],
      warnings: ["Face differs from the character reference", "Text detected in the illustration"],
    });
    const unvisited = summarizeNodes({ ...RUN, steps: RUN.steps.filter((step) => step.node !== "consistency_check") });
    expect(unvisited.consistency_check.pageResults).toEqual([]);
  });
});
