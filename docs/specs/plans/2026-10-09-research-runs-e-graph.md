# Research Runs E — Pipeline Graph and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** The run page shows the path a run took through the 11-node pipeline as a graph: visited nodes solid with visit counts, taken edges thick with traversal counts, the node it ended on marked. Clicking a node opens a panel that says, in words, what that node did. Then the whole PR is documented and checked in a real browser.

**Architecture:** One constant, `PIPELINE_GRAPH`, holds hand-placed node boxes and edge paths in a 570 × 720 coordinate space. A pure `pathCounts(steps)` turns the step list into node and edge counts. The server page computes a per-node summary with the pure `summarizeNodes(run)` and hands only steps, `ended_on` and summaries to the client `PipelineGraph`. Edges are SVG. Nodes are HTML `<button>`s laid over the SVG by percentage, so they are real controls in flow order. The panel is a native `<dialog>`.

**Tech Stack:** React 19.2 client components, SVG, native `<dialog>`, Tailwind tokens, phosphor icons, vitest + Testing Library, `playwright-cli` for the browser check.

**Spec:** `docs/specs/research-run-browser.md` §5.3, §7, §8.

**Plan set:** A → B → C → D → E (this file). E needs D's `RunDetail` types, `format.ts` and `page.tsx`. Branch `feat/research-run-browser`, one PR.


**Execution record (2026-10-09):** Tasks 1–4 implemented on `feat/research-run-browser`.
The component file is `PipelineGraphView.tsx` because Windows resolves `./PipelineGraph` to
`pipelineGraph.ts`; the summary also includes per-attempt verdicts as required by the spec.
Existing page tests mock fetch, so the integration test uses that seam rather than `mockLoad`.
Task 4's PR number remains pending Task 5 Step 7. Spec status and CHANGELOG state that explicitly.

Verification: backend ruff passed; pytest 1,474 passed, 87 skipped, 6 deselected. Frontend lint,
build/typecheck and all 596 tests passed. Traversal counts and section-link focus were deliberately
broken and observed failing, then restored. Signed-out browser checks passed at 1280 × 800 and
360 × 780 with no console errors. A separate captured-fixture page verified native Enter/Escape,
focus return, section links, desktop graph and phone bottom sheet; nodes measured 44.45 px high
and the graph scrolled inside its box without page overflow. The temporary fixture route was removed.

**Remaining:** owner sign-in, an identified synthetic student run, signed-in checks and endpoint
latency (Steps 4–5); real-data phone detail/header/image checks (Step 6); owner approval before
push, PR creation and PR-number doc update (Step 7). This plan remains until those release checks
are completed. No donated story was opened. No credentials or tokens were read.

## Global Constraints

- `PIPELINE_GRAPH` cites `backend/pipeline/graph.py:build_graph` as its source. Its 18 edges are exactly the edges `build_graph` can take, minus `output_mod → output_mod` (a self-loop the router allows but never takes in practice; its visits still count on the node).
- Node labels (plain words; the panel also shows the node id):

  | id | label |
  |---|---|
  | `input_gate` | Input safety |
  | `analyze` | Analyze story |
  | `segment` | Split into pages |
  | `char_bible` | Draw references |
  | `char_ref_mod` | Reference safety |
  | `reveal` | Child confirms |
  | `generate_scene` | Draw page |
  | `consistency_check` | Consistency check |
  | `regenerate` | Redraw page |
  | `output_mod` | Page safety |
  | `compose` | Compose book |

- `ended_on` marking: `failed` → red ring, "Failed here"; `waiting` → amber ring, "Waiting for the child"; `running` → blue ring, "Running now" (the spec names the first two; `running` is the third kind Plan A returns).
- Node accessible name: `<label>, ran N times` ("ran once", "did not run"), then `, N redraws` on the consistency check, then the ended text in lower case. Example: "Consistency check, ran 7 times, 3 redraws".
- Tab order follows the flow: the node array order is the DOM order.
- Every node button at least 44 px tall at the graph's minimum width (528 px: 48 × 528 / 570 = 44.5). Below that the graph scrolls sideways inside its own box, never the page.
- Escape, the close button, and a backdrop click close the panel, and focus returns to the node that opened it.
- Commits carry no `Co-Authored-By` or generated-by trailer. The PR body ends without a "Generated with Claude Code" line.

## Review Focus

