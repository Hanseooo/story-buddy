import { sceneFailureLabel, VERDICT_CHECK_LABELS } from "@/utils/metrics";
import ImageViewer from "../ImageViewer";
import type { RunAttempt, RunCharacter, RunScene } from "../types";
import SafetyBadge from "./SafetyBadge";

function Verdict({ attempt }: { attempt: RunAttempt }) {
  if (attempt.passed) {
    return <span className="rounded-full bg-success/15 px-2.5 py-1 text-xs font-bold text-success">Passed</span>;
  }
  // A recorded reason means the judge answered even if its verdict object was not kept.
  if (attempt.vlm_verdict == null && attempt.failure_reasons.length === 0) {
    return <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-bold text-foreground/70">Not checked</span>;
  }
  return <span className="rounded-full bg-destructive/15 px-2.5 py-1 text-xs font-bold text-destructive">Failed</span>;
}

function AttemptCard({ attempt, page, index, shipped }: { attempt: RunAttempt; page: number; index: number; shipped: boolean }) {
  const failedChecks = attempt.vlm_verdict
    ? (Object.keys(VERDICT_CHECK_LABELS) as (keyof typeof VERDICT_CHECK_LABELS)[]).filter((key) => attempt.vlm_verdict?.[key] === false)
    : [];

  return (
    <li
      aria-label={`Attempt ${index + 1}`}
      className={`relative flex flex-col gap-3 rounded-2xl bg-background p-3 neo-border ${shipped ? "ring-3 ring-success" : ""}`}
    >
      {shipped && (
        <span className="absolute left-3 top-3 z-10 rounded-full bg-success px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-on-success">
          Shipped
        </span>
      )}
      <ImageViewer src={attempt.image_url} alt={`Page ${page}, attempt ${index + 1}`} className="aspect-square w-full" />
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-bold">Attempt {index + 1}</span>
        <Verdict attempt={attempt} />
      </div>
      {(attempt.failure_reasons.length > 0 || failedChecks.length > 0) && (
        <ul aria-label="What the judge flagged" className="flex flex-wrap gap-1.5">
          {attempt.failure_reasons.map((reason) => (
            <li key={reason} className="rounded-md bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive">{sceneFailureLabel(reason)}</li>
          ))}
          {failedChecks.map((key) => (
            <li key={key} className="rounded-md bg-warning/20 px-2 py-0.5 text-xs font-medium">Not: {VERDICT_CHECK_LABELS[key]}</li>
          ))}
        </ul>
      )}
      {attempt.scene_contradictions && attempt.scene_contradictions.length > 0 && (
        <div className="text-xs">
          <p className="font-bold text-foreground/70">Contradicts the page</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {attempt.scene_contradictions.map((contradiction) => <li key={contradiction}>{contradiction}</li>)}
          </ul>
        </div>
      )}
      {attempt.vlm_verdict?.differences_observed && (
        <p className="text-xs text-foreground/70"><span className="font-bold">Judge notes:</span> {attempt.vlm_verdict.differences_observed}</p>
      )}
      {attempt.prompt && (
        <details className="text-xs">
          <summary className="inline-flex min-h-11 cursor-pointer items-center font-bold text-primary focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">Prompt</summary>
          <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-muted/30 p-2 font-mono">{attempt.prompt}</pre>
        </details>
      )}
    </li>
  );
}

export default function Pages({
  scenes,
  characters,
  objects,
}: {
  scenes: RunScene[];
  characters: RunCharacter[];
  objects: { obj_id: string; name: string }[];
}) {
  const characterNames = new Map(characters.map((character) => [character.char_id, character.name]));
  const objectNames = new Map(objects.map((object) => [object.obj_id, object.name]));

  return (
    <section id="pages" aria-labelledby="pages-heading" className="scroll-mt-6 space-y-4">
      <h2 id="pages-heading" className="font-display text-2xl font-bold">Pages</h2>
      {scenes.length === 0 && <p className="text-sm text-foreground/60">No pages were drawn.</p>}
      {scenes.map((scene, sceneIndex) => (
        <article
          key={scene.scene_id}
          aria-labelledby={`page-${sceneIndex + 1}`}
          className="grid grid-cols-1 gap-5 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]"
        >
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 id={`page-${sceneIndex + 1}`} className="font-display text-xl font-bold">Page {sceneIndex + 1}</h3>
              <SafetyBadge status={scene.moderation_status} label="Safety" />
            </div>
            <p className="text-base leading-relaxed">{scene.text_excerpt}</p>
            {scene.visual_direction && (
              <div>
                <h4 className="text-[11px] font-bold uppercase tracking-wider text-foreground/50">Drawing direction</h4>
                <p className="text-sm text-foreground/80">{scene.visual_direction}</p>
              </div>
            )}
            {scene.characters_present.length > 0 && (
              <p className="text-sm"><span className="font-bold">Cast:</span> {scene.characters_present.map((id) => characterNames.get(id) ?? id).join(", ")}</p>
            )}
            {scene.objects_present.length > 0 && (
              <p className="text-sm"><span className="font-bold">Objects:</span> {scene.objects_present.map((id) => objectNames.get(id) ?? id).join(", ")}</p>
            )}
            <p className="text-xs text-foreground/60">
              {scene.attempts.length} {scene.attempts.length === 1 ? "attempt" : "attempts"} · {scene.regeneration_count} redraws
            </p>
          </div>
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {scene.attempts.map((attempt, attemptIndex) => (
              <AttemptCard key={attemptIndex} attempt={attempt} page={sceneIndex + 1} index={attemptIndex} shipped={scene.shipped_attempt === attemptIndex} />
            ))}
          </ul>
        </article>
      ))}
    </section>
  );
}
