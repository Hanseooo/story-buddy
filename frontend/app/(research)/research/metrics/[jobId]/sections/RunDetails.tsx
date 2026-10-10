import { formatDuration } from "../format";
import type { RunDetail } from "../types";

const TIME = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  timeZone: "UTC",
});

export default function RunDetails({ run }: { run: RunDetail }) {
  const versions = [...new Set(run.characters.flatMap((character) =>
    character.ref_verdict_prompt_version == null ? [] : [character.ref_verdict_prompt_version]
  ))];

  return (
    <section id="details" aria-labelledby="details-heading" className="scroll-mt-6 space-y-3">
      <h2 id="details-heading" className="font-display text-2xl font-bold">Run details</h2>
      <dl className="grid grid-cols-1 gap-3 rounded-2xl bg-surface p-4 text-sm neo-border sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Prompt versions</dt>
          <dd>{versions.length > 0 ? `Reference judge prompt v${versions.join(", v")}` : "None recorded for this run"}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Models</dt>
          <dd>Not recorded for this run</dd>
        </div>
      </dl>
      {run.steps.length > 0 && (
        <>
          <ul aria-label="Step timings" className="space-y-2 md:hidden">
            {run.steps.map((step, index) => (
              <li key={`${step.node}-${index}`} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 rounded-xl bg-surface p-3 text-sm neo-border">
                <span className="row-span-3 flex size-8 items-center justify-center rounded-lg bg-muted/50 font-mono text-xs">{index + 1}</span>
                <span className="font-semibold">{step.node}</span>
                <time className="text-xs text-foreground/60" dateTime={step.started_at}>{TIME.format(new Date(step.started_at))} UTC</time>
                <span className="text-xs font-mono text-foreground/70">{formatDuration(step.duration_ms)}</span>
              </li>
            ))}
          </ul>
          <div className="hidden overflow-x-auto rounded-2xl bg-surface neo-border md:block">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Every step the run took, in order</caption>
              <thead className="border-b border-muted bg-muted/20 text-xs font-semibold uppercase tracking-wider text-foreground/50">
                <tr>
                  <th scope="col" className="px-4 py-3">#</th>
                  <th scope="col" className="px-4 py-3">Step</th>
                  <th scope="col" className="px-4 py-3">Started (UTC)</th>
                  <th scope="col" className="px-4 py-3">Took</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-muted/40 font-mono text-xs">
                {run.steps.map((step, index) => (
                  <tr key={`${step.node}-${index}`}>
                    <td className="px-4 py-2">{index + 1}</td>
                    <th scope="row" className="px-4 py-2 font-medium">{step.node}</th>
                    <td className="px-4 py-2">{TIME.format(new Date(step.started_at))}</td>
                    <td className="px-4 py-2">{formatDuration(step.duration_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