1. **A step that is not on the map** (a node added to `build_graph` later). Expect the graph to render and a "1 step not on this map" note, never a crash. Pinned in Task 1 (`unknownSteps`) and Task 3 (the note renders).
2. **A run blocked at the input gate**: one step, `ended_on` on `input_gate`. Expect one solid node with "Failed here" and every other node faded. Pinned in Task 1 (`nodeName`).
3. **Closing the panel by keyboard.** Expect focus back on the node button, so a keyboard user does not land at the top of the page. Pinned in Task 3.
4. **The section link in the panel.** Following it must close the panel and leave the reader at the section, not jump back to the node. Pinned in Task 3.
5. **A phone at 360 px.** Expect nodes still 44 px tall and readable, the page itself not scrolling sideways. Checked in Task 5's browser pass; no unit test can measure it.

---

## File map

All under `frontend/app/(research)/research/metrics/[jobId]/` unless the path says otherwise.

| File | Responsibility |
|---|---|
| `pipelineGraph.ts` + `pipelineGraph.test.ts` | `PIPELINE_GRAPH`, `pathCounts`, `nodeName`, `ENDED_TEXT` |
| `nodeSummary.ts` + `nodeSummary.test.ts` | `summarizeNodes(run)`: per-node lines and the section to jump to |
| `PipelineGraph.tsx` + `PipelineGraph.test.tsx` | SVG edges, node buttons, legend, unknown-step note, panel state |
| `NodePanel.tsx` | the native `<dialog>` sheet |
| `page.tsx` (modify) | mount the graph |
| `docs/specs/ROUTE_MAP.md`, `CHANGELOG.md`, `docs/specs/research-run-browser.md` (modify) | docs |

Commands run from `frontend/` unless they start with `cd`.

---

### Task 1: `PIPELINE_GRAPH`, `pathCounts`, `nodeName`

**Files:**
- Create: `[jobId]/pipelineGraph.ts`
- Test: `[jobId]/pipelineGraph.test.ts`

**Interfaces:**
- Consumes: `RunStep`, `EndedOn` (Plan D Task 1).
- Produces:
  - `GRAPH_WIDTH = 570`, `GRAPH_HEIGHT = 720`, `NODE_W = 150`, `NODE_H = 48`.
  - `type GraphNode = { id: string; label: string; x: number; y: number }` (top-left corner).
  - `type GraphEdge = { from: string; to: string; label?: string; d: string; lx: number; ly: number }` (`d` is the SVG path, `lx, ly` the label centre).
  - `PIPELINE_GRAPH: { nodes: GraphNode[]; edges: GraphEdge[] }`.
  - `type PathCounts = { nodes: Record<string, number>; edges: Record<string, number>; unknownSteps: number }`; edge keys are `"from->to"`.
  - `pathCounts(steps: RunStep[]): PathCounts`.
  - `ENDED_TEXT: Record<EndedOn["kind"], string>`.
  - `nodeName(node: GraphNode, counts: PathCounts, endedOn: EndedOn | null): string`.

- [x] **Step 1: Write the failing tests.**

```ts
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
```

- [x] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/pipelineGraph.test.ts"`
Expected: FAIL, `Failed to resolve import "./pipelineGraph"`.

- [x] **Step 3: Implement.** Layout: the main line runs down x 155-305 on a 72-unit pitch; `regenerate` sits right of the consistency check. Loops back up run on the left (lanes x 125 and x 85). The rare skips (`reveal` straight to page safety or the book, the check straight to the book) run on the far right (lanes x 535 and x 555, and x 335).

```ts
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
```

- [x] **Step 4: Run them and confirm they pass.**

Run: the Step 2 command.
Expected: 3 passed.

- [x] **Step 5: Break it on purpose.** In `pathCounts`, change `counts.edges[key] = (counts.edges[key] ?? 0) + 1` to `counts.edges[key] = 1` (marks an edge as taken but loses how often). Run: the `pathCounts` test FAILS on `consistency_check->regenerate`, expected 2, got 1. Restore: PASS.

- [x] **Step 6: Commit.**

```bash
git add "app/(research)/research/metrics/[jobId]/pipelineGraph.ts" "app/(research)/research/metrics/[jobId]/pipelineGraph.test.ts"
git commit -m "feat(run-detail): pipeline graph layout and path counts (#104)"
```

---

### Task 2: `summarizeNodes`

**Files:**
- Create: `[jobId]/nodeSummary.ts`
- Test: `[jobId]/nodeSummary.test.ts`

