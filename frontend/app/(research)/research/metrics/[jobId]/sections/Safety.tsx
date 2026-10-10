import type { ReactNode } from "react";
import type { RunDetail } from "../types";
import SafetyBadge from "./SafetyBadge";

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
      <h3 className="text-xs font-semibold uppercase tracking-widest text-foreground/50">{title}</h3>
      {children}
    </div>
  );
}

export default function Safety({ run }: { run: RunDetail }) {
  const input = run.moderation?.input ?? null;
  const referencesPassed = run.characters.filter((character) => character.ref_moderation_status === "passed").length;
  const pagesPassed = run.scenes.filter((scene) => scene.moderation_status === "passed").length;
  const pagesFailed = run.scenes.flatMap((scene, index) => (scene.moderation_status === "failed" ? [index + 1] : []));

  return (
    <section id="safety" aria-labelledby="safety-heading" className="scroll-mt-6 space-y-3">
      <h2 id="safety-heading" className="font-display text-2xl font-bold">Safety checks</h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card title="Input gate">
          {input == null ? (
            <p className="text-sm font-medium text-foreground/70">Input safety result not recorded</p>
          ) : (
            <>
              <SafetyBadge status={input.passed ? "passed" : "flagged"} label="Story" />
              {input.categories.length > 0 && <p className="text-xs text-foreground/70">{input.categories.join(", ")}</p>}
            </>
          )}
        </Card>
        <Card title="Reference checks">
          <p className="text-sm font-medium">{referencesPassed} of {run.characters.length} references passed</p>
          {run.cost && run.cost.ref_mod_retry_count > 0 && (
            <p className="text-xs text-foreground/70">{run.cost.ref_mod_retry_count} safety redraws</p>
          )}
        </Card>
        <Card title="Page checks">
          <p className="text-sm font-medium">{pagesPassed} of {run.scenes.length} pages passed</p>
          {pagesFailed.length > 0 && (
            <p className="text-xs font-medium text-destructive">Flagged: page {pagesFailed.join(", ")}</p>
          )}
        </Card>
      </div>
    </section>
  );
}
