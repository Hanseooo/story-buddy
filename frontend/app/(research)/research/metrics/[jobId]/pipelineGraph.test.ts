import { readFileSync } from "node:fs";
import path from "node:path";
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

// Seam S-3: node names come from backend/pipeline/graph.py read as text.
const GRAPH_PY = readFileSync(path.resolve(__dirname, "../../../../../../backend/pipeline/graph.py"), "utf8");
const GRAPH_NODES = [...GRAPH_PY.matchAll(/add_node\("([a-z_]+)"/g)].map((m) => m[1]);

describe("PIPELINE_GRAPH", () => {
  it("has the 14 nodes graph.py adds and every edge joins two of them", () => {
    const ids = new Set(PIPELINE_GRAPH.nodes.map((n) => n.id));
    expect(GRAPH_NODES).toHaveLength(14);
    expect([...ids].sort()).toEqual([...GRAPH_NODES].sort());
    expect(PIPELINE_GRAPH.edges).toHaveLength(28);
    for (const e of PIPELINE_GRAPH.edges) {
      expect(ids.has(e.from) && ids.has(e.to)).toBe(true);
    }
  });

  it("draws the teacher-review edges and keeps a run in the new nodes on the map", () => {
    const keys = PIPELINE_GRAPH.edges.map((e) => `${e.from}->${e.to}`);
    for (const k of [
      "input_gate->optional_themes", "optional_themes->analyze", "input_gate->moderation_review",
      "optional_themes->moderation_review", "char_ref_mod->moderation_review", "reveal->moderation_review",
      "output_mod->moderation_review", "moderation_review->moderation_replace",
      "moderation_replace->char_ref_mod", "moderation_replace->consistency_check",
    ]) expect(keys).toContain(k);
    expect(pathCounts(steps("input_gate", "moderation_review", "moderation_replace")).unknownSteps).toBe(0);
  });
});

describe("nodeName for a teacher hold", () => {
  it("says the run is waiting for the teacher, not the child", () => {
    const held = pathCounts(steps("input_gate", "moderation_review"));
    expect(nodeName(node("moderation_review"), held, { node: "moderation_review", kind: "teacher" })).toBe(
      "Teacher review, ran once, waiting for the teacher"
    );
  });
});
