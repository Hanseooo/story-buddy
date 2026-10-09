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
      <div aria-hidden="true" className="mx-auto mt-3 h-1.5 w-12 rounded-full bg-foreground/25 md:hidden" />
      {node && (
        <div className="flex flex-col gap-5 p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="node-panel-title" className="font-display text-2xl font-bold">{node.label}</h2>
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

          {summary && (
            <>
              <div>
                <h3 className="text-sm font-bold">What this step does</h3>
                <p className="mt-1 text-sm leading-relaxed">{summary.purpose}</p>
              </div>
              <div>
                <h3 className="text-sm font-bold">What happened in this run</h3>
                <p className="mt-1 text-sm leading-relaxed">{summary.result}</p>
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
              {summary.lines.length > 0 && (
                <details className="text-sm">
                  <summary className={`min-h-11 cursor-pointer py-3 font-bold text-primary ${FOCUS}`}>Recorded results</summary>
                  <ul className="mt-1 list-disc space-y-2 pl-5 leading-relaxed">
                    {summary.lines.map((line, i) => <li key={i}>{line}</li>)}
                  </ul>
                </details>
              )}
            </>
          )}
          <details className="text-sm">
            <summary className={`min-h-11 cursor-pointer py-3 font-bold text-primary ${FOCUS}`}>Execution details</summary>
            <p className="mt-1 font-mono text-xs text-foreground/70">{node.id}</p>
            <p className="mt-2 text-foreground/70">{visits.length === 0 ? "No executions recorded." : `Ran ${visits.length} ${visits.length === 1 ? "time" : "times"}.`}</p>
            <ol className="mt-2 space-y-1 font-mono text-xs">
              {visits.map((v, i) => (
                <li key={i}>
                  {i + 1}. {TIME.format(new Date(v.started_at))} UTC · {formatDuration(v.duration_ms)}
                </li>
              ))}
            </ol>
          </details>
        </div>
      )}
    </dialog>
  );
}