**Interfaces:**
- Consumes: `RunDetail` (Plan D Task 1), `PIPELINE_GRAPH` (Task 1). Section ids from Plan D: `story`, `characters`, `pages`, `safety`, `details`.
- Produces:
  - `type NodeSummary = { lines: string[]; section: { id: string; label: string } }`.
  - `summarizeNodes(run: RunDetail): Record<string, NodeSummary>`, one entry per `PIPELINE_GRAPH` node. Pure; runs on the server.

- [x] **Step 1: Write the failing tests.** These use Plan D's captured fixture: input passed, 7 words, character Mia whose reference matches, page 1 shipped on attempt 2 of 2, page 2 on attempt 1 of 1.

```ts
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
```

- [x] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/nodeSummary.test.ts"`
Expected: FAIL, `Failed to resolve import "./nodeSummary"`.

- [x] **Step 3: Implement.**

```ts
import type { RunDetail } from "./types";

export type NodeSummary = { lines: string[]; section: { id: string; label: string } };

const STORY = { id: "story", label: "Story" };
const CHARACTERS = { id: "characters", label: "Characters" };
const PAGES = { id: "pages", label: "Pages" };
const SAFETY = { id: "safety", label: "Safety checks" };

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

function inputGate(run: RunDetail): string[] {
  const input = run.moderation?.input ?? null;
  const lines = [
    input == null
      ? "Input safety result not recorded."
      : input.passed
        ? "Story passed the safety check."
        : `Story flagged: ${input.categories.join(", ") || "no category given"}.`,
  ];
  if (run.story) lines.push(`${run.story.word_count} words after redaction.`);
  if (run.story?.truncated) lines.push("The story was cut to the word limit.");
  return lines;
}

function references(run: RunDetail): string[] {
  const lines = run.characters.map((c) => {
    const verdict = c.ref_verdict == null ? "not judged" : c.ref_verdict.matches_description ? "matches the description" : "does not match the description";
    return `${c.name}: reference ${verdict}; safety ${c.ref_moderation_status ?? "not checked"}.`;
  });
  if (run.cost && run.cost.ref_mod_retry_count > 0) lines.push(`${plural(run.cost.ref_mod_retry_count, "safety redraw", "safety redraws")}.`);
  return lines.length > 0 ? lines : ["No references were recorded."];
}

function attempts(run: RunDetail): string[] {
  const lines = run.scenes.map((s, i) => {
    const outcome = s.shipped_attempt == null ? "nothing shipped yet" : `shipped attempt ${s.shipped_attempt + 1}`;
    return `Page ${i + 1}: ${plural(s.attempts.length, "attempt", "attempts")}, ${outcome}.`;
  });
  return lines.length > 0 ? lines : ["No pages were drawn."];
}

export function summarizeNodes(run: RunDetail): Record<string, NodeSummary> {
  const objects = run.state?.objects?.map((o) => o.name) ?? [];
  const places = run.state?.locations?.map((l) => l.name) ?? [];
  const shipped = run.scenes.filter((s) => s.shipped_attempt != null).length;
  return {
    input_gate: { lines: inputGate(run), section: SAFETY },
    analyze: {
      lines: [
        `Characters: ${run.characters.map((c) => c.name).join(", ") || "none"}.`,
        `Objects: ${objects.join(", ") || "none"}.`,
        `Places: ${places.join(", ") || "none"}.`,
      ],
      section: STORY,
    },
    segment: {
      lines: run.scenes.length > 0 ? run.scenes.map((s, i) => `Page ${i + 1}: ${s.visual_direction ?? s.text_excerpt}`) : ["No pages were made."],
      section: PAGES,
    },
    char_bible: { lines: references(run), section: CHARACTERS },
    char_ref_mod: { lines: references(run), section: CHARACTERS },
    reveal: {
      lines: [
        "Waited for the child to confirm the characters.",
        `Try-again taps: ${run.cost?.ref_retry_count ?? 0}.`,
      ],
      section: CHARACTERS,
    },
    generate_scene: { lines: attempts(run), section: PAGES },
    consistency_check: { lines: attempts(run), section: PAGES },
    regenerate: { lines: attempts(run), section: PAGES },
    output_mod: {
      lines: run.scenes.length > 0 ? run.scenes.map((s, i) => `Page ${i + 1}: safety ${s.moderation_status ?? "not checked"}.`) : ["No pages were checked."],
      section: SAFETY,
    },
    compose: { lines: [`${shipped} of ${run.scenes.length} pages shipped.`], section: PAGES },
  };
}
```

