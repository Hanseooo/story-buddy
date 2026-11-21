import type { EndedOn, RunStep } from "./types";

export const GRAPH_WIDTH = 790;
export const GRAPH_HEIGHT = 792;
export const NODE_W = 150;
export const NODE_H = 48;

export type GraphNode = { id: string; label: string; x: number; y: number };
export type GraphEdge = { from: string; to: string; label?: string; d: string; lx: number; ly: number };

const X = 155; // main line, left edge
const T = 585; // teacher-review column, left edge

// Hand-placed copy of backend/pipeline/graph.py:build_graph (checked 2026-11-21). A node or edge added
// there needs adding here; until then its steps show as "not on this map". `output_mod -> output_mod`
// is left out: the router allows it, no run takes it, and its visits still count on the node. So are the
// `moderation_review -> <node it held>` edges: an allowed hold resumes where the run stopped, which this map
// shows by the step order. The right-hand column and the paths into it only run in teacher-review mode.
export const PIPELINE_GRAPH: { nodes: GraphNode[]; edges: GraphEdge[] } = {
  nodes: [
    { id: "input_gate", label: "Input safety", x: X, y: 12 },
    { id: "optional_themes", label: "Theme safety", x: X, y: 84 },
    { id: "analyze", label: "Analyze story", x: X, y: 156 },
    { id: "segment", label: "Split into pages", x: X, y: 228 },
    { id: "char_bible", label: "Draw references", x: X, y: 300 },
    { id: "char_ref_mod", label: "Reference safety", x: X, y: 372 },
    { id: "reveal", label: "Child confirms", x: X, y: 444 },
    { id: "generate_scene", label: "Draw page", x: X, y: 516 },
    { id: "consistency_check", label: "Consistency check", x: X, y: 588 },
    { id: "regenerate", label: "Redraw page", x: 365, y: 588 },
    { id: "output_mod", label: "Page safety", x: X, y: 660 },
    { id: "moderation_review", label: "Teacher review", x: T, y: 372 },
    { id: "moderation_replace", label: "Replace drawing", x: T, y: 588 },
    { id: "compose", label: "Compose book", x: X, y: 732 },
  ],
  edges: [
    // The main line, top to bottom.
    { from: "input_gate", to: "optional_themes", d: "M230 60 V84", lx: 252, ly: 72 },
    { from: "optional_themes", to: "analyze", d: "M230 132 V156", lx: 252, ly: 144 },
    { from: "analyze", to: "segment", d: "M230 204 V228", lx: 252, ly: 216 },
    { from: "segment", to: "char_bible", d: "M230 276 V300", lx: 252, ly: 288 },
    { from: "char_bible", to: "char_ref_mod", d: "M230 348 V372", lx: 252, ly: 360 },
    { from: "char_ref_mod", to: "reveal", d: "M230 420 V444", lx: 252, ly: 432 },
    { from: "reveal", to: "generate_scene", d: "M230 492 V516", lx: 252, ly: 504 },
    { from: "generate_scene", to: "consistency_check", d: "M230 564 V588", lx: 252, ly: 576 },
    { from: "consistency_check", to: "output_mod", d: "M230 636 V660", lx: 252, ly: 648 },
    { from: "output_mod", to: "compose", d: "M230 708 V732", lx: 252, ly: 720 },
    // Skips the themes step when the class chose none.
    { from: "input_gate", to: "analyze", label: "no themes", d: "M155 36 H115 V180 H155", lx: 115, ly: 108 },
    // Loops back up, on the left.
    { from: "char_ref_mod", to: "char_bible", label: "safety redraw", d: "M155 402 H125 V330 H155", lx: 125, ly: 366 },
    { from: "reveal", to: "char_bible", label: "try again", d: "M155 474 H85 V318 H155", lx: 85, ly: 432 },
    { from: "consistency_check", to: "generate_scene", label: "next page", d: "M155 622 H125 V546 H155", lx: 125, ly: 584 },
    { from: "output_mod", to: "generate_scene", label: "next page", d: "M155 690 H85 V534 H155", lx: 85, ly: 612 },
    // The redraw loop, on the right.
    { from: "consistency_check", to: "regenerate", label: "redraw", d: "M305 604 H365", lx: 335, ly: 594 },
    { from: "regenerate", to: "consistency_check", d: "M365 620 H305", lx: 335, ly: 630 },
    // Rare skips, right of the redraw loop.
    { from: "reveal", to: "output_mod", d: "M305 480 H535 V678 H305", lx: 535, ly: 579 },
    { from: "reveal", to: "compose", d: "M305 456 H555 V762 H305", lx: 555, ly: 609 },
    { from: "consistency_check", to: "compose", d: "M290 636 V648 H335 V744 H305", lx: 335, ly: 702 },
    // Teacher-review mode: a flag holds the run for the teacher instead of stopping it.
    { from: "input_gate", to: "moderation_review", label: "flagged text", d: "M305 36 H640 V372", lx: 640, ly: 200 },
    { from: "optional_themes", to: "moderation_review", label: "flagged theme", d: "M305 108 H680 V372", lx: 680, ly: 260 },
    { from: "char_ref_mod", to: "moderation_review", label: "flagged reference", d: "M305 396 H585", lx: 445, ly: 386 },
    { from: "reveal", to: "moderation_review", label: "held pencil text", d: "M305 468 H660 V420", lx: 610, ly: 458 },
    { from: "output_mod", to: "moderation_review", label: "flagged page", d: "M305 684 H755 V396 H735", lx: 755, ly: 540 },
    { from: "moderation_review", to: "moderation_replace", label: "replace", d: "M710 420 V588", lx: 710, ly: 504 },
    { from: "moderation_replace", to: "consistency_check", label: "new page", d: "M660 636 V643 H275 V636", lx: 470, ly: 643 },
    { from: "moderation_replace", to: "char_ref_mod", label: "new reference", d: "M735 612 H770 V360 H280 V372", lx: 770, ly: 480 },
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
  teacher: "Waiting for the teacher",
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
