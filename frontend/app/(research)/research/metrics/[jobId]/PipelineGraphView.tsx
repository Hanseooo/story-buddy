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