- [x] **Step 4: Run them and confirm they pass.**

Run: the Step 2 command.
Expected: 2 passed.

- [x] **Step 5: Commit.**

```bash
git add "app/(research)/research/metrics/[jobId]/nodeSummary.ts" "app/(research)/research/metrics/[jobId]/nodeSummary.test.ts"
git commit -m "feat(run-detail): plain-words summary per pipeline node"
```

---

### Task 3: `PipelineGraph` and `NodePanel`

**Files:**
- Create: `[jobId]/PipelineGraph.tsx`, `[jobId]/NodePanel.tsx`
- Test: `[jobId]/PipelineGraph.test.tsx`

**Interfaces:**
- Consumes: Task 1, Task 2, `formatDuration` (Plan D Task 2).
- Produces:
  - `PipelineGraph({ steps, endedOn, summaries }: { steps: RunStep[]; endedOn: EndedOn | null; summaries: Record<string, NodeSummary> })`, default export, client, section id `graph`.
  - `NodePanel({ node, visits, summary, onClose, onJump }: { node: GraphNode | null; visits: RunStep[]; summary: NodeSummary | null; onClose: () => void; onJump: () => void })`, default export, client. Open while `node` is not null.

- [x] **Step 1: Write the failing tests.**

```tsx
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import fixture from "./__fixtures__/run.json";
import { summarizeNodes } from "./nodeSummary";
import PipelineGraph from "./PipelineGraph";
import type { RunDetail } from "./types";

const RUN = fixture as unknown as RunDetail;

beforeAll(() => {
  // jsdom has <dialog> but not its modal methods. These do what the browser does, `close` event included.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

const renderGraph = (steps = RUN.steps) =>
  render(<PipelineGraph steps={steps} endedOn={RUN.ended_on} summaries={summarizeNodes(RUN)} />);

describe("PipelineGraph", () => {
  it("lists the nodes in flow order with what happened at each", () => {
    renderGraph();
    const names = within(screen.getByRole("list", { name: "Pipeline steps" }))
      .getAllByRole("button")
      .map((b) => b.getAttribute("aria-label"));

    expect(names[0]).toBe("Input safety, ran once");
    expect(names).toContain("Split into pages, did not run");
    expect(names).toContain("Consistency check, ran 2 times, 1 redraw");
    expect(names.at(-1)).toBe("Compose book, did not run");
  });

  it("opens a panel for a node and returns focus to it on close", () => {
    renderGraph();
    const check = screen.getByRole("button", { name: "Consistency check, ran 2 times, 1 redraw" });
    check.focus();
    fireEvent.click(check);

    const panel = screen.getByRole("dialog", { name: "Consistency check" });
    expect(panel).toHaveAttribute("open");
    expect(panel).toHaveTextContent("Page 1: 2 attempts, shipped attempt 2.");

    fireEvent.click(within(panel).getByRole("button", { name: "Close panel" }));
    expect(panel).not.toHaveAttribute("open");
    expect(check).toHaveFocus();
  });

  it("the section link closes the panel without pulling focus back", () => {
    renderGraph();
    const check = screen.getByRole("button", { name: "Consistency check, ran 2 times, 1 redraw" });
    fireEvent.click(check);
    const panel = screen.getByRole("dialog", { name: "Consistency check" });

    const jump = within(panel).getByRole("link", { name: "Go to Pages" });
    expect(jump).toHaveAttribute("href", "#pages");
    fireEvent.click(jump);

    expect(panel).not.toHaveAttribute("open");
    expect(check).not.toHaveFocus();
  });

  it("notes steps that are not on the map instead of failing", () => {
    renderGraph([...RUN.steps, { node: "proofread", started_at: "2026-10-01T10:00:20+00:00", duration_ms: null }]);
    expect(screen.getByText("1 step not on this map.")).toBeInTheDocument();
  });
});
```

- [x] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/PipelineGraph.test.tsx"`
Expected: FAIL, `Failed to resolve import "./PipelineGraph"`.

- [x] **Step 3: Write `NodePanel.tsx`.** A bottom sheet on phones, a right-hand sheet from `md`:

