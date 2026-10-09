import { describe, expect, it } from "vitest";
import type { RunStep } from "./types";
import { nodeName, pathCounts, PIPELINE_GRAPH } from "./pipelineGraph";

const steps = (...nodes: string[]): RunStep[] => nodes.map((node) => ({ node, started_at: "", duration_ms: null }));
const node = (id: string) => PIPELINE_GRAPH.nodes.find((n) => n.id === id)!;

describe("pathCounts", () => {
  it("counts visits and traversals through both loops, and flags a step not on the map", () => {
    const counts = pathCounts(
      steps(
        "input_gate", "analyze", "segment", "char_bible", "char_ref_mod", "char_bible", "char_ref_mod", "reveal",
        "generate_scene", "consistency_check", "regenerate", "consistency_check", "regenerate", "consistency_check",
        "output_mod", "generate_scene", "consistency_check", "output_mod", "compose", "proofread"
      )
    );

    expect(counts.nodes.consistency_check).toBe(4);
    expect(counts.nodes.regenerate).toBe(2);
    expect(counts.nodes.char_bible).toBe(2);
    expect(counts.edges["consistency_check->regenerate"]).toBe(2);
    expect(counts.edges["regenerate->consistency_check"]).toBe(2);
    expect(counts.edges["char_ref_mod->char_bible"]).toBe(1);
    expect(counts.edges["output_mod->generate_scene"]).toBe(1);
    expect(counts.edges["consistency_check->output_mod"]).toBe(2);
    expect(counts.unknownSteps).toBe(1);
  });
});

describe("nodeName", () => {
  it("names visits, redraws and where the run ended", () => {
    const looped = pathCounts(steps("generate_scene", "consistency_check", "regenerate", "consistency_check"));
    expect(nodeName(node("consistency_check"), looped, null)).toBe("Consistency check, ran 2 times, 1 redraw");

    const blocked = pathCounts(steps("input_gate"));
    expect(nodeName(node("input_gate"), blocked, { node: "input_gate", kind: "failed" })).toBe(
      "Input safety, ran once, failed here"
    );
    expect(nodeName(node("analyze"), blocked, { node: "input_gate", kind: "failed" })).toBe("Analyze story, did not run");
  });
});

describe("PIPELINE_GRAPH", () => {
  it("has 11 nodes and every edge joins two of them", () => {
    const ids = new Set(PIPELINE_GRAPH.nodes.map((n) => n.id));
    expect(ids.size).toBe(11);
    expect(PIPELINE_GRAPH.edges).toHaveLength(18);
    for (const e of PIPELINE_GRAPH.edges) {
      expect(ids.has(e.from) && ids.has(e.to)).toBe(true);
    }
  });
});
