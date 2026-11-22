import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PipelineMap from "./PipelineMap";

// Seam S-3: node names come from backend/pipeline/graph.py read as text.
const GRAPH_PY = readFileSync(path.resolve(__dirname, "../../backend/pipeline/graph.py"), "utf8");
const GRAPH_NODES = [...GRAPH_PY.matchAll(/add_node\("([a-z_]+)"/g)].map((m) => m[1]);
// Hand-read from graph.py: these three are reachable only when moderation_context.mode is "teacher_review_v1".
const TEACHER_ONLY = ["optional_themes", "moderation_review", "moderation_replace"];

const ids = (els: Element[]) => els.map((el) => el.getAttribute("data-node")).sort();

describe("PipelineMap", () => {
  it("shows exactly the nodes graph.py adds, 14 of them", () => {
    expect(GRAPH_NODES).toHaveLength(14);
    const { container } = render(<PipelineMap />);
    expect(ids([...container.querySelectorAll("[data-node]")])).toEqual([...GRAPH_NODES].sort());
  });

  it("marks 11 nodes as baseline and the 3 teacher-review nodes as teacher review only", () => {
    const { container } = render(<PipelineMap />);
    const teacher = [...container.querySelectorAll('[data-node][data-mode="teacher-review"]')];
    const baseline = [...container.querySelectorAll('[data-node][data-mode="both"]')];
    expect(ids(teacher)).toEqual([...TEACHER_ONLY].sort());
    expect(baseline).toHaveLength(11);
  });

  it("starts with every node visible and no calc() in an SVG path", () => {
    const { container } = render(<PipelineMap />);
    for (const el of container.querySelectorAll("[data-node]")) {
      expect(el.getAttribute("style") ?? "").not.toMatch(/opacity:\s*0/);
    }
    for (const p of container.querySelectorAll("path[d]")) expect(p.getAttribute("d")).not.toContain("calc");
    expect(screen.getAllByRole("listitem").length).toBeGreaterThanOrEqual(14);
  });
});