```tsx
"use client";

import { useEffect, useRef } from "react";
import { X } from "@phosphor-icons/react";
import { formatDuration } from "./format";
import type { NodeSummary } from "./nodeSummary";
import type { GraphNode } from "./pipelineGraph";
import type { RunStep } from "./types";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const TIME = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC" });

export default function NodePanel({
  node,
  visits,
  summary,
  onClose,
  onJump,
}: {
  node: GraphNode | null;
  visits: RunStep[];
  summary: NodeSummary | null;
  onClose: () => void;
  onJump: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (node && !el.open) el.showModal();
    if (!node && el.open) el.close();
  }, [node]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="node-panel-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) ref.current?.close();
      }}
      className="fixed inset-x-0 bottom-0 top-auto m-0 max-h-[85dvh] w-full max-w-none overflow-y-auto rounded-t-3xl bg-surface p-0 text-foreground backdrop:bg-foreground/40 md:inset-y-0 md:left-auto md:right-0 md:h-dvh md:max-h-none md:max-w-md md:rounded-l-3xl md:rounded-tr-none"
    >
      {node && (
        <div className="flex flex-col gap-5 p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="node-panel-title" className="font-display text-2xl font-bold">{node.label}</h2>
              <p className="font-mono text-xs text-foreground/50">{node.id}</p>
            </div>
            <button
              type="button"
              aria-label="Close panel"
              onClick={() => ref.current?.close()}
              className={`inline-flex size-11 shrink-0 items-center justify-center rounded-full neo-border ${FOCUS}`}
            >
              <X weight="bold" className="size-5" aria-hidden />
            </button>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Visits</h3>
            {visits.length === 0 ? (
              <p className="mt-1 text-sm text-foreground/70">This step did not run in this run.</p>
            ) : (
              <ol className="mt-1 space-y-1 font-mono text-xs">
                {visits.map((v, i) => (
                  <li key={i}>
                    {i + 1}. {TIME.format(new Date(v.started_at))} UTC · {formatDuration(v.duration_ms)}
                  </li>
                ))}
              </ol>
            )}
          </div>

          {summary && (
            <>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-foreground/50">What it did</h3>
                <ul className="mt-1 space-y-1 text-sm">
                  {summary.lines.map((line, i) => <li key={i}>{line}</li>)}
                </ul>
              </div>
              <a
                href={`#${summary.section.id}`}
                onClick={() => {
                  onJump();
                  ref.current?.close();
                }}
                className={`inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-4 text-sm font-bold text-on-primary hover:bg-primary-deep ${FOCUS}`}
              >
                Go to {summary.section.label}
              </a>
            </>
          )}
        </div>
      )}
    </dialog>
  );
}
```

- [x] **Step 4: Write `PipelineGraph.tsx`.**

```tsx
"use client";

import { useMemo, useRef, useState } from "react";
import NodePanel from "./NodePanel";
import type { NodeSummary } from "./nodeSummary";
import {
  ENDED_TEXT,
  GRAPH_HEIGHT,
  GRAPH_WIDTH,
  NODE_H,
  NODE_W,
  nodeName,
  pathCounts,
  PIPELINE_GRAPH,
} from "./pipelineGraph";
import type { EndedOn, RunStep } from "./types";

const pct = (value: number, of: number) => `${(value / of) * 100}%`;

const RING: Record<EndedOn["kind"], string> = {
  failed: "ring-3 ring-destructive",
  waiting: "ring-3 ring-warning",
  running: "ring-3 ring-info",
};
const ENDED_TONE: Record<EndedOn["kind"], string> = {
  failed: "text-destructive",
  waiting: "text-foreground",
  running: "text-info",
};

