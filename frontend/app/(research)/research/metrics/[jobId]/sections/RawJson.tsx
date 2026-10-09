"use client";

import { useState } from "react";
import { Check, Copy } from "@phosphor-icons/react";
import type { RunDetail } from "../types";

export default function RawJson({ state }: { state: RunDetail["state"] }) {
  const [copied, setCopied] = useState(false);
  const text = JSON.stringify(state, null, 2);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be unavailable; the JSON remains selectable below.
    }
  }

  return (
    <section id="raw" aria-labelledby="raw-heading" className="scroll-mt-6">
      <details className="rounded-3xl bg-surface neo-border neo-shadow-sm">
        <summary className="flex min-h-14 cursor-pointer items-center rounded-3xl px-5 font-display text-lg font-bold focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">
          <h2 id="raw-heading">Raw state (JSON)</h2>
        </summary>
        <div className="space-y-3 border-t border-muted px-5 pb-5 pt-3">
          <p className="text-xs text-foreground/60">The checkpointed StoryMemory, with the raw story text and account ids removed.</p>
          <button
            type="button"
            aria-label="Copy JSON"
            onClick={copy}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-on-primary hover:bg-primary-deep focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            {copied ? <Check weight="bold" className="size-4" aria-hidden /> : <Copy weight="bold" className="size-4" aria-hidden />}
            <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
          </button>
          <pre className="max-h-[60dvh] overflow-auto rounded-xl bg-muted/30 p-3 font-mono text-xs">{text}</pre>
        </div>
      </details>
    </section>
  );
}
