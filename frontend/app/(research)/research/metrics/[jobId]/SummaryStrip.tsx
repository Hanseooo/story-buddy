import { failureLabel, formatJob } from "@/utils/metrics";
import { formatDuration, totalDurationMs } from "./format";
import type { RunDetail } from "./types";

function Item({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
      <dt className="text-xs font-semibold uppercase tracking-widest text-foreground/50">{label}</dt>
      <dd className="font-display text-2xl font-bold">{value}</dd>
      {note && <dd className="text-xs text-foreground/50">{note}</dd>}
    </div>
  );
}

export default function SummaryStrip({ run }: { run: RunDetail }) {
  const { job } = run;
  const { scenesDisplay, costDisplay } = formatJob(job);

  return (
    <dl aria-label="Summary" className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <Item label="Pages passed" value={scenesDisplay} />
      <Item label="Redraws" value={String(job.regen_count ?? "—")} />
      <Item label="Reference retries" value={String(job.ref_retry_count ?? "—")} />
      <Item label="Cost" value={costDisplay} />
      <Item label="Total time" value={formatDuration(totalDurationMs(run.steps))} note="Includes time waiting for the child" />
      {job.status === "failed" && <Item label="Failure" value={job.failure_reason ? failureLabel(job.failure_reason) : "No reason recorded"} />}
    </dl>
  );
}