export default function PipelineGraph({
  steps,
  endedOn,
  summaries,
}: {
  steps: RunStep[];
  endedOn: EndedOn | null;
  summaries: Record<string, NodeSummary>;
}) {
  const counts = useMemo(() => pathCounts(steps), [steps]);
  const [openId, setOpenId] = useState<string | null>(null);
  const buttons = useRef<Record<string, HTMLButtonElement | null>>({});
  const jumping = useRef(false);
  const open = PIPELINE_GRAPH.nodes.find((n) => n.id === openId) ?? null;

  function handleClose() {
    const id = openId;
    setOpenId(null);
    // Back to the node that opened the panel, unless the reader followed the section link.
    if (!jumping.current && id) buttons.current[id]?.focus();
    jumping.current = false;
  }

  return (
    <section id="graph" aria-labelledby="graph-heading" className="scroll-mt-6 space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 id="graph-heading" className="font-display text-2xl font-bold">Path through the pipeline</h2>
        <p className="text-xs text-foreground/60">Solid steps ran. Faded steps did not. ×N is how many times. Select a step for details.</p>
      </div>
      <p className="text-xs text-foreground/60 sm:hidden">Swipe sideways to see the redraw loop.</p>

      <div className="overflow-x-auto rounded-3xl bg-surface p-3 neo-border neo-shadow-sm">
        <div
          className="relative mx-auto min-w-[528px] max-w-[570px]"
          style={{ aspectRatio: `${GRAPH_WIDTH} / ${GRAPH_HEIGHT}` }}
        >
          <svg viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`} className="absolute inset-0 size-full" aria-hidden>
            <defs>
              <marker id="arrow-on" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M0 0 L10 5 L0 10 z" className="fill-primary" />
              </marker>
              <marker id="arrow-off" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M0 0 L10 5 L0 10 z" className="fill-foreground/25" />
              </marker>
            </defs>
            {PIPELINE_GRAPH.edges.map((e) => {
              const n = counts.edges[`${e.from}->${e.to}`] ?? 0;
              const text = [e.label, n > 1 ? `×${n}` : ""].filter(Boolean).join(" ");
              return (
                <g key={`${e.from}->${e.to}`} className={n > 0 ? "text-primary" : "text-foreground/25"}>
                  <path
                    d={e.d}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={n > 0 ? 3 : 1.5}
                    strokeDasharray={n > 0 ? undefined : "4 4"}
                    markerEnd={`url(#${n > 0 ? "arrow-on" : "arrow-off"})`}
                  />
                  {text && (
                    <text
                      x={e.lx}
                      y={e.ly}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      strokeWidth={4}
                      style={{ paintOrder: "stroke" }}
                      className="fill-current stroke-surface text-[12px] font-bold"
                    >
                      {text}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          <ul aria-label="Pipeline steps">
            {PIPELINE_GRAPH.nodes.map((node) => {
              const n = counts.nodes[node.id] ?? 0;
              const ended = endedOn?.node === node.id ? endedOn.kind : null;
              return (
                <li
                  key={node.id}
                  className="absolute"
                  style={{ left: pct(node.x, GRAPH_WIDTH), top: pct(node.y, GRAPH_HEIGHT), width: pct(NODE_W, GRAPH_WIDTH), height: pct(NODE_H, GRAPH_HEIGHT) }}
                >
                  <button
                    ref={(el) => {
                      buttons.current[node.id] = el;
                    }}
                    type="button"
                    aria-label={nodeName(node, counts, endedOn)}
                    onClick={() => setOpenId(node.id)}
                    className={`relative flex size-full flex-col items-center justify-center rounded-xl px-2 text-center leading-tight transition-colors focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 ${
                      n > 0
                        ? "bg-surface text-foreground neo-border hover:bg-primary/10"
                        : "border border-dashed border-foreground/25 bg-surface/60 text-foreground/45 hover:bg-muted/40"
                    } ${ended ? RING[ended] : ""}`}
                  >
                    <span className="text-xs font-bold sm:text-sm">{node.label}</span>
                    {ended && <span className={`text-[10px] font-bold ${ENDED_TONE[ended]}`}>{ENDED_TEXT[ended]}</span>}
                    {n > 1 && (
                      <span className="absolute -right-2 -top-2 rounded-full bg-primary px-1.5 py-0.5 text-[11px] font-bold text-on-primary">
                        ×{n}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </div>

      {counts.unknownSteps > 0 && (
        <p className="text-xs font-medium text-foreground/70">
          <span>{counts.unknownSteps} {counts.unknownSteps === 1 ? "step" : "steps"} not on this map.</span> See{" "}
          <a href="#details" className="font-bold text-primary underline">Run details</a> for every step.
        </p>
      )}

      <NodePanel
        node={open}
        visits={open ? steps.filter((s) => s.node === open.id) : []}
        summary={open ? (summaries[open.id] ?? null) : null}
        onClose={handleClose}
        onJump={() => {
          jumping.current = true;
        }}
      />
    </section>
  );
}
```

- [x] **Step 5: Run the tests and confirm they pass.**

Run: the Step 2 command.
Expected: 4 passed.

- [x] **Step 6: Break it on purpose.** In `handleClose`, delete `!jumping.current &&`. Run: `the section link closes the panel without pulling focus back` FAILS. Restore: PASS.

- [x] **Step 7: Commit.**

```bash
git add "app/(research)/research/metrics/[jobId]/PipelineGraph.tsx" "app/(research)/research/metrics/[jobId]/NodePanel.tsx" "app/(research)/research/metrics/[jobId]/PipelineGraph.test.tsx"
git commit -m "feat(run-detail): clickable pipeline graph with a node panel (#104)"
```

---

### Task 4: Mount the graph, then the docs

**Files:**
- Modify: `[jobId]/page.tsx`, `[jobId]/page.test.tsx`
- Modify: `docs/specs/ROUTE_MAP.md`, `CHANGELOG.md`, `docs/specs/research-run-browser.md`

**Interfaces:**
- Consumes: `PipelineGraph` (Task 3), `summarizeNodes` (Task 2).

- [x] **Step 1: Write the failing test.** Append to `page.test.tsx` inside `describe("RunPage states", …)`:

```tsx
  it("a checkpointed run shows the graph before the story", async () => {
    mockLoad.mockResolvedValue({ kind: "ok", run: RUN });
    await renderPage();
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings.slice(0, 2)).toEqual(["Path through the pipeline", "Story"]);
  });
```

- [x] **Step 2: Run it and confirm it fails.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/page.test.tsx"`
Expected: FAIL, the first level-2 heading is "Story".

- [x] **Step 3: Mount it.** In `page.tsx`, add the imports:

```tsx
import { summarizeNodes } from "./nodeSummary";
import PipelineGraph from "./PipelineGraph";
```

and make the checkpointed branch start with the graph:

```tsx
      {run.checkpointed ? (
        <>
          <PipelineGraph steps={run.steps} endedOn={run.ended_on} summaries={summarizeNodes(run)} />
          <Story story={run.story} />
```

- [x] **Step 4: Run the page tests and confirm they pass.**

Run: the Step 2 command.
Expected: all PASS.

- [x] **Step 5: ROUTE_MAP.** In `docs/specs/ROUTE_MAP.md` §1, after the Student routes table and before `---`, add:

```markdown
### Research routes

Researcher accounts (`role = 'researcher'`). The header has Runs, Annotate and Adjudicate tabs
(`docs/specs/research-run-browser.md` §3).

| URL pattern | Page | Rendering | Notes |
|---|---|---|---|
| `/research/metrics` | Run list | Server | Public. Totals, by-style table, URL filters. A run's title shows only to a viewer who can open it (ADR-064 rule 6) |
| `/research/metrics/[jobId]` | Run detail | Server | Login required. Reads `GET /research/runs/{job_id}`; annotators see approved runs, the adjudicator sees all (ADR-064 rule 2). Pipeline graph, pages, safety, raw state |
```

- [x] **Step 6: CHANGELOG.** Add at the top of `CHANGELOG.md`, above the first `##` entry (fill in the PR number once the PR exists, Task 5 Step 7):

```markdown
## PR #<n> · 2026-10-<dd>

Research run browser: run list, run detail with the pipeline graph, Langfuse warning.
[PR #<n>](https://github.com/Hanseooo/story-buddy/pull/<n>) · Closes #103, #104, #107 · Refs #108, #111

### Code

- **`GET /research/runs/{job_id}`** (`backend/app/research.py`): reads the run's LangGraph
  checkpoint history and returns a projection without raw story text or account ids. Annotators
  open approved runs; the adjudicator opens any run (ADR-064). `get_signed_url` takes
  `expires_in`; this route signs for an hour.
- **`/research/metrics`**: public run list with failed split, unchecked pages, images per page,
  a by-style table, status and style filters in the URL, and rows that open a run for allowed
  viewers. Titles never reach a viewer who cannot open the run.
- **`/research/metrics/[jobId]`**: run page with a clickable pipeline graph and node panel,
  story, characters, every page attempt with the shipped one marked, safety, timing, raw JSON.
- **Research header** on metrics, annotate and adjudicate, with Runs / Annotate / Adjudicate tabs.
  Login now returns a researcher to `/research/metrics/...`.
- **Langfuse button** behind `NEXT_PUBLIC_SHOW_LANGFUSE_LINKS` (off by default) and a warning that
  the trace holds the story before redaction.

### Docs

- ADR-064 (accepted). Spec `docs/specs/research-run-browser.md` and plans A-E in
  `docs/specs/plans/2026-10-09-research-runs-*.md`. ROUTE_MAP: research routes and the backend row.

### Checks

- Backend and frontend tests as listed in the PR. Browser check at desktop and 360 px; endpoint
  time on a real run: <fill in from Task 5 Step 5>.
```

- [x] **Step 7: Spec status.** In `docs/specs/research-run-browser.md`, change the `**Status:**` line to:

```markdown
**Status:** design approved 2026-10-09; ADR-064 accepted 2026-10-09; built on `feat/research-run-browser` (PR #<n>).
```

- [x] **Step 8: Commit.**

```bash
git add "app/(research)/research/metrics/[jobId]" ../docs/specs/ROUTE_MAP.md ../CHANGELOG.md ../docs/specs/research-run-browser.md
git commit -m "feat(run-detail): mount the graph; route map, changelog, spec status"
```

---

### Task 5: Browser check, timing, and the PR

No code unless the check finds a defect. A defect found here gets a failing test first, then the fix, in its own commit.

- [x] **Step 1: Full suites.**

Run: `cd ../backend && uv run pytest -q && uv run ruff check . && cd ../frontend && pnpm lint && pnpm test && pnpm build`
Expected: all green. Paste the summary lines into the PR body.

- [x] **Step 2: Start the app.** In two background shells: `cd backend && uv run uvicorn app.main:app --reload` and `cd frontend && pnpm dev`. The worker is not needed: the viewer only reads checkpoints that already exist.

- [x] **Step 3: Signed out, desktop (1280 × 800), with `playwright-cli`.**
  - `/research/metrics`: tiles, failed split, by-style table, filters. No run title anywhere in the page text. No Langfuse button (flag off).
  - Set a filter, reload: it stays. "Clear filters" on an empty result returns every row.
  - A locked row's "Sign in to view" goes to `/login?next=/research/metrics/<id>`.
  - Typing `/research/metrics/<id>` directly redirects to login.
  - Console: no errors.

- [ ] **Step 4: Login wall.** Stop. Ask the owner to sign in as the adjudicator in that browser and say when it is done. Do not type, read, or screenshot credentials or tokens.

- [ ] **Step 5: Signed in as adjudicator.**
  - The list shows titles and whole-row links; the header shows Runs active and the Adjudicator chip.
  - Open a run of a synthetic story (submitted through a test student account; no donated story is opened for this check). Every section renders; the graph highlights the path; counts match the timing table.
  - Keyboard only: Tab to a node, Enter opens the panel, Escape closes it, focus is back on the node. "Go to …" lands on the section.
  - Back ("All runs") restores the list's filters.
  - Time the endpoint for that run: in the browser network panel, or `curl -s -o /dev/null -w "%{time_total}\n"` with a token the owner pastes into their own shell (the agent never handles it). Record the time in the CHANGELOG. Over 3 s → open a follow-up issue for the ADR-064 fallback (latest state plus metadata), do not fix it in this PR.
  - Find and open, if they exist: a failed run (red "Failed here"), a waiting run (amber), a run blocked at the input gate ("Input safety result not recorded"), a run with no checkpoint ("No recorded steps"). Note any that do not exist in the data; they stay unit-tested only.
  - Stop the backend and reload a run: `error.tsx`, "Couldn't load this run", Retry works once it is back.
  - `/research/metrics/not-a-uuid`: "Run not found" with "All runs".
  - Console: no errors.

- [ ] **Step 6: Phone (360 × 780).** The list cards, the run page, the graph (scrolls inside its box, the page does not scroll sideways, nodes about 44 px tall), the node panel as a bottom sheet, the image viewer, the header tabs fitting without overflow. Annotate and adjudicate still look as before, with the header above them.

- [ ] **Step 7: Open the PR, after asking.** Ask the owner before pushing. Then:

```bash
git push -u origin feat/research-run-browser
gh pr create --title "Research run browser: run list, run detail with pipeline graph, Langfuse warning" --body-file <scratchpad>/pr-body.md
```

The body: what changed (the CHANGELOG entry), `Closes #103, #104, #107`, the deviations from the spec found while building (or "none"), the test and browser results with the endpoint time, and the states that could not be seen in real data. No "Generated with Claude Code" footer, no session link. Then put the PR number into the CHANGELOG and spec status lines and commit `docs: PR number for the research run browser`.

---

## Not covered by any test

- Visual layout of the graph (edge crossings, label overlap, sheet placement). Task 5's browser pass is the only check.
- Real checkpoint size and read time on production threads (ADR-064 consequence). Measured once in Task 5 Step 5.
