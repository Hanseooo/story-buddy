import type { EndedOn, RunStep } from "./types";

export const GRAPH_WIDTH = 570;
export const GRAPH_HEIGHT = 720;
export const NODE_W = 150;
export const NODE_H = 48;

export type GraphNode = { id: string; label: string; x: number; y: number };
export type GraphEdge = { from: string; to: string; label?: string; d: string; lx: number; ly: number };

const X = 155; // main line, left edge

// Hand-placed copy of backend/pipeline/graph.py:build_graph (checked 2026-10-09). A node or edge added
// there needs adding here; until then its steps show as "not on this map". `output_mod -> output_mod`
// is left out: the router allows it, no run takes it, and its visits still count on the node.
export const PIPELINE_GRAPH: { nodes: GraphNode[]; edges: GraphEdge[] } = {
  nodes: [
    { id: "input_gate", label: "Input safety", x: X, y: 12 },
    { id: "analyze", label: "Analyze story", x: X, y: 84 },
    { id: "segment", label: "Split into pages", x: X, y: 156 },
    { id: "char_bible", label: "Draw references", x: X, y: 228 },
    { id: "char_ref_mod", label: "Reference safety", x: X, y: 300 },
    { id: "reveal", label: "Child confirms", x: X, y: 372 },
    { id: "generate_scene", label: "Draw page", x: X, y: 444 },
    { id: "consistency_check", label: "Consistency check", x: X, y: 516 },
    { id: "regenerate", label: "Redraw page", x: 365, y: 516 },
    { id: "output_mod", label: "Page safety", x: X, y: 588 },
    { id: "compose", label: "Compose book", x: X, y: 660 },
  ],
  edges: [
    // The main line, top to bottom.
    { from: "input_gate", to: "analyze", d: "M230 60 V84", lx: 252, ly: 72 },
    { from: "analyze", to: "segment", d: "M230 132 V156", lx: 252, ly: 144 },
    { from: "segment", to: "char_bible", d: "M230 204 V228", lx: 252, ly: 216 },
    { from: "char_bible", to: "char_ref_mod", d: "M230 276 V300", lx: 252, ly: 288 },
    { from: "char_ref_mod", to: "reveal", d: "M230 348 V372", lx: 252, ly: 360 },
    { from: "reveal", to: "generate_scene", d: "M230 420 V444", lx: 252, ly: 432 },
    { from: "generate_scene", to: "consistency_check", d: "M230 492 V516", lx: 252, ly: 504 },
    { from: "consistency_check", to: "output_mod", d: "M230 564 V588", lx: 252, ly: 576 },
    { from: "output_mod", to: "compose", d: "M230 636 V660", lx: 252, ly: 648 },
    // Loops back up, on the left.
    { from: "char_ref_mod", to: "char_bible", label: "safety redraw", d: "M155 330 H125 V258 H155", lx: 125, ly: 294 },
    { from: "reveal", to: "char_bible", label: "try again", d: "M155 402 H85 V246 H155", lx: 85, ly: 360 },
    { from: "consistency_check", to: "generate_scene", label: "next page", d: "M155 550 H125 V474 H155", lx: 125, ly: 512 },
    { from: "output_mod", to: "generate_scene", label: "next page", d: "M155 618 H85 V462 H155", lx: 85, ly: 540 },
    // The redraw loop, on the right.
    { from: "consistency_check", to: "regenerate", label: "redraw", d: "M305 532 H365", lx: 335, ly: 522 },
    { from: "regenerate", to: "consistency_check", d: "M365 548 H305", lx: 335, ly: 562 },
    // Rare skips, far right.
    { from: "reveal", to: "output_mod", d: "M305 408 H535 V606 H305", lx: 535, ly: 507 },
    { from: "reveal", to: "compose", d: "M305 384 H555 V690 H305", lx: 555, ly: 537 },
    { from: "consistency_check", to: "compose", d: "M290 564 V576 H335 V672 H305", lx: 335, ly: 630 },
  ],
};

const KNOWN = new Set(PIPELINE_GRAPH.nodes.map((n) => n.id));

export type PathCounts = { nodes: Record<string, number>; edges: Record<string, number>; unknownSteps: number };

export function pathCounts(steps: RunStep[]): PathCounts {
  const counts: PathCounts = { nodes: {}, edges: {}, unknownSteps: 0 };
  steps.forEach((step, i) => {
    counts.nodes[step.node] = (counts.nodes[step.node] ?? 0) + 1;
    if (!KNOWN.has(step.node)) counts.unknownSteps += 1;
    if (i > 0) {
      const key = `${steps[i - 1].node}->${step.node}`;
      counts.edges[key] = (counts.edges[key] ?? 0) + 1;
    }
  });
  return counts;
}

export const ENDED_TEXT: Record<EndedOn["kind"], string> = {
  failed: "Failed here",
  waiting: "Waiting for the child",
  running: "Running now",
};

export function nodeName(node: GraphNode, counts: PathCounts, endedOn: EndedOn | null): string {
  const n = counts.nodes[node.id] ?? 0;
  const parts = [node.label, n === 0 ? "did not run" : n === 1 ? "ran once" : `ran ${n} times`];
  if (node.id === "consistency_check") {
    const redraws = counts.edges["consistency_check->regenerate"] ?? 0;
    if (redraws > 0) parts.push(`${redraws} ${redraws === 1 ? "redraw" : "redraws"}`);
  }
  if (endedOn?.node === node.id) parts.push(ENDED_TEXT[endedOn.kind].toLowerCase());
  return parts.join(", ");
}
