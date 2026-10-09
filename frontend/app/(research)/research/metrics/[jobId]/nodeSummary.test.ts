import { describe, expect, it } from "vitest";
import fixture from "./__fixtures__/run.json";
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
    expect(summary.result).toBe("2 drawings passed required checks; 1 failed; 0 have no check result.");
    expect(summarizeNodes({ ...RUN, steps: [...RUN.steps, { ...RUN.steps[0], node: "generate_scene" }] }).generate_scene.result).toBe("Recorded initial drawings for 2 pages.");
    expect(summarizeNodes(RUN).regenerate.result).toBe("Recorded 1 extra drawing across 1 page.");
    expect(summarizeNodes(RUN).regenerate.lines).toEqual([
      "Page 1: 1 redraw recorded. Attempt 2 was selected for the book.",
    ]);
    expect(summary.lines).toEqual([
      "Page 1: 2 attempts, attempt 2 selected for the book.",
      "Page 1, attempt 1: failed required checks. Required-check issues: Character colour differs from the reference.",
      "Page 1, attempt 2: passed required checks.",
      "Page 2: 1 attempt, attempt 1 selected for the book.",
      "Page 2, attempt 1: passed required checks.",
    ]);
    expect(summary.section.id).toBe("pages");
    const unchecked = {
      ...RUN,
      scenes: [{ ...RUN.scenes[0], shipped_attempt: null, attempts: [{ ...RUN.scenes[0].attempts[0], failure_reasons: [] }] }],
    };
    expect(summarizeNodes(unchecked).consistency_check.lines).toEqual([
      "Page 1: 1 attempt, no drawing selected for the book yet.",
      "Page 1, attempt 1: not checked.",
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
    expect(summarizeNodes(compositionFailure).consistency_check.lines[1]).toBe(
      "Page 1, attempt 1: failed required checks. Required-check issues: wrong_colour."
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
  });
});
