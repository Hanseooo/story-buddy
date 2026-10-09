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
